"""Tests for Extension Catalog and Ecosystem (Phase 9)."""

import json
from pathlib import Path
from urllib.request import Request

import pytest

from packages.review.extensions.catalog import (
    CatalogError,
    LocalCatalogProvider,
    RemoteCatalogProvider,
    SafeRedirectHandler,
)
from packages.review.extensions.errors import ExtensionSecurityError


@pytest.fixture
def sample_catalog_data() -> dict:
    return {
        "schema_version": "1.0.0",
        "extensions": [
            {
                "id": "org.security.secrets-scanner",
                "name": "Secrets & Key Scanner",
                "description": "Scans repository commits and files for leaked API keys.",
                "author": "Security Team",
                "latest_version": "1.2.0",
                "versions": {
                    "1.2.0": {
                        "source_url": "https://extensions.logicfalcon.org/pkgs/secrets-scanner-1.2.0.tar.gz",
                        "integrity_hash": "sha256:abc12345",
                        "min_logicfalcon": ">=0.1.4",
                    }
                },
            },
            {
                "id": "org.legacy.old-plugin",
                "name": "Deprecated Legacy Plugin",
                "description": "Old plugin replaced by core features.",
                "author": "Legacy Authors",
                "latest_version": "0.5.0",
                "deprecated": True,
                "deprecation_reason": "Superseded by logicfalcon unified engine.",
                "versions": {"0.5.0": {}},
            },
            {
                "id": "org.malicious.revoked-tool",
                "name": "Revoked Tool",
                "description": "Flagged as unsafe.",
                "author": "Bad Actor",
                "latest_version": "1.0.0",
                "revoked": True,
                "revocation_reason": "Violated security policy.",
                "versions": {"1.0.0": {}},
            },
            # Malformed entry (missing name and version) should be skipped cleanly
            {"id": "invalid-entry-missing-name"},
        ],
    }


def test_local_catalog_provider(tmp_path: Path, sample_catalog_data: dict) -> None:
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text(json.dumps(sample_catalog_data), encoding="utf-8")

    provider = LocalCatalogProvider(catalog_file)
    items = provider.get_index()

    # Should parse 3 valid items and skip the malformed entry
    assert len(items) == 3

    # Inspect items
    secrets_item = provider.get_item("org.security.secrets-scanner")
    assert secrets_item is not None
    assert secrets_item.name == "Secrets & Key Scanner"
    assert "1.2.0" in secrets_item.versions
    assert secrets_item.deprecated is False
    assert secrets_item.revoked is False

    deprecated_item = provider.get_item("org.legacy.old-plugin")
    assert deprecated_item is not None
    assert deprecated_item.deprecated is True
    assert "Superseded" in (deprecated_item.deprecation_reason or "")

    revoked_item = provider.get_item("org.malicious.revoked-tool")
    assert revoked_item is not None
    assert revoked_item.revoked is True
    assert "security policy" in (revoked_item.revocation_reason or "")

    # Search keyword
    matches = provider.search("scanner")
    assert len(matches) == 1
    assert matches[0].id == "org.security.secrets-scanner"


def test_remote_catalog_ssrf_protection() -> None:
    # Attempting to fetch catalog from private or loopback IP must be blocked by SSRF defense
    provider = RemoteCatalogProvider(index_url="http://127.0.0.1:8080/catalog.json")
    with pytest.raises(CatalogError, match="Failed to fetch catalog"):
        provider.get_index()


def test_safe_redirect_handler_blocks_loopback() -> None:
    handler = SafeRedirectHandler(max_redirects=5)
    req = Request("https://extensions.logicfalcon.org/catalog.json")
    with pytest.raises(ExtensionSecurityError, match=r"127\.0\.0\.1"):
        handler.redirect_request(req, None, 302, "Found", {}, "http://127.0.0.1:8080/internal.json")


def test_safe_redirect_handler_blocks_cloud_metadata() -> None:
    handler = SafeRedirectHandler(max_redirects=5)
    req = Request("https://extensions.logicfalcon.org/catalog.json")
    with pytest.raises(ExtensionSecurityError, match=r"169\.254\.169\.254"):
        handler.redirect_request(req, None, 302, "Found", {}, "http://169.254.169.254/latest/meta-data/")


def test_safe_redirect_handler_blocks_rfc1918_private_ip() -> None:
    handler = SafeRedirectHandler(max_redirects=5)
    req = Request("https://extensions.logicfalcon.org/catalog.json")
    with pytest.raises(ExtensionSecurityError, match=r"10\.0\.0\.1"):
        handler.redirect_request(req, None, 301, "Moved", {}, "http://10.0.0.1/catalog.json")


def test_safe_redirect_handler_blocks_forbidden_scheme() -> None:
    handler = SafeRedirectHandler(max_redirects=5)
    req = Request("https://extensions.logicfalcon.org/catalog.json")
    with pytest.raises(ExtensionSecurityError, match="Prohibited URL scheme"):
        handler.redirect_request(req, None, 302, "Found", {}, "file:///etc/passwd")


def test_safe_redirect_handler_blocks_dns_rebinding(monkeypatch: pytest.MonkeyPatch) -> None:
    # Simulate a domain that resolves to an RFC 1918 private IP (DNS rebinding)
    import socket

    def mock_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.50", 0))]

    monkeypatch.setattr("socket.getaddrinfo", mock_getaddrinfo)
    handler = SafeRedirectHandler(max_redirects=5)
    req = Request("https://extensions.logicfalcon.org/catalog.json")
    with pytest.raises(ExtensionSecurityError, match="resolves to private/reserved IP"):
        handler.redirect_request(req, None, 302, "Found", {}, "https://rebound-domain.org/catalog.json")


def test_safe_redirect_handler_blocks_redirect_cycles(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    def mock_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr("socket.getaddrinfo", mock_getaddrinfo)
    handler = SafeRedirectHandler(max_redirects=5)
    req = Request("https://extensions.logicfalcon.org/catalog.json")
    r1 = handler.redirect_request(req, None, 302, "Found", {}, "https://cdn.logicfalcon.org/catalog-v2.json")
    assert r1 is not None
    with pytest.raises(CatalogError, match="Redirect loop detected"):
        handler.redirect_request(r1, None, 302, "Found", {}, "https://cdn.logicfalcon.org/catalog-v2.json")


def test_safe_redirect_handler_bounds_redirect_count(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    def mock_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr("socket.getaddrinfo", mock_getaddrinfo)
    handler = SafeRedirectHandler(max_redirects=3)
    req = Request("https://extensions.logicfalcon.org/catalog.json")
    r1 = handler.redirect_request(req, None, 302, "Found", {}, "https://cdn1.logicfalcon.org/catalog.json")
    r2 = handler.redirect_request(r1, None, 302, "Found", {}, "https://cdn2.logicfalcon.org/catalog.json")
    r3 = handler.redirect_request(r2, None, 302, "Found", {}, "https://cdn3.logicfalcon.org/catalog.json")
    with pytest.raises(CatalogError, match="Exceeded maximum redirect limit"):
        handler.redirect_request(r3, None, 302, "Found", {}, "https://cdn4.logicfalcon.org/catalog.json")


def test_safe_redirect_handler_rejects_malformed_control_characters() -> None:
    handler = SafeRedirectHandler(max_redirects=5)
    req = Request("https://extensions.logicfalcon.org/catalog.json")
    with pytest.raises(CatalogError, match="illegal control characters"):
        handler.redirect_request(req, None, 302, "Found", {}, "https://cdn.logicfalcon.org/\r\nInjected-Header: evil")


def test_safe_redirect_handler_allows_safe_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    def mock_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr("socket.getaddrinfo", mock_getaddrinfo)
    handler = SafeRedirectHandler(max_redirects=5)
    req = Request("https://extensions.logicfalcon.org/v1/catalog.json")
    new_req = handler.redirect_request(req, None, 302, "Found", {}, "https://cdn.logicfalcon.org/v2/catalog.json")
    assert new_req is not None
    assert new_req.full_url == "https://cdn.logicfalcon.org/v2/catalog.json"


def test_safe_redirect_handler_resolves_relative_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    def mock_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr("socket.getaddrinfo", mock_getaddrinfo)
    handler = SafeRedirectHandler(max_redirects=5)
    req = Request("https://extensions.logicfalcon.org/v1/catalog.json")
    new_req = handler.redirect_request(req, None, 301, "Moved", {}, "/v2/catalog.json")
    assert new_req is not None
    assert new_req.full_url == "https://extensions.logicfalcon.org/v2/catalog.json"


def test_remote_catalog_offline_cache_fallback(tmp_path: Path, sample_catalog_data: dict) -> None:
    cache_file = tmp_path / "catalog_cache.json"
    cache_file.write_text(json.dumps(sample_catalog_data), encoding="utf-8")

    # Point to an unreachable URL, but with valid pre-existing cache file
    provider = RemoteCatalogProvider(
        index_url="https://non-existent-domain-123456789.org/catalog.json",
        cache_file=cache_file,
    )

    # Should gracefully fall back to cache
    items = provider.get_index()
    assert len(items) == 3
    assert provider.get_item("org.security.secrets-scanner") is not None
