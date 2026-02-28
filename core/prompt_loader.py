"""
Skill prompt loader - reads language-specific prompt YAML files and overlays
them onto skill tool definitions at runtime.

Prompt files live at:
    prompts/en.yaml   (English, also the canonical fallback)
    prompts/zh.yaml   (Chinese, independently tunable)
    prompts/<lang>.yaml  (add more as needed)

YAML structure per skill:
    <skill_name>:
      description: "..."
      parameters:
        <param_name>: "..."   # replaces only the 'description' field of that param

The Python class attributes (description / parameters) always serve as the
ultimate fallback when no YAML entry exists for a skill or language.
"""

import yaml
from pathlib import Path
from typing import Any


_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# Cache: {language: {skill_name: {description, parameters}}}
_cache: dict[str, dict] = {}

_active_language: str = "en"


def setup(language: str) -> None:
    """Set the active language for prompt resolution."""
    global _active_language
    _active_language = language


def _load(language: str) -> dict:
    """Load (and cache) the prompt YAML for *language*.

    Falls back to 'en' when the requested file does not exist.
    Returns an empty dict when neither file exists.
    """
    if language in _cache:
        return _cache[language]

    path = _PROMPTS_DIR / f"{language}.yaml"
    if not path.exists():
        # Try English fallback
        path = _PROMPTS_DIR / "en.yaml"
    if not path.exists():
        _cache[language] = {}
        return {}

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    _cache[language] = data
    return data


def overlay(skill_name: str, tool_def: dict) -> dict:
    """Return a copy of *tool_def* with language-specific prompt fields merged in.

    Only the 'description' of the function and per-parameter 'description'
    fields are overridden; the rest of the schema (types, required, etc.)
    stays untouched.
    """
    prompts = _load(_active_language)
    entry: dict = prompts.get(skill_name, {})
    if not entry:
        return tool_def  # Nothing to overlay

    import copy
    result = copy.deepcopy(tool_def)
    func = result["function"]

    # Override top-level skill description
    if "description" in entry:
        func["description"] = str(entry["description"]).strip()

    # Override individual parameter descriptions
    param_overrides: dict = entry.get("parameters", {})
    if param_overrides:
        props: dict = func.get("parameters", {}).get("properties", {})
        for param_name, desc in param_overrides.items():
            if param_name in props:
                props[param_name]["description"] = str(desc).strip()

    return result
