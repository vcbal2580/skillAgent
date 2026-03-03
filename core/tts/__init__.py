"""
TTS (Text-To-Speech) subsystem for SkillAgent.

Architecture
───────────────────────────────────────────
  TTSBase          abstract interface
    ├─ DisabledEngine   no-op (engine: disabled)
    ├─ EdgeEngine       edge-tts cloud  (engine: edge)
    ├─ Pyttsx3Engine    offline / local (engine: pyttsx3)
    ├─ DashscopeEngine  DashScope CosyVoice cloud (engine: dashscope)
    └─ FishAudioEngine  Fish Audio cloud + community voices (engine: fish)

  create_engine(cfg)   factory — reads config, returns the right engine

config.yaml schema
───────────────────────────────────────────
  tts:
    enabled: true
    engine: edge          # edge | pyttsx3 | dashscope | fish | disabled
    edge:
      voice: zh-CN-XiaoxiaoNeural
      rate: "+0%"
      volume: "+0%"
    pyttsx3:
      rate: 175
      volume: 1.0
      voice_index: 0
    dashscope:
      api_key: ""         # falls back to config.llm.api_key if empty
      model: cosyvoice-v1
      voice: longxiaochun
      format: mp3
    fish:
      api_key: ""         # FISH_AUDIO_API_KEY env var also accepted
      reference_id: ""    # UUID from fish.audio/m/<id>/
      format: mp3
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


# ──────────────────────────────────────────────────────────────
# Abstract base
# ──────────────────────────────────────────────────────────────

class TTSBase(ABC):
    """Common interface for all TTS engines."""

    @abstractmethod
    def speak(self, text: str) -> None:
        """Synthesise *text* and play it through the default audio output."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the engine's dependencies are installed and ready."""


# ──────────────────────────────────────────────────────────────
# Audio file playback helper (used by file-based engines)
# ──────────────────────────────────────────────────────────────

def _play_audio_file(path: str) -> None:
    """
    Play an audio file (mp3/wav) to the default output device.

    Priority order — uses the first available method:
      1. pygame.mixer  (installed with: pip install pygame)
      2. playsound     (installed with: pip install playsound==1.2.2)
      3. subprocess fallback:
           Windows → PowerShell MediaPlayer
           macOS   → afplay
           Linux   → ffplay (ffmpeg)
    """
    # ① pygame
    try:
        import pygame  # type: ignore
        pygame.mixer.init()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
        pygame.mixer.quit()
        return
    except ImportError:
        pass

    # ② playsound (pin 1.2.2 for Windows compat)
    try:
        from playsound import playsound  # type: ignore
        playsound(path)
        return
    except ImportError:
        pass

    # ③ subprocess fallback (no extra Python deps)
    import platform
    import subprocess
    system = platform.system()
    if system == "Windows":
        ps = (
            f'$m = [System.Windows.Media.MediaPlayer]::new(); '
            f'$m.Open([System.Uri]::new("{path}")); '
            f'$m.Play(); '
            f'Start-Sleep -Milliseconds '
            f'([int]($m.NaturalDuration.TimeSpan.TotalMilliseconds) + 500)'
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            check=False,
        )
    elif system == "Darwin":
        subprocess.run(["afplay", path], check=False)
    else:
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
            check=False,
        )


# ──────────────────────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────────────────────

def create_engine(tts_cfg: dict[str, Any]) -> TTSBase:
    """
    Build and return the TTS engine specified in *tts_cfg*.

    *tts_cfg* is the ``tts`` sub-dict read from config.yaml, e.g.::

        {
            "enabled": True,
            "engine": "edge",
            "edge": {"voice": "zh-CN-XiaoxiaoNeural", "rate": "+0%", "volume": "+0%"},
            ...
        }
    """
    if not tts_cfg.get("enabled", False):
        from core.tts.engine_disabled import DisabledEngine
        return DisabledEngine()

    engine_name = tts_cfg.get("engine", "disabled").lower()

    if engine_name == "edge":
        from core.tts.engine_edge import EdgeEngine
        return EdgeEngine(tts_cfg.get("edge", {}))

    if engine_name == "pyttsx3":
        from core.tts.engine_pyttsx3 import Pyttsx3Engine
        return Pyttsx3Engine(tts_cfg.get("pyttsx3", {}))

    if engine_name == "dashscope":
        from core.tts.engine_dashscope import DashscopeEngine
        return DashscopeEngine(tts_cfg.get("dashscope", {}))

    if engine_name == "fish":
        from core.tts.engine_fish import FishAudioEngine
        return FishAudioEngine(tts_cfg.get("fish", {}))

    # fallthrough → disabled
    from core.tts.engine_disabled import DisabledEngine
    return DisabledEngine()
