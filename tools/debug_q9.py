# -*- coding: utf-8 -*-
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
s = json.load(open('data/site.json', encoding='utf-8'))
ch = [c for c in s['chapters'] if c['id'] == 'p4c4'][0]
for q in ch['questions']:
    if q['num'] == 9:
        print('stem:', q['stem_text'][:100])
        for L in 'ABCD':
            print(L, ':', q['opts'].get(L, {}).get('text', ''))
        print('ans:', q['ans'])
