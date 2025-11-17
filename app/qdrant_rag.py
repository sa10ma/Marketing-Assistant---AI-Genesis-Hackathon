"""Qdrant RAG integration for Marketing assistant
- create collection
- embed text 
- put the data in qdrant
- search with filter by user id"""
import uuid
import google.generativeai as genai
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct,Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
from typing import Optional, Any,Dict
import json

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
    response=GenerativeModel('gemini-pro').generate_content(
        f"""
        Extract structured metadata from the user prompt .
        Output as json with keys: industry ,type ,topic ,tone.
        User prompt: {user_prompt}
    """
    )

    try:
        metadata=json.loads(response.text)
    except:
        metadata={
            "industry": None,
            "type": None,
            "topic": None,
            "tone": None
        }

    for key in ["industry","type","topic","tone"]:
        if not metadata.get(key) or metadata[key].lower() in ["unknown","none","n/a","not specified"]:  
            user_input=input(f"Please provide the {key} for your request: ")
            metadata[key]=user_input
    return metadata

def insert_data(user_id: int, text: str,url:Optional[str]=None,metadata:Optional[dict[str,Any]]=None):
    """Insert embedded data into Qdrant collection with user_id filter."""
    client = QdrantClient(host="qdrant", port=6333)
    
    if metadata is None:
        metadata = {}
    
    payload={
        "user_id": user_id,
        "text": text,
        "source_url": url or "",
        **metadata
    }

    embedding = embed_text(text)

    point = {"id": str(uuid.uuid4()),
        "vector": embedding,"payload":payload}
        
    client.upsert(
        collection_name="marketing_data",
        points=[point]
    )
    print(f"Data inserted for user_id: {user_id}")


def generate_retrieval_query(user_prompt: str):
    """Generate a retrieval queries based on user prompt."""
    response = genai.GenerativeModel("gemini-pro").generate_content(
    f"""
    Generate 5 short search queries that help retrieve:
    - product information
    - marketing strategies
    - industry insights
    - company description
    based on the following user prompt: {user_prompt}
    """
    )
    queries=response.text.strip().split("\n")
    return [query.strip("-. ").strip() for query in queries if query.strip()]

def retrieve_data(user_id: int,query: str, top_k: int = 5,metadata:Optional[dict]=None):
    """Retrieve data from Qdrant collection filtered by user_id and metadata."""
    client = QdrantClient(host="qdrant", port=6333)
    query_embedding = embed_text(query)

    must_conditions = [FieldCondition(key="user_id", match=MatchValue(value=user_id))]
    
    if metadata:
        for key in ["industry","type","topic","tone"]:
            if key in metadata and metadata[key]:
                must_conditions.append(FieldCondition(key=key, match=MatchValue(value=metadata[key])))

    search_result = client.search(
        collection_name="marketing_data",
        query_vector=query_embedding,
        limit=top_k,
        query_filter=Filter(must=must_conditions)
    )
    return [hit.payload for hit in search_result ]