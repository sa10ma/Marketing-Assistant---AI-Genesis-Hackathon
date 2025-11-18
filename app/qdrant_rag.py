"""Qdrant RAG integration for Marketing assistant
- create collection
- embed text 
- put the data in qdrant
- search with filter by user id"""
import uuid
from langchain_google_genai import ChatGoogleGenerativeAI
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct,Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
from typing import Optional, Any,Dict
import json
import os

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

def insert_data(user_id: int, text: str, url: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
    """Insert embedded data into Qdrant collection with user_id filter."""
    client = QdrantClient(host="qdrant", port=6333)
    
    if metadata is None:
        metadata = {}
    
    # Make metadata JSON-serializable
    metadata_safe = {k: str(v) if not isinstance(v, (str, int, float, bool, list, dict)) else v 
                     for k, v in metadata.items()}
    
    payload = {
        "user_id": user_id,
        "text": text,
        "source_url": url or "",
        **metadata_safe
    }

    embedding = embed_text(text).tolist()  # <-- important: convert NumPy array to list

    point = {
        "id": str(uuid.uuid4()),
        "vector": embedding,
        "payload": payload
    }
    
    client.upsert(
        collection_name="marketing_data",
        points=[point]
    )
    print(f"Data inserted for user_id: {user_id}")


def retrieve_data(user_id: int, query: str, top_k: int = 5, metadata: Optional[dict] = None):
    """Retrieve data from Qdrant collection filtered by user_id and metadata."""
    client = QdrantClient(host="qdrant", port=6333)
    query_embedding = embed_text(query).tolist()  # ensure it's a list

    must_conditions = [
        FieldCondition(key="user_id", match=MatchValue(value=user_id))
    ]
    
    if metadata:
        for key in ["industry", "type", "topic", "tone"]:
            if key in metadata and metadata[key]:
                must_conditions.append(FieldCondition(key=key, match=MatchValue(value=metadata[key])))

    # Use query_points instead of search
    search_result = client.search_points(
        collection_name="marketing_data",
        query_vector=query_embedding,
        top=top_k,
        filter=Filter(must=must_conditions)
    )

    return [hit.payload for hit in search_result]


# from qdrant_client import QdrantClient


# qdrant = QdrantClient(
#     host="qdrant",
#     port=6333
# )


# from qdrant_client.http.models import Filter, FieldCondition, MatchValue

# def search_knowledge(user_id: int, query: str, top_k: int = 5):
#     """
#     Searches Qdrant using vector similarity.
#     Works with SentenceTransformer embeddings.
#     """
#     # 1️⃣ Embed the query
#     query_vector = embed_text(query).tolist()

#     # 2️⃣ Build user filter
#     user_filter = Filter(
#         must=[
#             FieldCondition(key="user_id", match=MatchValue(value=user_id))
#         ]
#     )

#     # 3️⃣ Query Qdrant using vector
#     results = qdrant.query_points(
#         collection_name="marketing_data",
#         vector=query_vector,
#         limit=top_k,
#         query_filter=user_filter
#     )

#     return results.points




