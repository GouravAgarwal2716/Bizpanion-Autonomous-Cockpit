"""
Seed government scheme documents into Pinecone for RAG.
Run AFTER setting up Pinecone and Featherless.ai API keys in .env

Sources for real scheme PDFs:
  1. PM SVANidhi: https://pmsvanidhi.mohua.gov.in/
  2. PMEGP: https://www.kviconline.gov.in/pmegp/pmegpweb/docs/
  3. MUDRA: https://www.mudra.org.in/
  4. PM-KISAN: https://pmkisan.gov.in/
  5. NABARD schemes: https://www.nabard.org/

Run: python scripts/seed_schemes.py
"""
import asyncio
import sys
import os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.rag_agent import embed_and_upsert_documents


# ── Real government schemes for rural/small business entrepreneurs ─────────

SCHEME_DOCUMENTS = [
    # PM SVANidhi (Street Vendors Micro-credit)
    {
        "id": "pm-svanidhi-001",
        "text": """PM SVANidhi – PM Street Vendor's AtmaNirbhar Nidhi
Scheme for working capital loans to street vendors.
Loan Amount: ₹10,000 first loan, ₹20,000 second loan, ₹50,000 third loan.
Interest Subsidy: 7% interest subsidy on timely repayment.
Eligibility: Street vendors with Certificate of Vending / identity card issued by Urban Local Body.
Application: Apply at nearest bank branch or through PM SVANidhi Mobile App.
Apply URL: https://pmsvanidhi.mohua.gov.in/
Benefit: Working capital loan + credit score improvement + digital payment incentive ₹100/month.
Business types: vegetable_vendor, kirana_shop, food_processing, all""",
        "metadata": {
            "scheme_name": "PM SVANidhi",
            "eligibility": "Street vendors with ULB identification",
            "benefit": "₹10,000–₹50,000 micro-credit loan at 7% subsidy",
            "apply_url": "https://pmsvanidhi.mohua.gov.in/",
            "business_type": "all",
            "deadline": "",
        }
    },
    # PMEGP (Prime Minister's Employment Generation Programme)
    {
        "id": "pmegp-001",
        "text": """PMEGP – Prime Minister's Employment Generation Programme
Subsidy scheme for setting up micro-enterprises in non-farm sector.
Subsidy: 15% to 35% of project cost (higher for SC/ST/Women/OBC).
Project Cost: Manufacturing up to ₹50 lakh, Service sector up to ₹20 lakh.
Eligibility: Any Indian citizen 18+ years. For projects above ₹10 lakh in manufacturing / ₹5 lakh in service: minimum VIII standard pass.
Application: Apply through KVIC/State Khadi Board/DIC online portal.
Apply URL: https://www.kviconline.gov.in/pmegpweb/
Deadline: Rolling applications, financial year quota applies — apply before March 31.
Business types: handicraft, textile, food_processing, dairy_farmer, other""",
        "metadata": {
            "scheme_name": "PMEGP",
            "eligibility": "Any Indian citizen 18+, non-farm sector business",
            "benefit": "15–35% subsidy on project cost up to ₹50 lakh",
            "apply_url": "https://www.kviconline.gov.in/pmegpweb/",
            "business_type": "food_processing",
            "deadline": "2026-03-31",
        }
    },
    # MUDRA Loan – Shishu
    {
        "id": "mudra-shishu-001",
        "text": """MUDRA Loan – Pradhan Mantri MUDRA Yojana (Shishu category)
Collateral-free loans for small businesses and micro-enterprises.
Shishu: Up to ₹50,000 for businesses just starting or needing small capital.
Kishor: ₹50,001 to ₹5 lakh for established businesses requiring growth capital.
Tarun: ₹5 lakh to ₹10 lakh for larger expansion needs.
Eligibility: Non-corporate, non-farm small/micro enterprises. No collateral required for Shishu.
Apply at: Any public/private sector bank, MFI, NBFC, or online at mudra.org.in.
Apply URL: https://www.mudra.org.in/
Business types: vegetable_vendor, kirana_shop, grocery_store, handicraft, all""",
        "metadata": {
            "scheme_name": "PM MUDRA Yojana (Shishu)",
            "eligibility": "Non-farm micro/small enterprises, no collateral needed",
            "benefit": "Collateral-free loan up to ₹50,000 (Shishu) / ₹10 lakh (Tarun)",
            "apply_url": "https://www.mudra.org.in/",
            "business_type": "all",
            "deadline": "",
        }
    },
    # PM-KISAN
    {
        "id": "pmkisan-001",
        "text": """PM-KISAN – Pradhan Mantri Kisan Samman Nidhi
Direct income support to farmer families owning cultivable land.
Benefit: ₹6,000 per year in 3 installments of ₹2,000 each, directly to bank account.
Eligibility: All farmer families with cultivable land, subject to exclusion criteria.
Exclusion: Constitutional position holders, current/former MPs/MLAs, government service holders, income tax payers.
Application: Apply at nearest Common Service Centre or State/UT agriculture department.
Apply URL: https://pmkisan.gov.in/
Installment months: April, August, December.
Business types: dairy_farmer, vegetable_vendor""",
        "metadata": {
            "scheme_name": "PM-KISAN",
            "eligibility": "Farmer families owning cultivable land",
            "benefit": "₹6,000/year direct bank transfer in 3 installments",
            "apply_url": "https://pmkisan.gov.in/",
            "business_type": "dairy_farmer",
            "deadline": "",
        }
    },
    # Stand Up India
    {
        "id": "standup-india-001",
        "text": """Stand Up India Scheme
Bank loans between ₹10 lakh and ₹1 crore for SC/ST and women entrepreneurs.
For setting up greenfield enterprise in manufacturing, services, agri-allied activities, or trading sector.
Eligibility: SC or ST borrower, or woman entrepreneur. First-time borrower.
Loan: ₹10 lakh to ₹1 crore composite loan (working capital + term loan).
Apply URL: https://www.standupmitra.in/
Deadline: Scheme ongoing. Apply before financial year end March 31.
Business types: textile, food_processing, handicraft, grocery_store""",
        "metadata": {
            "scheme_name": "Stand Up India",
            "eligibility": "SC/ST or Women entrepreneurs, first-time borrower",
            "benefit": "₹10 lakh to ₹1 crore loan for greenfield enterprise",
            "apply_url": "https://www.standupmitra.in/",
            "business_type": "handicraft",
            "deadline": "2026-03-31",
        }
    },
    # NABARD Kisan Credit Card
    {
        "id": "kcc-001",
        "text": """Kisan Credit Card (KCC) – NABARD/RBI Scheme
Credit card for farmers to meet short-term credit needs for cultivation.
Limit: Based on cultivated land and scale of finance. Typically ₹1.6 lakh to ₹3 lakh.
Interest: 4% p.a. for loans up to ₹3 lakh with timely repayment (9% base - 5% subvention).
Eligibility: Farmers (owner, tenant, oral lessee), sharecroppers, SHG/JLG farmers.
Also covers: post-harvest expenses, produce marketing loans, allied activities like dairy, fishery.
Apply URL: https://www.nabard.org/
Business types: dairy_farmer, vegetable_vendor""",
        "metadata": {
            "scheme_name": "Kisan Credit Card",
            "eligibility": "Farmers, sharecroppers, SHG members",
            "benefit": "Short-term credit at 4% interest, up to ₹3 lakh",
            "apply_url": "https://www.nabard.org/",
            "business_type": "dairy_farmer",
            "deadline": "",
        }
    },
    # One District One Product (ODOP)
    {
        "id": "odop-001",
        "text": """One District One Product (ODOP) – MSME Ministry
Promotes unique/specialty products of each district.
Support includes: Marketing assistance, technology upgradation, credit linkage, packaging support.
Eligibility: MSMEs and artisans producing the notified ODOP product of their district.
Benefits: Subsidized exhibition participation, e-commerce platform listing on GeM, packaging development support.
Apply URL: https://www.india.gov.in/spotlight/one-district-one-product
Business types: handicraft, textile, food_processing""",
        "metadata": {
            "scheme_name": "One District One Product (ODOP)",
            "eligibility": "MSMEs and artisans producing district's notified product",
            "benefit": "Marketing, packaging, technology, and credit support",
            "apply_url": "https://www.india.gov.in/spotlight/one-district-one-product",
            "business_type": "handicraft",
            "deadline": "",
        }
    },
    # Agri Infrastructure Fund
    {
        "id": "aif-001",
        "text": """Agriculture Infrastructure Fund (AIF)
Medium-long term debt financing for post-harvest management and community farming assets.
Loan Amount: Up to ₹2 crore per project.
Interest Subvention: 3% interest subvention for 7 years.
Credit Guarantee: Coverage under CGTMSE for loans up to ₹2 crore.
Eligible Projects: Warehousing, cold chain, processing units, sorting/grading units, e-marketing platforms.
Eligibility: Farmers, FPOs, PACS, Marketing Cooperative Societies, SHGs, Joint Liability Groups.
Apply URL: https://agriinfra.dac.gov.in/
Deadline: Scheme open until 2025-26, apply before March 31, 2026.
Business types: dairy_farmer, food_processing, vegetable_vendor""",
        "metadata": {
            "scheme_name": "Agriculture Infrastructure Fund",
            "eligibility": "Farmers, FPOs, SHGs for post-harvest infrastructure",
            "benefit": "3% interest subvention on loans up to ₹2 crore",
            "apply_url": "https://agriinfra.dac.gov.in/",
            "business_type": "dairy_farmer",
            "deadline": "2026-03-31",
        }
    },
]


async def seed():
    print(f"Embedding and uploading {len(SCHEME_DOCUMENTS)} scheme documents to Pinecone...")
    count = await embed_and_upsert_documents(SCHEME_DOCUMENTS)
    print(f"✅ Seeded {count} scheme document chunks into Pinecone")
    print("\nTest query:")
    from agents.rag_agent import query_schemes
    results = await query_schemes("vegetable vendor loan", "vegetable_vendor", "Maharashtra", top_k=3)
    for r in results:
        print(f"  - {r['scheme_name']} (score: {r['score']:.3f}): {r['benefit']}")


if __name__ == "__main__":
    asyncio.run(seed())
