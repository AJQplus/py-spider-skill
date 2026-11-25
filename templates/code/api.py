#!/usr/bin/python
import json
import re
import time
from urllib.parse import urljoin, urlparse
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
    def getName(self): return "API站点"
    def init(self, extend=""):
        self.name = "API站点"; self.host = "https://example.com"; self.api = self.host + "/api.php/provide/vod/"
        self.backup_hosts = []; self.shield = []
        if isinstance(extend, str) and extend.strip():
            s = extend.strip()
            if s.startswith("{"):
                try:
                    cfg = json.loads(s)
                    self.host = cfg.get("host", self.host)
                    self.backup_hosts = cfg.get("backup_hosts", []) or []
                    self.shield = cfg.get("shield", []) or []
                except Exception: pass
            elif "://" in s: self.host = s
        self.api = self.host + "/api.php/provide/vod/"
        self.headers = {"User-Agent": "Mozilla/5.0", "Referer": self.host + "/"}
        self.session = requests.Session(); self.session.headers.update(self.headers); self._cache = {}; self._cache_ttl = 30; self._cache_max = 200
    def _origin(self, url):
        u = urlparse(url or "")
        return (u.scheme + "://" + u.netloc) if u.scheme in ("http", "https") and u.netloc else self.host
    def _set_host(self, h):
        self.host = h.rstrip("/"); self.api = self.host + "/api.php/provide/vod/"; self.headers["Referer"] = self.host + "/"; self.session.headers.update(self.headers)
    def _swap_host(self, url, host):
        u = urlparse(url or "")
        return host.rstrip("/") + (u.path or "/") + (("?" + u.query) if u.query else "") + (("#" + u.fragment) if u.fragment else "")
    def _hosts(self): return list(dict.fromkeys([self.host] + self.backup_hosts + self.shield))
    def _json(self, url, params=None):
        key = url + "?" + json.dumps(params or {}, sort_keys=True, ensure_ascii=False)
        if key in self._cache and time.time() - self._cache[key][0] < self._cache_ttl: return self._cache[key][1]
        for h in self._hosts():
            try:
                target = self._swap_host(url, h) if h != self.host else url
                r = self.session.get(target, params=params or {}, headers=self.headers, timeout=15, verify=False, proxies=self.session.proxies or None)
                d = r.json()
                if r.ok and isinstance(d, dict) and d:
                    if h != self.host: self._set_host(self._origin(h))
                    if len(self._cache) >= self._cache_max: self._cache.pop(next(iter(self._cache)))
                    self._cache[key] = (time.time(), d)
                    return d
            except Exception: continue
        return {}
    def _html(self, url):
        for h in self._hosts():
            try:
                target = self._swap_host(url, h) if h != self.host else url
                r = self.session.get(target, headers=self.headers, timeout=15, verify=False, proxies=self.session.proxies or None); r.encoding = r.apparent_encoding or "utf-8"
                if r.status_code == 200 and r.text:
                    if h != self.host: self._set_host(self._origin(h))
                    return r.text
            except Exception: continue
        return ""
    def _fix(self, url): return urljoin(self.host + "/", url or "")
    def _is_media(self, url):
        u = urlparse(url or "")
        return u.scheme in ("http", "https") and bool(u.netloc) and not re.search(r"\.(?:html?|php)(?:$|[?#/])", u.path, re.I)
    def _probe_media(self, url):
        if not self._is_media(url): return ""
        try:
            r = self.session.get(url, headers={**self.headers, "Range": "bytes=0-4095"}, timeout=15, verify=False, stream=True, proxies=self.session.proxies or None)
            try:
                data = next(r.iter_content(4096), b""); ctype = r.headers.get("Content-Type", "").lower(); final = r.url
                if r.ok and (b"#EXTM3U" in data or "mpegurl" in ctype or "vnd.apple" in ctype or b"ftyp" in data[:32] or "video/" in ctype or "x-flv" in ctype):
                    return final
                return ""
            finally:
                r.close()
        except Exception:
            return ""
    def _resolve_media(self, url, depth=0):
        url = self._fix(url)
        if self._is_media(url): return self._probe_media(url)
        if depth > 3: return ""
        body = self._html(url)
        m = re.search(r'player_data\s*=\s*', body)
        if m:
            try:
                value = json.loads(self._json_object(body, m.end())).get("url", "")
                if value: return self._resolve_media(urljoin(url, value), depth + 1)
            except Exception: pass
        m = re.search(r'(?:var\s+now|var\s+playurl)\s*=\s*["\']([^"\']+)', body)
        if m: return self._resolve_media(urljoin(url, m.group(1).replace("&amp;", "&")), depth + 1)
        frame = re.search(r'<iframe[^>]+src=["\']([^"\']+)', body, re.I)
        if frame: return self._resolve_media(urljoin(url, frame.group(1)), depth + 1)
        scopes = re.findall(r'<(?:script|video|source)[^>]*>.*?</(?:script|video|source)>|<(?:video|source)[^>]*>', body, re.I | re.S)
        haystack = "\n".join(scopes) if scopes else body
        candidates = re.findall(r'https?://[^"\'<>\s]+\.(?:m3u8|mp4)[^"\'<>\s]*', haystack, re.I)
        bad = re.compile(r'(?:^|[/_.-])(ad|ads|advert|preview|trailer|recommend|demo|sample)(?:[/_.-]|$)', re.I)
        candidates = list(dict.fromkeys(x.replace("&amp;", "&") for x in candidates if not bad.search(urlparse(x).path)))
        tokens = re.findall(r'[A-Za-z0-9]{4,}', urlparse(url).path + "?" + urlparse(url).query)
        current_ids = [x for x in tokens if any(c.isdigit() for c in x) and x.lower() not in ("html", "m3u8", "index")]
        candidates.sort(key=lambda x: (not any(i in x for i in current_ids), len(x)))
        return self._resolve_media(candidates[0], depth + 1) if candidates else ""
    def _item(self, v): return {"vod_id": str(v.get("vod_id", "")), "vod_name": v.get("vod_name", ""), "vod_pic": self._fix(v.get("vod_pic", ""))}
    def localProxy(self, param):
        try:
            try:
                data = json.loads(param); url = data.get("url", "")
            except Exception:
                url = str(param or "")
            if not url: return b""
            r = self.session.get(url, headers=self.headers, timeout=15, verify=False, proxies=self.session.proxies or None)
            try:
                return r.content if r.ok else b""
            finally:
                r.close()
        except Exception:
            return b""
    def proxyPic(self, pic): return self.localProxy(pic)
    def homeContent(self, filter):
        d = self._json(self.api, {"ac": "list"}); return {"class": d.get("class", []), "list": [], "filters": {}}
    def homeVideoContent(self):
        d = self._json(self.api, {"ac": "detail", "pg": 1}); items = d.get("list", [])
        return {"list": [self._item(v) for v in items]}
    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if str(pg).isdigit() else 1; d = self._json(self.api, {"ac": "detail", "t": tid, "pg": pg})
        return {"page": pg, "pagecount": int(d.get("pagecount", 1) or 1), "limit": int(d.get("limit", 20) or 20), "total": int(d.get("total", 0) or 0), "list": [self._item(v) for v in d.get("list", [])]}
    def detailContent(self, ids):
        ids = ids if isinstance(ids, list) else [ids]
        d = self._json(self.api, {"ac": "detail", "ids": ids[0]}); out = []
        for v in d.get("list", []):
            f = v.get("vod_play_from", ""); u = v.get("vod_play_url", "")
            if (f or u) and (not f or not u or len(str(f).split("$$$")) != len(str(u).split("$$$"))): continue
            out.append({**self._item(v), "vod_play_from": f, "vod_play_url": u})
        return {"list": out}
    def searchContent(self, key, quick, pg="1"):
        pg = int(pg) if str(pg).isdigit() else 1; d = self._json(self.api, {"ac": "detail", "wd": key, "pg": pg}); items = d.get("list", [])
        if not items: items = self._json(self.api, {"ac": "list", "wd": key, "pg": pg}).get("list", [])
        return {"page": pg, "pagecount": int(d.get("pagecount", 1) or 1), "limit": int(d.get("limit", 20) or 20), "total": int(d.get("total", 0) or 0), "list": [self._item(v) for v in items]}
    def playerContent(self, flag, id, vipFlags):
        if self._is_media(id):
            probe = self._probe_media(id)
            if probe: return {"parse": 0, "url": probe, "header": json.dumps(self.headers)}
        last = ""
        for h in self._hosts():
            u = id if id.startswith("http") else h + id
            u = self._resolve_media(u)
            if self._is_media(u):
                probe = self._probe_media(u)
                if probe: return {"parse": 0, "url": probe, "header": json.dumps(self.headers)}
            last = u if self._is_media(u) else last
        return {"parse": 0 if self._is_media(last) else 1, "url": last, "header": json.dumps(self.headers)}