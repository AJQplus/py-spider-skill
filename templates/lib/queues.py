#!/usr/bin/python
"""队列辅助：短视频/音乐点击上下文、随机池去重。"""
import random


def encode_click(prefix, vid, idx, payload=""):
    return prefix + str(vid) + "$" + str(idx) + (("$" + str(payload)) if payload else "")


def build_pool(clicked_id, candidates, size=29):
    seen = {str(clicked_id)}
    pool = []
    for item in candidates:
        key = str(item.get("vod_id", "") if isinstance(item, dict) else item)
        if key and key not in seen:
            seen.add(key)
            pool.append(item)
        if len(pool) >= size:
            break
    random.shuffle(pool)
    return pool


def parse_payload(play_id, sep="$"):
    parts = str(play_id or "").split(sep)
    return {"prefix": parts[0] if parts else "", "vid": parts[1] if len(parts) > 1 else "", "idx": parts[2] if len(parts) > 2 else "", "payload": parts[3] if len(parts) > 3 else ""}
