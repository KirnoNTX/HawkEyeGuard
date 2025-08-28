##################################
#                                #
#       Guard Version 1.0.0      #
#                                #
##################################

import json
import os
import subprocess
import time
from typing import Any, Dict, List, Set

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
                if first.startswith('"') and first.endswith('"') is False:
                    pass
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


def apply_guard(interval_seconds: int, targets: List[str]) -> int:
    if interval_seconds < 1:
        interval_seconds = 5
    targets_l = [t.lower() for t in targets]
    print("[OK] Guard running every", interval_seconds, "seconds")
    try:
        while True:
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
    bl = read_blacklist(BLACKLIST_PATH)
    if not bl:
        print("[FAIL] Empty blacklist")
    return apply_guard(interval, bl)


if __name__ == "__main__":
    raise SystemExit(main())
