#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Глубокая сверка JS-чанков SP vs SC:
1) наборы module-id в каждой паре чанков должны совпадать;
2) basePath-литерал должен присутствовать в JS обеих сборок;
3) ключевые строки функционала (роуты, табы админки,_ARTикулы) — равные множества.
"""
import os, re, urllib.request

TOKEN = os.environ.get("GH_TOKEN", "")
RAW = "https://raw.githubusercontent.com/andreyshalnov/{repo}/main/{path}"
SPB, SCB = "P6yxmiFjby9OUSJBxUQL6", "Kc0XrrrtaqB2o0b0zihWm".replace("m", "w")

PAIRS = [
    ("4f944173aa25ec4e.js", "e22ddfc77ddb9924.js"),
    ("b5f9265de5a508fe.js", "ba6c4aae54615e57.js"),
    ("turbopack-85c5fcab3b1aa3bd.js", "turbopack-e2db3c0d94f989be.js"),
]

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "diag2/1.0"})
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    return urllib.request.urlopen(req, timeout=60).read()

def mod_ids(b):
    """module-id: e.i(NNNNN), I[NNNNN], (NNNNN,(e,t,n)=> — все числовые ссылки."""
    ids = set()
    ids |= set(re.findall(rb"[.(]i\((\d{2,6})\)", b))
    ids |= set(re.findall(rb"I\[(\d{2,6})", b))
    ids |= set(re.findall(rb"[,(](\d{2,6}),\(", b))
    return {int(x) for x in ids}

fails = []
for spn, scn in PAIRS:
    sp = fetch(RAW.format(repo="SpaceCam", path=f"_next/static/chunks/{spn}"))
    sc = fetch(RAW.format(repo="SC", path=f"_next/static/chunks/{scn}"))
    a, b = mod_ids(sp), mod_ids(sc)
    only_a, only_b = sorted(a - b), sorted(b - a)
    ok = not only_a and not only_b
    print(f"{'  OK  ' if ok else '  FAIL'} {spn[:12]}↔{scn[:12]}: module-id {len(a)} vs {len(b)}; только SP: {only_a[:8]}{'...' if len(only_a)>8 else ''}; только SC: {only_b[:8]}{'...' if len(only_b)>8 else ''}")
    if not ok:
        fails.append((spn, only_a, only_b))

# basePath-литералы в JS обеих сборок (по всем общим + парным чанкам)
print("\n── basePath-литералы в JS ──")
all_sp = [PAIRS[0][0], PAIRS[1][0], PAIRS[2][0], "42879de7b8087bc9.js"]
all_sc = [PAIRS[0][1], PAIRS[1][1], PAIRS[2][1], "42879de7b8087bc9.js"]
sp_n = sum(fetch(RAW.format(repo="SpaceCam", path=f"_next/static/chunks/{n}")).count(b'"/SpaceCam"') for n in all_sp)
sc_n = sum(fetch(RAW.format(repo="SC", path=f"_next/static/chunks/{n}")).count(b'"/SC"') for n in all_sc)
print(f"  '/SpaceCam' в SP JS: {sp_n} раз; '/SC' в SC JS: {sc_n} раз")
if not (sp_n > 0 and sc_n > 0):
    fails.append("basePath-литерал не найден в одной из сборок!")

# ключевые функциональные строки: множества должны совпасть
print("\n── Ключевые строки функционала (админ-табы, роуты, функции) ──")
KEYS = [b"#/admin", b"#/products", b"#/project-reg", b"#/solutions", b"#/dealers",
        b"\xd0\xa1\xd0\xb2\xd0\xb5\xd1\x80\xd0\xba\xd0\xb0 \xd0\xbd\xd0\xb0\xd0\xbb\xd0\xb8\xd1\x87\xd0\xb8\xd1\x8f",  # Сверка наличия
        b"\xd0\x9f\xd1\x80\xd0\xbe\xd0\xb4\xd0\xb0\xd0\xb6\xd0\xb8 \xd0\xb2 \xd1\x88\xd1\x82\xd1\x83\xd0\xba\xd0\xb0\xd1\x85",  # Продажи в штуках
        b"\xd0\x98\xd0\xbc\xd0\xbf\xd0\xbe\xd1\x80\xd1\x82",  # Импорт
        b"sb_publishable_", b"supabase.co"]
def joined(repo, names):
    out = b""
    for n in names:
        out += fetch(RAW.format(repo=repo, path=f"_next/static/chunks/{n}"))
    return out
jsp = joined("SpaceCam", all_sp)
jsc = joined("SC", all_sc)
for k in KEYS:
    ok = (k in jsp) == (k in jsc)
    print(f"  {'  OK  ' if ok else '  FAIL'} {k[:30]!r}: SP={k in jsp}, SC={k in jsc}")
    if not ok:
        fails.append(k)

print("\nИТОГ:", "ВСЁ СХОДИТСЯ — JS функционально идентичен" if not fails else f"ПРОБЛЕМЫ: {len(fails)}")
