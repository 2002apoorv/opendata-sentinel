import ipaddress
import socket
from urllib.parse import urlparse
from typing import Tuple

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback IPv4
    ipaddress.ip_network("10.0.0.0/8"),        # Private class A
    ipaddress.ip_network("172.16.0.0/12"),     # Private class B
    ipaddress.ip_network("192.168.0.0/16"),    # Private class C
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local / Cloud metadata (AWS, GCP, Azure)
    ipaddress.ip_network("0.0.0.0/8"),         # Current network
    ipaddress.ip_network("::1/128"),           # Loopback IPv6
    ipaddress.ip_network("fc00::/7"),          # Unique local IPv6
    ipaddress.ip_network("fe80::/10"),         # Link-local IPv6
]

FORBIDDEN_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "instance-data",
    "metadata.google.internal",
    "169.254.169.254",
}


def validate_source_url(url: str) -> Tuple[bool, str]:
    """
    Validates that a URL is safe to retrieve, mitigating Server-Side Request Forgery (SSRF).
    Only http and https schemes are permitted. Resolves hostnames to verify that the target IP
    does not belong to private networks, loopback addresses, or cloud metadata services.
    """
    if not url or not isinstance(url, str):
        return False, "URL cannot be empty."

    parsed = urlparse(url.strip())

    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Unsupported scheme '{parsed.scheme}'. Only http:// and https:// URLs are permitted."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL does not contain a valid hostname."

    hostname_lower = hostname.lower()
    if hostname_lower in FORBIDDEN_HOSTNAMES or hostname_lower.endswith(".local") or hostname_lower.endswith(".internal"):
        return False, f"Requests to '{hostname}' are blocked for security (SSRF prevention)."

    # Resolve IP addresses
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        return False, f"Could not resolve hostname '{hostname}': {str(e)}"
    except Exception as e:
        return False, f"DNS resolution failed: {str(e)}"

    for entry in addr_info:
        sockaddr = entry[4]
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            for blocked_net in BLOCKED_IP_NETWORKS:
                if ip_obj in blocked_net:
                    return False, f"Destination IP {ip_str} resolves to a private or restricted network range."
        except ValueError:
            return False, f"Invalid resolved IP address: {ip_str}"

    return True, "URL is valid and safe."
