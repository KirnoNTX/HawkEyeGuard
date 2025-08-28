##################################
#                                #
#       Guard Version 1.0.0      #
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
STATE_PATH = os.path.join(ROOT, "state.json")

def read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("[FAIL] Read JSON:", path, "-", str(e))
        return {}

def write_json(path: str, data: Dict[str, Any]) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print("[FAIL] Write JSON:", path, "-", str(e))
        return False

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
        if os.path.isfile(CONFIG_PATH):
            print("[OK] Using cached: config.json")
            return False
        print("[FAIL] URL not set and no cache: config.json")
        return False
    data = fetch(u)
    if data is None or len(data) == 0:
        if os.path.isfile(CONFIG_PATH):
            print("[OK] Using cached: config.json")
            return False
        print("[FAIL] No cache for: config.json")
        return False
    if not is_valid_json_bytes(data):
        if os.path.isfile(CONFIG_PATH):
            print("[OK] Invalid JSON, using cached: config.json")
            return False
        print("[FAIL] Invalid JSON and no cache: config.json")
        return False
    current = None
    try:
        with open(CONFIG_PATH, "rb") as f:
            current = f.read()
    except Exception:
        current = None
    if current is not None and current == data:
        print("[OK] No change for: config.json")
        return False
    ok = write_bytes(CONFIG_PATH, data)
    if ok:
        print("[OK] Config refreshed")
    else:
        print("[FAIL] Cannot refresh config")
    return ok

def read_state() -> Dict[str, Any]:
    if not os.path.isfile(STATE_PATH):
        return {}
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("[FAIL] Read state:", str(e))
        return {}

def write_state(state: Dict[str, Any]) -> bool:
    return write_json(STATE_PATH, state)

def parse_message(cfg: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], int]:
    if not isinstance(cfg, dict):
        return None, None, 0
    msg = cfg.get("message")
    if not isinstance(msg, dict):
        return None, None, 0
    mid = str(msg.get("id")).strip() if msg.get("id") is not None else None
    text = str(msg.get("text")).strip() if msg.get("text") is not None else None
    dur = int(msg.get("duration_seconds", 60)) if isinstance(msg.get("duration_seconds", 60), int) else 60
    if dur < 1:
        dur = 30
    return mid if mid else None, text if text else None, dur

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

def apply_guard(interval_seconds: int, targets: List[str], poll_seconds: int) -> int:
    if interval_seconds < 1:
        interval_seconds = 5
    if poll_seconds < 5:
        poll_seconds = 15
    targets_l = [t.lower() for t in targets]
    print("[OK] Guard running every", interval_seconds, "seconds")
    last_poll = 0.0
    state = read_state()
    last_seen_id = state.get("last_message_id")
    try:
        while True:
            now = time.time()
            if now - last_poll >= poll_seconds:
                had = refresh_config_from_url()
                cfg_now = read_json(CONFIG_PATH)
                mid, text, dur = parse_message(cfg_now)
                if mid and text and mid != last_seen_id:
                    sent = show_message(text, dur)
                    if sent:
                        last_seen_id = mid
                        state["last_message_id"] = mid
                        state["last_message_time"] = int(time.time())
                        write_state(state)
                last_poll = now
            running = list_process_names()
            to_kill = [t for t in targets_l if t in running]
            for n in to_kill:
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
    interval = int(cfg.get("interval_seconds", 10)) if isinstance(cfg, dict) else 10
    poll = int(cfg.get("message_poll_seconds", 30)) if isinstance(cfg, dict) else 30
    bl = read_blacklist(BLACKLIST_PATH)
    if not bl:
        print("[FAIL] Empty blacklist")
    return apply_guard(interval, bl, poll)

if __name__ == "__main__":
    raise SystemExit(main())
