"""Постит анонс новой статьи в топик «Апокриф» канала @TheElderScrollsRu.

Запускается из GitHub Actions после успешного деплоя. Читает список добавленных
.md-файлов в src/content/posts/ из аргументов (передаются workflow'ом из git diff),
для каждого формирует короткий анонс и шлёт через Bot API.

Env vars (через GitHub Secrets):
    TELEGRAM_BOT_TOKEN   — токен бота от @BotFather
    TELEGRAM_CHAT_ID     — @TheElderScrollsRu или числовой -100xxxxxxxxxx
    TELEGRAM_THREAD_ID   — id топика «Апокриф» (=5)
    SITE_URL             — https://ramen-necklace.github.io/botse-apocrypha

Если хоть одного из них нет — скрипт молча выходит с кодом 0 (для случая, когда
секреты ещё не настроены: деплой работает, уведомления просто не уходят).
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

POSTS_DIR = Path("src/content/posts")
MAX_NOTIFICATIONS_PER_RUN = 5  # safeguard от взрывного коммита
CAPTION_LIMIT = 1024  # Telegram sendPhoto
TEXT_LIMIT = 4096  # Telegram sendMessage
EXCERPT_TARGET = 600  # сколько символов тела показывать в анонсе


def env(name: str) -> str | None:
    v = os.environ.get(name, "").strip()
    return v or None


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Очень узкий YAML-парсер под нашу схему (string, list-of-strings, list-of-objects).

    Это намеренно не общий YAML, чтобы не тащить pyyaml. Структура frontmatter
    у нас фиксированная (см. src/content/config.ts), достаточно покрыть её.
    """
    lines = text.split("\n")
    if lines[0] != "---":
        raise ValueError("no frontmatter")
    end = lines.index("---", 1)
    fm_lines = lines[1:end]
    body = "\n".join(lines[end + 1:]).lstrip("\n")

    data: dict[str, Any] = {}
    i = 0
    while i < len(fm_lines):
        line = fm_lines[i]
        if not line.strip() or line.startswith(" "):
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()

        if rest == "" or rest == "[]":
            if rest == "[]":
                data[key] = []
                i += 1
                continue
            items: list[Any] = []
            i += 1
            while i < len(fm_lines) and (fm_lines[i].startswith("  ") or fm_lines[i].startswith("\t")):
                sub = fm_lines[i]
                if sub.lstrip().startswith("- "):
                    item_text = sub.lstrip()[2:]
                    if ":" in item_text:
                        obj: dict[str, Any] = {}
                        k, _, v = item_text.partition(":")
                        obj[k.strip()] = _unquote(v.strip())
                        i += 1
                        while i < len(fm_lines) and fm_lines[i].startswith("    "):
                            k2, _, v2 = fm_lines[i].strip().partition(":")
                            obj[k2.strip()] = _unquote(v2.strip())
                            i += 1
                        items.append(obj)
                        continue
                    items.append(_unquote(item_text))
                i += 1
            data[key] = items
        else:
            data[key] = _unquote(rest)
            i += 1

    return data, body


def _unquote(s: str) -> str:
    if not s:
        return s
    if (s[0], s[-1]) in (('"', '"'), ("'", "'")):
        try:
            return json.loads(s) if s[0] == '"' else s[1:-1]
        except json.JSONDecodeError:
            return s[1:-1]
    if s == "true":
        return True  # type: ignore[return-value]
    if s == "false":
        return False  # type: ignore[return-value]
    return s


def make_excerpt(body: str, limit: int) -> str:
    """Берёт первые `limit` символов тела, обрезает по предложению/слову."""
    body = re.sub(r"<https?://[^>]+>", "", body)  # вырезать autolink-URL'ы
    body = re.sub(r"\s+", " ", body).strip()
    if len(body) <= limit:
        return body
    cut = body[:limit]
    for stop in ("\n\n", ". ", "! ", "? "):
        idx = cut.rfind(stop)
        if idx > limit * 0.6:
            return cut[: idx + 1].rstrip() + " …"
    return cut.rsplit(" ", 1)[0] + " …"


def slug_from_filename(path: Path) -> str:
    return path.stem


def build_message(meta: dict[str, Any], body: str, site_url: str) -> tuple[str, str | None]:
    """Возвращает (html_text, cover_url_or_None)."""
    title = html.escape(meta.get("title", "Без заголовка"))
    category = html.escape(meta.get("category", "Прочее"))
    excerpt_budget = (CAPTION_LIMIT if meta.get("cover") else TEXT_LIMIT) - 350  # запас на title/линк/тег
    excerpt = html.escape(make_excerpt(body, min(EXCERPT_TARGET, excerpt_budget)))

    post_url = f"{site_url.rstrip('/')}/posts/{slug_from_filename(Path(meta['_path']))}/"

    parts = [
        f"<b>{title}</b>",
        f"<i>#{category.replace(' ', '_').replace('/', '_')}</i>",
        "",
        excerpt,
        "",
        f'<a href="{html.escape(post_url, quote=True)}">Читать в Апокрифе →</a>',
    ]
    text = "\n".join(parts)

    cover = meta.get("cover")
    cover_url = None
    if cover:
        cover_path = cover.lstrip("/")
        cover_url = f"{site_url.rstrip('/')}/{cover_path}"

    return text, cover_url


def telegram_call(token: str, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send(token: str, chat_id: str, thread_id: str, text: str, cover_url: str | None) -> dict[str, Any]:
    if cover_url:
        return telegram_call(token, "sendPhoto", {
            "chat_id": chat_id,
            "message_thread_id": thread_id,
            "photo": cover_url,
            "caption": text,
            "parse_mode": "HTML",
        })
    return telegram_call(token, "sendMessage", {
        "chat_id": chat_id,
        "message_thread_id": thread_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "false",
    })


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows CI safety

    token = env("TELEGRAM_BOT_TOKEN")
    chat = env("TELEGRAM_CHAT_ID")
    thread = env("TELEGRAM_THREAD_ID")
    site = env("SITE_URL")
    if not (token and chat and thread and site):
        print("[notify] секреты не настроены (TELEGRAM_*/SITE_URL) — пропускаю отправку")
        return 0

    files = [Path(p) for p in argv[1:] if p.strip()]
    if not files:
        print("[notify] новых постов нет")
        return 0
    if len(files) > MAX_NOTIFICATIONS_PER_RUN:
        print(f"[notify] {len(files)} новых файлов > лимита {MAX_NOTIFICATIONS_PER_RUN} — пропускаю "
              f"(это похоже на массовый импорт, не на обычную публикацию)")
        return 0

    for path in files:
        if not path.exists():
            print(f"[notify] {path} не найден, пропускаю")
            continue
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        meta["_path"] = str(path)
        text, cover = build_message(meta, body, site)
        try:
            result = send(token, chat, thread, text, cover)
            ok = result.get("ok")
            print(f"[notify] {path.name}: {'OK' if ok else result}")
        except Exception as e:  # noqa: BLE001 — Actions всё равно покажет stderr
            print(f"[notify] {path.name}: FAILED — {e}")
            return 1
        time.sleep(4)  # safety против rate-limit Telegram (20/min на канал)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
