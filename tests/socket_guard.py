"""Socket guard to block non-loopback network calls during tests.

Ensures no test makes real external network requests.
Only loopback addresses (127.0.0.1, ::1, localhost) are permitted.
"""

from __future__ import annotations

import ipaddress
import socket
from typing import Any

_ORIGINAL_CONNECT = socket.socket.connect
_ORIGINAL_CONNECT_EX = socket.socket.connect_ex
_GUARD_INSTALLED = False


def is_loopback_host(host: Any) -> bool:
    """Return True if host resolves to a loopback interface."""
    if not isinstance(host, str):
        return False
    host_clean = host.strip().lower()
    if host_clean in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return True
    try:
        ip = ipaddress.ip_address(host_clean)
        return ip.is_loopback
    except ValueError:
        return False


def _guarded_connect(self: socket.socket, address: Any) -> None:
    if isinstance(address, (tuple, list)) and len(address) > 0:
        host = address[0]
        if not is_loopback_host(host):
            raise RuntimeError(
                f"External network connection blocked in test suite: attempted connection to {address}. "
                "Tests must use offline/mock clients or loopback only."
            )
    return _ORIGINAL_CONNECT(self, address)


def _guarded_connect_ex(self: socket.socket, address: Any) -> int:
    if isinstance(address, (tuple, list)) and len(address) > 0:
        host = address[0]
        if not is_loopback_host(host):
            raise RuntimeError(
                f"External network connection blocked in test suite: attempted connection to {address}. "
                "Tests must use offline/mock clients or loopback only."
            )
    return _ORIGINAL_CONNECT_EX(self, address)


def install_socket_guard() -> None:
    """Install socket.connect guard to block non-loopback network calls."""
    global _GUARD_INSTALLED
    if not _GUARD_INSTALLED:
        socket.socket.connect = _guarded_connect
        socket.socket.connect_ex = _guarded_connect_ex
        _GUARD_INSTALLED = True


def uninstall_socket_guard() -> None:
    """Uninstall socket.connect guard."""
    global _GUARD_INSTALLED
    if _GUARD_INSTALLED:
        socket.socket.connect = _ORIGINAL_CONNECT
        socket.socket.connect_ex = _ORIGINAL_CONNECT_EX
        _GUARD_INSTALLED = False


# Install guard immediately upon module import
install_socket_guard()
