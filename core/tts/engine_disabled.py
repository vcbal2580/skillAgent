"""
DisabledEngine — no-op TTS engine.

Used when tts.enabled = false or tts.engine = disabled.
"""

from core.tts import TTSBase


class DisabledEngine(TTSBase):
    """Silent pass-through; TTS is off."""

    def speak(self, text: str) -> None:  # noqa: ARG002
        return

    def is_available(self) -> bool:
        return True
