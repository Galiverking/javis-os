"""Local Fast-Path Intent Router for Javis OS.
Directly handles common local desktop actions with P50 <= 0.8s latency.
Uses strict single-intent whitelist to prevent false positives.
Compounds and complex queries (> 35 chars or conjunctions) automatically bypass to Tier 2 (Hermes).
"""

import logging
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Optional

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

logger = logging.getLogger(__name__)


@dataclass
class FastPathResult:
    matched: bool
    action: Optional[str] = None
    speech_response: Optional[str] = None
    error: Optional[str] = None


class FastPathRouter:
    """Matches single-intent desktop commands and executes them directly."""

    COMPOUND_REGEX = re.compile(r"(\s*(และ|พร้อมกับ|ต่อด้วย|จากนั้น)\s*|แล้ว(ค่อย|ก็|\S+))")

    def is_compound(self, text: str) -> bool:
        """Checks if text contains conjunctions indicating compound multi-step tasks."""
        clean = text.strip()
        if len(clean) > 35:
            return True
        if re.search(r"^(ตอนนี้)?(กี่โมง|กี่หลง|เวลาเท่าไหร่)(แล้ว)?$", clean):
            return False
        return bool(self.COMPOUND_REGEX.search(clean))

    def match(self, text: str) -> Optional[FastPathResult]:
        """Convenience method returning FastPathResult if matched, else None."""
        res = self.route(text)
        return res if res.matched else None

    def route(self, text: str) -> FastPathResult:
        """Route transcript to local command or return matched=False to fallback to Hermes."""
        clean = text.strip()

        # Rule 0: If compound or long, bypass directly to Tier 2
        if self.is_compound(clean):
            return FastPathResult(matched=False)

        # Rule 1: Get Time ("กี่โมงแล้ว", "ตอนนี้กี่โมง", "ตอนนี้กี่โมงแล้ว", "เวลาเท่าไหร่")
        if re.search(r"^(ตอนนี้)?(กี่โมง|กี่หลง|เวลาเท่าไหร่)(แล้ว)?$", clean):
            return FastPathResult(matched=True, action="get_time", speech_response=get_current_time_str())

        # Rule 2: Get Date ("วันนี้วันอะไร", "วันที่เท่าไหร่", "วันนี้วันที่เท่าไหร่")
        if re.search(r"^(วันนี้วัน(อะไร|ที่เท่าไหร่)|วันที่เท่าไหร่)$", clean):
            return FastPathResult(matched=True, action="get_date", speech_response=get_current_date_str())

        # Rule 3: Battery & Power Status ("เช็คแบต", "แบตเตอรี่เหลือเท่าไหร่", "สถานะแบตเตอรี่")
        if re.search(r"^(เช็ค|ดู|ตรวจ)?\s*(แบต|แบตเตอรี่)(\s*(เหลือเท่าไหร่|เป็นยังไง|สถานะ))?$", clean):
            return FastPathResult(matched=True, action="get_battery", speech_response=get_battery_status())

        # Rule 4: System Resources / Health ("สถานะเครื่อง", "เช็คเครื่อง", "เช็คแรม", "ตรวจเครื่อง")
        if re.search(r"^(สถานะเครื่อง|เช็คเครื่อง|เช็คแรม|ตรวจเครื่อง|การทำงานเครื่อง)$", clean):
            return FastPathResult(matched=True, action="get_system_status", speech_response=get_system_resources())

        # Rule 5: Volume & Mute Controls ("ปิดเสียง", "เปิดเสียง", "ลดเสียง", "เพิ่มเสียง")
        if re.search(r"^(ปิดเสียง|เงียบเสียง)$", clean):
            _, msg = set_mute_volume(True)
            return FastPathResult(matched=True, action="mute_volume", speech_response=msg)

        if re.search(r"^เปิดเสียง$", clean):
            _, msg = set_mute_volume(False)
            return FastPathResult(matched=True, action="unmute_volume", speech_response=msg)

        vol_down = re.match(r"^ลดเสียง(\s*(\d+)%)?$", clean)
        if vol_down:
            percent = vol_down.group(2) or "10"
            try:
                subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"-{percent}%"], check=True)
                return FastPathResult(matched=True, action="set_volume", speech_response=f"ลดเสียงลง {percent} เปอร์เซ็นต์แล้วครับ")
            except Exception as e:
                return FastPathResult(matched=True, action="set_volume", error=str(e), speech_response="ไม่สามารถปรับเสียงได้ครับ")

        vol_up = re.match(r"^เพิ่มเสียง(\s*(\d+)%)?$", clean)
        if vol_up:
            percent = vol_up.group(2) or "10"
            try:
                subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"+{percent}%"], check=True)
                return FastPathResult(matched=True, action="set_volume", speech_response=f"เพิ่มเสียงขึ้น {percent} เปอร์เซ็นต์แล้วครับ")
            except Exception as e:
                return FastPathResult(matched=True, action="set_volume", error=str(e), speech_response="ไม่สามารถปรับเสียงได้ครับ")

        # Rule 6: Web Search ("ค้นหา [ข้อความ]", "เสิร์ช [ข้อความ]", "หาข้อมูล [ข้อความ]")
        search_match = re.match(r"^(ค้นหา|เสิร์ช|หาข้อมูล(เรื่อง)?)\s+(.+)$", clean)
        if search_match:
            query = search_match.group(3).strip()
            ok, msg = search_web_query(query)
            return FastPathResult(matched=True, action="search_web", speech_response=msg)

        # Rule 7: Life Manager Web App command
        if re.search(r"^เปิด\s*(ระบบ\s*)?(life\s*manager|การเรียน|จัดการชีวิต|ตารางเรียน|การบ้าน)$", clean, re.IGNORECASE):
            try:
                from javis.integrations.life_manager import LifeManagerClient
                client = LifeManagerClient()
                client.open_web_app()
                return FastPathResult(
                    matched=True,
                    action="open_life_manager",
                    speech_response="เปิดระบบจัดการชีวิตและการเรียนในเบราว์เซอร์ให้เรียบร้อยแล้วครับ",
                )
            except Exception as e:
                return FastPathResult(matched=True, action="open_life_manager", error=str(e), speech_response="ไม่สามารถเปิดระบบได้ครับ")

        # Life Manager Voice Briefing ("สรุปงานวันนี้", "บรีฟงาน", "มีงานค้างไหม", "สถานะการเรียน")
        if re.search(r"^(สรุป(งาน|การเรียน|ภารกิจ)?(\s*วันนี้)?|บรีฟ(งาน)?(\s*วันนี้)?|มีงาน(อะไร)?ค้าง(บ้าง|ไหม)?|สถานะ(การบ้าน|การเรียน))$", clean):
            try:
                from javis.integrations.life_manager import LifeManagerClient
                client = LifeManagerClient()
                briefing = client.get_briefing()
                if briefing:
                    return FastPathResult(matched=True, action="life_briefing", speech_response=briefing)
                return FastPathResult(matched=True, action="life_briefing", speech_response="ไม่พบข้อมูลภารกิจที่ค้างอยู่ครับ")
            except Exception as e:
                return FastPathResult(matched=True, action="life_briefing", error=str(e), speech_response="ไม่สามารถดึงข้อมูลสรุปได้ครับ")

        # Life Manager Timetable ("ตารางเรียนวันนี้", "วันนี้เรียนอะไรบ้าง", "มีเรียนอะไรบ้าง")
        if re.search(r"^(ตารางเรียน(\s*วันนี้)?|(วันนี้)?มีเรียน(อะไร(บ้าง)?)?|วันนี้เรียนอะไรบ้าง)$", clean):
            try:
                from javis.integrations.life_manager import LifeManagerClient
                client = LifeManagerClient()
                timetable_text = client.get_today_timetable()
                return FastPathResult(matched=True, action="life_timetable", speech_response=timetable_text)
            except Exception as e:
                return FastPathResult(matched=True, action="life_timetable", error=str(e), speech_response="ไม่สามารถดึงตารางเรียนได้ครับ")

        # Rule 8: Open Websites / Known Services ("เปิดยูทูป", "เปิดกูเกิล", "เปิด github", etc.)
        web_match = re.match(r"^เปิด\s*(เว็บ\s*)?(ยูทูป|youtube|กูเกิล|google|github|กิตฮับ|facebook|เฟสบุ๊ค)$", clean, re.IGNORECASE)
        if web_match:
            site_name = web_match.group(2).strip()
            ok, msg = open_website_or_url(site_name)
            return FastPathResult(matched=True, action="open_website", speech_response=msg)

        # Rule 9: Open Desktop Apps ("เปิด VS Code", "เปิด Chrome", "เปิด เทอร์มินัล", "เปิดเครื่องคิดเลข")
        app_match = re.match(r"^เปิด\s*(แอป\s*|โปรแกรม\s*)?([a-zA-Z0-9_\-\sก-๙]+)$", clean)
        if app_match:
            app_name = app_match.group(2).strip().lower()
            ok, msg = open_desktop_application(app_name)
            return FastPathResult(matched=True, action="open_app", speech_response=msg)

        # No fast-path rule matched -> Delegate to Hermes Gateway / Gemini Brain
        return FastPathResult(matched=False)
