"""Extension catalog abstraction supporting local indices, remote HTTPS indices, and offline caching."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from urllib.request import HTTPRedirectHandler, Request, build_opener

from packages.review.extensions.errors import CatalogError, ExtensionSecurityError
from packages.review.extensions.policy import validate_safe_url

DEFAULT_CACHE_DIR = Path.home() / ".logicfalcon" / "cache"


@dataclass
class CatalogVersionEntry:
    """Metadata for a specific released version of an extension in the catalog."""

    version: str
    source_url: str
    integrity_hash: str | None = None
    min_logicfalcon: str = ">=0.1.4"
    min_python: str = ">=3.12"
    capabilities: list[str] = field(default_factory=list)


@dataclass
class CatalogItem:
    """Extension listing within the catalog."""

    id: str
    name: str
    description: str
    author: str
    latest_version: str
    versions: dict[str, CatalogVersionEntry] = field(default_factory=dict)
    deprecated: bool = False
    deprecation_reason: str | None = None
    revoked: bool = False
    revocation_reason: str | None = None


class BaseCatalogProvider(ABC):
    """Abstract base provider for querying extension catalogs."""

    @abstractmethod
    def get_index(self) -> list[CatalogItem]:
        """Returns all valid extension listings from the catalog."""
        raise NotImplementedError

    def get_item(self, extension_id: str) -> CatalogItem | None:
        """Looks up a specific extension by its identifier."""
        norm_id = extension_id.strip().lower()
        for item in self.get_index():
            if item.id.lower() == norm_id:
                return item
        return None

    def search(self, query: str) -> list[CatalogItem]:
        """Searches catalog by keyword in ID, name, or description."""
        q = query.strip().lower()
        results: list[CatalogItem] = []
        for item in self.get_index():
            if q in item.id.lower() or q in item.name.lower() or q in item.description.lower():
                results.append(item)
        return results


class LocalCatalogProvider(BaseCatalogProvider):
    """Catalog provider that loads extensions from a local JSON index file."""

    def __init__(self, index_file: Path | str) -> None:
        self.index_file = Path(index_file)

    def get_index(self) -> list[CatalogItem]:
        if not self.index_file.is_file():
            return []
        try:
            raw_data = json.loads(self.index_file.read_text(encoding="utf-8"))
            return _parse_catalog_items(raw_data)
        except Exception as e:
            raise CatalogError(f"Failed to read local catalog '{self.index_file}': {e}") from e


class SafeRedirectHandler(HTTPRedirectHandler):
    """Hardened HTTP redirect handler that strictly validates every redirect destination.

    Enforces:
    - Re-validation of each redirect target against SSRF boundaries (loopback, private, IMDS).
    - Maximum redirect depth (default: 5) to prevent infinite loops.
    - Cycle / repeat destination detection.
    - Malformed and control-character header protection.
    - Preserves HTTPS/TLS verification.
    """

    def __init__(
        self,
        max_redirects: int = 5,
        allowed_schemes: tuple[str, ...] = ("https", "http"),
    ) -> None:
        super().__init__()
        self.max_redirects = max_redirects
        self.allowed_schemes = allowed_schemes
        self.redirect_count = 0
        self.visited_urls: set[str] = set()

    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Request | None:
        self.redirect_count += 1
        if self.redirect_count > self.max_redirects:
            raise CatalogError(
                f"Exceeded maximum redirect limit of {self.max_redirects} while fetching catalog."
            )

        if not newurl or not isinstance(newurl, str):
            raise CatalogError("Catalog redirect response contained missing or malformed Location header.")

        # Sanitize whitespace and reject control characters that could induce header injection
        target_raw = newurl.strip()
        if any(c in target_raw for c in ("\r", "\n", "\0")):
            raise CatalogError("Redirect destination contained illegal control characters.")

        # Resolve relative redirects against parent request URL
        target_url = urljoin(req.full_url, target_raw)

        # Detect redirect cycle
        if target_url in self.visited_urls:
            raise CatalogError(f"Redirect loop detected targeting '{target_url}'.")
        self.visited_urls.add(target_url)

        # Strictly validate destination against SSRF rules (private IPs, loopback, IMDS, forbidden schemes)
        validate_safe_url(target_url, allowed_schemes=self.allowed_schemes)

        # Construct new request via standard library implementation
        return super().redirect_request(req, fp, code, msg, headers, target_url)


class RemoteCatalogProvider(BaseCatalogProvider):
    """Remote HTTPS catalog provider with SSRF validation, redirect re-validation, timeouts, and local offline cache."""

    def __init__(
        self,
        index_url: str,
        cache_file: Path | None = None,
        timeout_seconds: float = 10.0,
        max_bytes: int = 5 * 1024 * 1024,
        max_redirects: int = 5,
        allowed_schemes: tuple[str, ...] = ("https", "http"),
    ) -> None:
        self.index_url = index_url
        self.cache_file = cache_file or (DEFAULT_CACHE_DIR / "catalog_cache.json")
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes
        self.max_redirects = max_redirects
        self.allowed_schemes = allowed_schemes

    def get_index(self) -> list[CatalogItem]:
        try:
            # Validate initial URL scheme and protect against SSRF before connecting
            validate_safe_url(self.index_url, allowed_schemes=self.allowed_schemes)

            req = Request(
                self.index_url,
                headers={"User-Agent": "LogicFalcon-Extension-Platform/0.1.5"},
            )
            redirect_handler = SafeRedirectHandler(
                max_redirects=self.max_redirects,
                allowed_schemes=self.allowed_schemes,
            )
            opener = build_opener(redirect_handler)

            with opener.open(req, timeout=self.timeout_seconds) as resp:
                content = resp.read(self.max_bytes)
                raw_json = json.loads(content.decode("utf-8"))

                # Write fresh cache atomically
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                tmp_cache = self.cache_file.with_suffix(".tmp")
                tmp_cache.write_text(json.dumps(raw_json, indent=2), encoding="utf-8")
                tmp_cache.replace(self.cache_file)

                return _parse_catalog_items(raw_json)

        except (ExtensionSecurityError, CatalogError) as err:
            # Security violations (SSRF, prohibited IPs, bad schemes) and redirect errors fail closed immediately
            # They MUST NEVER fall back to offline cache!
            raise CatalogError(f"Failed to fetch catalog from '{self.index_url}': {err}") from err
        except Exception as net_err:
            # Transient network/connectivity errors fall back to valid offline cache if available
            if self.cache_file.is_file():
                try:
                    cached_data = json.loads(self.cache_file.read_text(encoding="utf-8"))
                    return _parse_catalog_items(cached_data)
                except Exception:
                    pass
            raise CatalogError(f"Failed to fetch catalog from '{self.index_url}' and no valid cache available: {net_err}") from net_err


def _parse_catalog_items(raw_data: Any) -> list[CatalogItem]:
    """Strictly validates and parses catalog JSON items, skipping malformed or malicious entries."""
    if not isinstance(raw_data, (list, dict)):
        return []

    entries = raw_data if isinstance(raw_data, list) else raw_data.get("extensions", [])
    parsed: list[CatalogItem] = []

    for item in entries:
        if not isinstance(item, dict):
            continue
        ext_id = item.get("id")
        name = item.get("name")
        latest_version = item.get("latest_version")
        if not ext_id or not name or not latest_version:
            continue

        versions_dict: dict[str, CatalogVersionEntry] = {}
        for ver_str, ver_data in item.get("versions", {}).items():
            if isinstance(ver_data, dict):
                versions_dict[ver_str] = CatalogVersionEntry(
                    version=ver_str,
                    source_url=ver_data.get("source_url", ""),
                    integrity_hash=ver_data.get("integrity_hash"),
                    min_logicfalcon=ver_data.get("min_logicfalcon", ">=0.1.4"),
                    min_python=ver_data.get("min_python", ">=3.12"),
                    capabilities=ver_data.get("capabilities", []),
                )

        parsed.append(
            CatalogItem(
                id=ext_id,
                name=name,
                description=item.get("description", ""),
                author=item.get("author", "Unknown"),
                latest_version=latest_version,
                versions=versions_dict,
                deprecated=bool(item.get("deprecated", False)),
                deprecation_reason=item.get("deprecation_reason"),
                revoked=bool(item.get("revoked", False)),
                revocation_reason=item.get("revocation_reason"),
            )
        )
    return sorted(parsed, key=lambda x: x.id)
