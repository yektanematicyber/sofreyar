from typing import Any
from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception supporting a standardized machine-readable error code."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str,
        headers: dict[str, str] | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code
        self.extra = extra or {}


class EmptyPantryException(AppException):
    def __init__(self, detail: str = "انبار شما خالی است. لطفاً ابتدا موادی به انبار خود اضافه کنید."):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="EMPTY_PANTRY",
        )


class InvalidRequestException(AppException):
    def __init__(self, detail: str = "درخواست نامعتبر است.", extra: dict[str, Any] | None = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="INVALID_REQUEST",
            extra=extra,
        )


class LLMTimeoutException(AppException):
    def __init__(self, detail: str = "پاسخ سرویس هوش مصنوعی بیش از حد مجاز طول کشید. لطفاً مجدداً تلاش کنید."):
        super().__init__(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=detail,
            error_code="LLM_TIMEOUT",
        )


class LLMProviderException(AppException):
    def __init__(self, detail: str = "خطا در برقراری ارتباط با ارائه‌دهنده هوش مصنوعی."):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
            error_code="LLM_PROVIDER_ERROR",
        )


class InvalidLLMResponseException(AppException):
    def __init__(self, detail: str = "پاسخ دریافتی از هوش مصنوعی ساختار معتبری نداشت."):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
            error_code="INVALID_LLM_RESPONSE",
        )


class RateLimitExceededException(AppException):
    def __init__(self, retry_after: int, detail: str | None = None):
        message = detail or f"سقف مجاز درخواست‌های پیشنهاد غذا به پایان رسیده است. لطفاً {retry_after} ثانیه دیگر امتحان کنید."
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=message,
            error_code="RATE_LIMIT_EXCEEDED",
            headers={"Retry-After": str(retry_after)},
        )


class RecipeNotFoundException(AppException):
    def __init__(self, detail: str = "دستور پخت مورد نظر یافت نشد."):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code="RECIPE_NOT_FOUND",
        )


class DatabaseException(AppException):
    def __init__(self, detail: str = "خطای داخلی در پایگاه داده رخ داده است."):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="DATABASE_ERROR",
        )
