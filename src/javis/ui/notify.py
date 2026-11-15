"""Desktop Notification Handler using Linux native notify-send.
Asynchronous, non-blocking notification dispatch.
"""

import asyncio
import shutil
import subprocess
from typing import Optional


def send_notification(title: str, message: str, timeout_ms: int = 3000, urgency: str = "normal") -> None:
    """Send desktop notification via notify-send asynchronously."""
    if not shutil.which("notify-send"):
        return

    cmd = [
        "notify-send",
        "-a", "Javis OS",
        "-t", str(timeout_ms),
        "-u", urgency,
        title,
        message,
    ]
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


async def send_notification_async(title: str, message: str, timeout_ms: int = 3000) -> None:
    """Async wrapper for non-blocking notification."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, send_notification, title, message, timeout_ms)
