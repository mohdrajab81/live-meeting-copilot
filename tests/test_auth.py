"""
Tests for app.api.auth — token mode, loopback mode, bearer/header/query extraction.
"""

import pytest
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.api.auth import (
    _is_loopback_host,
    _extract_bearer_token,
    _extract_token_from_headers,
    _extract_token_from_query,
    require_http_auth,
    is_websocket_authorized,
)


# ---------------------------------------------------------------------------
# Helpers to build fake Request / WebSocket objects
# ---------------------------------------------------------------------------

class _FakeClient:
    def __init__(self, host: str):
        self.host = host


def _make_request(headers=None, query_params=None, client_host="127.0.0.1"):
    req = MagicMock()
    req.client = _FakeClient(client_host)
    req.headers = dict(headers or {})
    req.query_params = dict(query_params or {})
    return req


def _make_websocket(headers=None, query_params=None, client_host="127.0.0.1"):
    ws = MagicMock()
    ws.client = _FakeClient(client_host)
    ws.headers = dict(headers or {})
    ws.query_params = dict(query_params or {})
    return ws


# ---------------------------------------------------------------------------
# _is_loopback_host
# ---------------------------------------------------------------------------

class TestIsLoopbackHost:
    def test_localhost_string(self):
        assert _is_loopback_host("localhost")

    def test_ipv4_loopback(self):
        assert _is_loopback_host("127.0.0.1")

    def test_ipv4_loopback_other_range(self):
        assert _is_loopback_host("127.255.255.255")

    def test_ipv6_loopback(self):
        assert _is_loopback_host("::1")

    def test_testclient_string(self):
        assert _is_loopback_host("testclient")

    def test_external_ipv4_rejected(self):
        assert not _is_loopback_host("192.168.1.1")

    def test_external_ipv4_public(self):
        assert not _is_loopback_host("8.8.8.8")

    def test_empty_string_rejected(self):
        assert not _is_loopback_host("")

    def test_garbage_string_rejected(self):
        assert not _is_loopback_host("not-an-ip")

    def test_ipv6_non_loopback_rejected(self):
        assert not _is_loopback_host("2001:db8::1")

    def test_ipv6_scoped_loopback(self):
        # Zone ID suffix should be stripped before parsing
        assert _is_loopback_host("::1%eth0")


# ---------------------------------------------------------------------------
# _extract_bearer_token
# ---------------------------------------------------------------------------

class TestExtractBearerToken:
    def test_valid_bearer(self):
        assert _extract_bearer_token("Bearer mytoken") == "mytoken"

    def test_case_insensitive_bearer_prefix(self):
        assert _extract_bearer_token("bearer mytoken") == "mytoken"

    def test_no_bearer_prefix_returns_empty(self):
        assert _extract_bearer_token("mytoken") == ""

    def test_empty_string_returns_empty(self):
        assert _extract_bearer_token("") == ""

    def test_bearer_only_no_token_returns_empty(self):
        # "Bearer " with trailing space and nothing after
        assert _extract_bearer_token("Bearer ") == ""

    def test_token_with_spaces_stripped(self):
        assert _extract_bearer_token("Bearer   mytoken  ") == "mytoken"


# ---------------------------------------------------------------------------
# _extract_token_from_headers
# ---------------------------------------------------------------------------

class TestExtractTokenFromHeaders:
    def test_authorization_bearer(self):
        assert _extract_token_from_headers({"authorization": "Bearer abc"}) == "abc"

    def test_x_api_key(self):
        assert _extract_token_from_headers({"x-api-key": "xyz"}) == "xyz"

    def test_authorization_takes_precedence(self):
        result = _extract_token_from_headers({
            "authorization": "Bearer abc",
            "x-api-key": "xyz",
        })
        assert result == "abc"

    def test_empty_headers_returns_empty(self):
        assert _extract_token_from_headers({}) == ""


# ---------------------------------------------------------------------------
# _extract_token_from_query
# ---------------------------------------------------------------------------

class TestExtractTokenFromQuery:
    def test_token_param(self):
        assert _extract_token_from_query({"token": "myval"}) == "myval"

    def test_api_token_param(self):
        assert _extract_token_from_query({"api_token": "myval"}) == "myval"

    def test_token_takes_precedence_over_api_token(self):
        result = _extract_token_from_query({"token": "a", "api_token": "b"})
        assert result == "a"

    def test_empty_params_returns_empty(self):
        assert _extract_token_from_query({}) == ""


# ---------------------------------------------------------------------------
# require_http_auth — loopback mode (no token configured)
# ---------------------------------------------------------------------------

class TestRequireHttpAuthLoopbackMode:
    def test_loopback_ip_allowed(self, monkeypatch):
        monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
        req = _make_request(client_host="127.0.0.1")
        require_http_auth(req)  # must not raise

    def test_testclient_host_allowed(self, monkeypatch):
        monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
        req = _make_request(client_host="testclient")
        require_http_auth(req)

    def test_external_ip_rejected(self, monkeypatch):
        monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
        req = _make_request(client_host="10.0.0.1")
        with pytest.raises(HTTPException) as exc:
            require_http_auth(req)
        assert exc.value.status_code == 401

    def test_public_ip_rejected(self, monkeypatch):
        monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
        req = _make_request(client_host="203.0.113.5")
        with pytest.raises(HTTPException) as exc:
            require_http_auth(req)
        assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# require_http_auth — token mode
# ---------------------------------------------------------------------------

class TestRequireHttpAuthTokenMode:
    def test_valid_bearer_token_passes(self, monkeypatch):
        monkeypatch.setenv("API_AUTH_TOKEN", "secret123")
        req = _make_request(
            headers={"authorization": "Bearer secret123"},
            client_host="10.0.0.1",
        )
        require_http_auth(req)  # must not raise

    def test_invalid_bearer_token_rejected(self, monkeypatch):
        monkeypatch.setenv("API_AUTH_TOKEN", "secret123")
        req = _make_request(
            headers={"authorization": "Bearer wrongtoken"},
            client_host="10.0.0.1",
        )
        with pytest.raises(HTTPException) as exc:
            require_http_auth(req)
        assert exc.value.status_code == 401

    def test_x_api_key_passes(self, monkeypatch):
        monkeypatch.setenv("API_AUTH_TOKEN", "secret123")
        req = _make_request(
            headers={"x-api-key": "secret123"},
            client_host="10.0.0.1",
        )
        require_http_auth(req)

    def test_query_param_token_passes(self, monkeypatch):
        monkeypatch.setenv("API_AUTH_TOKEN", "secret123")
        req = _make_request(
            query_params={"token": "secret123"},
            client_host="10.0.0.1",
        )
        require_http_auth(req)

    def test_api_token_query_param_passes(self, monkeypatch):
        monkeypatch.setenv("API_AUTH_TOKEN", "secret123")
        req = _make_request(
            query_params={"api_token": "secret123"},
            client_host="10.0.0.1",
        )
        require_http_auth(req)

    def test_wrong_query_token_rejected(self, monkeypatch):
        monkeypatch.setenv("API_AUTH_TOKEN", "secret123")
        req = _make_request(
            query_params={"token": "bad"},
            client_host="10.0.0.1",
        )
        with pytest.raises(HTTPException):
            require_http_auth(req)

    def test_loopback_still_requires_token_when_configured(self, monkeypatch):
        """When API_AUTH_TOKEN is set, even 127.0.0.1 must provide it."""
        monkeypatch.setenv("API_AUTH_TOKEN", "secret123")
        req = _make_request(client_host="127.0.0.1")
        with pytest.raises(HTTPException) as exc:
            require_http_auth(req)
        assert exc.value.status_code == 401

    def test_loopback_with_valid_token_passes(self, monkeypatch):
        monkeypatch.setenv("API_AUTH_TOKEN", "secret123")
        req = _make_request(
            headers={"authorization": "Bearer secret123"},
            client_host="127.0.0.1",
        )
        require_http_auth(req)

    def test_no_token_provided_rejected(self, monkeypatch):
        monkeypatch.setenv("API_AUTH_TOKEN", "secret123")
        req = _make_request(client_host="10.0.0.1")
        with pytest.raises(HTTPException):
            require_http_auth(req)


# ---------------------------------------------------------------------------
# is_websocket_authorized
# ---------------------------------------------------------------------------

class TestIsWebsocketAuthorized:
    def test_loopback_allowed_without_token(self, monkeypatch):
        monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
        ws = _make_websocket(client_host="127.0.0.1")
        assert is_websocket_authorized(ws) is True

    def test_external_rejected_without_token(self, monkeypatch):
        monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
        ws = _make_websocket(client_host="8.8.8.8")
        assert is_websocket_authorized(ws) is False

    def test_valid_bearer_token_allows_external(self, monkeypatch):
        monkeypatch.setenv("API_AUTH_TOKEN", "wstoken")
        ws = _make_websocket(
            headers={"authorization": "Bearer wstoken"},
            client_host="8.8.8.8",
        )
        assert is_websocket_authorized(ws) is True

    def test_invalid_token_rejects(self, monkeypatch):
        monkeypatch.setenv("API_AUTH_TOKEN", "wstoken")
        ws = _make_websocket(
            headers={"authorization": "Bearer badtoken"},
            client_host="8.8.8.8",
        )
        assert is_websocket_authorized(ws) is False

    def test_loopback_needs_token_when_configured(self, monkeypatch):
        monkeypatch.setenv("API_AUTH_TOKEN", "wstoken")
        ws = _make_websocket(client_host="127.0.0.1")
        assert is_websocket_authorized(ws) is False

    def test_query_token_param_works_for_ws(self, monkeypatch):
        monkeypatch.setenv("API_AUTH_TOKEN", "wstoken")
        ws = _make_websocket(
            query_params={"token": "wstoken"},
            client_host="8.8.8.8",
        )
        assert is_websocket_authorized(ws) is True
