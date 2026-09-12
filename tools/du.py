# -*- coding: utf-8 -*-
import os, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
def du(path):
    t = 0
    for r, _, fs in os.walk(path):
        for f in fs:
            t += os.path.getsize(os.path.join(r, f))
    return t
for d in ('data', 'data/shots', 'assets', 'site', 'tools'):
    print(d, du(d) // 1024, 'KB')
for f in ('data/site.json', 'data/qbook_raw.json', 'data/abook_raw.json'):
    print(f, os.path.getsize(f) // 1024, 'KB')
