#!/usr/bin/python
"""HLS 通用辅助：m3u8 重写、AES-128 解密、key/ts 代理 URL。"""
import base64
import re
from urllib.parse import urljoin

try:
    from Crypto.Cipher import AES
except Exception:
    AES = None


def _is_absolute(url):
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url or ""))


def resolve(href, base_url):
    if not href:
        return ""
    return href if _is_absolute(href) else urljoin(base_url or "", href)


def rewrite_m3u8(text, base_url="", key_prefix="", ts_prefix=""):
    out = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if line.startswith("#EXT-X-KEY"):
            m = re.search(r'URI="([^"]+)"', line)
            if m and key_prefix:
                line = line.replace(m.group(1), key_prefix + resolve(m.group(1), base_url))
            out.append(line)
        elif line.startswith("#") or not line:
            out.append(line)
        else:
            resolved = resolve(line, base_url)
            out.append(ts_prefix + resolved if ts_prefix else resolved)
    return "\n".join(out)


def _unpad(data):
    if not data:
        return data
    pad = data[-1]
    if 0 < pad <= 16 and data[-pad:] == bytes([pad]) * pad:
        return data[:-pad]
    return data


def decrypt_ts(data, key, iv=None):
    if AES is None or not data or not key:
        return data
    try:
        if isinstance(key, str):
            k = bytes.fromhex(key) if re.fullmatch(r"[0-9a-fA-F]{32}", key) else base64.b64decode(key)
        else:
            k = key
        if iv is None:
            iv_bytes = b"\x00" * 16
        elif isinstance(iv, bytes):
            iv_bytes = iv
        else:
            iv_s = str(iv).replace("0x", "")
            iv_bytes = bytes.fromhex(iv_s) if re.fullmatch(r"[0-9a-fA-F]{32}", iv_s) else b"\x00" * 16
        return _unpad(AES.new(k, AES.MODE_CBC, iv_bytes).decrypt(data))
    except Exception:
        return data


def probe_playlist(text):
    head = (text or "")[:1024]
    is_hls = "#EXTM3U" in head
    key = None
    for raw in (text or "").splitlines():
        if raw.startswith("#EXT-X-KEY"):
            method = re.search(r"METHOD=([^,]+)", raw)
            uri = re.search(r'URI="([^"]+)"', raw)
            iv = re.search(r"IV=([0-9A-Fa-fx]+)", raw)
            key = {
                "method": method.group(1) if method else "AES-128",
                "uri": uri.group(1) if uri else "",
                "iv": iv.group(1) if iv else "",
            }
            break
    return (is_hls, key is not None, (key or {}).get("method", ""), (key or {}).get("uri", ""), (key or {}).get("iv", ""))
