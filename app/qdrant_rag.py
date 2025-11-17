"""Qdrant RAG integration for Marketing assistant
- create collection
- embed text 
- put the data in qdrant
- search with filter by user id"""
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct,Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
from typing import Optional, Any,Dict

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

def retrieve_data(user_id: int, query: str, top_k: int = 5):
    """Retrieve data from Qdrant collection filtered by user_id."""
    client = QdrantClient(host="qdrant", port=6333)
    query_embedding = embed_text(query)

    search_result = client.search(
    collection_name="marketing_data",
    query_vector=query_embedding,
    limit=top_k,
    query_filter=Filter(
        must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
    )
   
        )
    return [hit.payload for hit in search_result ]


insert_data(
            user_id=42,
            text="Test marketing content",
            url="https://example.com",
            metadata={"campaign": "launch"}
        )

results=retrieve_data(user_id=42, query="marketing")
print("Retrieved results:", results)
