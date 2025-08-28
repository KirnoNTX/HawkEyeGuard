##################################
#                                #
#       Guard Version 1.0.1      #
#                                #
##################################

import json
import os
import subprocess
import time
import urllib.request
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT, "config.json")
BLACKLIST_PATH = os.path.join(ROOT, "blacklist.json")

def read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("[FAIL] Read JSON:", path, "-", str(e))
        return {}

def read_blacklist(path: str) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()]
            return []
    except Exception as e:
        print("[FAIL] Read blacklist:", str(e))
        return []

def list_process_names() -> Set[str]:
    try:
        p = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, check=False)
        lines = p.stdout.splitlines()
        names: Set[str] = set()
        for line in lines:
            if not line:
                continue
            try:
                first = line.split('","', 1)[0]
                name = first.strip().strip('"')
                if name:
                    names.add(name.lower())
            except Exception:
                continue
        return names
    except Exception as e:
        print("[FAIL] tasklist:", str(e))
        return set()

def kill_process(name: str) -> bool:
    try:
        r = subprocess.run(["taskkill", "/F", "/IM", name], capture_output=True, text=True, check=False)
        if r.returncode == 0:
            print("[OK] Killed:", name)
            return True
        if "not found" in (r.stdout + r.stderr).lower():
            return False
        print("[FAIL] Kill:", name, "-", (r.stderr or r.stdout).strip())
        return False
    except Exception as e:
        print("[FAIL] Kill exception:", name, "-", str(e))
        return False

def fetch(url: str, timeout: int = 10) -> Optional[bytes]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print("[FAIL] Fetch:", url, "-", str(e))
        return None

def is_valid_json_bytes(data: bytes) -> bool:
    try:
        json.loads(data.decode("utf-8"))
        return True
    except Exception:
        return False

def is_likely_html(data: bytes) -> bool:
    head = data[:256].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html") or b"<head" in head or b"<body" in head

def write_bytes(path: str, data: bytes) -> bool:
    try:
        with open(path, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        print("[FAIL] Write file:", path, "-", str(e))
        return False

def refresh_config_from_url() -> bool:
    cfg = read_json(CONFIG_PATH)
    urls = cfg.get("urls", {}) if isinstance(cfg, dict) else {}
    u = urls.get("config") if isinstance(urls, dict) else None
    if not u or not isinstance(u, str) or not u.strip():
        return False
    data = fetch(u)
    if data is None or len(data) == 0 or is_likely_html(data) or not is_valid_json_bytes(data):
        return False
    try:
        cur = open(CONFIG_PATH, "rb").read()
    except Exception:
        cur = None
    if cur is not None and cur == data:
        print("[OK] Config no change")
        return False
    ok = write_bytes(CONFIG_PATH, data)
    if ok:
        print("[OK] Config changed")
    return ok

def parse_message(cfg: Dict[str, Any]) -> Tuple[bool, Optional[str], int, str]:
    if not isinstance(cfg, dict):
        return False, None, 0, ""
    msg = cfg.get("message")
    if not isinstance(msg, dict):
        return False, None, 0, ""
    show = str(msg.get("show", "")).strip().lower() == "show"
    text = str(msg.get("text")).strip() if msg.get("text") else None
    dur_raw = msg.get("duration_seconds", 60)
    dur = int(dur_raw) if isinstance(dur_raw, int) else 60
    if dur < 1:
        dur = 30
    sig = f"{text or ''}|{dur}"
    return show and bool(text), text, dur, sig

def show_message(text: str, duration_seconds: int) -> bool:
    try:
        r = subprocess.run(["msg", "*", "/time:" + str(duration_seconds), text], capture_output=True, text=True, check=False)
        if r.returncode == 0:
            print("[OK] Message sent")
            return True
        print("[FAIL] Message:", (r.stderr or r.stdout).strip())
        return False
    except Exception as e:
        print("[FAIL] Message exception:", str(e))
        return False

def apply_guard(interval_seconds: int, poll_seconds: int) -> int:
    if interval_seconds < 1:
        interval_seconds = 1
    if poll_seconds < 1:
        poll_seconds = 1
    print("[OK] Guard running every", interval_seconds, "seconds")
    last_poll = 0.0
    last_sig = ""
    try:
        while True:
            now = time.time()
            if now - last_poll >= poll_seconds:
                _ = refresh_config_from_url()
                cfg = read_json(CONFIG_PATH)
                do_show, text, dur, sig = parse_message(cfg)
                if do_show and sig != last_sig:
                    if show_message(text or "", dur):
                        last_sig = sig
                if not do_show:
                    last_sig = ""
                last_poll = now
            bl = read_blacklist(BLACKLIST_PATH)
            running = list_process_names()
            for n in bl:
                if n.lower() in running:
                    kill_process(n)
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("[OK] Guard interrupted")
        return 0
    except Exception as e:
        print("[FAIL] Guard loop:", str(e))
        return 1

def main() -> int:
    cfg = read_json(CONFIG_PATH)
    interval_raw = cfg.get("interval_seconds", 2) if isinstance(cfg, dict) else 2
    poll_raw = cfg.get("message_poll_seconds", 2) if isinstance(cfg, dict) else 2
    interval = int(interval_raw) if isinstance(interval_raw, int) else 2
    poll = int(poll_raw) if isinstance(poll_raw, int) else 2
    return apply_guard(interval, poll)

if __name__ == "__main__":
    raise SystemExit(main())
