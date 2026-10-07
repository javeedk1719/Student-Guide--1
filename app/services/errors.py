class ExternalServiceError(Exception):
    """Raised when Groq / YouTube / NewsAPI fail. main.py turns it into a clean JSON error.
    The message must never contain API keys or full URLs."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
