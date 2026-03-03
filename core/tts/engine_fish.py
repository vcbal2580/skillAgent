"""
FishAudioEngine — Fish Audio cloud TTS with community voice library.

Fish Audio hosts thousands of voice models including popular anime/game
characters. Each model is identified by a unique reference_id.

Requires:   pip install fish-audio-sdk
Playback:   pip install pygame   (recommended)
         or pip install playsound==1.2.2
         or subprocess fallback

Config keys under tts.fish:
  api_key      : Fish Audio API key  (https://fish.audio — also supports env FISH_AUDIO_API_KEY)
  reference_id : voice model ID      (copy from the model page URL on fish.audio)
  format       : output format       (default: mp3)
  latency      : "normal" or "balanced" (default: normal — lower latency)
  chunk_length : synthesis chunk size in chars (default: 200)

How to find a reference_id:
  1. Go to https://fish.audio
  2. Search for the character / voice you want (e.g. "鸣人", "路飞", "明日香")
  3. Open the model page — the ID is the UUID in the URL:
       https://fish.audio/m/<reference_id>/
  4. Paste that UUID into tts.fish.reference_id

Popular anime character voice IDs change over time as the community
uploads new models. See config.example.yaml for current examples.
"""

from __future__ import annotations

import io
import os
import tempfile
from typing import Any

from core.tts import TTSBase, _play_audio_file
from core.tts.engine_edge import _strip_markdown

_DEFAULT_FORMAT       = "mp3"
_DEFAULT_LATENCY      = "normal"
_DEFAULT_CHUNK_LENGTH = 200


class FishAudioEngine(TTSBase):
    """TTS via Fish Audio — cloud service with community anime/voice model library."""

    def __init__(self, cfg: dict[str, Any]) -> None:
        self._api_key = (
            cfg.get("api_key", "")
            or os.environ.get("FISH_AUDIO_API_KEY", "")
        )
        self._reference_id  = cfg.get("reference_id", "")
        self._format        = cfg.get("format",       _DEFAULT_FORMAT)
        self._latency       = cfg.get("latency",      _DEFAULT_LATENCY)
        self._chunk_length  = int(cfg.get("chunk_length", _DEFAULT_CHUNK_LENGTH))

    # ------------------------------------------------------------------ #

    def is_available(self) -> bool:
        try:
            import fish_audio_sdk  # type: ignore  # noqa: F401
            return bool(self._api_key) and bool(self._reference_id)
        except ImportError:
            return False

    def speak(self, text: str) -> None:
        """Synthesise *text* via Fish Audio and play it."""
        if not text or not text.strip():
            return
        clean = _strip_markdown(text)
        self._synthesise_and_play(clean)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _synthesise_and_play(self, text: str) -> None:
        try:
            from fish_audio_sdk import Session, TTSRequest  # type: ignore
        except ImportError:
            print("[TTS] fish-audio-sdk not installed. Run: pip install fish-audio-sdk")
            return

        if not self._api_key:
            print("[TTS] Fish Audio api_key is not set. "
                  "Set tts.fish.api_key in config.yaml or env FISH_AUDIO_API_KEY.")
            return

        if not self._reference_id:
            print("[TTS] Fish Audio reference_id is not set. "
                  "Add tts.fish.reference_id (voice model UUID) to config.yaml.")
            return

        try:
            session = Session(self._api_key)
            request = TTSRequest(
                reference_id=self._reference_id,
                text=text,
                chunk_length=self._chunk_length,
                format=self._format,
                latency=self._latency,
            )

            # Collect streamed audio chunks into a buffer
            buf = io.BytesIO()
            for chunk in session.tts(request):
                buf.write(chunk)

            # Write to a temp file and play
            suffix = f".{self._format}"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(buf.getvalue())
                tmp_path = tmp.name

            try:
                _play_audio_file(tmp_path)
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        except Exception as e:
            print(f"[TTS][FishAudio] Error: {e}")
