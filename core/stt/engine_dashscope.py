"""
STT engine: Alibaba Cloud DashScope Paraformer.

* transcribe_file  → Transcription (async batch, requires public HTTP/HTTPS URL)
* transcribe_mic   → Recognition   (real-time streaming, feeds raw PCM frames)

Config keys:
  stt.engine: "dashscope"
  stt.api_key: "your-dashscope-api-key"   (falls back to llm.api_key)
  stt.language: "zh"                       (optional BCP-47 hint)

Requires: pip install dashscope
Mic recording also requires: pip install sounddevice
"""

import json
import time
import threading
import urllib.request
from core.config import config


class DashScopeSTTEngine:
    name = "dashscope"

    def __init__(self):
        import dashscope
        api_key = config.get("stt.api_key") or config.get("llm.api_key", "")
        dashscope.api_key = api_key
        self.language = config.get("stt.language", "zh")

    def transcribe_file(self, audio_path: str, language: str = None) -> str:
        """Transcribe via DashScope Transcription (async batch API).

        audio_path must be a publicly accessible HTTP/HTTPS URL.
        Local files are not supported by the cloud API - use engine_openai instead.
        """
        from dashscope.audio.asr import Transcription

        if not (audio_path.startswith("http://") or audio_path.startswith("https://")):
            raise ValueError(
                "DashScope Transcription requires a public HTTP(S) URL. "
                f"Got: {audio_path!r}. "
                "Upload the file to a public URL first, or switch to stt.engine=openai for local files."
            )

        lang = language or self.language
        response = Transcription.async_call(
            model="paraformer-v2",
            file_urls=[audio_path],
            language_hints=[lang] if lang else None,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"DashScope STT submit failed ({response.status_code}): {response.message}"
            )

        task_id = response.output.task_id

        # Poll until task finishes (max 60 s)
        for _ in range(60):
            time.sleep(1)
            result = Transcription.fetch(task_id=task_id)
            status = result.output.task_status
            if status == "SUCCEEDED":
                texts = []
                for r in result.output.results:
                    url = getattr(r, "transcription_url", None)
                    if url:
                        with urllib.request.urlopen(url) as resp:
                            data = json.loads(resp.read())
                        sentences = (
                            data.get("transcripts", [{}])[0].get("sentences", [])
                        )
                        texts.append(" ".join(s.get("text", "") for s in sentences))
                return " ".join(texts)
            if status in ("FAILED", "CANCELLED"):
                raise RuntimeError(f"DashScope transcription task {status}")

        raise TimeoutError("DashScope transcription timed out after 60 s")

    def transcribe_mic(self, duration: int = 5, language: str = None) -> str:
        """Record from microphone and transcribe via DashScope Recognition (streaming).

        Requires: pip install sounddevice
        """
        import sounddevice as sd
        from dashscope.audio.asr import Recognition, RecognitionCallback

        texts: list[str] = []
        done = threading.Event()

        class _Callback(RecognitionCallback):
            def on_event(self, result):
                sentence = result.get_sentence()
                if sentence and Recognition.is_sentence_end(sentence):
                    texts.append(sentence.get("text", ""))

            def on_complete(self):
                done.set()

            def on_error(self, result):
                done.set()

        lang = language or self.language
        recognizer = Recognition(
            model="paraformer-realtime-v2",
            format="pcm",
            sample_rate=16000,
            language_hints=[lang] if lang else None,
            callback=_Callback(),
        )
        recognizer.start()

        sample_rate = 16000
        chunk_samples = int(0.1 * sample_rate)  # 100 ms chunks
        total_samples = duration * sample_rate
        recorded = 0

        print(f"[STT-DashScope] Recording {duration}s... ", end="", flush=True)
        while recorded < total_samples:
            n = min(chunk_samples, total_samples - recorded)
            chunk = sd.rec(n, samplerate=sample_rate, channels=1, dtype="int16", blocking=True)
            recognizer.send_audio_frame(chunk.tobytes())
            recorded += n
        print("done.")

        recognizer.stop()
        done.wait(timeout=10)
        return " ".join(texts)
