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

## Контент

Каждый пост — отдельный markdown-файл в `src/content/posts/<id>.md` с YAML
frontmatter по схеме `src/content/config.ts`. Картинки лежат в `public/images/`
и подключаются по абсолютному пути от корня сайта.

Новые посты добавляются через Pages CMS (форма коммитит markdown в репо).
