"""
STT engine: OpenAI Whisper API (or any Whisper-compatible endpoint).

Config keys used:
  stt.engine: "openai"
  llm.api_key  / llm.base_url  - reuse LLM credentials by default
  stt.api_key  - override with dedicated key (optional)
  stt.base_url - override with dedicated base URL (optional)
  stt.openai_model: "whisper-1"  (default)
  stt.language: "zh"             (optional BCP-47 hint)
"""

from openai import OpenAI
from core.config import config


class OpenAISTTEngine:
    name = "openai"

    def __init__(self):
        api_key = config.get("stt.api_key") or config.get("llm.api_key", "")
        base_url = config.get("stt.base_url") or config.get("llm.base_url", "")
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)
        self.model = config.get("stt.openai_model", "whisper-1")
        self.language = config.get("stt.language", None)

    def transcribe_file(self, audio_path: str, language: str = None) -> str:
        """Transcribe an existing audio file."""
        lang = language or self.language
        kwargs = {"model": self.model}
        if lang:
            kwargs["language"] = lang
        with open(audio_path, "rb") as f:
            result = self.client.audio.transcriptions.create(file=f, **kwargs)
        return result.text

    def transcribe_mic(self, duration: int = 5, language: str = None) -> str:
        """Record from microphone for `duration` seconds and transcribe.

        Requires: pip install sounddevice scipy
        """
        import tempfile, os
        import sounddevice as sd
        import scipy.io.wavfile as wavfile

        sample_rate = 16000
        print(f"[STT] Recording {duration}s... ", end="", flush=True)
        audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")
        sd.wait()
        print("done.")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            wavfile.write(tmp_path, sample_rate, audio)
            return self.transcribe_file(tmp_path, language=language)
        finally:
            os.unlink(tmp_path)
