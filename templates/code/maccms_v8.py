#!/usr/bin/python
import json
import re
import time
from urllib.parse import urljoin, urlparse
import requests
try:
    from lxml import etree
except Exception:
    etree = None
from base.spider import Spider
try:
    from templates.lib import hls as _hls, image as _img
except Exception:
    try:
        from lib import hls as _hls, image as _img
    except Exception:
        _hls = _img = None


class Spider(Spider):
    def getName(self): return "站点名"
    def init(self, extend=""):
        self.name = "站点名"
        self.host = "https://example.com"
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
        self.headers = {"User-Agent": "Mozilla/5.0", "Referer": self.host + "/"}
        self.categories = []
        self.session = requests.Session(); self.session.headers.update(self.headers); self._cache = {}; self._cache_ttl = 30; self._cache_max = 200
    def _set_host(self, h):
        self.host = h.rstrip("/"); self.headers["Referer"] = self.host + "/"; self.session.headers.update(self.headers)
    def _swap_host(self, url, host):
        u = urlparse(url or "")
        return host.rstrip("/") + (u.path or "/") + (("?" + u.query) if u.query else "") + (("#" + u.fragment) if u.fragment else "")
    def _hosts(self): return list(dict.fromkeys([self.host] + self.backup_hosts + self.shield))
    def _get(self, url, depth=0):
        if depth > 3: return ""
        url = self._fix(url)
        if depth == 0 and not re.search(r"/(?:play|player)/", url, re.I) and url in self._cache and time.time() - self._cache[url][0] < self._cache_ttl: return self._cache[url][1]
        for h in self._hosts():
            try:
                target = self._swap_host(url, h) if h != self.host else url
                r = self.session.get(target, headers=self.headers, timeout=15, verify=False, proxies=self.session.proxies or None); r.encoding = r.apparent_encoding or "utf-8"
                if r.status_code == 200 and r.text:
                    m = re.search(r'SUCCESS_URLS\s*=\s*\[(.*?)\]', r.text, re.S)
                    if m:
                        for x in re.findall(r'"(https?://[^"]+)"', m.group(1)):
                            try:
                                t2 = self._get(x, depth + 1)
                                if t2 and len(t2) > 500: self._set_host(self._origin(x)); return t2
                            except Exception: pass
                        continue
                    if h != self.host: self._set_host(h)
                    if depth == 0:
                        if len(self._cache) >= self._cache_max: self._cache.pop(next(iter(self._cache)))
                        self._cache[url] = (time.time(), r.text)
                    return r.text
            except Exception: continue
        return ""
    def _origin(self, url):
        u = urlparse(url or "")
        return (u.scheme + "://" + u.netloc) if u.scheme in ("http", "https") and u.netloc else self.host
    def _tree(self, html):
        return etree.HTML(html or "") if etree is not None else None
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
        body = self._get(url)
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
    def _text(self, node): return " ".join("".join(node.xpath(".//text()")).split()) if node is not None else ""
    def _pagecount(self, html, pg):
        tree = self._tree(html); nums = []
        nodes = tree.xpath('//*[contains(@class,"page") or contains(@class,"pagination") or contains(@class,"pager")]//a')
        for a in nodes:
            href = a.get("href", ""); text = "".join(a.xpath(".//text()")).strip()
            m = re.search(r"(?:[?&]page=|/page/)(\d+)", href, re.I)
            if m: nums.append(int(m.group(1)))
            elif text.isdigit(): nums.append(int(text))
        nxt = tree.xpath('//a[@rel="next" or contains(@class,"next") or contains(normalize-space(.),"下一页")]')
        return max(nums + [pg + 1 if nxt else pg])
    def _list(self, html):
        tree = self._tree(html); out = []; seen = set()
        items = tree.xpath('//a[contains(@class,"videopic")]') or tree.xpath('//div[contains(@class,"item")]//a[.//img]') or tree.xpath('//a[contains(@href,"/movie/") and .//img]')
        for a in items:
            try:
                href = self._fix(a.get("href")); m = re.search(r"(?:index|detail)?(\d+)\.html", href)
                if not m or m.group(1) in seen: continue
                seen.add(m.group(1)); img = a.xpath('.//img')[0] if a.xpath('.//img') else None
                pic = self._fix((img.get("data-original") or img.get("data-src") or img.get("src")) if img is not None else "")
                name = a.get("title") or (img.get("alt") if img is not None else "") or self._text(a)
                out.append({"vod_id": m.group(1), "vod_name": name, "vod_pic": pic})
            except Exception: continue
        return out
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
    def homeContent(self, filter): return {"class": self.categories, "list": self._list(self._get(self.host)), "filters": {"default": []}}
    def homeVideoContent(self): return {"list": self._list(self._get(self.host)), "page": 1, "pagecount": self._pagecount(self._get(self.host), 1), "limit": 20, "total": 0}
    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if str(pg).isdigit() else 1; html = self._get(f"{self.host}/search.php?searchtype=5&tid={tid}&page={pg}"); items = self._list(html); limit = len(items) or 20; pagecount = self._pagecount(html, pg)
        return {"page": pg, "pagecount": pagecount, "limit": limit, "total": 0, "list": items}
    def detailContent(self, ids):
        out = []
        ids = ids if isinstance(ids, list) else [ids]
        for vid in ids:
            try:
                tree = self._tree(self._get(f"{self.host}/movie/index{vid}.html")); name = self._text(tree.xpath("//h1 | //h2")[0]) if tree.xpath("//h1 | //h2") else str(vid)
                pic = self._fix((tree.xpath('//div[contains(@class,"pic")]//img/@src') or tree.xpath('//img/@data-original') or [""])[0])
                fs = []; us = []; seen = set()
                for panel in tree.xpath('//div[contains(@class,"panel")]') or tree.xpath('//div[contains(@class,"playlist")]'):
                    opt = panel.xpath('.//a[contains(@class,"option")]'); source = self._source_name((opt[0].get("title") or self._text(opt[0])) if opt else "", len(fs) + 1)
                    eps = panel.xpath('.//ul[contains(@class,"playlistlink")]//a') or panel.xpath('.//ul//a[contains(@href,"/play/")]')
                    links = [self._text(a) + "$" + self._fix(a.get("href")) for a in eps if a.get("href")]
                    sid = self._parse_play_href(eps[0].get("href")) if eps and eps[0].get("href") else {"sid": ""}
                    key = str(sid.get("sid", ""))
                    if links and key not in seen:
                        seen.add(key); fs.append(source); us.append("#".join(links))
                if len(fs) != len(us): continue
                play_from, play_url = self._pack_lines(fs, us); out.append({"vod_id": str(vid), "vod_name": name, "vod_pic": pic, "vod_play_from": play_from, "vod_play_url": play_url})
            except Exception: continue
        return {"list": out}
    def searchContent(self, key, quick, pg="1"):
        try: r = self.session.post(self.host + "/search.php", data={"searchword": key}, headers=self.headers, timeout=15, verify=False, proxies=self.session.proxies or None); r.encoding = r.apparent_encoding or "utf-8"; items = self._list(r.text); page = int(pg); return {"list": items, "page": page, "pagecount": self._pagecount(r.text, page), "limit": len(items), "total": 0}
        except Exception: return {"list": [], "page": int(pg)}
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