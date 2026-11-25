#!/usr/bin/env python3
import sys

def page(v):
    return isinstance(v, dict) and {'page','pagecount','limit','total','list'} <= set(v)

def detail(v):
    if not isinstance(v, dict) or not isinstance(v.get('list'), list): return False
    for x in v['list']:
        if not isinstance(x, dict): return False
        f, u = str(x.get('vod_play_from','')), str(x.get('vod_play_url',''))
        if f or u:
            if not f or not u or len(f.split('$$$')) != len(u.split('$$$')): return False
    return True

def main():
    if len(sys.argv) != 2: return 2
    path=sys.argv[1]
    import importlib.util
    spec=importlib.util.spec_from_file_location('source',path); mod=importlib.util.module_from_spec(spec)
    try: spec.loader.exec_module(mod); obj=mod.Spider(); obj.init('')
    except Exception as e: print('BLOCKED:',e); return 2
    required=('homeContent','homeVideoContent','categoryContent','detailContent','searchContent','playerContent')
    if any(not callable(getattr(obj,x,None)) for x in required): print('FAIL: 六接口缺失'); return 1
    try:
        checks=[obj.homeContent(False),obj.homeVideoContent(),obj.categoryContent('',1,False,''),obj.searchContent('测试','0','1')]
        if not page(checks[2]) or not page(checks[3]): print('FAIL: 列表契约'); return 1
        if not detail(obj.detailContent([''])): print('FAIL: 详情契约'); return 1
    except Exception as e: print('FAIL:',e); return 1
    print('PASS: 行为契约'); return 0
if __name__=='__main__': raise SystemExit(main())
