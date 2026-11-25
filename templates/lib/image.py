#!/usr/bin/python
"""图片通用辅助：魔数校验、AES-CBC 图片解密、长度检查。"""
import re

MAGIC = {
    b"\xff\xd8\xff": "jpeg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
    b"RIFF": "webp",
}


def sniff(data):
    if not data:
        return ""
    for magic, name in MAGIC.items():
        if data[: len(magic)] == magic:
            return name
    return ""


def ok_image(data, min_len=100):
    return data is not None and len(data) >= min_len and bool(sniff(data))


def decrypt_image(data, key, iv=None, mode="cbc"):
    try:
        from Crypto.Cipher import AES
    except Exception:
        return data
    if not data or not key:
        return data
    try:
        if isinstance(key, str):
            k = bytes.fromhex(key) if re.fullmatch(r"[0-9a-fA-F]{32}", key) else key.encode("utf-8")
        else:
            k = key
        if iv is None:
            iv_bytes = b"\x00" * 16
        elif isinstance(iv, bytes):
            iv_bytes = iv
        elif re.fullmatch(r"[0-9a-fA-F]{32}", str(iv)):
            iv_bytes = bytes.fromhex(str(iv))
        else:
            iv_bytes = str(iv).encode("utf-8")
        k = k[:16] if len(k) >= 16 else k + b"\x00" * (16 - len(k))
        iv_bytes = iv_bytes[:16] if len(iv_bytes) >= 16 else iv_bytes + b"\x00" * (16 - len(iv_bytes))
        dec = AES.new(k, AES.MODE_CBC, iv_bytes).decrypt(data)
        pad = dec[-1]
        if 0 < pad <= 16 and dec[-pad:] == bytes([pad]) * pad:
            dec = dec[:-pad]
        return dec
    except Exception:
        return data


def cut_eoi(data):
    idx = data.rfind(b"\xff\xd9")
    return data[: idx + 2] if idx >= 0 else data
