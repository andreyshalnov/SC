# SC — копия рабочего сайта SpaceCam в репозитории andreyshalnov/SC

## Что это

Полная копия работающего сайта SpaceCam (репозиторий `andreyshalnov/SpaceCam`,
https://andreyshalnov.github.io/SpaceCam/), выложенная в репозиторий
`andreyshalnov/SC` и доступная по адресу:

**https://andreyshalnov.github.io/SC/**

Копия собрана из тех же исходников (main репо SpaceCam) с basePath `/SC`.
Подтверждено: в сборке ноль путей `/SpaceCam/`, все ассеты ссылаются на `/SC/...`.

## Общий бэкенд

Supabase-проект тот же, что у оригинала: `kgdrtrfwsyixprvuzdqj` (см.
`src/lib/supabase.ts`, publishable-ключ публичный). Каталог, цены, склад,
новости и реестр объектов полностью общие — обе копии показывают одни данные.
Все изменения данных (админка, импорт остатков) синхронны на обеих копиях.

## Отличия от репозитория SpaceCam

| | SpaceCam | SC |
|---|---|---|
| basePath | `/SpaceCam` | `/SC` |
| Канонический деплой | `scripts/deploy_spacecam.sh` | `scripts/deploy_sc.sh` |
| Верификация | `scripts/verify_deploy.py` | `scripts/verify_sc.py` |
| URL live | https://andreyshalnov.github.io/SpaceCam/ | https://andreyshalnov.github.io/SC/ |

Всё остальное идентично. Документы `STATE.md`, `TECH_SPEC.md`,
`PROJECT_NOTES.md` скопированы из оригинала как историческая справка: описанные
в них протоколы (деплой, верификация, работа с БД) применимы к SC с поправкой
на имена скриптов и basePath из таблицы выше. `docs/backup/` не копировался
(бэкапы остаются только в репозитории SpaceCam).

## Деплой

```bash
cd <клон этого репозитория>
GH_TOKEN='<PAT с правами на SC>' bash scripts/deploy_sc.sh "описание правки"
```

Скрипт: pull → синк исходников в workspace `/home/z/my-project` (или
`SC_WORK=...`) → сборка `NEXT_EXPORT=1 NEXT_PUBLIC_BASE_PATH=/SC` → копирование
статики в корень репо (проектные пути `src/`, `scripts/`, `docs/*.md` защищены)
→ коммит → push. Через 1–3 мин: `python3 scripts/verify_sc.py [--full]`.

## Эталонные счётчики БД для `verify_sc.py --full`

Сняты при создании копии 09.11.2026: `objects` 258, `object_specs` 436,
`object_spec_items` 1094, `object_types` 14, `profiles` 14, `prices` 2487.
При изменении данных обновлять здесь и в `scripts/verify_sc.py` (ключ
`expected`).

## История деплоев

| Дата | Коммит | Что сделано | Верификация |
|---|---|---|---|
| 09.11.2026 | `fd1f06d` | Первая выкатка: копия SpaceCam main `a09b615`, basePath `/SC`. Первый билд Pages упал (разовый сбой сборщика), перезапущен через `POST /pages/builds` — прошёл за ~2 мин | `verify_sc.py`: 17 OK / 0 FAIL |
| 09.11.2026 | `08e8a18` | Docs fixpoint | `verify_sc.py`: 17 OK / 0 FAIL |
| 09.11.2026 | см. git log | Сверка идентичности SpaceCam ↔ SC: git-деревья (768 общих файлов: 753 blob-идентичны, остальные 15 равны после нормализации basePath), CSS байт-в-байт, JS-чанки — наборы module-id равны (139=139), basePath зашит в обе сборки; live-рендер 6 роутов (#/, switches, product, about, project-reg, nodes) — DOM идентичен. Скрипты: `scripts/compare_spacecam_sc.py`, `scripts/compare_chunks_deep.py` | идентичность подтверждена |

### Как запустить сверку

```bash
GH_TOKEN='<PAT>' python3 scripts/compare_spacecam_sc.py     # деревья+нормализация+live-пробы
GH_TOKEN='<PAT>' python3 scripts/compare_chunks_deep.py     # module-id + basePath в JS-чанках
```

Скрипты сверяются с live-версиями обоих сайтов и репозиториями через GitHub API.

Примечание: локальный клон этого репозитория в песочнице может откатываться
при перезапуске (как и workspace SpaceCam). Источник истины — этот репозиторий
на GitHub; восстановление: `git clone https://github.com/andreyshalnov/SC.git`.
