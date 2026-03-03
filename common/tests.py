# -*- coding: utf-8 -*-
"""common/tests.py - Response helpers and EnvelopeRenderer tests."""
import json
from unittest.mock import MagicMock
from django.test import TestCase
from rest_framework import status
from common.renderers import EnvelopeRenderer
from common.views import error_response, success_response


class SuccessResponseTest(TestCase):
    def test_default(self):
        r = success_response(results={"key": "value"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["message"], "OK")
        self.assertIsNone(r.data["error"])
        self.assertEqual(r.data["results"]["key"], "value")

    def test_custom_message_and_status(self):
        r = success_response(results=[], message="Created", http_status=status.HTTP_201_CREATED)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["message"], "Created")

    def test_none_results(self):
        r = success_response()
        self.assertIsNone(r.data["results"])


class ErrorResponseTest(TestCase):
    def test_default(self):
        r = error_response(error="Something wrong", message="Bad Input")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["error"]["type"], "VALIDATION_ERROR")

    def test_custom_error_type(self):
        r = error_response(error="Not found", error_type="NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.data["error"]["type"], "NOT_FOUND")

    def test_auto_detect_401(self):
        r = error_response(http_status=status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(r.data["error"]["type"], "AUTHENTICATION_ERROR")

    def test_auto_detect_403(self):
        r = error_response(http_status=status.HTTP_403_FORBIDDEN)
        self.assertEqual(r.data["error"]["type"], "PERMISSION_DENIED")

    def test_auto_detect_500(self):
        r = error_response(http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(r.data["error"]["type"], "SERVER_ERROR")


class EnvelopeRendererTest(TestCase):
    def setUp(self):
        self.renderer = EnvelopeRenderer()

    def _ctx(self, code):
        resp = MagicMock()
        resp.status_code = code
        return {"response": resp}

    def test_already_wrapped(self):
        data = {"message": "OK", "error": None, "results": [1, 2]}
        out = json.loads(self.renderer.render(data, renderer_context=self._ctx(200)))
        self.assertEqual(out["results"], [1, 2])

    def test_unwrapped_success(self):
        data = {"id": 1, "name": "Test"}
        out = json.loads(self.renderer.render(data, renderer_context=self._ctx(200)))
        self.assertEqual(out["message"], "OK")
        self.assertEqual(out["results"]["id"], 1)

    def test_unwrapped_error(self):
        data = {"detail": "Not found."}
        out = json.loads(self.renderer.render(data, renderer_context=self._ctx(404)))
        self.assertEqual(out["error"]["type"], "NOT_FOUND")
        self.assertIsNone(out["results"])

    def test_error_message_from_detail(self):
        data = {"detail": "Permission denied"}
        out = json.loads(self.renderer.render(data, renderer_context=self._ctx(403)))
        self.assertEqual(out["message"], "Permission denied")
