"""Smart Action & System Processing Engine for Javis OS.
Executes local actions: app launching, system inspection, volume, browser, and search.
"""

import datetime
import logging
import os
import re
import subprocess
import urllib.parse
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def get_current_time_str() -> str:
    """Return polite Thai time string."""
    now = datetime.datetime.now()
    return f"ตอนนี้เวลา {now.hour} นาฬิกา {now.minute} นาทีครับ"


def get_current_date_str() -> str:
    """Return polite Thai day of week and full date string."""
    now = datetime.datetime.now()
    thai_days = [
        "วันจันทร์", "วันอังคาร", "วันพุธ", "วันพฤหัสบดี",
        "วันศุกร์", "วันเสาร์", "วันอาทิตย์"
    ]
    thai_months = [
        "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
        "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
    ]
    day_name = thai_days[now.weekday()]
    return f"วันนี้คือ{day_name} ที่ {now.day} {thai_months[now.month]} พุทธศักราช {now.year + 543} ครับ"


def get_battery_status() -> str:
    """Inspect battery percentage and charging state."""
    try:
        # Check /sys/class/power_supply/BAT0
        cap_file = "/sys/class/power_supply/BAT0/capacity"
        stat_file = "/sys/class/power_supply/BAT0/status"
        if os.path.exists(cap_file):
            with open(cap_file) as f:
                capacity = f.read().strip()
            state = "ปกติ"
            if os.path.exists(stat_file):
                with open(stat_file) as f:
                    raw_state = f.read().strip().lower()
                    if raw_state == "charging":
                        state = "กำลังเสียบสายชาร์จอยู่"
                    elif raw_state == "full":
                        state = "แบตเตอรี่เต็มแล้ว"
                    elif raw_state == "discharging":
                        state = "กำลังใช้งานแบตเตอรี่"
            return f"แบตเตอรี่เหลือ {capacity} เปอร์เซ็นต์ {state}ครับ"
    except Exception as e:
        logger.warning("Error reading battery: %s", e)
    return "ไม่สามารถตรวจสอบข้อมูลแบตเตอรี่ได้ในขณะนี้ครับ"


def get_system_resources() -> str:
    """Check CPU load and available RAM."""
    try:
        # Memory
        mem_avail_mb = None
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    mem_avail_mb = int(line.split()[1]) // 1024
                    break
        
        # Load average (1 min)
        load1, _, _ = os.getloadavg()
        cpu_count = os.cpu_count() or 1
        load_pct = min(100, int((load1 / cpu_count) * 100))

        if mem_avail_mb is not None:
            if mem_avail_mb >= 1024:
                mem_str = f"{mem_avail_mb / 1024:.1f} กิกะไบต์"
            else:
                mem_str = f"{mem_avail_mb} เมกะไบต์"
            return f"ระบบทำงานปกติครับ แรมเหลือใช้งาน {mem_str} ซีพียูมีโหลดประมาณ {load_pct} เปอร์เซ็นต์ครับ"
    except Exception as e:
        logger.warning("Error reading resources: %s", e)
    return "ระบบปฏิบัติการทำงานเป็นปกติครับ"


def open_desktop_application(app_name: str) -> Tuple[bool, str]:
    """Launch application by friendly Thai/English name."""
    clean = app_name.strip().lower()
    app_map = {
        "เครื่องคิดเลข": "gnome-calculator",
        "calculator": "gnome-calculator",
        "calc": "gnome-calculator",
        "ไฟล์": "nemo",
        "จัดการไฟล์": "nemo",
        "โฟลเดอร์": "nemo",
        "files": "nemo",
        "เบราว์เซอร์": "firefox",
        "เบราว์เซอร์หลัก": "firefox",
        "อินเทอร์เน็ต": "firefox",
        "เน็ต": "firefox",
        "เว็บ": "firefox",
        "firefox": "firefox",
        "chrome": "google-chrome",
        "google chrome": "google-chrome",
        "โครม": "google-chrome",
        "กูเกิลโครม": "google-chrome",
        "vscode": "code",
        "vs code": "code",
        "โค้ด": "code",
        "เทอร์มินัล": "x-terminal-emulator",
        "terminal": "x-terminal-emulator",
        "celluloid": "celluloid",
        "เครื่องเล่นเพลง": "celluloid",
        "เครื่องเล่นวิดีโอ": "celluloid",
    }
    
    bin_target = app_map.get(clean, clean)
    try:
        subprocess.Popen(
            [bin_target],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True, f"เปิด {app_name} ให้เรียบร้อยแล้วครับ"
    except Exception as e:
        logger.error("Failed to launch %s: %s", bin_target, e)
        return False, f"ขออภัยครับ ไม่พบหรือไม่สามารถเปิด {app_name} ได้ครับ"


def open_website_or_url(target: str) -> Tuple[bool, str]:
    """Open known website or custom URL."""
    clean = target.strip().lower()
    site_map = {
        "ยูทูป": "https://www.youtube.com",
        "youtube": "https://www.youtube.com",
        "กูเกิล": "https://www.google.com",
        "google": "https://www.google.com",
        "github": "https://www.github.com",
        "กิตฮับ": "https://www.github.com",
        "เฟสบุ๊ค": "https://www.facebook.com",
        "facebook": "https://www.facebook.com",
    }

    url = site_map.get(clean)
    if not url:
        if clean.startswith("http://") or clean.startswith("https://"):
            url = clean
        elif "." in clean and not " " in clean:
            url = f"https://{clean}"
        else:
            return False, "ไม่พบที่อยู่เว็บไซต์ที่ระบุครับ"

    try:
        subprocess.Popen(
            ["xdg-open", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True, f"เปิด {target} ในเบราว์เซอร์ให้เรียบร้อยแล้วครับ"
    except Exception as e:
        logger.error("Failed to open URL %s: %s", url, e)
        return False, f"ไม่สามารถเปิด {target} ได้ครับ"


def search_web_query(query: str) -> Tuple[bool, str]:
    """Open browser with Google Search query."""
    clean = query.strip()
    if not clean:
        return False, "กรุณาระบุสิ่งที่ต้องการค้นหาครับ"
    
    encoded = urllib.parse.quote(clean)
    search_url = f"https://www.google.com/search?q={encoded}"
    try:
        subprocess.Popen(
            ["xdg-open", search_url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True, f"กำลังค้นหาข้อมูลเกี่ยวกับ {clean} ให้บนเบราว์เซอร์ครับ"
    except Exception as e:
        logger.error("Failed to search web for %s: %s", clean, e)
        return False, "ไม่สามารถเปิดหน้าค้นหาได้ครับ"


def set_mute_volume(mute: bool) -> Tuple[bool, str]:
    """Mute or unmute speaker output."""
    val = "1" if mute else "0"
    action_text = "ปิดเสียง" if mute else "เปิดเสียง"
    try:
        subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", val], check=True)
        return True, f"{action_text}เรียบร้อยแล้วครับ"
    except Exception as e:
        logger.error("Failed to set mute: %s", e)
        return False, f"ไม่สามารถ{action_text}ได้ครับ"
