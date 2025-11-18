"""Qdrant RAG integration for Marketing assistant
- create collection
- embed text 
- put the data in qdrant
- search with filter by user id"""
import uuid
from langchain_google_genai import ChatGoogleGenerativeAI
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct,Filter, FieldCondition, MatchValue, MatchAny
from sentence_transformers import SentenceTransformer
from typing import Optional, Any,Dict, List
import json
import os

CORE_PROFILE_TYPES = [
    "Company Name",
    "Product Description",
    "Target Audience",
    "Tone of Voice",
]

def create_qdrant_collection():
    """Create a Qdrant collection for storing marketing data."""
    client = QdrantClient(host="qdrant", port=6333)
    client.recreate_collection(
        collection_name="marketing_data",
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    )
    print("Qdrant collection created successfully.")

model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

def embed_text(text: str):
    "Embed text using SentenceTransformer model."
    return model.encode(text, convert_to_numpy=True)

def extract_metadata(user_prompt: str):
    """Extracts metadata from user prompt and asks for missing or unclear data 
    returns a dictionary"""
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        api_key=os.getenv("GEMINI_API_KEY")
    )

    prompt=f"""
        Extract structured metadata from the user prompt .
        Output as json with keys: industry ,type ,topic ,tone.
        User prompt: {user_prompt}
    """
    response = llm.invoke(prompt).content

    try:
        metadata=json.loads(response)
    except:
        metadata={
            "industry": None,
            "type": None,
            "topic": None,
            "tone": None
        }

    for key in ["industry","type","topic","tone"]:
        if not metadata.get(key):  
            user_input=input(f"Please provide the {key} for your request: ")
            metadata[key]=user_input
    return metadata

def insert_data(user_id: int, data: Dict[str, str], metadata: Optional[Dict[str, Any]] = None):
    """
    Inserts data (e.g., business profile chunks or research results) into Qdrant.
    It takes a dictionary of {title: content_text} and creates multiple points, 
    using the 'title' as the chunk's 'type' in the payload.
    
    Args:
        user_id: ID of the user owning the data.
        data: Dictionary where keys are chunk titles (e.g., 'Target Audience')
                      and values are the text content.
        metadata: Optional dictionary of generic metadata to apply to all chunks 
                  (e.g., date_added, source).
    """
    client = QdrantClient(host="qdrant", port=6333)
    points_to_insert: List[PointStruct] = []
    
    if metadata is None:
        metadata = {}
    
    # Pre-process general metadata (applied to all chunks)
    metadata_safe = {k: str(v) if not isinstance(v, (str, int, float, bool, list, dict)) else v 
                     for k, v in metadata.items()}

    # Iterate over the provided profile data to create multiple points
    for title, text_content in data.items():
        if not text_content:
            continue # Skip empty data

        # 1. Embed the content
        embedding = embed_text(text_content).tolist() 

        # 2. Construct the chunk-specific payload
        payload = {
            "user_id": user_id,
            "text": text_content,       # The actual content to be retrieved
            "type": title,              # The descriptive title/field name (e.g., "Target Audience")
            **metadata_safe             # Other generic metadata
        }

        # 3. Create the Qdrant PointStruct
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload=payload
        )
        points_to_insert.append(point)

    # Perform batch upsert
    if points_to_insert:
        client.upsert(
            collection_name="marketing_data",
            points=points_to_insert,
            wait=True # Wait for the operation to complete for reliable testing
        )
        print(f"Batch data inserted: {len(points_to_insert)} chunks for user_id: {user_id}")
    else:
        print("No data provided to insert.")


def insert_qa(user_id: int, question: str, answer: str, metadata: dict):
    client = QdrantClient(host="qdrant", port=6333)

    embedding = embed_text(question).tolist()

    payload = {
        "user_id": user_id,
        "question": question,
        "answer": answer,
        "type": "research_qna",
        **metadata
    }

    client.upsert(
        collection_name="marketing_data",
        points=[
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=payload
            )
        ],
        wait=True
    )

def retrieve_data(user_id: int, query: str, top_k: int = 5):
    """
    Retrieve data using a two-pronged approach: 
    1. Guaranteed retrieval of core profile data (via filters).
    2. Contextual retrieval of relevant research data (via vector search).
    """
    client = QdrantClient(host="qdrant", port=6333)
    query_embedding = embed_text(query).tolist()
    
    all_retrieved_payloads = []

    # --- PRONG 1: GUARANTEED CORE PROFILE RETRIEVAL (NON-SEMANTIC) ---
    profile_filter = Filter(
        must=[
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            FieldCondition(key="type", match=MatchAny(any=CORE_PROFILE_TYPES))
        ]
    )
    
    # Use the client.scroll method for guaranteed retrieval without a vector
    profile_results, _ = client.scroll(
        collection_name="marketing_data",
        scroll_filter=profile_filter,
        limit=len(CORE_PROFILE_TYPES) * 2, 
        with_payload=True,
    )
    
    all_retrieved_payloads.extend([hit.payload for hit in profile_results])

    # --- PRONG 2: CONTEXTUAL RESEARCH RETRIEVAL (SEMANTIC SEARCH) ---
    # Goal: Retrieve the most relevant market research/campaign data based on the query.
    
    # Must: Filter by user_id
    must_conditions = [
        FieldCondition(key="user_id", match=MatchValue(value=user_id))
    ]
    
    # MustNot: Exclude the core profile types already retrieved
    must_not_conditions = [
        FieldCondition(key="type", match=MatchAny(any=CORE_PROFILE_TYPES))
    ]
    
    search_filter = Filter(
        must=must_conditions,
        must_not=must_not_conditions
    )

    search_result = client.query_points(
        collection_name= "marketing_data",
        query=query_embedding,
        limit=top_k, 
        query_filter=search_filter,
        with_payload=True 
    )

    # Combine and deduplicate the results
    retrieved_payloads = [point.payload for point in search_result.points]

    return retrieved_payloads




