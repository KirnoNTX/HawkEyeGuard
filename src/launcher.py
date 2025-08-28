##################################
#                                #
#    LaunchGuard Version 1.0.0   #
#                                #
##################################

import json
import os
import sys
import subprocess
import urllib.request
from typing import Any, Dict, Optional

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT, "config.json")
BLACKLIST_PATH = os.path.join(ROOT, "blacklist.json")
GUARD_PATH = os.path.join(ROOT, "guard.py")

def read_json(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        print("[FAIL] Missing file:", path)
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("[FAIL] Read JSON:", path, "-", str(e))
        return {}

def write_bytes(path: str, data: bytes) -> bool:
    try:
        with open(path, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        print("[FAIL] Write file:", path, "-", str(e))
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

def fetch_and_update(url: Optional[str], target_path: str) -> bool:
    if not url or not isinstance(url, str) or url.strip() == "":
        print("[FAIL] URL not set for:", os.path.basename(target_path))
        return False
    data = fetch(url)
    if data is None or len(data) == 0:
        if os.path.isfile(target_path):
            print("[OK] Using cached:", os.path.basename(target_path))
            return False
        print("[FAIL] No cache for:", os.path.basename(target_path))
        return False
    if target_path.lower().endswith((".json",)):
        if not is_valid_json_bytes(data):
            if os.path.isfile(target_path):
                print("[OK] Invalid JSON, using cached:", os.path.basename(target_path))
                return False
            print("[FAIL] Invalid JSON and no cache for:", os.path.basename(target_path))
            return False
    current = None
    try:
        with open(target_path, "rb") as f:
            current = f.read()
    except Exception:
        current = None
    if current is not None and current == data:
        print("[OK] No change for:", os.path.basename(target_path))
        return False
    ok = write_bytes(target_path, data)
    if ok:
        print("[OK] Updated:", os.path.basename(target_path))
    else:
        print("[FAIL] Cannot write:", os.path.basename(target_path))
    return ok

def ensure_updates() -> bool:
    cfg = read_json(CONFIG_PATH)
    urls = cfg.get("urls", {}) if isinstance(cfg, dict) else {}
    ok1 = fetch_and_update(urls.get("config"), CONFIG_PATH)
    cfg = read_json(CONFIG_PATH)
    urls = cfg.get("urls", {}) if isinstance(cfg, dict) else urls
    ok2 = fetch_and_update(urls.get("blacklist"), BLACKLIST_PATH)
    ok3 = fetch_and_update(urls.get("guard"), GUARD_PATH)
    return any([ok1, ok2, ok3])

def run_guard() -> int:
    try:
        p = subprocess.Popen([sys.executable, GUARD_PATH], cwd=ROOT)
        return p.wait()
    except Exception as e:
        print("[FAIL] Launch guard.py:", str(e))
        return 1

def main() -> int:
    args = set(a.lower() for a in sys.argv[1:])
    print("[OK] HawkEyeGuard starting")
    _ = ensure_updates()
    if "--no-run" in args or "--fetch-only" in args:
        print("[OK] Fetch-only mode complete")
        return 0
    if not os.path.isfile(GUARD_PATH):
        print("[FAIL] guard.py missing")
        return 1
    code = run_guard()
    print("[OK] Guard exited with code", code)
    return int(code)

if __name__ == "__main__":
    raise SystemExit(main())
