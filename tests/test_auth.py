"""
Tests for app.api.auth — loopback-only HTTP and WebSocket authorization.
"""

import pytest
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.api.auth import (
    _is_loopback_host,
    is_websocket_authorized,
    require_http_auth,
)


class _FakeClient:
    def __init__(self, host: str):
        self.host = host


def _make_request(client_host="127.0.0.1"):
    req = MagicMock()
    req.client = _FakeClient(client_host)
    req.headers = {}
    req.query_params = {}
    return req


def _make_websocket(client_host="127.0.0.1"):
    ws = MagicMock()
    ws.client = _FakeClient(client_host)
    ws.headers = {}
    ws.query_params = {}
    return ws


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
        assert _is_loopback_host("::1%eth0")


class TestRequireHttpAuth:
    def test_loopback_ip_allowed(self):
        req = _make_request(client_host="127.0.0.1")
        require_http_auth(req)

    def test_testclient_host_allowed(self):
        req = _make_request(client_host="testclient")
        require_http_auth(req)

    def test_external_ip_rejected(self):
        req = _make_request(client_host="10.0.0.1")
        with pytest.raises(HTTPException) as exc:
            require_http_auth(req)
        assert exc.value.status_code == 401

    def test_public_ip_rejected(self):
        req = _make_request(client_host="203.0.113.5")
        with pytest.raises(HTTPException) as exc:
            require_http_auth(req)
        assert exc.value.status_code == 401


class TestIsWebsocketAuthorized:
    def test_loopback_allowed(self):
        ws = _make_websocket(client_host="127.0.0.1")
        assert is_websocket_authorized(ws) is True

    def test_testclient_allowed(self):
        ws = _make_websocket(client_host="testclient")
        assert is_websocket_authorized(ws) is True

    def test_external_rejected(self):
        ws = _make_websocket(client_host="8.8.8.8")
        assert is_websocket_authorized(ws) is False
