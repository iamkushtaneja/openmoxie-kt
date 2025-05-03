import os
import aiohttp

DEEPGRAM_API_KEY = "c9b5e3e513c639354f50487f595c29441e6ce03a"
DEEPGRAM_API_URL = "https://api.deepgram.com/v1/listen"

async def transcribe_audio(audio_bytes, model="nova", language="en"):
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "audio/wav",
    }
    params = {
        "model": model,
        "language": language,
        "punctuate": "true",
        "interim_results": "false"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(DEEPGRAM_API_URL, headers=headers, params=params, data=audio_bytes) as resp:
            resp.raise_for_status()
            result = await resp.json()
            return result["results"]["channels"][0]["alternatives"][0]["transcript"] if result["results"]["channels"][0]["alternatives"] else ""
