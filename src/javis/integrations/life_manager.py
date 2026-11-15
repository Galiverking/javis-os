"""Life & Study Manager Integration for Javis OS.
Connects Javis OS directly to the Google Apps Script Web App API and local CLI/MCP tools.
"""

import datetime
import json
import logging
import os
import subprocess
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Primary Web App Endpoints & Paths
LIFE_MANAGER_WEB_APP_URL = (
    "https://script.google.com/macros/s/AKfycby7D79JtUjD3gCNuYDb6xlxJ2GPa1v_uIuypdbyQPRqxEmLai62WDyvn4XeJu5FId8mzQ/exec"
)
GDRIVE_PROJECT_DIR = "/home/apichet/GoogleDrive/Gemini/life_manager"
LOCAL_EXPERIMENT_DIR = "/home/apichet/for-hermes/02_experiments/life_manager"
LOCAL_STUDY_MANAGER_DIR = "/home/apichet/study-manager"


class LifeManagerClient:
    """Client for querying and managing Life & Study Manager via API and local tools."""

    def __init__(self, web_app_url: str = LIFE_MANAGER_WEB_APP_URL, gdrive_dir: str = GDRIVE_PROJECT_DIR):
        self.web_app_url = web_app_url
        self.gdrive_dir = gdrive_dir

    def open_web_app(self) -> bool:
        """Opens the Life & Study Manager Web App in the default browser (Brave)."""
        try:
            subprocess.Popen(
                ["xdg-open", self.web_app_url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return True
        except Exception as e:
            logger.error("Failed to open Life Manager URL: %s", e)
            return False

    def get_briefing(self, timeout_sec: float = 6.0) -> Optional[str]:
        """Fetch real-time morning / daily voice briefing text from API."""
        url = f"{self.web_app_url}?api=briefing"
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "JavisOS-VoiceAssistant/0.2"},
            )
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                text = resp.read().decode("utf-8").strip()
                if text:
                    return text
        except Exception as e:
            logger.warning("Failed to fetch briefing from Web App API: %s", e)

        # Fallback to local data if Drive is mounted and API fails/offline
        return self._get_local_briefing_fallback()

    def get_api_data(self, api_type: str = "stats", timeout_sec: float = 6.0) -> Optional[Dict[str, Any]]:
        """Fetch structured JSON data from Web App (stats, tasks, assignments, attendance, all)."""
        url = f"{self.web_app_url}?api={urllib.parse.quote(api_type)}"
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "JavisOS-VoiceAssistant/0.2"},
            )
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except Exception as e:
            logger.warning("Failed to fetch '%s' from Life Manager API: %s", api_type, e)
            return None

    def post_action(self, action: str, data: Optional[Dict[str, Any]] = None, timeout_sec: float = 8.0) -> Dict[str, Any]:
        """Post mutation action to Web App (e.g. add_task, complete_task)."""
        payload = {"action": action}
        if data:
            payload.update(data)
        encoded = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.web_app_url,
            data=encoded,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "JavisOS-VoiceAssistant/0.2",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except Exception as e:
            logger.error("Error executing post action '%s': %s", action, e)
            return {"success": False, "error": str(e)}

    def _get_local_briefing_fallback(self) -> str:
        """Fallback summary calculated from local JSON files in Google Drive if API is unreachable."""
        life_json = os.path.join(self.gdrive_dir, "data", "life_data.json")
        study_json = os.path.join(self.gdrive_dir, "data", "study_data.json")

        pending_tasks = 0
        pending_assignments = 0

        if os.path.exists(life_json):
            try:
                with open(life_json, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    pending_tasks = sum(1 for t in d.get("tasks", []) if not t.get("completed"))
            except Exception:
                pass

        if os.path.exists(study_json):
            try:
                with open(study_json, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    pending_assignments = sum(1 for a in d.get("assignments", []) if not a.get("completed"))
            except Exception:
                pass

        return f"ขณะนี้มีภารกิจค้างทำ {pending_tasks} งาน และการบ้านรอส่ง {pending_assignments} งานค่ะ"

    def get_today_timetable(self) -> str:
        """Fetch today's school timetable from local study manager or Drive."""
        days_en = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        now = datetime.datetime.now()
        day_en = days_en[now.weekday()]

        timetable_file = os.path.join(LOCAL_STUDY_MANAGER_DIR, "data", "timetable.json")
        if os.path.exists(timetable_file):
            try:
                with open(timetable_file, "r", encoding="utf-8") as f:
                    schedule = json.load(f)
                today_periods = [s for s in schedule if s.get("day") == day_en]
                if today_periods:
                    items = [f"คาบที่ {p.get('period')} {p.get('subject')} ห้อง {p.get('room')}" for p in today_periods]
                    return f"ตารางเรียนวันนี้มีดังนี้ครับ: {', '.join(items)} ครับ"
                else:
                    return "วันนี้ไม่มีตารางเรียนครับ พักผ่อนได้เต็มที่ครับ"
            except Exception as e:
                logger.warning("Error reading timetable: %s", e)
        return "ไม่สามารถดึงตารางเรียนได้ในขณะนี้ครับ"
