#!/usr/bin/python
"""盾检测/破解/保序探活通用库（v9.5）。仅供本技能内部复用，不直接发布。"""
import re
import socket
import hashlib
from concurrent.futures import ThreadPoolExecutor

SHIELD_SIGNS = {
    'cf': ['Just a moment', 'Attention Required', 'cf-chl-widget', 'cf-turnstile',
           'challenge-form', 'window._cf_chl_opt', 'cf-mitigated'],
    'slider': ['滑动验证', 'slideBox', 'huadong_', '人机身份验证'],
    'waf': ['/_waf/', 'GoCaptcha', 'gocaptcha'],
    'challenge': ['安全验证', 'security verification', '正在验证', '请稍候'],
}

def detect_shield(html, status_code=200):
    """盾类型：none/cf/slider/waf/challenge/short/empty"""
    if not html:
        return 'empty'
    head = html[:3000]
    for kind, marks in SHIELD_SIGNS.items():
        for m in marks:
            if m in head:
                return kind
    if status_code == 418:
        return 'waf'
    if len(html) < 1500:
        return 'short'
    return 'none'

def has_expected_content(html, keywords=None, min_len=1500):
    """真内容校验：既不能是盾页，也要含站点特征。拿 200 不等于过盾。"""
    if not html or len(html) < min_len:
        return False
    head = html[:3000]
    for marks in SHIELD_SIGNS.values():
        for m in marks:
            if m in head:
                return False
    if keywords:
        return any(k in html for k in keywords)
    return True

SLIDER_RE = re.compile(r'src="(/huadong_[^"]+\.js)\?id=(\d+)"')
DEFAULT_VERIFY_PATH = '/a20be899_96a6_40b2_88ba_32f1f75f1552_yanzheng_huadong.php'
DEFAULT_VERIFY_TYPE = 'ad82060c2e67cc7e2cc47552a4fc1242'

def solve_slider(session, host, html=None, target_url=None, timeout=15):
    """huadong_*.js 纯计算破解。target_url = 触发验证的那个页面（全程 Referer 都用它）。"""
    try:
        target_url = target_url or (host + '/')
        if html is None:
            r = session.get(target_url, timeout=timeout)
            html = r.text
            if r.status_code != 403 and '滑动验证' not in html:
                return True, '无需验证'
        m = SLIDER_RE.search(html)
        if not m:
            return False, '页面无 huadong JS'
        js_path, ts = m.group(1), m.group(2)
        js = session.get(host + js_path + '?id=' + ts,
                         headers={'Referer': target_url}, timeout=timeout).text
        key = js_path.rsplit('_', 1)[-1].replace('.js', '')
        if not key:
            km = re.search(r'key\s*=\s*"([^"]+)"', js)
            key = km.group(1) if km else ''
        vm = re.search(r'value\s*=\s*"([^"]+)"', js)
        if not (key and vm):
            return False, '提 key/value 失败'
        sign_src = ''.join(str(ord(c) + 1) for c in vm.group(1))
        sign = hashlib.md5(sign_src.encode('utf-8')).hexdigest()
        pm = re.search(r'c\.get\("(/[a-z0-9_]+_yanzheng_huadong\.php)\?type=([a-f0-9]+)&key="', js)
        vpath, vtype = (pm.group(1), pm.group(2)) if pm else (DEFAULT_VERIFY_PATH, DEFAULT_VERIFY_TYPE)
        session.get('%s%s?type=%s&key=%s&value=%s' % (host, vpath, vtype, key, sign),
                    headers={'Referer': target_url}, timeout=timeout)
        return True, '已提交验证'
    except Exception as e:
        return False, '异常: %s' % str(e)[:80]

def make_session(headers=None, proxy=None, auto_proxy=True):
    """建 session；自动探测本机代理（发给别人的源不要写死地址）。"""
    import os
    import requests
    requests.packages.urllib3.disable_warnings()
    s = requests.Session()
    if headers:
        s.headers.update(headers)
    if proxy:
        s.proxies = {'http': proxy, 'https': proxy}
        return s
    if not auto_proxy:
        return s
    p = (os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY') or os.environ.get('ALL_PROXY') or '')
    if p:
        s.proxies = {'http': p, 'https': p}
        return s
    for port in (7890, 7891, 1080, 1087, 10809, 24780, 2333, 6153, 16666, 20170, 9090, 7070):
        try:
            socket.create_connection(('127.0.0.1', port), timeout=0.3).close()
            s.proxies = {'http': 'http://127.0.0.1:%d' % port, 'https': 'http://127.0.0.1:%d' % port}
            return s
        except Exception:
            continue
    return s

def probe_hosts(candidates, check_path='/', keyword='', ua=None, timeout=5, workers=10):
    """并发探活；用 ex.map() 保序，返回第一个可用域名。"""
    import requests
    ua = ua or ('Mozilla/5.0 (Linux; Android 16; 2510DRK44C) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Version/4.0 Chrome/143.0.7499.192 Mobile Safari/537.36')
    def test(host):
        try:
            host = host.rstrip('/')
            r = requests.get(host + check_path,
                             headers={'User-Agent': ua, 'Referer': host + '/'},
                             timeout=(1.5, timeout), verify=False)
            if r.status_code == 200 and (not keyword or keyword in r.text):
                return host
        except Exception:
            pass
        return None
    if not candidates:
        return ''
    with ThreadPoolExecutor(max_workers=min(workers, len(candidates))) as ex:
        for res in ex.map(test, candidates):
            if res:
                return res
    return ''
