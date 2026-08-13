"""
Application-wide custom exceptions.

استفاده از استثناهای اختصاصی به‌جای Exception خام باعث می‌شود
لایه‌ی هندلر (بات یا API) بتواند خطاها را دقیق‌تر تفکیک و مدیریت کند.
"""


class GreenVitaError(Exception):
    """Base exception for all application-specific errors."""

    def __init__(self, message: str = "خطای داخلی رخ داد.", *, code: str = "internal_error"):
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(GreenVitaError):
    """Raised when a requested entity does not exist."""

    def __init__(self, entity: str = "مورد", *, code: str = "not_found"):
        super().__init__(f"{entity} پیدا نشد.", code=code)


class ValidationError(GreenVitaError):
    """Raised when input data fails validation rules."""

    def __init__(self, message: str = "داده‌های ورودی نامعتبر است.", *, code: str = "validation_error"):
        super().__init__(message, code=code)


class AuthenticationError(GreenVitaError):
    """Raised on failed login / invalid credentials."""

    def __init__(self, message: str = "احراز هویت ناموفق بود.", *, code: str = "auth_error"):
        super().__init__(message, code=code)


class AIProviderError(GreenVitaError):
    """Raised when an AI provider call fails (timeout, bad response, quota, etc.)."""

    def __init__(self, message: str = "سرویس هوش مصنوعی پاسخگو نیست.", *, code: str = "ai_provider_error"):
        super().__init__(message, code=code)


class ConfigurationError(GreenVitaError):
    """Raised when required configuration/env vars are missing or invalid."""

    def __init__(self, message: str = "پیکربندی پروژه ناقص است.", *, code: str = "configuration_error"):
        super().__init__(message, code=code)
