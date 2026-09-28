"""Unit tests for the socket guard."""

from __future__ import annotations

import socket
import unittest

from socket_guard import install_socket_guard, is_loopback_host


class SocketGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        install_socket_guard()

    def test_is_loopback_host(self) -> None:
        self.assertTrue(is_loopback_host("127.0.0.1"))
        self.assertTrue(is_loopback_host("localhost"))
        self.assertTrue(is_loopback_host("::1"))
        self.assertTrue(is_loopback_host("127.0.0.2"))
        self.assertFalse(is_loopback_host("api.openai.com"))
        self.assertFalse(is_loopback_host("8.8.8.8"))
        self.assertFalse(is_loopback_host("example.com"))

    def test_external_connect_raises_runtime_error(self) -> None:
        s = socket.socket()
        try:
            with self.assertRaises(RuntimeError) as ctx:
                s.connect(("api.openai.com", 443))
            self.assertIn("External network connection blocked", str(ctx.exception))
        finally:
            s.close()

    def test_external_ip_connect_raises_runtime_error(self) -> None:
        s = socket.socket()
        try:
            with self.assertRaises(RuntimeError) as ctx:
                s.connect(("8.8.8.8", 53))
            self.assertIn("External network connection blocked", str(ctx.exception))
        finally:
            s.close()

    def test_loopback_connect_does_not_raise_runtime_error(self) -> None:
        s = socket.socket()
        try:
            # Connecting to a closed loopback port should raise ConnectionRefusedError or OSError from OS,
            # but NEVER RuntimeError from socket guard.
            try:
                s.connect(("127.0.0.1", 59999))
            except (ConnectionRefusedError, OSError) as exc:
                self.assertNotIsInstance(exc, RuntimeError)
        finally:
            s.close()


if __name__ == "__main__":
    unittest.main()
