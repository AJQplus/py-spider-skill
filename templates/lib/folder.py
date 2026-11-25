#!/usr/bin/python
"""folder 路由辅助：vod_tag 构造与二级分发。"""


def is_folder(tid):
    return str(tid or "").startswith("folder$")


def parse_folder(tid):
    if not is_folder(tid):
        return {}
    parts = str(tid).split("$")
    return {"tag": parts[1] if len(parts) > 1 else "", "id": parts[2] if len(parts) > 2 else ""}


def make_folder(tag, rid):
    return "folder$" + str(tag) + "$" + str(rid)


def page_param(pg, kinds=("?page=", "/page/", "/p/")):
    pg = int(pg) if str(pg).isdigit() else 1
    if pg <= 1:
        return ""
    return kinds[0] + str(pg)
