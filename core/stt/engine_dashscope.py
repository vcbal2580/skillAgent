"""
STT engine: Alibaba Cloud DashScope Paraformer (real-time recognition).

Config keys:
  stt.engine: "dashscope"
  stt.api_key: "your-dashscope-api-key"   (falls back to llm.api_key)
  stt.language: "zh"                       (optional)

Requires: pip install dashscope
"""

import os
from pathlib import Path
from core.config import config


class DashScopeSTTEngine:
    name = "dashscope"

    def __init__(self):
        import dashscope
        api_key = config.get("stt.api_key") or config.get("llm.api_key", "")
        dashscope.api_key = api_key
        self.language = config.get("stt.language", "zh")

    def transcribe_file(self, audio_path: str, language: str = None) -> str:
        """Transcribe an audio file via DashScope Paraformer."""
        from dashscope.audio.asr import Recognition

        lang = language or self.language
        result = Recognition.call(
            model="paraformer-realtime-v2",
            file_urls=[Path(audio_path).as_uri()],
            language_hints=[lang] if lang else None,
        )
        if result.status_code == 200:
            sentences = result.get_body().get("result", {}).get("sentences", [])
            return " ".join(s.get("text", "") for s in sentences)
        raise RuntimeError(f"DashScope STT error {result.status_code}: {result.message}")

    def transcribe_mic(self, duration: int = 5, language: str = None) -> str:
        """Record from microphone and transcribe.

        Requires: pip install sounddevice scipy
        """
        import tempfile, os
        import sounddevice as sd
        import scipy.io.wavfile as wavfile

        sample_rate = 16000
        print(f"[STT-DashScope] Recording {duration}s... ", end="", flush=True)
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
