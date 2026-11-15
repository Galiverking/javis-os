"""PTT (Push-to-Talk) IPC Server & Client for Cinnamon Native Shortcut (Shift + Super).
Instead of flaky X11 key grabbing in process, uses Unix Domain Socket for 100% reliable IPC.
"""

import asyncio
import os
from pathlib import Path
from typing import Callable, Optional


class PTTListener:
    """Unix Socket listener for PTT events sent by `javis ptt`."""

    def __init__(self, socket_path: Optional[str] = None, on_ptt_toggle: Optional[Callable[[], None]] = None):
        self.socket_path = socket_path or str(Path.home() / ".local" / "share" / "javis" / "javis.sock")
        self.on_ptt_toggle = on_ptt_toggle
        self._server: Optional[asyncio.Server] = None
        self._running = False

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            data = await reader.readline()
            command = data.decode("utf-8").strip()
            if command == "PTT_TOGGLE":
                if self.on_ptt_toggle:
                    if asyncio.iscoroutinefunction(self.on_ptt_toggle):
                        await self.on_ptt_toggle()
                    else:
                        self.on_ptt_toggle()
                writer.write(b"OK: PTT_TOGGLED\n")
            elif command == "PING":
                writer.write(b"PONG\n")
            else:
                writer.write(b"ERR: UNKNOWN_COMMAND\n")
            await writer.drain()
        except Exception as e:
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    async def start(self):
        """Starts listening for PTT IPC commands."""
        sock_file = Path(self.socket_path)
        sock_file.parent.mkdir(parents=True, exist_ok=True)
        if sock_file.exists():
            sock_file.unlink()

        self._server = await asyncio.start_unix_server(self._handle_client, path=self.socket_path)
        self._running = True

    async def stop(self):
        """Stops the socket server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        sock_file = Path(self.socket_path)
        if sock_file.exists():
            sock_file.unlink()
        self._running = False


async def send_ptt_toggle(socket_path: Optional[str] = None) -> bool:
    """Client function invoked by CLI `javis ptt` to trigger listening."""
    sock_path = socket_path or str(Path.home() / ".local" / "share" / "javis" / "javis.sock")
    if not os.path.exists(sock_path):
        return False
    try:
        reader, writer = await asyncio.open_unix_connection(sock_path)
        writer.write(b"PTT_TOGGLE\n")
        await writer.drain()
        resp = await reader.readline()
        writer.close()
        await writer.wait_closed()
        return resp.strip() == b"OK: PTT_TOGGLED"
    except Exception:
        return False
