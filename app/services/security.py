"""
Page2PDF — Security Service
SSRF protection and URL security validation.
"""

import ipaddress
import socket
import logging
from urllib.parse import urlparse
from typing import Tuple

logger = logging.getLogger(__name__)

# Private and reserved IP ranges that must be blocked
BLOCKED_IP_RANGES = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.88.99.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("255.255.255.255/32"),
    # IPv6
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("ff00::/8"),
    ipaddress.ip_network("::ffff:0:0/96"),
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
    "metadata.google.internal",
    "metadata",
    "169.254.169.254",
}

ALLOWED_SCHEMES = {"http", "https"}


def is_private_ip(ip_str: str) -> bool:
    """Check if an IP address belongs to a private or reserved range."""
    try:
        ip = ipaddress.ip_address(ip_str)
        for network in BLOCKED_IP_RANGES:
            if ip in network:
                return True
        return False
    except ValueError:
        return True  # Treat unparseable IPs as private (safe default)


def validate_url_security(url: str) -> Tuple[bool, str]:
    """
    Validate a URL for security concerns (SSRF protection).
    Returns (is_safe, error_message).
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format."

    # Check scheme
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return False, f"URL scheme '{parsed.scheme}' is not allowed. Only HTTP and HTTPS are supported."

    # Check for empty hostname
    hostname = parsed.hostname
    if not hostname:
        return False, "URL must contain a valid hostname."

    # Check against blocked hostnames
    if hostname.lower() in BLOCKED_HOSTNAMES:
        return False, "Access to this host is not allowed."

    # Check for IP-based URLs
    try:
        ip = ipaddress.ip_address(hostname)
        if is_private_ip(str(ip)):
            return False, "Access to private/internal IP addresses is not allowed."
    except ValueError:
        # Not an IP address, it's a hostname - resolve and check
        pass

    # DNS resolution check
    try:
        resolved_ips = socket.getaddrinfo(hostname, None)
        for result in resolved_ips:
            ip_str = result[4][0]
            if is_private_ip(ip_str):
                logger.warning(f"URL {url} resolves to private IP {ip_str}")
                return False, "This URL resolves to a private/internal address and cannot be accessed."
    except socket.gaierror:
        return False, "Unable to resolve the hostname. Please check the URL."
    except Exception as e:
        logger.error(f"DNS resolution error for {url}: {e}")
        return False, "Unable to validate the URL. Please try again."

    # Check for common suspicious patterns
    if parsed.port and parsed.port not in (80, 443, 8080, 8443):
        # Allow common web ports only
        pass  # We'll allow unusual ports but log them
        logger.info(f"URL with non-standard port: {url}")

    return True, ""


def validate_redirect_url(url: str) -> Tuple[bool, str]:
    """Validate a redirect target URL (same rules as initial URL)."""
    return validate_url_security(url)
