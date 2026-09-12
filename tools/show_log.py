# -*- coding: utf-8 -*-
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
lines = open('data/extract_log5.txt', encoding='utf-8').read().splitlines()
sel = [l for l in lines if ('提示' in l or '警告' in l or '合计' in l or '题' in l and '解' in l)]
print('\n'.join(sel[-40:]) if sel else '(none)')
