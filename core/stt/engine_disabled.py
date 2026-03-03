"""STT engine: disabled stub - returns empty string for all inputs."""


class DisabledSTTEngine:
    """No-op STT engine used when speech input is not configured."""

    name = "disabled"

    def transcribe_file(self, audio_path: str, language: str = None) -> str:
        return ""

    def transcribe_mic(self, duration: int = 5, language: str = None) -> str:
        return ""
