# Апокриф · The Elder Scrolls: Betrayal of the Second Era

Сайт-апокриф русскоязычного коммьюнити настолки **BotSE** — обзоры, видеообзоры,
летсплеи, гайды по классам, обучалки, лор, принтабли, цены. Контент собран из
топика «Апокриф» канала [@TheElderScrollsRu](https://t.me/TheElderScrollsRu).

Живёт на GitHub Pages, генерируется Astro, контент — markdown в `src/content/posts/`.

## Локальный запуск

```bash
npm install
npm run dev       # http://localhost:4321/botse-apocrypha
npm run build
npm run preview
```

## Деплой

`main` → GitHub Actions (`.github/workflows/deploy.yml`) → GitHub Pages.

Перед первым деплоем:

1. Settings → Visibility → Public (для бесплатного Pages).
2. Settings → Pages → Source: **GitHub Actions**.
3. Запушить в `main` — деплой пойдёт автоматически.

URL: <https://ramen-necklace.github.io/botse-apocrypha/>

## Админка

GUI-редактор — [Pages CMS](https://pagescms.org). Хостится у них, своей инфры
поднимать не надо.

Первичная настройка (один раз):

1. Зайти на [app.pagescms.org](https://app.pagescms.org/) и залогиниться через GitHub.
2. Установить GitHub App «Pages CMS» на этот репо
   (Settings → Integrations → GitHub Apps → Configure).
3. В UI Pages CMS появится коллекция «Посты» по схеме из `.pages.yml`.

Дальше: создаёшь/правишь пост в форме → Pages CMS коммитит markdown в `main` →
GitHub Actions пересобирает сайт (~30 сек).

## Структура

```
.pages.yml                   # схема контента для Pages CMS
astro.config.mjs             # site + base
public/images/<slug>/        # картинки к посту
src/
  content/posts/<YYYY-MM-DD-HHMMSS>.md
  content/config.ts          # Zod-схема frontmatter и список категорий
  components/                # Header, CategoryChips, PostCard, Ornament
  pages/                     # index, category/[slug], posts/[slug]
.github/
  workflows/deploy.yml       # build → deploy → notify-telegram
  scripts/notify_telegram.py # отправка анонсов в Telegram
```

## Контент

Каждый пост — отдельный markdown-файл в `src/content/posts/<timestamp>.md` с
YAML frontmatter по схеме `src/content/config.ts`. Имя файла генерится Pages
CMS из времени создания (`YYYY-MM-DD-HHMMSS`) — slug в URL = это же имя.
Картинки лежат в `public/images/<slug>/` и подключаются по абсолютному пути.

Категория выбирается из закрытого списка (11 значений). Опциональные поля:
`tags`, `sources` (внешние ссылки списком), `cover` (обложка карточки),
`images`, и `telegram_url` — последний **только** если к посту прикреплён
большой файл (PDF/видео/ttsmod/zip > 100 МБ), который физически хранится
в Telegram. Не использовать `telegram_url` как «ссылку на источник».

Новые посты добавляются через Pages CMS (форма коммитит markdown в репо).

## Анонсы в Telegram

После успешного деплоя (`.github/workflows/deploy.yml`) job `notify-telegram`
смотрит, какие `.md` появились в `src/content/posts/` относительно предыдущего
коммита, и шлёт по одному анонсу в топик «Апокриф» канала
[@TheElderScrollsRu](https://t.me/TheElderScrollsRu) через Bot API.

Что нужно один раз настроить:

1. **Создать бота:** в Telegram написать `@BotFather` → `/newbot` → имя → username
   → получить `bot_token` (формат `1234567890:ABCdef...`).
2. **Добавить бота админом** в канал/группу @TheElderScrollsRu с правом
   «Post messages». Бот должен видеть топик «Апокриф».
3. **Узнать chat_id и thread_id:**
   - `chat_id` для публичного канала = `@TheElderScrollsRu` (можно так и оставить),
     либо числовой `-100xxxxxxxxxx` (надёжнее, не зависит от смены username).
     Числовой можно подсмотреть через `getUpdates` или `@RawDataBot`.
   - `thread_id` — `5` (из URL `t.me/TheElderScrollsRu/5/...`).
4. **Положить в GitHub Secrets** (`Settings → Secrets and variables → Actions
   → New repository secret`):
   - `TELEGRAM_BOT_TOKEN` — токен из шага 1
   - `TELEGRAM_CHAT_ID` — `@TheElderScrollsRu` или числовой ID
   - `TELEGRAM_THREAD_ID` — `5`
   - `SITE_URL` (опционально) — переопределяет дефолт
     `https://ramen-necklace.github.io/botse-apocrypha`

Если секретов нет — job просто пропускает отправку, деплой работает как обычно.
Если в одном коммите больше 5 новых файлов — job тоже скипается (защита от
взрывного импорта). Правки уже существующих постов уведомления не триггерят.

Принудительно отключить уведомление для конкретного коммита — добавить
`[skip-notify]` в commit message.
