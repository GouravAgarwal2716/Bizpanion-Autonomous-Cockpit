"""
API Diagnostic Script for Featherless, Supabase, and Pinecone.
"""
import asyncio
import httpx
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import settings
from services.supabase_client import get_supabase


async def check_featherless():
    print("\n--- 1. Testing Featherless.ai ---")
    headers = {
        "Authorization": f"Bearer {settings.FEATHERLESS_API_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        # Check models endpoint
        r = await client.get(f"{settings.FEATHERLESS_BASE_URL}/models", headers=headers)
        print(f"Models endpoint status: {r.status_code}")
        if r.status_code == 200:
            models = r.json()
            model_ids = [m.get("id") for m in models.get("data", [])]
            print(f"✅ Featherless key is VALID. Available models count: {len(model_ids)}")
            
            # Test chat completion with first supported model
            test_models = ["meta-llama/Llama-3.3-70B-Instruct", "meta-llama/Llama-3.1-8B-Instruct", "Qwen/Qwen2.5-7B-Instruct", "mistralai/Mistral-7B-Instruct-v0.3"]
            working_model = None
            for tm in test_models:
                try:
                    chat_res = await client.post(
                        f"{settings.FEATHERLESS_BASE_URL}/chat/completions",
                        headers=headers,
                        json={"model": tm, "messages": [{"role": "user", "content": "Hello!"}], "max_tokens": 10},
                    )
                    if chat_res.status_code == 200:
                        print(f"✅ Chat completions working with model: {tm}")
                        working_model = tm
                        break
                    else:
                        print(f"Model {tm} status {chat_res.status_code}: {chat_res.text[:100]}")
                except Exception as ex:
                    print(f"Model {tm} error: {ex}")
        else:
            print(f"Featherless response: {r.text}")


async def check_supabase():
    print("\n--- 2. Testing Supabase Database ---")
    try:
        sb = get_supabase()
        # Query public market_prices or business_profile
        res = sb.table("business_profile").select("count", count="exact").execute()
        print(f"✅ Supabase connected successfully! Table query status: OK (rows: {res.count})")
    except Exception as e:
        print(f"⚠️ Supabase check notice: {e}")
        print("Note: If tables are not yet created, run backend/supabase/migrations/001_init.sql in Supabase SQL Editor.")


async def check_pinecone():
    print("\n--- 3. Testing Pinecone ---")
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        indexes = pc.list_indexes()
        names = [idx.name for idx in indexes]
        print(f"✅ Pinecone connected successfully! Existing indexes: {names}")
    except Exception as e:
        print(f"⚠️ Pinecone notice: {e}")


async def main():
    print("=" * 60)
    print("🔍 BIZPANION API CREDENTIALS VERIFICATION")
    print("=" * 60)
    await check_featherless()
    await check_supabase()
    await check_pinecone()
    print("\n" * 1 + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
