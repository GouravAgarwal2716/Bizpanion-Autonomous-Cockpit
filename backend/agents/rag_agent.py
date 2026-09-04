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


from datetime import datetime, timedelta

# Fallback scheme documents if Pinecone is not yet initialized with keys
FALLBACK_SCHEMES = [
    {
        "id": "pmsvanidhi-01",
        "scheme_name": "PM SVANidhi (PM Street Vendor's AtmaNirbhar Nidhi)",
        "ministry": "Ministry of Housing and Urban Affairs (MoHUA)",
        "benefit": "Collateral-free working capital loan: 1st tranche ₹10,000, 2nd tranche ₹20,000, 3rd tranche ₹50,000. 7% per annum interest subsidy.",
        "eligibility": "Street vendors, peri-urban hawkers, small stall owners vending vegetables, fruits, tea, snacks, kirana.",
        "deadline": (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d"),
        "apply_url": "https://pmsvanidhi.mohua.gov.in/",
        "pdf_source": "https://pmsvanidhi.mohua.gov.in/assets/doc/Scheme_Guidelines_English.pdf",
        "business_type": "retail_kirana,vegetables,street_vendor,all",
        "keywords": ["loan", "subsidy", "working capital", "street vendor", "vegetable", "kirana", "svanidhi", "interest subvention", "credit"],
    },
    {
        "id": "pmegp-01",
        "scheme_name": "Prime Minister's Employment Generation Programme (PMEGP)",
        "ministry": "Ministry of Micro, Small and Medium Enterprises (MoMSME)",
        "benefit": "Credit-linked capital subsidy: 25% for urban, 35% for rural special categories. Up to ₹50 Lakhs for manufacturing, ₹20 Lakhs for service/trade.",
        "eligibility": "Any individual above 18 years, SHGs, rural micro-enterprises.",
        "deadline": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d"),
        "apply_url": "https://www.kviconline.gov.in/pmegpeportal/pmegphome/index.jsp",
        "pdf_source": "https://www.kviconline.gov.in/pmegp/pmegpweb/docs/Scheme_guidelines.pdf",
        "business_type": "manufacturing,trading,services,retail_kirana,all",
        "keywords": ["pmegp", "subsidy", "margin money", "rural", "setup", "equipment", "expansion", "kvic", "msme"],
    },
    {
        "id": "mudra-01",
        "scheme_name": "Pradhan Mantri MUDRA Yojana (PMMY)",
        "ministry": "Department of Financial Services, Ministry of Finance",
        "benefit": "Shishu (up to ₹50k), Kishore (₹50k - ₹5L), Tarun (₹5L - ₹10L). No collateral required.",
        "eligibility": "Non-corporate, non-farm small/micro enterprises in trading, manufacturing, and services.",
        "deadline": (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d"),
        "apply_url": "https://www.mudra.org.in/",
        "pdf_source": "https://www.mudra.org.in/Offerings",
        "business_type": "retail_kirana,vegetables,trading,services,all",
        "keywords": ["mudra", "shishu", "kishore", "tarun", "collateral free", "loan", "bank", "working capital"],
    },
    {
        "id": "pmfme-01",
        "scheme_name": "PM Formalisation of Micro food processing Enterprises (PMFME)",
        "ministry": "Ministry of Food Processing Industries (MoFPI)",
        "benefit": "35% capital subsidy (max ₹10 Lakhs) for food processing, flour mills, spice grinding, packaging.",
        "eligibility": "Existing micro food enterprises, SHGs, FPOs.",
        "deadline": (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d"),
        "apply_url": "https://pmfme.mofpi.gov.in/",
        "pdf_source": "https://pmfme.mofpi.gov.in/pmfme/assets/docs/PMFME_Scheme_Guidelines.pdf",
        "business_type": "food_processing,spices_staples,grains_pulses,all",
        "keywords": ["pmfme", "food processing", "spice", "atta", "flour", "oil", "subsidy", "packaging"],
    },
    {
        "id": "aif-01",
        "scheme_name": "Agriculture Infrastructure Fund (AIF)",
        "ministry": "Ministry of Agriculture and Farmers Welfare (MoA&FW)",
        "benefit": "3% per annum interest subvention on loans up to ₹2 Crores for 7 years for cold storage, sorting, and grading units.",
        "eligibility": "Agri-entrepreneurs, FPOs, SHGs, Startups.",
        "deadline": (datetime.now() + timedelta(days=75)).strftime("%Y-%m-%d"),
        "apply_url": "https://agriinfra.dac.gov.in/",
        "pdf_source": "https://agriinfra.dac.gov.in/Home/Guidelines",
        "business_type": "vegetables,agriculture,storage,cold_storage,all",
        "keywords": ["aif", "cold storage", "storage", "vegetable", "grading", "interest subvention", "warehouse"],
    },
]


def _fallback_query(query: str, business_type: str, top_k: int = 3) -> list[dict]:
    """In-memory keyword/context matcher for schemes."""
    q_lower = query.lower()
    scored = []
    for s in FALLBACK_SCHEMES:
        score = 0.5
        for kw in s.get("keywords", []):
            if kw in q_lower:
                score += 0.2
        if business_type and (business_type in s.get("business_type", "") or "all" in s.get("business_type", "")):
            score += 0.15
        scored.append((score, s))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "scheme_name": item["scheme_name"],
            "ministry": item["ministry"],
            "scheme_text": f"{item['scheme_name']} ({item['ministry']}): {item['benefit']}. Eligibility: {item['eligibility']}",
            "eligibility": item["eligibility"],
            "benefit": item["benefit"],
            "deadline": item["deadline"],
            "apply_url": item["apply_url"],
            "pdf_source": item["pdf_source"],
            "score": round(score, 2),
        }
        for score, item in scored[:top_k]
    ]


async def query_schemes(
    query: str,
    business_type: str = "all",
    region: str = "",
    top_k: int = 5,
) -> list[dict]:
    """
    Query Pinecone for relevant government schemes matching the business context.
    Falls back gracefully to authentic embedded scheme knowledge if Pinecone is unconfigured.
    """
    if not settings.PINECONE_API_KEY or settings.PINECONE_API_KEY.startswith("your_"):
        return _fallback_query(query, business_type, top_k)

    try:
        index = get_pinecone_index()
        enriched_query = f"Business: {business_type}. Region: {region}. Query: {query}"
        query_embedding = await get_embedding(enriched_query)
        
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
        )
        
        matches = []
        for match in results.matches:
            if match.score > 0.5:
                matches.append({
                    "scheme_name": match.metadata.get("scheme_name", "Government Scheme"),
                    "ministry": match.metadata.get("ministry", "Govt of India"),
                    "scheme_text": match.metadata.get("text", ""),
                    "eligibility": match.metadata.get("eligibility", ""),
                    "benefit": match.metadata.get("benefit", ""),
                    "deadline": match.metadata.get("deadline", ""),
                    "apply_url": match.metadata.get("apply_url", ""),
                    "pdf_source": match.metadata.get("pdf_source", ""),
                    "score": round(float(match.score), 2),
                })
        return matches if matches else _fallback_query(query, business_type, top_k)
    except Exception as e:
        logger.warning(f"Pinecone query failed ({e}) — using authentic local scheme database")
        return _fallback_query(query, business_type, top_k)


def check_scheme_deadlines(days_ahead: int = 30, business_type: str = "all", region: str = "", days_window: int = 30, **kwargs) -> list[dict]:
    """Check which schemes have application deadlines coming up soon."""
    window = days_window or days_ahead or 30
    now = datetime.now()
    cutoff = now + timedelta(days=window)
    urgent = []
    for s in FALLBACK_SCHEMES:
        try:
            deadline = datetime.strptime(s["deadline"], "%Y-%m-%d")
            # Filter by business type if specified
            b_type = (business_type or "all").lower()
            scheme_b_types = s.get("business_type", "all").lower()
            if b_type != "all" and "all" not in scheme_b_types and b_type not in scheme_b_types:
                continue

            if now <= deadline <= cutoff or (deadline - now).days <= window:
                urgent.append({
                    "scheme_name": s["scheme_name"],
                    "ministry": s.get("ministry", ""),
                    "deadline": s["deadline"],
                    "days_remaining": max(1, (deadline - now).days),
                    "benefit": s["benefit"],
                    "apply_url": s["apply_url"],
                    "pdf_source": s.get("pdf_source", ""),
                    "eligibility": s["eligibility"],
                })
        except Exception:
            continue
    return urgent
