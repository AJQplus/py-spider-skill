#!/usr/bin/env python3
import ast
import re
import sys
from pathlib import Path
REQUIRED={'homeContent','homeVideoContent','categoryContent','detailContent','searchContent','playerContent'}
def audit(path):
    text=path.read_text(encoding='utf-8',errors='ignore')
    try: tree=ast.parse(text)
    except SyntaxError as exc: return ['语法错误: '+str(exc)]
    cls=next((x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='Spider'),None)
    if cls is None:return ['缺少 Spider']
    methods={x.name for x in cls.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef))}
    errors=['缺少接口: '+x for x in sorted(REQUIRED-methods)]
    if 'from base.spider import Spider' not in text:
        errors.append('缺少 base.spider.Spider 导入')
    if 'from lxml import etree' in text and 'try:' not in text:
        errors.append('可选依赖未做导入兜底')
    if 'vod_play_from' in text and 'vod_play_url' in text and 'join(fs)' in text and 'join(us)' in text and ('len(fs)' not in text or 'len(us)' not in text):errors.append('线路数量未强制校验')
    if re.search(r'parse["\']\s*[:=]\s*0',text) and not any(x in text for x in ('_probe_media','_validate_media','#EXTM3U')):errors.append('parse:0 缺少媒体门禁')
    return errors
def main():
    if len(sys.argv)!=2:return 2
    root=Path(sys.argv[1]); paths=[root] if root.is_file() else sorted(root.rglob('*.py')); failed=0
    for path in paths:
        if 'archive' in path.parts or '__pycache__' in path.parts:continue
        errors=audit(path); print(f'{path}: '+('FAIL: '+'; '.join(errors) if errors else 'PASS')); failed+=bool(errors)
    return 1 if failed else 0
if __name__=='__main__':raise SystemExit(main())