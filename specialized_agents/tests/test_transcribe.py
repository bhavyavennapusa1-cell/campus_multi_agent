import wave
import io
import pytest
from fastapi.testclient import TestClient
from server import app


def generate_wav_fixture_bytes() -> bytes:
    """Generates a valid 1-second 44.1kHz mono PCM WAV file in memory."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(44100)
        # Write 1 second of silent PCM audio (0x0000)
        wav_file.writeframes(b'\x00\x00' * 44100)
    return buf.getvalue()


def test_transcribe_audio_valid_file():
    client = TestClient(app)
    wav_bytes = generate_wav_fixture_bytes()

    response = client.post(
        "/transcribe",
        files={"audio": ("test_sample.wav", wav_bytes, "audio/wav")}
    )

    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert isinstance(data["text"], str)
    assert len(data["text"]) > 0


def test_transcribe_audio_empty_file():
    client = TestClient(app)
    response = client.post(
        "/transcribe",
        files={"audio": ("empty.wav", b"", "audio/wav")}
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_transcribe_audio_invalid_format():
    client = TestClient(app)
    response = client.post(
        "/transcribe",
        files={"audio": ("document.txt", b"Hello world text file", "text/plain")}
    )

    assert response.status_code == 400
    assert "invalid file format" in response.json()["detail"].lower()
