"""
STT (Speech-To-Text) engine factory.
Mirrors the TTS engine pattern: select engine via config `stt.engine`.

Supported engines:
  disabled    - always returns empty string (default / no mic)
  openai      - OpenAI Whisper API  (or any Whisper-compatible endpoint)
  dashscope   - Alibaba Cloud Paraformer via DashScope SDK
"""

from core.config import config


def get_stt_engine():
    """Return the configured STT engine instance."""
    engine_name = config.get("stt.engine", "disabled").lower()

    if engine_name == "openai":
        from core.stt.engine_openai import OpenAISTTEngine
        return OpenAISTTEngine()

    if engine_name == "dashscope":
        from core.stt.engine_dashscope import DashScopeSTTEngine
        return DashScopeSTTEngine()

    from core.stt.engine_disabled import DisabledSTTEngine
    return DisabledSTTEngine()
