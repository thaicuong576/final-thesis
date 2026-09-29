"""Test package root. Automatically installs the socket guard for unittest discovery."""

try:
    import socket_guard  # noqa: F401
except ImportError:
    from . import socket_guard  # noqa: F401
