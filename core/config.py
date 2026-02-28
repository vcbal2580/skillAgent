"""
Configuration management - loads config.yaml and environment variables.
"""

import os
import yaml
from pathlib import Path
from typing import Any


class Config:
    """Singleton configuration manager."""

    _instance = None
    _data: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, config_path: str = None):
        """Load configuration from YAML file."""
        if config_path is None:
            # Look for config.yaml relative to project root
            config_path = Path(__file__).parent.parent / "config.yaml"

        with open(config_path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f)

        # If system_prompt is a file reference ("file:path/to/persona.md"),
        # load the file content so users can maintain large prompts separately.
        prompt = self._data.get("agent", {}).get("system_prompt", "")
        if isinstance(prompt, str) and prompt.strip().startswith("file:"):
            persona_path = Path(config_path).parent / prompt.strip()[5:].strip()
            self._data["agent"]["system_prompt"] = persona_path.read_text(encoding="utf-8")

        # Override with environment variables
        self._apply_env_overrides()
        # Ensure data directories exist
        self._ensure_directories()

    def _apply_env_overrides(self):
        """Override config values with environment variables."""
        # LLM API key from env (try multiple env var names)
        if not self._data.get("llm", {}).get("api_key"):
            api_key = (
                os.getenv("OPENAI_API_KEY", "")
                or os.getenv("DASHSCOPE_API_KEY", "")
                or os.getenv("ZHIPU_API_KEY", "")
            )
            self._data.setdefault("llm", {})["api_key"] = api_key

        # Allow env-based base_url override
        env_base_url = os.getenv("LLM_BASE_URL", "")
        if env_base_url:
            self._data["llm"]["base_url"] = env_base_url

        # Allow env-based model override
        env_model = os.getenv("LLM_MODEL", "")
        if env_model:
            self._data["llm"]["model"] = env_model

    def _ensure_directories(self):
        """Create data directories if they don't exist."""
        paths = [
            self.get("knowledge.persist_directory", "./data/chromadb"),
            os.path.dirname(self.get("storage.db_path", "./data/agent.db")),
        ]
        for p in paths:
            Path(p).mkdir(parents=True, exist_ok=True)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get config value by dot-separated key path.
        Example: config.get("llm.model") -> "gpt-4o-mini"
        """
        keys = key.split(".")
        val = self._data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
            if val is None:
                return default
        return val

    @property
    def data(self) -> dict:
        return self._data


# Global config instance
config = Config()
