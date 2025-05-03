import requests

RETELL_API_KEY = "key_e840399d939ccaf7a9168a360c0e"
RETELL_API_URL = "https://api.retellai.com/v1/speech-to-text"

def transcribe_audio(audio_bytes, language="en-US"):
    headers = {
        "Authorization": f"Bearer {RETELL_API_KEY}",
    }
    files = {
        "audio": ("audio.wav", audio_bytes, "audio/wav"),
    }
    data = {
        "language": language,
    }
    response = requests.post(RETELL_API_URL, headers=headers, files=files, data=data)
    response.raise_for_status()
    return response.json().get("transcript", "")