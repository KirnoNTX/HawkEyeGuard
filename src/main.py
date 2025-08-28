##################################
#                                #
#     Launcher Version 1.0.0     #
#                                #
##################################

import json
import os
import sys
import tempfile
import subprocess
import urllib.request
from typing import Any, Dict, Optional, Tuple

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

def read_bytes(path: str) -> Optional[bytes]:
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None

def atomic_write(path: str, data: bytes) -> bool:
    d = os.path.dirname(path) or "."
    try:
        with tempfile.NamedTemporaryFile("wb", delete=False, dir=d) as tf:
            tmp = tf.name
            tf.write(data)
        bak = path + ".bak"
        if os.path.isfile(path):
            try:
                if os.path.isfile(bak):
                    os.remove(bak)
                os.replace(path, bak)
            except Exception:
                pass
        os.replace(tmp, path)
        return True
    except Exception as e:
        print("[FAIL] Atomic write:", path, "-", str(e))
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return False

def is_likely_html(data: bytes) -> bool:
    head = data[:256].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html") or b"<head" in head or b"<body" in head

def is_valid_json_bytes(data: bytes) -> bool:
    try:
        json.loads(data.decode("utf-8"))
        return True
    except Exception:
        return False

def fetch(url: str, timeout: int = 10) -> Tuple[Optional[bytes], Optional[str]]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            ct = r.headers.get("Content-Type", "")
            return r.read(), ct
    except Exception as e:
        print("[FAIL] Fetch:", url, "-", str(e))
        return None, None

def safe_update_json(url: Optional[str], target_path: str, name: str) -> bool:
    if not url or not isinstance(url, str) or not url.strip():
        if os.path.isfile(target_path):
            print("[OK] URL not set, using cached:", name)
            return False
        print("[FAIL] URL not set and no cache:", name)
        return False
    data, ct = fetch(url)
    if data is None or len(data) == 0:
        if os.path.isfile(target_path):
            print("[OK] Using cached:", name)
            return False
        print("[FAIL] No cache for:", name)
        return False
    if ("json" not in (ct or "").lower()) or is_likely_html(data) or not is_valid_json_bytes(data):
        if os.path.isfile(target_path):
            print("[OK] Invalid remote content, using cached:", name)
            return False
        print("[FAIL] Invalid remote content and no cache:", name)
        return False
    current = read_bytes(target_path)
    if current is not None and current == data:
        print("[OK] No change for:", name)
        return False
    ok = atomic_write(target_path, data)
    if ok:
        print("[OK] Updated:", name)
    else:
        print("[FAIL] Cannot write:", name)
    return ok

def restore_if_corrupt_json(path: str, name: str) -> None:
    if not os.path.isfile(path):
        return
    b = read_bytes(path)
    if not b:
        bak = path + ".bak"
        if os.path.isfile(bak):
            try:
                os.replace(bak, path)
                print("[OK] Restored from .bak:", name)
            except Exception as e:
                print("[FAIL] Restore .bak:", name, "-", str(e))
        return
    if not is_valid_json_bytes(b):
        bak = path + ".bak"
        if os.path.isfile(bak):
            try:
                os.replace(bak, path)
                print("[OK] Restored invalid JSON from .bak:", name)
            except Exception as e:
                print("[FAIL] Restore .bak:", name, "-", str(e))

def ensure_updates() -> bool:
    cfg_local = read_json(CONFIG_PATH)
    urls_local = cfg_local.get("urls", {}) if isinstance(cfg_local, dict) else {}
    changed_cfg = safe_update_json(urls_local.get("config"), CONFIG_PATH, "config.json")
    restore_if_corrupt_json(CONFIG_PATH, "config.json")
    cfg_eff = read_json(CONFIG_PATH) if os.path.isfile(CONFIG_PATH) else {}
    urls_eff = cfg_eff.get("urls", {}) if isinstance(cfg_eff, dict) else urls_local
    changed_bl = safe_update_json(urls_eff.get("blacklist"), BLACKLIST_PATH, "blacklist.json")
    changed_guard = False
    if urls_eff.get("guard"):
        data, ct = fetch(urls_eff.get("guard"))
        if data is None or is_likely_html(data):
            print("[OK] Using cached:", "guard.py" if os.path.isfile(GUARD_PATH) else "no guard.py cache")
            changed_guard = False
        else:
            cur = read_bytes(GUARD_PATH)
            if cur is not None and cur == data:
                print("[OK] No change for:", "guard.py")
                changed_guard = False
            else:
                changed_guard = atomic_write(GUARD_PATH, data)
                if changed_guard:
                    print("[OK] Updated:", "guard.py")
                else:
                    print("[FAIL] Cannot write:", "guard.py")
    else:
        if os.path.isfile(GUARD_PATH):
            print("[OK] URL not set, using cached:", "guard.py")
        else:
            print("[FAIL] URL not set and no cache:", "guard.py")
    return any([changed_cfg, changed_bl, changed_guard])

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
