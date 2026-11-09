#!/usr/bin/env bash
# Статический экспорт SC (копия SpaceCam) для GitHub Pages (basePath /SC)
set -euo pipefail
cd "${SC_WORK:-/home/z/my-project}"
NEXT_EXPORT=1 NEXT_PUBLIC_BASE_PATH=/SC bun run build
touch out/.nojekyll
echo "--- export done ---"
ls out/ | head -20
