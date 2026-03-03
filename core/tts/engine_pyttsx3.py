"""
Pyttsx3Engine — offline TTS using the system's native speech engine.

Requires:   pip install pyttsx3
On Windows: uses SAPI5 (built-in), no network, no extra installs.
On macOS:   uses NSSpeechSynthesizer (built-in).
On Linux:   uses espeak (apt-get install espeak).

Config keys under tts.pyttsx3:
  rate        : words per minute       (default: 175)
  volume      : 0.0 – 1.0             (default: 1.0)
  voice_index : index into the system's installed voice list (default: 0)
                set to -1 to let pyttsx3 choose automatically
"""

from __future__ import annotations

from typing import Any

from core.tts import TTSBase
from core.tts.engine_edge import _strip_markdown  # reuse the markdown cleaner

_DEFAULT_RATE        = 175
_DEFAULT_VOLUME      = 1.0
_DEFAULT_VOICE_INDEX = 0


class Pyttsx3Engine(TTSBase):
    """Fully offline TTS backed by the OS speech engine via pyttsx3."""

    def __init__(self, cfg: dict[str, Any]) -> None:
        self._rate        = int(cfg.get("rate",        _DEFAULT_RATE))
        self._volume      = float(cfg.get("volume",    _DEFAULT_VOLUME))
        self._voice_index = int(cfg.get("voice_index", _DEFAULT_VOICE_INDEX))
        self._engine      = None  # lazy-initialised on first use

    # ------------------------------------------------------------------ #

    def is_available(self) -> bool:
        try:
            import pyttsx3  # type: ignore  # noqa: F401
            return True
        except ImportError:
            return False

    def speak(self, text: str) -> None:
        """Synthesise and play *text* synchronously through the local engine."""
        if not text or not text.strip():
            return
        clean = _strip_markdown(text)
        engine = self._get_engine()
        if engine is None:
            return
        engine.say(clean)
        engine.runAndWait()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _get_engine(self):
        """Return (and lazily initialise) the pyttsx3 engine instance."""
        if self._engine is not None:
            return self._engine
        try:
            import pyttsx3  # type: ignore
        except ImportError:
            print("[TTS] pyttsx3 not installed. Run: pip install pyttsx3")
            return None

        engine = pyttsx3.init()
        engine.setProperty("rate",   self._rate)
        engine.setProperty("volume", self._volume)

        # Select voice by index if valid
        if self._voice_index >= 0:
            voices = engine.getProperty("voices")
            if voices and self._voice_index < len(voices):
                engine.setProperty("voice", voices[self._voice_index].id)

        self._engine = engine
        return engine
