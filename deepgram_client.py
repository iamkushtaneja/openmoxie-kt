import os
import aiohttp
import asyncio
import websockets
import json

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "c9b5e3e513c639354f50487f595c29441e6ce03a")
DEEPGRAM_API_URL = "https://api.deepgram.com/v1/listen"
DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen"

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

# Streaming transcription generator for partial/final results
async def stream_transcribe(audio_chunk_iter, model="nova", language="en"):
    url = f"{DEEPGRAM_WS_URL}?model={model}&language={language}&punctuate=true&interim_results=true"
    async with websockets.connect(
        url,
        extra_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"}
    ) as ws:
        async def send_audio():
            async for chunk in audio_chunk_iter:
                await ws.send(chunk)
            await ws.send(json.dumps({"type": "end"}))
        send_task = asyncio.create_task(send_audio())
        async for message in ws:
            data = json.loads(message)
            if "results" in data and data["results"].get("channels"):
                alt = data["results"]["channels"][0]["alternatives"][0]
                # alt contains {"transcript": ..., "confidence": ..., "words": [...], "punctuated": ...}
                yield alt
        await send_task
