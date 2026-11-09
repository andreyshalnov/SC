#!/usr/bin/env bash
# ═════════════════════════════════════════════════════════════════════════════
# Канонический деплой SC (копия сайта SpaceCam в репо andreyshalnov/SC).
#
# Использование:
#   GH_TOKEN='<PAT>' bash scripts/deploy_sc.sh "описание правки"
#
# Отличия от deploy_spacecam.sh (оригинал в репо SpaceCam):
#   • basePath /SC  (NEXT_PUBLIC_BASE_PATH=/SC) вместо /SpaceCam;
#   • push в origin = andreyshalnov/SC;
#   • верификация: scripts/verify_sc.py (BASE = .../SC/).
# Supabase-бэкенд общий с оригиналом — данные (каталог, цены, склад, реестр
# объектов) полностью совпадают на обеих копиях.
#
# Что делает:
#   1) git pull --ff-only этого репозитория + проверка чистоты дерева
#   2) синкает исходники репо (src/ + конфиги) в рабочее пространство
#      $SC_WORK (по умолчанию /home/z/my-project)
#   3) bun install + статический экспорт (NEXT_PUBLIC_BASE_PATH=/SC)
#   4) копирует сборку в корень репо, НЕ трогая проектные пути:
#      src/, scripts/, docs/*.md, docs/sql/, .git
#   5) коммит + push (Pages пересоберётся за 1–3 мин)
#   6) напоминает про верификацию: python3 scripts/verify_sc.py
#
# Требования: bun, rsync, git. GH_TOKEN — PAT с правами на репозиторий SC.
# ═════════════════════════════════════════════════════════════════════════════
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${SC_WORK:-/home/z/my-project}"
MSG="${1:?Использование: deploy_sc.sh \"описание правки\"}"

echo "── 1/6 Репо: pull + проверка чистоты ──"
cd "$REPO"
git pull --ff-only origin main
if [ -n "$(git status --porcelain)" ]; then
  echo "ОШИБКА: рабочее дерево репо не чистое — закоммитьте или спрячьте правки."; exit 1
fi
[ -d "$REPO/src" ] || { echo "ОШИБКА: в репо нет src/ — некуда собирать."; exit 1; }

echo "── 2/6 Синк исходников репо → workspace ($WORK) ──"
[ -d "$WORK" ] || { echo "ОШИБКА: нет workspace $WORK"; exit 1; }
rsync -a --delete "$REPO/src/" "$WORK/src/"
for f in next.config.ts package.json postcss.config.mjs tsconfig.json bun.lock components.json tailwind.config.ts; do
  [ -f "$REPO/$f" ] && cp "$REPO/$f" "$WORK/$f"
done

echo "── 2.5/6 Статика репо → workspace public/ ──"
for d in products brands dealers solutions; do
  [ -d "$REPO/$d" ] && rsync -a --delete "$REPO/$d/" "$WORK/public/$d/"
done
mkdir -p "$WORK/public/docs" && cp -f "$REPO"/docs/*.pdf "$WORK/public/docs"/
for f in logo.png logo-light.png logo.svg robots.txt; do
  [ -f "$REPO/$f" ] && cp -f "$REPO/$f" "$WORK/public/$f"
done

echo "── 3/6 Сборка static export (basePath /SC) ──"
cd "$WORK"
bun install >/dev/null
NEXT_EXPORT=1 NEXT_PUBLIC_BASE_PATH=/SC bun run build
touch out/.nojekyll
[ -f out/index.html ] || { echo "ОШИБКА: out/index.html не создан"; exit 1; }

echo "── 4/6 Статика → корень репо (проектные пути защищены) ──"
cd "$REPO"
rsync -a --delete "$WORK/out/" "$REPO/" \
  --exclude '.git' \
  --exclude '/src' \
  --exclude '/scripts' \
  --exclude '/docs/sql' \
  --exclude '/docs/SC_NOTES.md' \
  --exclude '/docs/PROJECT_NOTES.md' \
  --exclude '/docs/TECH_SPEC.md' \
  --exclude '/docs/STATE.md' \
  --exclude '/package.json' \
  --exclude '/bun.lock' \
  --exclude '/tsconfig.json' \
  --exclude '/next.config.ts' \
  --exclude '/postcss.config.mjs' \
  --exclude '/next-env.d.ts'

echo "── 5/6 Коммит + push ──"
git add -A
if git diff --cached --quiet; then
  echo "Изменений нет — деплой не нужен."; exit 0
fi
git commit -m "Deploy: $MSG"
git push origin main

echo "── 6/6 Верификация ──"
echo "Через 1–3 мин (кеш Pages 600 с) выполните:"
echo "  python3 $REPO/scripts/verify_sc.py"
echo "Деплой '$MSG' отправлен: $(git rev-parse --short HEAD)"
