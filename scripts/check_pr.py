#!/usr/bin/env python3
import datetime
import json
import os
import subprocess
import urllib.request

LOG_FILE = "/home/apichet/for-hermes/01_projects/javis-os/pr_monitor.log"
REPO = "Galiverking/javis-os"
URL = f"https://api.github.com/repos/{REPO}/pulls?state=open"

def check():
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    req = urllib.request.Request(URL, headers={"User-Agent": "JavisOS-PR-Monitor/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            prs = json.loads(resp.read().decode())
            
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            if prs:
                f.write(f"[{now_str}] FOUND {len(prs)} OPEN PR(s):\n")
                for p in prs:
                    pr_info = f"  - #{p.get('number')}: {p.get('title')} by {p.get('user', {}).get('login')} ({p.get('html_url')})\n"
                    f.write(pr_info)
                title = f"Javis OS: ตรวจพบ {len(prs)} PR ใหม่!"
                body = f"#{prs[0].get('number')}: {prs[0].get('title')}"
                subprocess.Popen(["notify-send", "-u", "critical", title, body], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                f.write(f"[{now_str}] Check completed: No open PRs.\n")
                print(f"[{now_str}] Check completed: No open PRs.")
    except Exception as e:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{now_str}] Error checking PRs: {e}\n")
        print(f"[{now_str}] Error: {e}")

if __name__ == "__main__":
    check()
