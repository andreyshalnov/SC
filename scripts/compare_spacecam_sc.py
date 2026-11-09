#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сверка SpaceCam vs SC: доказательство идентичности дизайна и функционала.

Метод:
  1) git-деревья обоих репо (recursive) → path → blob sha;
  2) уникальные для одного репо файлы — сверка со списком ожидаемых;
  3) все общие файлы с разными sha → побайтовое сравнение после нормализации
     basePath (/SpaceCam → /SC) и имени build-каталога turbopack;
  4) непарные чанки (те, что содержат basePath в контенте) → матч по
     нормализованному контенту;
  5) live-пробы: bytes на github.io == bytes в репо для обоих сайтов.
Код возврата 0 = доказана идентичность (с точностью до basePath/id сборки).
"""
import hashlib
import json
import os
import re
import sys
import urllib.request

TOKEN = os.environ.get("GH_TOKEN", "")
RAW = "https://raw.githubusercontent.com/andreyshalnov/{repo}/main/{path}"
LIVE = "https://andreyshalnov.github.io/{site}/{path}"

failures = []
notes = []


def check(ok, text):
    print(("  OK   " if ok else "  FAIL ") + text)
    if not ok:
        failures.append(text)


def fetch(url, auth=False):
    req = urllib.request.Request(url)
    if auth and TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("User-Agent", "sc-compare/1.0")
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def get_tree(repo):
    d = json.loads(fetch(f"https://api.github.com/repos/andreyshalnov/{repo}/git/trees/main?recursive=1", auth=True))
    if d.get("truncated"):
        notes.append(f"{repo}: дерево ОБРЕЗАНО — сравнение неполное!")
    out = {}
    for t in d["tree"]:
        if t["type"] == "blob":
            out[t["path"]] = t["sha"]
    return out


sp_raw = get_tree("SpaceCam")
sc_raw = get_tree("SC")

# build-каталоги turbopack (_next/static/<RANDOM>/_buildManifest.js)
def build_dir(tree):
    for p in tree:
        m = re.match(r"_next/static/([^/]+)/_buildManifest\.js$", p)
        if m:
            return m.group(1)
    return None

SPB, SCB = build_dir(sp_raw), build_dir(sc_raw)
print(f"build-каталоги: SpaceCam={SPB} SC={SCB}")

# нормализация путей: уникальный build-каталог SpaceCam → каталог SC
sp = {p.replace(f"_next/static/{SPB}/", f"_next/static/{SCB}/"): s for p, s in sp_raw.items()}
sc = dict(sc_raw)

def norm(b):
    b = b.replace(b"/SpaceCam", b"/SC")
    if SPB and SCB:
        b = b.replace(SPB.encode(), SCB.encode())
    # маскируем hash-имена чанков: они зависят от контента, в который
    # зашит basePath, потому различаются даже при идентичном коде
    b = re.sub(rb"[0-9a-f]{16}\.js", b"~CHUNK~.js", b)
    b = re.sub(rb"[0-9a-f]{16}\.css", b"~CHUNK~.css", b)
    b = re.sub(rb"turbopack-[0-9a-f]{16}", b"turbopack-~T~", b)
    return b

# операционные скрипты (не часть сайта) — различия допустимы по дизайну задачи
OPS_DIFFER = {"scripts/build_static_export.sh"}

common = set(sp) & set(sc)
only_sp = sorted(set(sp) - set(sc))
only_sc = sorted(set(sc) - set(sp))
same, differ = [], []
for p in sorted(common):
    (same if sp[p] == sc[p] else differ).append(p)

print(f"\n── 1. Деревья ──")
print(f"SpaceCam файлов: {len(sp_raw)}, SC: {len(sc_raw)}")
print(f"общих: {len(common)}, из них идентичных blob: {len(same)}, различаются: {len(differ)}")

# 2. уникальные файлы
EXPECTED_ONLY_SP = {"scripts/deploy_spacecam.sh", "scripts/verify_deploy.py"}
EXPECTED_ONLY_SC = {"docs/SC_NOTES.md", "scripts/deploy_sc.sh", "scripts/verify_sc.py", "scripts/compare_spacecam_sc.py", "scripts/compare_chunks_deep.py"}
print(f"\n── 2. Файлы только в одном репо ──")
unexpected = []
for p in only_sp:
    if p.startswith("docs/backup/") or p in EXPECTED_ONLY_SP or p.startswith("_next/static/chunks/"):
        continue
    unexpected.append("SpaceCam: " + p)
for p in only_sc:
    if p in EXPECTED_ONLY_SC or p.startswith("_next/static/chunks/"):
        continue
    unexpected.append("SC: " + p)
check(not unexpected, f"нет неожиданных уникальных файлов (найдено: {unexpected if unexpected else '0'})")
print(f"  ожидаемо только в SpaceCam: {len([p for p in only_sp if p.startswith('docs/backup/')])} (docs/backup/) + 2 скрипта + чанки")
print(f"  ожидаемо только в SC: {len(EXPECTED_ONLY_SC)} (SC-скрипты/notes + скрипты сверки) + чанки")

# 3. общие файлы с разными sha: нормализация должна свести их
print(f"\n── 3. Общие файлы с разными blob (проверка: различия = только basePath/id сборки) ──")
bad = []
ops_ok = []
for p in differ:
    if p in OPS_DIFFER:
        spb = fetch(RAW.format(repo="SpaceCam", path=p))
        scb = fetch(RAW.format(repo="SC", path=p))
        ok = (b"/SpaceCam" in spb and b"NEXT_PUBLIC_BASE_PATH=/SpaceCam" in spb
              and b"NEXT_PUBLIC_BASE_PATH=/SC" in scb and b"/SpaceCam" not in scb)
        if ok:
            ops_ok.append(p)
            print(f"  OK   {p}: операционный скрипт, basePath адаптирован (не часть сайта)")
        else:
            bad.append(f"{p}: неожиданное содержимое операционного скрипта")
        continue
    try:
        spb = fetch(RAW.format(repo="SpaceCam", path=p))
        scb = fetch(RAW.format(repo="SC", path=p))
    except Exception as e:
        bad.append(f"{p}: fetch error {e}")
        continue
    if norm(spb) == norm(scb):
        print(f"  OK   {p}: идентичен после нормализации ({len(spb)} b)")
    else:
        bad.append(p)
        nb, ns = norm(spb), norm(scb)
        i = next((k for k in range(min(len(nb), len(ns))) if nb[k:k+1] != ns[k:k+1]), 0)
        w = nb[max(0,i-40):i+40], ns[max(0,i-40):i+40]
        notes.append(f"{p}: первое расхождение @{i}: {w}")

check(not bad, f"все различающиеся общие файлы сводятся нормализацией (проблемные: {bad if bad else '0'})")

# 4. непарные чанки: матч по нормализованному контенту
print(f"\n── 4. Непарные чанки ──")
sp_chunks = sorted(p for p in only_sp if p.startswith("_next/static/chunks/"))
sc_chunks = sorted(p for p in only_sc if p.startswith("_next/static/chunks/"))
print(f"  SpaceCam: {sp_chunks}")
print(f"  SC:       {sc_chunks}")
sp_cache, sc_cache = {}, {}
for p in sp_chunks:
    sp_cache[p] = fetch(RAW.format(repo="SpaceCam", path=p))
for p in sc_chunks:
    sc_cache[p] = fetch(RAW.format(repo="SC", path=p))
paired, unpaired = [], list(sc_chunks)
for spn in sp_chunks:
    hit = None
    for scn in unpaired:
        if norm(sp_cache[spn]) == norm(sc_cache[scn]):
            hit = scn
            break
    if hit:
        paired.append((spn, hit))
        unpaired.remove(hit)
        print(f"  OK   пара: {spn} ↔ {hit} (после нормализации контент равен)")
    else:
        bad.append(f"чанк {spn} без пары в SC")
check(len(paired) == len(sp_chunks) == len(sc_chunks),
      f"все непарные чанки сматчены по контенту: {len(paired)} пар; без пары: {unpaired if unpaired else '0'}")

# 5. live-пробы
print(f"\n── 5. Live-пробы (github.io == репо) ──")
def sha(b):
    return hashlib.sha256(b).hexdigest()

css = next(p for p in sorted(common) if p.startswith("_next/static/chunks/") and p.endswith(".css"))
js = next(p for p in sorted(same) if p.startswith("_next/static/chunks/") and p.endswith(".js"))
photo = next(p for p in sorted(common) if p.startswith("products/") and re.search(r"\.(jpg|png|webp)$", p))
pdf = next(p for p in sorted(common) if p.startswith("docs/") and p.endswith(".pdf"))
probes = ["index.html", "404.html", "robots.txt", css, js, "logo.png", photo, pdf]
for p in probes:
    try:
        sp_live = fetch(LIVE.format(site="SpaceCam", path=p))
        sc_live = fetch(LIVE.format(site="SC", path=p))
        sp_repo = fetch(RAW.format(repo="SpaceCam", path=p))
        sc_repo = fetch(RAW.format(repo="SC", path=p))
        ok_sp = sha(sp_live) == sha(sp_repo)
        ok_sc = sha(sc_live) == sha(sc_repo)
        ok_eq = sha(sp_repo) == sha(sc_repo) or norm(sp_repo) == norm(sc_repo)
        kind = "ident" if sha(sp_repo) == sha(sc_repo) else "norm"
        check(ok_sp and ok_sc and ok_eq,
              f"{p}: live SP==repo {ok_sp}, live SC==repo {ok_sc}, SP==SC ({kind})")
    except Exception as e:
        check(False, f"{p}: ошибка пробы {e}")

# CSS-дизайн: побайтовое равенство всех CSS
print(f"\n── 6. CSS (дизайн) ──")
css_common = [p for p in sorted(common) if p.endswith(".css")]
for p in css_common:
    eq = sp[p] == sc[p]
    check(eq, f"{p}: blob {'идентичен' if eq else 'РАЗЛИЧАЕТСЯ'}")

print(f"\n── 7. Живая HTML-страница: контент после нормализации+маски ──")
for p in ("index.html", "404.html"):
    spb = fetch(LIVE.format(site="SpaceCam", path=p))
    scb = fetch(LIVE.format(site="SC", path=p))
    check(norm(spb) == norm(scb), f"{p} (live): разметка/контент идентичны после нормализации")

print(f"\n── Итог ──")
print(f"Идентичных файлов (blob): {len(same)} из {len(common)} общих")
for n in notes:
    print("NOTE:", n)
if failures:
    print("ЕСТЬ РАСХОЖДЕНИЯ:")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("ВЕРДИКТ: SpaceCam и SC идентичны по дизайну и функционалу (различия только basePath /SpaceCam↔/SC и id сборки turbopack).")
sys.exit(0)
