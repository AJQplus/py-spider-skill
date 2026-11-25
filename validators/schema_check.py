#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def _walk_required(schema, inst, path=''):
    errors = []
    req = schema.get('required', [])
    for key in req:
        if key not in inst:
            errors.append(f'{path}.{key}: 缺少必填字段')
    for key, sub in schema.get('properties', {}).items():
        if key not in inst:
            continue
        if sub.get('type') == 'object':
            if isinstance(inst[key], dict):
                errors += _walk_required(sub, inst[key], path + '.' + key)
            else:
                errors.append(f'{path}.{key}: 类型应为 object')
        elif sub.get('type') == 'array' and not isinstance(inst[key], list):
            errors.append(f'{path}.{key}: 类型应为 array')
        elif sub.get('type') in ('string', 'boolean', 'integer') and sub.get('type') == 'boolean' and not isinstance(inst[key], bool):
            errors.append(f'{path}.{key}: 类型应为 boolean')
        elif sub.get('enum') and inst[key] not in sub['enum']:
            errors.append(f'{path}.{key}: 取值不在枚举内')
    return errors

def main():
    if len(sys.argv) != 3:
        print('用法: schema_check.py schema.json instance.json'); return 2
    try:
        schema = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
        inst = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
    except Exception as exc:
        print('FAIL:', exc); return 1
    errors = _walk_required(schema, inst)
    for e in errors:
        print('FAIL:', e)
    print('PASS' if not errors else 'FAIL')
    return 0 if not errors else 1

if __name__ == '__main__':
    raise SystemExit(main())
