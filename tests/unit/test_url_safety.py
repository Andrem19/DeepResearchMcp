"""Unit tests for app.fetch.url_safety — validate_url, SSRF protection."""

from __future__ import annotations

import pytest

from app.errors import URLSafetyError
from app.fetch.url_safety import validate_url

# ---------------------------------------------------------------------------
# Safe URLs — HTTPS OK
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_https_url_passes():
    assert validate_url("https://example.com/page") == "https://example.com/page"


@pytest.mark.unit
def test_http_url_passes():
    assert validate_url("http://example.com") == "http://example.com"


@pytest.mark.unit
def test_https_with_path_and_query():
    url = "https://example.com/docs?q=test&page=1"
    assert validate_url(url) == url


# ---------------------------------------------------------------------------
# Dangerous schemes
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_file_scheme_blocked():
    with pytest.raises(URLSafetyError, match="scheme"):
        validate_url("file:///etc/passwd")


@pytest.mark.unit
def test_ftp_scheme_blocked():
    with pytest.raises(URLSafetyError, match="scheme"):
        validate_url("ftp://example.com/file")


@pytest.mark.unit
def test_javascript_scheme_blocked():
    with pytest.raises(URLSafetyError, match="scheme"):
        validate_url("javascript:alert(1)")


@pytest.mark.unit
def test_data_scheme_blocked():
    with pytest.raises(URLSafetyError, match="scheme"):
        validate_url("data:text/html,<h1>hi</h1>")


# ---------------------------------------------------------------------------
# Localhost blocked
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_localhost_blocked():
    with pytest.raises(URLSafetyError, match="localhost"):
        validate_url("http://localhost:8080/admin")


@pytest.mark.unit
def test_localhost_localdomain_blocked():
    with pytest.raises(URLSafetyError, match="localhost"):
        validate_url("http://localhost.localdomain/test")


# ---------------------------------------------------------------------------
# Loopback IPs blocked
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_127_0_0_1_blocked():
    with pytest.raises(URLSafetyError, match="[Ll]oopback"):
        validate_url("http://127.0.0.1/secret")


@pytest.mark.unit
def test_127_0_0_2_blocked():
    with pytest.raises(URLSafetyError):
        validate_url("http://127.0.0.2/test")


# ---------------------------------------------------------------------------
# Cloud metadata IP blocked
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_169_254_169_254_blocked():
    with pytest.raises(URLSafetyError):
        validate_url("http://169.254.169.254/latest/meta-data/")


# ---------------------------------------------------------------------------
# Private IPv4 blocked
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_10_x_private_blocked():
    with pytest.raises(URLSafetyError, match="[Pp]rivate"):
        validate_url("http://10.0.0.1/")


@pytest.mark.unit
def test_172_16_private_blocked():
    with pytest.raises(URLSafetyError, match="[Pp]rivate"):
        validate_url("http://172.16.0.1/")


@pytest.mark.unit
def test_192_168_private_blocked():
    with pytest.raises(URLSafetyError, match="[Pp]rivate"):
        validate_url("http://192.168.1.1/")


# ---------------------------------------------------------------------------
# IPv6 loopback blocked
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ipv6_loopback_blocked():
    with pytest.raises(URLSafetyError, match="[Ll]oopback"):
        validate_url("http://[::1]/")


# ---------------------------------------------------------------------------
# IPv6-mapped private blocked
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ipv6_mapped_private_blocked():
    with pytest.raises(URLSafetyError):
        validate_url("http://[::ffff:192.168.1.1]/")


# ---------------------------------------------------------------------------
# Link-local blocked
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_link_local_blocked():
    with pytest.raises(URLSafetyError):
        validate_url("http://169.254.0.1/")


# ---------------------------------------------------------------------------
# Domain allowlist / blocklist
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_blocked_domain():
    with pytest.raises(URLSafetyError, match="[Bb]locked"):
        validate_url("https://evil.com/", blocked_domains=["evil.com"])


@pytest.mark.unit
def test_allowed_domain_passes():
    assert validate_url(
        "https://good.com/",
        allowed_domains=["good.com"],
    ) == "https://good.com/"


@pytest.mark.unit
def test_not_in_allowlist_blocked():
    with pytest.raises(URLSafetyError, match="allowlist"):
        validate_url(
            "https://other.com/",
            allowed_domains=["good.com"],
        )


@pytest.mark.unit
def test_blocked_case_insensitive():
    with pytest.raises(URLSafetyError):
        validate_url("https://Evil.COM/", blocked_domains=["evil.com"])


# ---------------------------------------------------------------------------
# No hostname
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_no_hostname_rejected():
    with pytest.raises(URLSafetyError, match="hostname"):
        validate_url("https://")
