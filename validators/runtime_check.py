#!/usr/bin/env python3
import json
import sys

def page_result(value):
    if not isinstance(value, dict): return False, '返回值不是字典'
    keys = {'page', 'pagecount', 'limit', 'total', 'list'}
    miss = keys - set(value)
    return (not miss, '缺少字段: ' + ','.join(sorted(miss))) if miss else (True, '')

def detail_result(value):
    if not isinstance(value, dict) or not isinstance(value.get('list'), list): return False, '详情返回结构错误'
    for item in value['list']:
        if not isinstance(item, dict): return False, '详情项不是字典'
        if 'vod_play_from' in item or 'vod_play_url' in item:
            if 'vod_play_from' not in item or 'vod_play_url' not in item: return False, '线路字段不完整'
            fs = str(item['vod_play_from']).split('$$$') if item['vod_play_from'] else []
            us = str(item['vod_play_url']).split('$$$') if item['vod_play_url'] else []
            if len(fs) != len(us): return False, '线路数量不一致'
    return True, ''

def main():
    if len(sys.argv) != 2:
        print('用法: runtime_check.py result.json'); return 2
    try: data = json.load(open(sys.argv[1], encoding='utf-8'))
    except Exception as exc: print('FAIL:', exc); return 1
    ok, msg = page_result(data) if 'page' in data else detail_result(data)
    print('PASS' if ok else 'FAIL: ' + msg)
    return 0 if ok else 1

if __name__ == '__main__': raise SystemExit(main())
