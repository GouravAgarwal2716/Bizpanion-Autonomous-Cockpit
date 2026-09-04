"""
RAG Agent — Featherless Embeddings + Pinecone
Retrieves relevant government scheme information for a business query.
"""
import asyncio
from pinecone import Pinecone, ServerlessSpec
from services.featherless import get_embedding, get_embeddings_batch
from config import settings
import logging

logger = logging.getLogger(__name__)

_pinecone_index = None


def get_pinecone_index():
    global _pinecone_index
    if _pinecone_index is None:
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        # Create index if it doesn't exist
        existing = [idx.name for idx in pc.list_indexes()]
        if settings.PINECONE_INDEX_NAME not in existing:
            pc.create_index(
                name=settings.PINECONE_INDEX_NAME,
                dimension=4096,   # Qwen3-Embedding-8B output dim
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            logger.info(f"Created Pinecone index: {settings.PINECONE_INDEX_NAME}")
        _pinecone_index = pc.Index(settings.PINECONE_INDEX_NAME)
    return _pinecone_index


async def embed_and_upsert_documents(documents: list[dict]) -> int:
    """
    Embed and upsert scheme documents into Pinecone.
    Each document: {"id": str, "text": str, "metadata": dict}
    """
    index = get_pinecone_index()
    texts = [d["text"] for d in documents]
    embeddings = await get_embeddings_batch(texts)
    
    vectors = [
        {
            "id": doc["id"],
            "values": emb,
            "metadata": {**doc["metadata"], "text": doc["text"][:500]},
        }
        for doc, emb in zip(documents, embeddings)
    ]
    
    # Upsert in batches of 100
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        index.upsert(vectors=vectors[i:i+batch_size])
    
    return len(vectors)


async def query_schemes(
    query: str,
    business_type: str,
    region: str,
    top_k: int = 5,
) -> list[dict]:
    """
    Query Pinecone for relevant government schemes matching the business context.
    Returns list of matching scheme chunks with text and metadata.
    """
    index = get_pinecone_index()
    
    # Enrich query with context
    enriched_query = f"Business: {business_type}. Region: {region}. Query: {query}"
    query_embedding = await get_embedding(enriched_query)
    
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        filter={
            "$or": [
                {"business_type": {"$eq": business_type}},
                {"business_type": {"$eq": "all"}},
            ]
        } if business_type else {},
    )
    
    matches = []
    for match in results.matches:
        if match.score > 0.6:  # Only return confident matches
            matches.append({
                "scheme_name": match.metadata.get("scheme_name", "Unknown Scheme"),
                "scheme_text": match.metadata.get("text", ""),
                "eligibility": match.metadata.get("eligibility", ""),
                "benefit": match.metadata.get("benefit", ""),
                "deadline": match.metadata.get("deadline", ""),
                "apply_url": match.metadata.get("apply_url", ""),
                "score": match.score,
            })
    
    return matches


async def check_scheme_deadlines(
    business_type: str,
    region: str,
    days_window: int = 7,
) -> list[dict]:
    """
    Find schemes with deadlines within the next `days_window` days.
    """
    from datetime import datetime, timedelta
    
    all_schemes = await query_schemes(
        query=f"deadline application scheme subsidy loan",
        business_type=business_type,
        region=region,
        top_k=10,
    )
    
    urgent = []
    today = datetime.now().date()
    cutoff = today + timedelta(days=days_window)
    
    for scheme in all_schemes:
        deadline_str = scheme.get("deadline", "")
        if not deadline_str:
            continue
        try:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            if today <= deadline <= cutoff:
                scheme["days_remaining"] = (deadline - today).days
                urgent.append(scheme)
        except (ValueError, TypeError):
            continue
    
    return urgent
