# -*- coding: utf-8 -*-
import os, glob, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
junk = glob.glob('assets/*{_tag}*')
for f in junk:
    os.remove(f)
print('junk removed:', len(junk))
all_png = glob.glob('assets/*.png')
print('remaining pngs:', len(all_png))
sizes = [os.path.getsize(f) for f in all_png]
print('total KB:', sum(sizes) // 1024, 'max KB:', max(sizes) // 1024)
