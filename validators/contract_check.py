#!/usr/bin/env python3
import ast,sys
from pathlib import Path

def check(path):
    tree=ast.parse(Path(path).read_text(encoding='utf-8'))
    cls=next((x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='Spider'),None)
    if cls is None:return ['缺少 Spider']
    methods={x.name:x for x in cls.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef))}
    errors=[]
    required=['homeContent','homeVideoContent','categoryContent','detailContent','searchContent','playerContent']
    for name in required:
        if name not in methods: errors.append('缺少接口:'+name)
    for name in ('categoryContent','searchContent'):
        n=methods.get(name)
        if n is None:continue
        source=ast.get_source_segment(Path(path).read_text(encoding='utf-8'),n) or ''
        if ('self._page' not in source) and ('pagecount' not in source or 'list' not in source): errors.append(name+'缺少分页或列表字段')
    for n in ast.walk(tree):
        if isinstance(n,ast.Return) and isinstance(n.value,ast.Dict):
            keys={k.value for k in n.value.keys if isinstance(k,ast.Constant)}
            if 'vod_play_from' in keys and 'vod_play_url' not in keys: errors.append('详情线路字段不完整')
    return list(dict.fromkeys(errors))

def main():
    if len(sys.argv)!=2:return 2
    paths=[Path(sys.argv[1])] if Path(sys.argv[1]).is_file() else sorted(Path(sys.argv[1]).rglob('*.py'))
    failed=0
    for p in paths:
        if '__pycache__' in p.parts or 'archive' in p.parts:continue
        e=check(p)
        print(f'{p}: '+('FAIL: '+'; '.join(e) if e else 'PASS'))
        failed+=bool(e)
    return 1 if failed else 0
if __name__=='__main__':raise SystemExit(main())