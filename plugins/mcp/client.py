"""Generic MCP client with transparent socket / stdio transport.

The class targets the dual-transport ``mcp_local.py`` server that ships in
``~/projects/mazemaker-mcp/`` (commit 245e83f, branch
``feat/mcp-dual-listener``) but is deliberately backend-agnostic — any MCP
server that speaks the JSON-RPC 2.0 ``initialize`` / ``tools/list`` /
``tools/call`` triplet can be driven through it.

Two transports are supported, and the *same* :class:`MCPClient` instance
picks one transparently:

  * **Unix socket** — 4-byte big-endian length-prefixed UTF-8 JSON, matching
    ``embed_provider.py`` framing on the mazemaker-mcp side.  Preferred
    when the socket is reachable, because it shares the long-lived
    ``Mazemaker`` instance across every attached agent.
  * **stdio subprocess fallback** — newline-delimited JSON-RPC over stdin /
    stdout.  Used when the socket is missing or refuses the connection;
    spawns a child process running ``python3 mcp_local.py``.

Hermes callers don't need to know which transport is active; behaviour is
identical from the outside.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


_DEFAULT_SOCKET = str(Path.home() / ".mazemaker" / "mcp.sock")
_DEFAULT_FALLBACK_CMD: List[str] = [
    sys.executable or "python3",
    str(Path.home() / "projects" / "mazemaker-mcp" / "mcp_local.py"),
]


class MCPClientError(RuntimeError):
    """Raised for protocol-level / transport failures the caller can act on."""


class MCPClient:
    """Length-prefixed-socket *or* stdio JSON-RPC client to an MCP server.

    Construction does NOT block on a network round-trip — it just resolves
    which transport will be used.  Call :meth:`initialize` once before
    issuing :meth:`list_tools` / :meth:`call_tool`.

    Parameters
    ----------
    socket_path:
        Filesystem path to the Unix domain socket the server binds to.
        Defaults to ``~/.mazemaker/mcp.sock``.
    spawn_fallback_cmd:
        Argv of the stdio fallback process, used when the socket is not
        reachable.  ``None`` disables the fallback (socket-only mode).
        Defaults to ``[sys.executable, "~/projects/mazemaker-mcp/mcp_local.py"]``.
    connect_timeout:
        Seconds to wait for the initial socket ``connect()`` before falling
        back to stdio.  Default 1.5s — enough for a healthy local socket,
        short enough not to stall the agent's startup if the daemon is dead.
    request_timeout:
        Per-call ceiling for ``call_tool`` round-trips, in seconds.  ``None``
        means no timeout (rely on the underlying transport).
    """

    PROTOCOL_VERSION = "2024-11-05"
    CLIENT_INFO = {"name": "hermes-mcp-client", "version": "1.0.0"}

    def __init__(
        self,
        socket_path: Optional[str] = None,
        spawn_fallback_cmd: Optional[Sequence[str]] = _DEFAULT_FALLBACK_CMD,
        *,
        connect_timeout: float = 1.5,
        request_timeout: Optional[float] = 30.0,
    ) -> None:
        self._socket_path = os.path.expanduser(socket_path or _DEFAULT_SOCKET)
        self._fallback_cmd: Optional[List[str]] = (
            [os.path.expanduser(str(a)) for a in spawn_fallback_cmd]
            if spawn_fallback_cmd
            else None
        )
        self._connect_timeout = connect_timeout
        self._request_timeout = request_timeout

        # Transport state — exactly one of these is bound after _connect().
        self._sock: Optional[socket.socket] = None
        self._proc: Optional[subprocess.Popen] = None
        self._transport: Optional[str] = None

        # Concurrency: a single inflight request per client. Mazemaker
        # serialises on the server side anyway, but the wire-format
        # framing is not interleavable so we lock here too.
        self._lock = threading.Lock()
        self._next_id = 1
        self._initialised = False
        self._closed = False

        self._connect()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def transport(self) -> Optional[str]:
        """Return ``"socket"`` or ``"stdio"`` once connected, else ``None``."""
        return self._transport

    def initialize(self) -> Dict[str, Any]:
        """Send the JSON-RPC ``initialize`` handshake. Idempotent."""
        if self._initialised:
            return {}
        result = self._rpc(
            "initialize",
            {
                "protocolVersion": self.PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": self.CLIENT_INFO,
            },
        )
        # Best-effort "initialized" notification — server treats it as a
        # no-op but spec-compliant clients send it.
        try:
            self._notify("notifications/initialized", {})
        except Exception:
            pass
        self._initialised = True
        return result or {}

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return the server's ``tools/list`` response (the schemas)."""
        if not self._initialised:
            self.initialize()
        result = self._rpc("tools/list", {})
        return list((result or {}).get("tools") or [])

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Invoke ``tools/call`` and return the unwrapped result.

        On a successful tool call the MCP envelope looks like:
            {"content": [{"type": "text", "text": "<json blob>"}], "isError": false}
        We return the raw envelope unchanged so the caller can decide whether
        to parse the text payload as JSON or pass it through verbatim.
        """
        if not self._initialised:
            self.initialize()
        return self._rpc("tools/call", {"name": name, "arguments": arguments or {}})

    def close(self) -> None:
        """Tear down the transport. Safe to call multiple times."""
        if self._closed:
            return
        self._closed = True
        if self._sock is not None:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        if self._proc is not None:
            try:
                if self._proc.stdin and not self._proc.stdin.closed:
                    self._proc.stdin.close()
            except Exception:
                pass
            try:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
                    self._proc.wait(timeout=1.0)
            except Exception:
                pass
            self._proc = None

    # ------------------------------------------------------------------
    # Transport selection
    # ------------------------------------------------------------------

    def _connect(self) -> None:
        """Try the socket; fall back to spawning the stdio subprocess."""
        sock = self._try_socket()
        if sock is not None:
            self._sock = sock
            self._transport = "socket"
            logger.debug("MCPClient connected via unix socket %s", self._socket_path)
            return

        if self._fallback_cmd is None:
            raise MCPClientError(
                f"MCP socket {self._socket_path} unreachable and stdio fallback disabled"
            )

        self._proc = self._spawn_stdio()
        self._transport = "stdio"
        logger.debug("MCPClient connected via stdio subprocess: %s", " ".join(self._fallback_cmd))

    def _try_socket(self) -> Optional[socket.socket]:
        if not os.path.exists(self._socket_path):
            return None
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self._connect_timeout)
        try:
            sock.connect(self._socket_path)
        except OSError as exc:
            logger.debug("Socket connect to %s failed: %s", self._socket_path, exc)
            try:
                sock.close()
            except OSError:
                pass
            return None
        # Drop the connect-timeout — once we're talking, blocking I/O is fine
        # (length-prefix framing means we always know how many bytes to read).
        sock.settimeout(self._request_timeout)
        return sock

    def _spawn_stdio(self) -> subprocess.Popen:
        cmd = list(self._fallback_cmd or _DEFAULT_FALLBACK_CMD)
        env = dict(os.environ)
        # Prevent the spawned daemon from re-binding ITS socket if we already
        # found the socket missing — set a never-existing path so the spawned
        # process owns its own, fresh socket scoped to our PID. This is
        # belt-and-braces; the parent code already established that the
        # socket was unreachable.
        env.setdefault("MCP_SOCK_PATH", str(Path(self._socket_path).with_name(
            f"mcp.{os.getpid()}.sock")))
        try:
            proc = subprocess.Popen(  # noqa: S603 — argv comes from trusted config
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=env,
                bufsize=0,
                close_fds=True,
            )
        except FileNotFoundError as exc:
            raise MCPClientError(f"MCP fallback command not found: {cmd[0]}") from exc
        return proc

    # ------------------------------------------------------------------
    # JSON-RPC plumbing
    # ------------------------------------------------------------------

    def _rpc(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            req_id = self._next_id
            self._next_id += 1
            payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send(data)
            response_raw = self._recv()
        if response_raw is None:
            raise MCPClientError(f"MCP server closed connection during {method}")
        try:
            response = json.loads(response_raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MCPClientError(f"Invalid JSON response from {method}: {exc}") from exc
        if isinstance(response, dict) and "error" in response and response["error"]:
            err = response["error"]
            raise MCPClientError(f"MCP {method} error {err.get('code')}: {err.get('message')}")
        if isinstance(response, dict):
            return response.get("result")
        return None

    def _notify(self, method: str, params: Dict[str, Any]) -> None:
        """Fire-and-forget JSON-RPC notification (no id, no response)."""
        with self._lock:
            payload = {"jsonrpc": "2.0", "method": method, "params": params}
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send(data)
            # Socket transport responds with empty frame for notifications;
            # stdio transport sends nothing. Drain socket frame if applicable.
            if self._transport == "socket":
                try:
                    _ = self._recv_socket_frame()
                except Exception:
                    pass

    # ---- transport-specific I/O ----

    def _send(self, data: bytes) -> None:
        if self._transport == "socket":
            self._send_framed(data)
        elif self._transport == "stdio":
            self._send_line(data)
        else:
            raise MCPClientError("MCPClient is not connected")

    def _recv(self) -> Optional[bytes]:
        if self._transport == "socket":
            return self._recv_socket_frame()
        if self._transport == "stdio":
            return self._recv_line()
        raise MCPClientError("MCPClient is not connected")

    # ---- socket framing (4-byte big-endian length + body) ----

    def _send_framed(self, data: bytes) -> None:
        assert self._sock is not None
        header = struct.pack("!I", len(data))
        try:
            self._sock.sendall(header + data)
        except OSError as exc:
            raise MCPClientError(f"socket send failed: {exc}") from exc

    def _recv_socket_frame(self) -> Optional[bytes]:
        assert self._sock is not None
        header = self._recv_exactly_socket(4)
        if header is None:
            return None
        (msg_len,) = struct.unpack("!I", header)
        if msg_len == 0:
            return b""
        return self._recv_exactly_socket(msg_len)

    def _recv_exactly_socket(self, n: int) -> Optional[bytes]:
        assert self._sock is not None
        chunks: list[bytes] = []
        remaining = n
        while remaining > 0:
            try:
                chunk = self._sock.recv(remaining)
            except OSError as exc:
                raise MCPClientError(f"socket recv failed: {exc}") from exc
            if not chunk:
                return None
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    # ---- stdio framing (newline-delimited JSON) ----

    def _send_line(self, data: bytes) -> None:
        assert self._proc is not None and self._proc.stdin is not None
        try:
            self._proc.stdin.write(data + b"\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise MCPClientError(f"stdio send failed: {exc}") from exc

    def _recv_line(self) -> Optional[bytes]:
        assert self._proc is not None and self._proc.stdout is not None
        deadline = (
            time.monotonic() + self._request_timeout if self._request_timeout else None
        )
        while True:
            line = self._proc.stdout.readline()
            if not line:
                return None
            stripped = line.rstrip(b"\r\n")
            if not stripped:
                # Skip blank lines (some servers emit a leading blank on warmup).
                if deadline and time.monotonic() > deadline:
                    raise MCPClientError("stdio recv timed out")
                continue
            # Mazemaker's embed-server cold-load and a few other code paths
            # leak status banners to stdout — including ``[embed-server]`` /
            # ``[embed] Connected …`` lines that start with ``[``.  Those
            # land between our JSON-RPC frames and would crash json.loads.
            # Filter to JSON envelopes by attempting a parse — anything
            # that isn't a valid JSON object or array gets dropped.
            #
            # Single-response replies are always objects (``{"jsonrpc":…}``)
            # and batch replies are arrays — both must round-trip through
            # json.loads cleanly. Banners like ``[embed-server] CUDA: …`` do
            # not, so they fail the probe and we skip the line.
            try:
                json.loads(stripped)
            except (ValueError, json.JSONDecodeError):
                if deadline and time.monotonic() > deadline:
                    raise MCPClientError("stdio recv timed out")
                continue
            return stripped

    # ------------------------------------------------------------------
    # Context manager sugar
    # ------------------------------------------------------------------

    def __enter__(self) -> "MCPClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
