"""
Internationalization (i18n) helper using GNU gettext.

Usage:
    from core.i18n import _
    print(_("Hello world"))

The active language is read from config.yaml:
    language: zh   # or 'en'

Locale files live at:
    locales/<lang>/LC_MESSAGES/messages.po   (source)
    locales/<lang>/LC_MESSAGES/messages.mo   (compiled binary - required at runtime)

To recompile after editing a .po file:
    python scripts/compile_messages.py
"""

import gettext
from pathlib import Path
from typing import Callable

# Identity fallback - used before setup() is called
_gettext: Callable[[str], str] = lambda s: s

LOCALES_DIR = Path(__file__).parent.parent / "locales"


def setup(language: str = "en") -> None:
    """Load translations for *language* ('en', 'zh', ...).

    Falls back to returning the original msgid (English) when no compiled
    .mo file is found for the requested language.
    """
    global _gettext
    try:
        t = gettext.translation(
            domain="messages",
            localedir=str(LOCALES_DIR),
            languages=[language],
        )
        _gettext = t.gettext
    except FileNotFoundError:
        # No .mo for this language - fall back to identity (English msgid)
        _gettext = lambda s: s


def _(text: str) -> str:
    """Return *text* translated into the active language."""
    return _gettext(text)
