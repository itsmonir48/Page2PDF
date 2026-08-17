"""
Page2PDF — Security Tests
Tests for URL validation and SSRF protection.
"""
import pytest
from app.services.security import validate_url_security, is_private_ip


class TestURLSecurity:
    """Tests for URL security validation."""

    def test_valid_http_url(self):
        is_safe, _ = validate_url_security("http://example.com/article")
        assert is_safe

    def test_valid_https_url(self):
        is_safe, _ = validate_url_security("https://www.example.com/article")
        assert is_safe

    def test_invalid_scheme_ftp(self):
        is_safe, error = validate_url_security("ftp://example.com/file")
        assert not is_safe
        assert "scheme" in error.lower()

    def test_invalid_scheme_file(self):
        is_safe, error = validate_url_security("file:///etc/passwd")
        assert not is_safe

    def test_localhost_blocked(self):
        is_safe, error = validate_url_security("http://localhost/admin")
        assert not is_safe

    def test_127_0_0_1_blocked(self):
        is_safe, error = validate_url_security("http://127.0.0.1/")
        assert not is_safe

    def test_private_ip_10_blocked(self):
        is_safe, error = validate_url_security("http://10.0.0.1/")
        assert not is_safe

    def test_private_ip_172_blocked(self):
        is_safe, error = validate_url_security("http://172.16.0.1/")
        assert not is_safe

    def test_private_ip_192_blocked(self):
        is_safe, error = validate_url_security("http://192.168.1.1/")
        assert not is_safe

    def test_ipv6_loopback_blocked(self):
        is_safe, error = validate_url_security("http://[::1]/")
        assert not is_safe

    def test_empty_hostname(self):
        is_safe, error = validate_url_security("http://")
        assert not is_safe

    def test_no_scheme(self):
        is_safe, error = validate_url_security("example.com")
        assert not is_safe

    def test_metadata_endpoint_blocked(self):
        is_safe, error = validate_url_security("http://169.254.169.254/latest/meta-data/")
        assert not is_safe


class TestPrivateIP:
    """Tests for private IP detection."""

    def test_loopback(self):
        assert is_private_ip("127.0.0.1")

    def test_class_a(self):
        assert is_private_ip("10.255.255.255")

    def test_class_b(self):
        assert is_private_ip("172.31.0.1")

    def test_class_c(self):
        assert is_private_ip("192.168.0.1")

    def test_public_ip(self):
        assert not is_private_ip("8.8.8.8")

    def test_another_public(self):
        assert not is_private_ip("1.1.1.1")

    def test_invalid_ip(self):
        assert is_private_ip("not-an-ip")
