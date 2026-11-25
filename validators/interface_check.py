#!/usr/bin/env python3
import importlib.util,sys
from pathlib import Path
def main():
 if len(sys.argv)!=2: print('用法: interface_check.py source.py'); return 2
 p=Path(sys.argv[1]); spec=importlib.util.spec_from_file_location('source',p); mod=importlib.util.module_from_spec(spec)
 try: spec.loader.exec_module(mod)
 except Exception as e: print('BLOCKED: 导入失败:',e); return 2
 s=getattr(mod,'Spider',None)
 if s is None: print('FAIL: 缺少 Spider'); return 1
 try: obj=s(); obj.init('')
 except Exception as e: print('BLOCKED: 初始化失败:',e); return 2
 names=['homeContent','homeVideoContent','categoryContent','detailContent','searchContent','playerContent']; miss=[x for x in names if not callable(getattr(obj,x,None))]
 if miss: print('FAIL: 缺少接口:',','.join(miss)); return 1
 print('PASS: 六接口存在'); return 0
if __name__=='__main__': raise SystemExit(main())
