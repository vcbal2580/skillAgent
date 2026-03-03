"""
DashscopeEngine — Alibaba Cloud DashScope CosyVoice TTS.

Requires:   pip install dashscope
Playback:   pip install pygame   (recommended)
         or pip install playsound==1.2.2
         or subprocess fallback

Config keys under tts.dashscope:
  api_key : DashScope API key (falls back to config.llm.api_key if omitted)
  model   : TTS model          (default: cosyvoice-v1)
  voice   : voice ID           (default: longxiaochun)
  format  : output format      (default: mp3)

CosyVoice v1 built-in voices:
  longxiaochun   龙小淳 — 男声，成熟稳重
  longxiaocheng  龙小澄 — 男声，儒雅知性
  longxiaobai    龙小白 — 男声，朝气蓬勃
  longxiaoxia    龙小夏 — 女声，温柔甜美
  longxiaomei    龙小美 — 女声，端庄优雅
  longlaotie     龙老铁 — 男声，东北特色
  loongstella    — 英文女声

CosyVoice v2 voices (model: cosyvoice-v2):
  Same IDs as above; v2 supports emotion tags and instruction control.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any

from core.tts import TTSBase, _play_audio_file
from core.tts.engine_edge import _strip_markdown

_DEFAULT_MODEL  = "cosyvoice-v1"
_DEFAULT_VOICE  = "longxiaochun"
_DEFAULT_FORMAT = "mp3"


class DashscopeEngine(TTSBase):
    """TTS via Alibaba Cloud DashScope CosyVoice (cloud, requires API key)."""

    def __init__(self, cfg: dict[str, Any]) -> None:
        # Resolve API key: explicit cfg > LLM key (already in config)
        self._api_key = cfg.get("api_key", "") or self._resolve_api_key()
        self._model   = cfg.get("model",  _DEFAULT_MODEL)
        self._voice   = cfg.get("voice",  _DEFAULT_VOICE)
        self._format  = cfg.get("format", _DEFAULT_FORMAT)

    # ------------------------------------------------------------------ #

    def is_available(self) -> bool:
        try:
            import dashscope  # type: ignore  # noqa: F401
            return bool(self._api_key)
        except ImportError:
            return False

    def speak(self, text: str) -> None:
        """Synthesise *text* via CosyVoice and play it."""
        if not text or not text.strip():
            return
        clean = _strip_markdown(text)
        self._synthesise_and_play(clean)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _synthesise_and_play(self, text: str) -> None:
        try:
            import dashscope  # type: ignore
            from dashscope.audio.tts_v2 import SpeechSynthesizer  # type: ignore
        except ImportError:
            print("[TTS] dashscope not installed. Run: pip install dashscope")
            return

        if not self._api_key:
            print("[TTS] No DashScope API key. Set tts.dashscope.api_key in config.yaml")
            return

        dashscope.api_key = self._api_key

        # Stream synthesise into a temp file, then play
        suffix = f".{self._format}"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name

        try:
            synthesizer = SpeechSynthesizer(model=self._model, voice=self._voice)
            audio_data  = synthesizer.call(text)
            with open(tmp_path, "wb") as f:
                f.write(audio_data)
            _play_audio_file(tmp_path)
        except Exception as exc:
            print(f"[TTS] DashScope synthesis failed: {exc}")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    @staticmethod
    def _resolve_api_key() -> str:
        """Try to borrow the LLM API key as the DashScope TTS key."""
        try:
            from core.config import config  # type: ignore
            return config.get("llm.api_key", "") or os.getenv("DASHSCOPE_API_KEY", "")
        except Exception:
            return os.getenv("DASHSCOPE_API_KEY", "")
