#!/usr/bin/python
"""短剧/合集 episode_id 保留辅助。"""
import re


def keep_episode(video_id, episode_id):
    if not episode_id:
        return str(video_id)
    return str(video_id) + "_ep_" + str(episode_id)


def split_episode(vod_id):
    m = re.search(r"^(.*?)_ep_([^_]+)$", str(vod_id or ""))
    if not m:
        return {"video_id": str(vod_id or ""), "episode_id": ""}
    return {"video_id": m.group(1), "episode_id": m.group(2)}


def play_url(video_id, episode_id, template="drama-play?id={video_id}&episode_id={episode_id}"):
    parts = split_episode(vod_id=video_id) if "_ep_" in str(video_id) else {"video_id": str(video_id), "episode_id": str(episode_id or "")}
    return template.format(video_id=parts["video_id"], episode_id=parts["episode_id"])
