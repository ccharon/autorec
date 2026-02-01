import json
import os
import subprocess
from typing import Optional


def get_target_node_id(target_app: str, target_media_class: str) -> Optional[int]:
    """
    Finds the target app's PipeWire node via pw-dump.
    """
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    try:
        p = subprocess.run(["pw-dump"], capture_output=True, text=True, check=False, env=env)
    except FileNotFoundError:
        return None

    if p.returncode != 0 or not (p.stdout or "").strip():
        return None

    try:
        data = json.loads(p.stdout)
    except (json.JSONDecodeError, TypeError):
        return None

    candidates = []
    for obj in data:
        if obj.get("type") != "PipeWire:Interface:Node":
            continue
        props = obj.get("info", {}).get("props", {}) or {}
        if props.get("application.name") != target_app:
            continue
        media_class = props.get("media.class", "")
        if not media_class.startswith(target_media_class):
            continue
        node_id = obj.get("id")
        if node_id is not None:
            candidates.append((int(node_id), props.get("node.name", ""), media_class))

    if not candidates:
        return None

    # prefer highest id (typically newest stream)
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][0]
