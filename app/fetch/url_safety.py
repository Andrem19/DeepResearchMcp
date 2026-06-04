"""URL Safety Guard — blocks SSRF, private IPs, and dangerous schemes."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

from app.errors import URLSafetyError

# Allowed URL schemes
_ALLOWED_SCHEMES = {"http", "https"}

# Blocked schemes (explicit deny)
_BLOCKED_SCHEMES = {"file", "ftp", "gopher", "data", "javascript", "vbscript", "blob"}


def validate_url(url: str, *, allowed_domains: list[str] | None = None,
                 blocked_domains: list[str] | None = None) -> str:
    """Validate a URL for safety. Returns the URL if safe.

    Raises URLSafetyError if the URL is dangerous.
    """
    parsed = urlparse(url)

    # Check scheme
    scheme = parsed.scheme.lower()
    if scheme in _BLOCKED_SCHEMES:
        raise URLSafetyError(f"Blocked URL scheme: {scheme}")
    if scheme not in _ALLOWED_SCHEMES:
        raise URLSafetyError(f"Disallowed URL scheme: {scheme}")

    hostname = parsed.hostname
    if not hostname:
        raise URLSafetyError("URL has no hostname")

    hostname_lower = hostname.lower()

    # Check blocked domains
    if blocked_domains and hostname_lower in blocked_domains:
        raise URLSafetyError(f"Blocked domain: {hostname_lower}")

    # Check allowed domains (if set, only these are allowed)
    if allowed_domains and hostname_lower not in allowed_domains:
        raise URLSafetyError(f"Domain not in allowlist: {hostname_lower}")

    # Check for localhost
    if hostname_lower in ("localhost", "localhost.localdomain"):
        raise URLSafetyError("localhost is not allowed")

    # Check IP addresses
    _check_ip(hostname)

    return url


def _check_ip(hostname: str) -> None:
    """Check if hostname is a dangerous IP address."""
    # IPv6 in brackets
    clean = hostname.strip("[]")

    try:
        ip = ipaddress.ip_address(clean)
    except ValueError:
        # Not an IP address — it's a domain name, OK
        return

    # Loopback
    if ip.is_loopback:
        raise URLSafetyError(f"Loopback IP not allowed: {ip}")

    # Private (10.x, 172.16-31.x, 192.168.x)
    if ip.is_private:
        raise URLSafetyError(f"Private IP not allowed: {ip}")

    # Link-local (169.254.x.x, fe80::)
    if ip.is_link_local:
        raise URLSafetyError(f"Link-local IP not allowed: {ip}")

    # Reserved / multicast / unspecified
    if ip.is_reserved or ip.is_multicast or ip.is_unspecified:
        raise URLSafetyError(f"Reserved IP not allowed: {ip}")

    # Cloud metadata endpoint (169.254.169.254 handled by link-local, but be explicit)
    if clean == "169.254.169.254":
        raise URLSafetyError("Cloud metadata IP not allowed")

    # IPv4-mapped IPv6 that resolve to private
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        mapped = ip.ipv4_mapped
        if mapped.is_loopback or mapped.is_private or mapped.is_link_local:
            raise URLSafetyError(f"IPv6-mapped private IP not allowed: {ip}")
