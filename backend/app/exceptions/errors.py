"""Application exception hierarchy and consistent error codes.

Every application-level error carries a machine-readable ``code`` and an
HTTP ``status_code`` so the API can return consistent, non-leaky error
responses to clients.
"""

from typing import Any


class AppError(Exception):
    """Base class for all application-level errors.

    Attributes:
        code: machine-readable error code returned in API responses.
        status_code: HTTP status code to return to the client.
        detail: human-readable message; defaults to the class message.
    """

    code: str = "INTERNAL_ERROR"
    status_code: int = 500
    message: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.message
        super().__init__(self.detail)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the error into the stable API error envelope."""
        return {"error": {"code": self.code, "message": self.detail}}


class DataSFError(AppError):
    """Base class for failures while communicating with the DataSF API."""

    message = "The DataSF service could not be reached."


class DataSFTimeoutError(DataSFError):
    """The DataSF API did not respond within the configured timeout."""

    code = "DATASF_TIMEOUT"
    status_code = 504
    message = "The DataSF service timed out."


class DataSFUnavailableError(DataSFError):
    """Transport-level failure (connection refused, DNS, network, ...)."""

    code = "DATASF_UNAVAILABLE"
    status_code = 502
    message = "The DataSF service is currently unavailable."


class DataSFHttpError(DataSFError):
    """The DataSF API returned a non-success HTTP status."""

    code = "DATASF_UNAVAILABLE"
    status_code = 502

    def __init__(self, status_code: int, detail: str | None = None) -> None:
        self.upstream_status_code = status_code
        super().__init__(detail or f"The DataSF service returned HTTP {status_code}.")


class DataSFInvalidResponseError(DataSFError):
    """The DataSF API returned a body that could not be interpreted."""

    code = "DATASF_INVALID_RESPONSE"
    status_code = 502
    message = "The DataSF service returned an unexpected response."