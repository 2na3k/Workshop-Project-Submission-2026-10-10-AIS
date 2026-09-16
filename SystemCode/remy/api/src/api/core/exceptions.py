class AppError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, details: list[dict] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or []
