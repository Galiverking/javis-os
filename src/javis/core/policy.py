"""2-Tier Tool Runtime Policy & Registry with Zenity Hybrid Desktop Confirmation."""
from dataclasses import dataclass
from enum import Enum
import logging
import shutil
import subprocess
from typing import Any, Callable, Dict, List, Tuple
from javis.core.actions import (
    get_battery_status,
    get_current_date_str,
    get_current_time_str,
    get_system_resources,
    open_desktop_application,
    open_website_or_url,
    search_web_query,
    set_mute_volume,
)
from javis.core.memory import MemoryStore
from javis.integrations.life_manager import LifeManagerClient

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    SAFE = "SAFE"
    SENSITIVE = "SENSITIVE"


@dataclass
class ToolSpec:
    name: str
    description: str
    risk_level: RiskLevel
    parameters: Dict[str, str]
    handler: Callable[..., Tuple[bool, str]]


def ask_zenity_confirmation(title: str, prompt_text: str, timeout_sec: int = 15) -> bool:
    if not shutil.which("zenity"):
        return False
    try:
        res = subprocess.run(
            ["zenity", "--question", f"--title={title}", f"--text={prompt_text}", f"--timeout={timeout_sec}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout_sec + 2,
            check=False,
        )
        return res.returncode == 0
    except Exception:
        return False


class ToolPolicyEngine:
    """Executes registered OS and Life Manager tools under a strict 2-Tier Risk Policy."""

    def __init__(self, memory: MemoryStore, confirm_fn: Callable[[str, str], Any] = ask_zenity_confirmation) -> None:
        self.memory = memory
        self.confirm_fn = confirm_fn
        self.life_client = LifeManagerClient()
        self.tools: Dict[str, ToolSpec] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        self.register(ToolSpec("get_time", "Get current time", RiskLevel.SAFE, {}, lambda **_: (True, get_current_time_str())))
        self.register(ToolSpec("get_date", "Get current date", RiskLevel.SAFE, {}, lambda **_: (True, get_current_date_str())))
        self.register(ToolSpec("get_battery", "Check battery status", RiskLevel.SAFE, {}, lambda **_: (True, get_battery_status())))
        self.register(ToolSpec("get_system_status", "Check RAM and CPU", RiskLevel.SAFE, {}, lambda **_: (True, get_system_resources())))
        self.register(ToolSpec("mute_volume", "Mute/unmute speaker", RiskLevel.SAFE, {"mute": "bool"}, lambda mute=True, **_: set_mute_volume(bool(mute))))
        self.register(ToolSpec("open_app", "Launch desktop app", RiskLevel.SAFE, {"app_name": "str"}, lambda app_name="brave", **_: open_desktop_application(str(app_name))))
        self.register(ToolSpec("open_website", "Open website", RiskLevel.SAFE, {"target": "str"}, lambda target="google", **_: open_website_or_url(str(target))))
        self.register(ToolSpec("search_web", "Google search", RiskLevel.SAFE, {"query": "str"}, lambda query="", **_: search_web_query(str(query))))
        self.register(ToolSpec("life_briefing", "Life Manager daily briefing", RiskLevel.SAFE, {}, lambda **_: (True, self.life_client.get_briefing())))
        self.register(ToolSpec("life_timetable", "Grade 11/1 timetable", RiskLevel.SAFE, {}, lambda **_: (True, self.life_client.get_today_timetable())))
        self.register(ToolSpec("life_log_action", "Write action to Life Manager", RiskLevel.SENSITIVE, {"type": "str", "detail": "str"}, lambda type="task", detail="", **_: (True, str(self.life_client.post_action({"type": type, "detail": detail})))))

    def register(self, spec: ToolSpec) -> None:
        self.tools[spec.name] = spec

    def list_tools(self) -> List[ToolSpec]:
        return list(self.tools.values())

    async def execute_tool(self, name: str, args: Dict[str, Any]) -> Tuple[bool, str]:
        spec = self.tools.get(name)
        if spec is None:
            self.memory.log_tool_execution(name, args, "UNKNOWN", False, False, f"Unknown tool: {name}")
            return False, f"Unknown tool: {name}"

        confirmed = True
        if spec.risk_level == RiskLevel.SENSITIVE:
            res = self.confirm_fn("Javis OS Security Confirmation", f"Allow sensitive tool {spec.name} with {args}?")
            confirmed = (await res) if hasattr(res, "__await__") else bool(res)
            if not confirmed:
                msg = f"Denied {spec.name} by user confirmation policy."
                self.memory.log_tool_execution(name, args, spec.risk_level.value, False, False, msg)
                return False, msg

        try:
            ok, summary = spec.handler(**args)
        except Exception as exc:
            ok, summary = False, str(exc)

        self.memory.log_tool_execution(name, args, spec.risk_level.value, confirmed, ok, summary)
        return ok, summary
