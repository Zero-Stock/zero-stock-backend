"""
Custom DRF renderer that wraps ALL API responses in the unified envelope:

Success: {"message": "OK", "error": null, "results": <original_data>}
Error:   {"message": "...", "error": {"type": "...", "details": ...}, "results": null}

Error types:
- VALIDATION_ERROR  : 400 field validation failures
- NOT_FOUND         : 404 resource not found
- AUTHENTICATION_ERROR : 401 not authenticated
- PERMISSION_DENIED : 403 forbidden
- SERVER_ERROR      : 500 internal
- BAD_REQUEST       : 400 other bad requests
"""
from rest_framework.renderers import JSONRenderer


# ─────── HTTP status → error type mapping ───────
_STATUS_TO_TYPE = {
    400: "VALIDATION_ERROR",
    401: "AUTHENTICATION_ERROR",
    403: "PERMISSION_DENIED",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    429: "RATE_LIMITED",
}


def _error_type_for(status_code: int) -> str:
    if status_code in _STATUS_TO_TYPE:
        return _STATUS_TO_TYPE[status_code]
    if 400 <= status_code < 500:
        return "BAD_REQUEST"
    return "SERVER_ERROR"


class EnvelopeRenderer(JSONRenderer):
    """
    Wraps every DRF response in {message, error, results}.
    Works for standard CRUD, pagination, validation errors, etc.
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response") if renderer_context else None

        # Already wrapped by success_response / error_response helpers
        if isinstance(data, dict) and set(data.keys()) == {"message", "error", "results"}:
            # Skip double-wrapping
            return super().render(data, accepted_media_type, renderer_context)

        # Determine if this is an error response
        if response and response.status_code >= 400:
            envelope = {
                "message": self._extract_message(data) or "Error",
                "error": {
                    "type": _error_type_for(response.status_code),
                    "details": data,
                },
                "results": None,
            }
        else:
            envelope = {
                "message": "OK",
                "error": None,
                "results": data,
            }

        return super().render(envelope, accepted_media_type, renderer_context)

    @staticmethod
    def _extract_message(data):
        """Try to pull a human-readable message from error data."""
        if isinstance(data, dict):
            for key in ("detail", "message", "non_field_errors"):
                if key in data:
                    val = data[key]
                    if isinstance(val, list):
                        return str(val[0])
                    return str(val)
        if isinstance(data, list) and data:
            return str(data[0])
        return None
