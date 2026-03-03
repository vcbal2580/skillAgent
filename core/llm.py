"""
LLM client abstraction - wraps OpenAI-compatible APIs.
Supports text, vision (image), and audio (transcription) modalities.
"""

import base64
from pathlib import Path
from openai import OpenAI
from core.config import config


class LLMClient:
    """Unified LLM client supporting any OpenAI-compatible API."""

    def __init__(self):
        api_key = config.get("llm.api_key", "")
        base_url = config.get("llm.base_url", "")

        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url

        self.client = OpenAI(**kwargs)
        self.model = config.get("llm.model", "gpt-4o-mini")
        # Vision model - falls back to the same model (gpt-4o / qwen-vl-plus etc.)
        self.vision_model = config.get("llm.vision_model", self.model)
        # STT model for audio transcription
        self.stt_model = config.get("stt.openai_model", "whisper-1")
        self.temperature = config.get("llm.temperature", 0.7)
        self.max_tokens = config.get("llm.max_tokens", 2048)

    def chat(self, messages: list, tools: list = None, tool_choice: str = "auto") -> object:
        """
        Send a chat completion request.

        Args:
            messages: List of message dicts (role, content, etc.)
            tools: Optional list of tool/function definitions
            tool_choice: "auto", "none", or "required"

        Returns:
            The API response message object.
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message

    def chat_with_image(
        self,
        messages: list,
        image_source: str,
        tools: list = None,
        tool_choice: str = "auto",
    ) -> object:
        """
        Send a vision chat completion request with an image.

        Args:
            messages: Existing conversation messages (system + history).
            image_source: Either a public URL or a local file path.
                          Local files are base64-encoded automatically.
            tools: Optional tool definitions.
            tool_choice: Tool selection strategy.

        Returns:
            The API response message object.
        """
        image_content = self._build_image_content(image_source)

        # The last message should be a user message; attach the image to it.
        # If messages already end with a user message, append image content.
        enriched = list(messages)
        if enriched and enriched[-1]["role"] == "user":
            last_text = enriched[-1].get("content", "")
            enriched[-1] = {
                "role": "user",
                "content": [
                    {"type": "text", "text": last_text},
                    image_content,
                ],
            }
        else:
            enriched.append({
                "role": "user",
                "content": [image_content],
            })

        kwargs = {
            "model": self.vision_model,
            "messages": enriched,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message

    def transcribe_audio(self, audio_path: str, language: str = None) -> str:
        """
        Transcribe an audio file to text using Whisper (OpenAI or compatible).

        Args:
            audio_path: Local path to audio file (mp3/wav/m4a/ogg/webm/mp4).
            language: Optional BCP-47 language hint, e.g. "zh" or "en".

        Returns:
            Transcribed text string.
        """
        kwargs = {"model": self.stt_model}
        if language:
            kwargs["language"] = language
        with open(audio_path, "rb") as f:
            transcript = self.client.audio.transcriptions.create(file=f, **kwargs)
        return transcript.text

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_image_content(image_source: str) -> dict:
        """Return an OpenAI-compatible image_url content block."""
        if image_source.startswith("http://") or image_source.startswith("https://"):
            return {"type": "image_url", "image_url": {"url": image_source}}

        # Local file → base64 data URL
        path = Path(image_source)
        suffix = path.suffix.lower().lstrip(".")
        mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png",
                    "gif": "gif", "webp": "webp"}
        mime = mime_map.get(suffix, "jpeg")
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return {
            "type": "image_url",
            "image_url": {"url": f"data:image/{mime};base64,{b64}"},
        }
