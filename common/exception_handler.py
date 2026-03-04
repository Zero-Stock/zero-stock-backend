"""
Global DRF exception handler.

Catches Django's ProtectedError (and similar DB integrity errors) and
returns a structured JSON response instead of letting them bubble up as 500.
"""

from rest_framework.views import exception_handler as drf_exception_handler
from django.db.models import ProtectedError


def custom_exception_handler(exc, context):
    """
    Extend the default DRF exception handler with Django model-level errors.
    """
    # Let DRF handle its own exceptions first (404, 403, validation, etc.)
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    # ── ProtectedError: trying to delete a record still referenced by FK ──
    if isinstance(exc, ProtectedError):
        protected_objects = exc.protected_objects
        # Build a readable list of what's blocking deletion
        refs = {}
        for obj in protected_objects:
            model_name = obj.__class__.__name__
            refs.setdefault(model_name, []).append(str(obj))

        from rest_framework.response import Response
        return Response(
            {
                "message": "无法删除，该记录仍被其他数据引用。",
                "error": {
                    "type": "PROTECTED_ERROR",
                    "details": {
                        "referenced_by": refs,
                    },
                },
                "results": None,
            },
            status=409,
        )

    # Anything else → let Django return its default 500
    return None
