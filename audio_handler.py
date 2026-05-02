"""
Audio handler — downloads WhatsApp voice notes from Twilio and transcribes
them instantly using Groq's Whisper API.
"""

import os
import tempfile
import requests
from groq import Groq
from config import GROQ_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN

_client = Groq(api_key=GROQ_API_KEY)

def transcribe_audio(media_url: str) -> str:
    """
    Downloads an audio file from Twilio and transcribes it using Groq.
    """
    try:
        # 1. Download audio file securely using Twilio Auth
        response = requests.get(media_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
        response.raise_for_status()
        
        # 2. Save to a temporary file (WhatsApp uses .ogg)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_file:
            tmp_file.write(response.content)
            tmp_path = tmp_file.name
            
        # 3. Transcribe using Groq Whisper (lightning fast)
        with open(tmp_path, "rb") as audio_file:
            transcription = _client.audio.transcriptions.create(
                file=("audio.ogg", audio_file.read()),
                model="whisper-large-v3-turbo",
            )
            
        # 4. Clean up the temp file
        os.remove(tmp_path)
        
        return transcription.text.strip()
        
    except Exception as e:
        print(f"[audio_handler] Error transcribing voice note: {e}")
        return ""
