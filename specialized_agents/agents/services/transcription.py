"""
Voice Transcription Service Wrapper.
Handles Whisper speech-to-text with graceful fallback if model/dependencies are unavailable.
"""
import os
import tempfile
import logging

logger = logging.getLogger(__name__)

# Global model instance
_whisper_model = None


def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper
            # Load 'tiny' or 'base' for hackathon speed
            _whisper_model = whisper.load_model("tiny")
        except Exception as e:
            logger.warning(f"Could not load OpenAI Whisper model: {e}. Fallback transcriber will be used.")
            _whisper_model = False
    return _whisper_model if _whisper_model is not False else None


async def transcribe_audio_file(file_bytes: bytes, filename: str) -> str:
    """
    Transcribes audio bytes to text.
    Handles temporary file write/cleanup and error catching.
    """
    if not file_bytes or len(file_bytes) == 0:
        raise ValueError("Uploaded audio file is empty.")

    ext = os.path.splitext(filename)[1].lower() if filename else ".wav"
    if not ext:
        ext = ".wav"

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        model = get_whisper_model()
        if model is not None:
            result = model.transcribe(tmp_path)
            return result.get("text", "").strip()
        else:
            # Fallback mock transcription if Whisper binary/ffmpeg is not installed locally
            return f"[Simulated Speech Transcription]: Hello, I want to check my eligibility for Google internship and register for tomorrow's workshop."
    except Exception as e:
        logger.error(f"Error during audio transcription: {e}")
        raise RuntimeError(f"Transcription engine failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
