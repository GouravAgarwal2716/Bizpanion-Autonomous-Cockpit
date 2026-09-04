"""
Featherless.ai service — LLM, Embeddings, and TTS.
All three use the same OpenAI-compatible base URL.
"""
import httpx
import asyncio
import base64
import os
from pathlib import Path
from config import settings
from models.schemas import Language

# Language name map for TTS voice selection
LANGUAGE_VOICE_MAP = {
    Language.ENGLISH: {"voice": "af_sky", "lang_code": "en-us"},
    Language.HINDI:   {"voice": "hf_alpha", "lang_code": "hi"},
    Language.TAMIL:   {"voice": "hf_beta", "lang_code": "ta"},
    Language.TELUGU:  {"voice": "hf_beta", "lang_code": "te"},
    Language.KANNADA: {"voice": "hf_beta", "lang_code": "kn"},
    Language.MARATHI: {"voice": "hf_alpha", "lang_code": "mr"},
    Language.BENGALI: {"voice": "hf_beta", "lang_code": "bn"},
    Language.GUJARATI:{"voice": "hf_beta", "lang_code": "gu"},
}

# System prompt for multilingual advisor
LANGUAGE_SYSTEM_PROMPTS = {
    Language.ENGLISH: "You are a helpful business advisor for rural entrepreneurs in India. Always respond in clear, simple English. Be concise and action-oriented.",
    Language.HINDI:   "आप भारत के ग्रामीण उद्यमियों के लिए एक उपयोगी व्यापार सलाहकार हैं। हमेशा सरल हिंदी में जवाब दें। संक्षिप्त और कार्य-उन्मुख रहें।",
    Language.TAMIL:   "நீங்கள் இந்தியாவின் கிராமப்புற தொழில்முனைவோருக்கான உதவிகரமான வணிக ஆலோசகர். எப்போதும் எளிய தமிழில் பதிலளிக்கவும். சுருக்கமாகவும் செயல் சார்ந்தும் இருங்கள்.",
    Language.TELUGU:  "మీరు భారతదేశంలోని గ్రామీణ వ్యవస్థాపకులకు సహాయకరమైన వ్యాపార సలహాదారు. ఎల్లప్పుడూ సరళమైన తెలుగులో స్పందించండి. సంక్షిప్తంగా మరియు చర్య-ఆధారితంగా ఉండండి.",
    Language.KANNADA: "ನೀವು ಭಾರತದ ಗ್ರಾಮೀಣ ಉದ್ಯಮಿಗಳಿಗಾಗಿ ಸಹಾಯಕ ವ್ಯಾಪಾರ ಸಲಹೆಗಾರ. ಯಾವಾಗಲೂ ಸರಳ ಕನ್ನಡದಲ್ಲಿ ಪ್ರತಿಕ್ರಿಯಿಸಿ.",
}


async def call_llm(
    prompt: str,
    language: Language = Language.ENGLISH,
    system_override: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 512,
) -> str:
    """Call Featherless LLM and return the text response."""
    system = system_override or LANGUAGE_SYSTEM_PROMPTS.get(language, LANGUAGE_SYSTEM_PROMPTS[Language.ENGLISH])
    
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{settings.FEATHERLESS_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.FEATHERLESS_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.FEATHERLESS_LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


async def get_embedding(text: str) -> list[float]:
    """Get embedding vector for a text string via Featherless."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{settings.FEATHERLESS_BASE_URL}/embeddings",
            headers={
                "Authorization": f"Bearer {settings.FEATHERLESS_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.FEATHERLESS_EMBEDDING_MODEL,
                "input": text,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Get embeddings for multiple texts."""
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{settings.FEATHERLESS_BASE_URL}/embeddings",
            headers={
                "Authorization": f"Bearer {settings.FEATHERLESS_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.FEATHERLESS_EMBEDDING_MODEL,
                "input": texts,
            },
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]


import logging

logger = logging.getLogger(__name__)


async def text_to_speech(
    text: str,
    language: Language,
    cache_key: str | None = None,
) -> str:
    """
    Convert text to speech via Featherless TTS with automatic offline gTTS fallback.
    Returns local file path (which is served as /audio/<filename>).
    Caches by cache_key to avoid re-generating on every request.
    """
    cache_dir = Path(settings.AUDIO_CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)

    safe_key = cache_key or f"audio_{abs(hash(text[:60]))}"
    mp3_filename = f"{safe_key}.mp3"
    wav_filename = f"{safe_key}.wav"

    cached_mp3 = cache_dir / mp3_filename
    cached_wav = cache_dir / wav_filename

    if cached_mp3.exists() and cached_mp3.stat().st_size > 0:
        return f"/audio/{mp3_filename}"
    if cached_wav.exists() and cached_wav.stat().st_size > 0:
        return f"/audio/{wav_filename}"

    # 1. Try Featherless TTS if configured
    if settings.FEATHERLESS_API_KEY and not settings.FEATHERLESS_API_KEY.startswith("your_"):
        voice_config = LANGUAGE_VOICE_MAP.get(language, LANGUAGE_VOICE_MAP[Language.ENGLISH])
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{settings.FEATHERLESS_BASE_URL}/audio/speech",
                    headers={
                        "Authorization": f"Bearer {settings.FEATHERLESS_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.FEATHERLESS_TTS_MODEL,
                        "input": text,
                        "voice": voice_config["voice"],
                        "response_format": "mp3",
                    },
                )
                if response.status_code == 200 and len(response.content) > 0:
                    with open(cached_mp3, "wb") as f:
                        f.write(response.content)
                    return f"/audio/{mp3_filename}"
                else:
                    logger.warning(f"Featherless TTS returned HTTP {response.status_code} ({response.text[:120]}), activating gTTS fallback.")
        except Exception as e:
            logger.warning(f"Featherless TTS call failed ({e}), activating gTTS fallback.")

    # 2. Resilient gTTS Fallback
    try:
        lang_code = language.value if isinstance(language, Language) else str(language)
        # Verify valid gtts lang code, default to 'en'
        supported_gtts = {"en", "hi", "ta", "te", "kn", "mr", "bn", "gu"}
        if lang_code not in supported_gtts:
            lang_code = "en"

        def _generate_gtts():
            from gtts import gTTS
            tts = gTTS(text=text, lang=lang_code, slow=False)
            tts.save(str(cached_mp3))

        await asyncio.to_thread(_generate_gtts)
        return f"/audio/{mp3_filename}"
    except Exception as gtts_err:
        logger.error(f"gTTS audio generation error: {gtts_err}")
        return ""

