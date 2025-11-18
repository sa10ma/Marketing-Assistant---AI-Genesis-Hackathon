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


EMBED_CACHE = {}


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

def insert_data(user_id: int, data: Dict[str, str], type: str):
    """
    Inserts all profile data for a user into Qdrant as a single point.
    
    Args:
        user_id: ID of the user owning the data.
        data: Dictionary where keys are field titles (e.g., 'Target Audience') 
              and values are the text content.
    """
    print(f"\n hi from insert data function called by {type}")

    client = QdrantClient(host="qdrant", port=6333)


    # Combine all profile fields into a single text block for embedding
    combined_text = "\n".join(f"{k}: {v}" for k, v in data.items() if v)

    if not combined_text:
        print("No data provided to insert.")
        return

    # Generate embedding for the combined text
    embedding = embed_cached(combined_text)

    # Construct payload
    payload = {
        "user_id": user_id,
        "type": type
    }

    # Create and upsert the point
    point = PointStruct(
        id=str(uuid.uuid4()),
        vector=embedding,
        payload=payload
    )

    client.upsert(
        collection_name="marketing_data",
        points=[point],
        wait=True
    )

    print(f"Inserted single combined profile point for user_id: {user_id}")


def retrieve_data(user_id: int, query: str, top_k: int = 5):
    """
    Retrieve data using a two-pronged approach: 
    1. Guaranteed retrieval of core profile data (via filters).
    2. Contextual retrieval of relevant research data (via vector search).
    """

    print("\n hi from retrieve function")
    client = QdrantClient(host="qdrant", port=6333)
    query_embedding = embed_text(query).tolist()
    
    all_retrieved_payloads = []

    # --- PRONG 1: GUARANTEED CORE PROFILE RETRIEVAL (NON-SEMANTIC) ---
    profile_filter = Filter(
        must=[
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            FieldCondition(key="type", match=MatchAny(any=["profile_core"]))
        ]
    )
    
    # Use the client.scroll method for guaranteed retrieval without a vector
    profile_results, _ = client.scroll(
        collection_name="marketing_data",
        scroll_filter=profile_filter,
        limit=top_k, 
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
        FieldCondition(key="type", match=MatchAny(any=["profile_core"]))
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
    all_retrieved_payloads.extend([point.payload for point in search_result.points])
    
    return all_retrieved_payloads


def embed_cached(text: str):
    if text in EMBED_CACHE:
        return EMBED_CACHE[text]
    emb = embed_text(text).tolist()
    EMBED_CACHE[text] = emb
    return emb



