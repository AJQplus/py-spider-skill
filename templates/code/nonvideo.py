#!/usr/bin/python
import json
import re
from urllib.parse import urljoin, urlparse, quote
import requests
from base.spider import Spider
try:
    from templates.lib import hls as _hls, image as _img
except Exception:
    try:
        from lib import hls as _hls, image as _img
    except Exception:
        _hls = _img = None


class Spider(Spider):
    def getName(self): return "非影视站"
    def init(self, extend=""):
        self.name = "非影视站"; self.host = "https://example.com"; self.headers = {"User-Agent": "Mozilla/5.0", "Referer": self.host + "/"}
        self.session = requests.Session(); self.session.headers.update(self.headers)
    def _get(self, url):
        try:
            r = self.session.get(url, headers=self.headers, timeout=15, verify=False, proxies=self.session.proxies or None); r.encoding = r.apparent_encoding or "utf-8"; return r.text
        except Exception: return ""
    def _is_media(self, url):
        u = urlparse(url or "")
        return u.scheme in ("http", "https") and bool(u.netloc) and not re.search(r"\.(?:html?|php)(?:$|[?#/])", u.path, re.I)
    def _probe_media(self, url):
        if not self._is_media(url): return ""
        try:
            r = self.session.get(url, headers={**self.headers, "Range": "bytes=0-4095"}, timeout=15, verify=False, stream=True, proxies=self.session.proxies or None)
            try:
                data = next(r.iter_content(4096), b""); ctype = r.headers.get("Content-Type", "").lower()
                if r.ok and (b"#EXTM3U" in data or "mpegurl" in ctype or b"ftyp" in data[:32] or "video/" in ctype): return r.url
                return ""
            finally:
                r.close()
        except Exception: return ""
    def _fix(self, url): return urljoin(self.host + "/", url or "")
    def _tree(self, html):
        try: from lxml import etree; return etree.HTML(html or "")
        except Exception: return None
    def _text(self, node): return " ".join("".join(node.xpath(".//text()")).split()) if node is not None else ""
    def _page(self, html, pg):
        tree = self._tree(html); pg = int(pg) if str(pg).isdigit() else 1
        if tree is None: return {"page": pg, "pagecount": pg, "limit": 0, "total": 0, "list": []}
        return {"page": pg, "pagecount": pg, "limit": 0, "total": 0, "list": []}
    def localProxy(self, param):
        try:
            data = json.loads(param); url = data.get("url", "")
            if not url: return b""
            r = self.session.get(url, headers=self.headers, timeout=15, verify=False, proxies=self.session.proxies or None); r.close()
            return r.content if r.ok else b""
        except Exception: return b""
    def proxyPic(self, pic): return self.localProxy(pic)
    def homeContent(self, filter): return {"class": [], "list": [], "filters": {}}
    def homeVideoContent(self): return {"list": []}
    def categoryContent(self, tid, pg, filter, extend): return self._page(self._get(self._fix(str(tid))), pg)
    def detailContent(self, ids): return {"list": []}
    def searchContent(self, key, quick, pg="1"): return self._page(self._get(self.host + "/search?wd=" + quote(str(key))), pg)
    def playerContent(self, flag, id, vipFlags):
        if self._is_media(id):
            probe = self._probe_media(id)
            if probe: return {"parse": 0, "url": probe, "header": json.dumps(self.headers)}
        return {"parse": 0, "url": "", "header": json.dumps(self.headers)}