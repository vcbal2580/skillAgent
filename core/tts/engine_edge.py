"""
EdgeEngine — Microsoft Edge Neural TTS (cloud, free, no API key).

Requires:  pip install edge-tts
Playback:  pip install pygame   (recommended)
        or pip install playsound==1.2.2
        or subprocess fallback (PowerShell / afplay / ffplay)

Config keys under tts.edge:
  voice   : edge-tts voice name    (default: zh-CN-XiaoxiaoNeural)
  rate    : speaking rate offset   (default: +0%,  e.g. +20%, -10%)
  volume  : volume offset          (default: +0%,  e.g. +10%, -20%)

Popular Chinese voices:
  zh-CN-XiaoxiaoNeural   女声，温柔自然（推荐）
  zh-CN-YunxiNeural      男声，活泼自然
  zh-CN-YunjianNeural    男声，低沉厚重
  zh-CN-XiaoyiNeural     女声，活泼可爱
  zh-TW-HsiaoChenNeural  繁中女声
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from typing import Any

from core.tts import TTSBase, _play_audio_file

_DEFAULT_VOICE  = "zh-CN-XiaoxiaoNeural"
_DEFAULT_RATE   = "+0%"
_DEFAULT_VOLUME = "+0%"


class EdgeEngine(TTSBase):
    """TTS via Microsoft Edge's neural voices (online required)."""

    def __init__(self, cfg: dict[str, Any]) -> None:
        self._voice  = cfg.get("voice",  _DEFAULT_VOICE)
        self._rate   = cfg.get("rate",   _DEFAULT_RATE)
        self._volume = cfg.get("volume", _DEFAULT_VOLUME)

    # ------------------------------------------------------------------ #

    def is_available(self) -> bool:
        try:
            import edge_tts  # type: ignore  # noqa: F401
            return True
        except ImportError:
            return False

    def speak(self, text: str) -> None:
        """Synthesise *text* with edge-tts and play immediately."""
        if not text or not text.strip():
            return
        # Sanitise: remove markdown symbols that sound odd when spoken
        clean = _strip_markdown(text)
        asyncio.run(self._synthesise_and_play(clean))

    # ------------------------------------------------------------------ #
    # Internal async helpers
    # ------------------------------------------------------------------ #

    async def _synthesise_and_play(self, text: str) -> None:
        try:
            import edge_tts  # type: ignore
        except ImportError:
            print("[TTS] edge-tts not installed. Run: pip install edge-tts")
            return

        communicate = edge_tts.Communicate(
            text,
            self._voice,
            rate=self._rate,
            volume=self._volume,
        )

        # Stream audio into a temp mp3 file, then play
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            await communicate.save(tmp_path)
            _play_audio_file(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ──────────────────────────────────────────────────────────────
# Markdown stripper (keep spoken text clean)
# ──────────────────────────────────────────────────────────────

import re

_MD_PATTERNS = [
    re.compile(r"```.*?```", re.DOTALL),   # fenced code blocks
    re.compile(r"`[^`]+`"),                # inline code
    re.compile(r"\*{1,3}([^*]+)\*{1,3}"), # bold / italic
    re.compile(r"#{1,6}\s*"),              # headings
    re.compile(r"\[([^\]]+)\]\([^)]+\)"), # links → keep label
    re.compile(r"!\[[^\]]*\]\([^)]+\)"),  # images → remove
    re.compile(r"^[-*+]\s+", re.MULTILINE),  # list bullets
    re.compile(r"^>\s+", re.MULTILINE),   # blockquotes
    re.compile(r"\|[^\n]+\|"),            # table rows
    re.compile(r"─+|━+|═+"),             # separators
    re.compile(r"\n{3,}"),               # collapse blank lines
]

def _strip_markdown(text: str) -> str:
    """Remove common markdown syntax so TTS sounds natural."""
    for pat in _MD_PATTERNS:
        text = pat.sub(lambda m: m.group(1) if m.lastindex else " ", text)
    return text.strip()
