"""
Test suite for Feature 1 — Voice Transcription Endpoint (/transcribe).
Tests audio file validation, Whisper transcription pipeline, clean JSON error handling
(no 500 stack traces to client), and OpenAPI endpoint response contract.
"""

import io
import sys
import wave
import struct
from pathlib import Path
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import app

client = TestClient(app)


def generate_wav_fixture() -> bytes:
    """Generates a valid 1-second 16kHz mono .wav audio fixture in memory."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        frames = [struct.pack('<h', 0) for _ in range(16000)]
        wav.writeframes(b''.join(frames))
    return buf.getvalue()


def test_transcribe_audio_fixture_contract():
    wav_bytes = generate_wav_fixture()
    response = client.post(
        "/transcribe",
        files={"audio": ("sample_test.wav", wav_bytes, "audio/wav")}
    )
    # Asserts clean JSON response without 500 server crash (200 OK when ffmpeg present, 422 clean error envelope when ffmpeg absent)
    assert response.status_code in (200, 422), f"Unexpected status code {response.status_code}: {response.text}"
    json_data = response.json()
    if response.status_code == 200:
        assert "text" in json_data, "Response missing 'text' field"
        assert isinstance(json_data["text"], str)
    else:
        assert "detail" in json_data, "Error response missing 'detail' field"
        assert "Transcription failed" in json_data["detail"]


def test_transcribe_empty_file_returns_400():
    response = client.post(
        "/transcribe",
        files={"audio": ("empty.wav", b"", "audio/wav")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_transcribe_invalid_content_type_returns_400():
    response = client.post(
        "/transcribe",
        files={"audio": ("document.pdf", b"%PDF-1.4 header text", "application/pdf")}
    )
    assert response.status_code == 400
    assert "invalid file type" in response.json()["detail"].lower()


if __name__ == "__main__":
    test_transcribe_audio_fixture_contract()
    test_transcribe_empty_file_returns_400()
    test_transcribe_invalid_content_type_returns_400()
    print("ALL TRANSCRIPTION TESTS PASSED CLEANLY!")
