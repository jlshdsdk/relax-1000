# -*- coding: utf-8 -*-
import io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
print("=== figures tail ===")
t = open('data/figures_log.txt', encoding='utf-8').read()
print(t[-400:])
print("=== merge tail ===")
t = open('data/merge_log.txt', encoding='utf-8').read()
print(t[-2500:])
