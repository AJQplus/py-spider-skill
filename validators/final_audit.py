#!/usr/bin/env python3
import ast,sys,re
from pathlib import Path
REQ={'homeContent','homeVideoContent','categoryContent','detailContent','searchContent','playerContent'}
def audit(p):
 s=p.read_text(encoding='utf-8',errors='ignore'); e=[]
 try:t=ast.parse(s)
 except Exception as x:return ['语法错误:'+str(x)]
 c=next((x for x in t.body if isinstance(x,ast.ClassDef) and x.name=='Spider'),None)
 if not c:return ['缺少Spider']
 m={x.name for x in c.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef))}
 e += ['缺少接口:'+x for x in sorted(REQ-m)]
 if 'from base.spider import Spider' not in s:e.append('缺少T4基类导入')
 if 'vod_play_from' in s and 'vod_play_url' in s and 'join(fs)' in s and 'join(us)' in s and not ('len(fs)' in s and 'len(us)' in s):e.append('线路数量未校验')
 if re.search(r'parse["\']\s*[:=]\s*0',s) and not any(x in s for x in ('_probe_media','_validate_media','#EXTM3U')):e.append('parse0无媒体门禁')
 if re.search(r'from lxml import etree',s) and 'except Exception' not in s:e.append('lxml无导入兜底')
 return e
def main():
 root=Path(sys.argv[1] if len(sys.argv)>1 else 'templates/code'); bad=0
 for p in sorted(root.rglob('*.py')) if root.is_dir() else [root]:
  if 'archive' in p.parts or '__pycache__' in p.parts:continue
  e=audit(p); print(f'{p}: '+('FAIL: '+';'.join(e) if e else 'PASS'));bad+=bool(e)
 return 1 if bad else 0
if __name__=='__main__':raise SystemExit(main())
