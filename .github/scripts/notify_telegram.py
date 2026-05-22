"""Постит анонс новой статьи в топик «Апокриф» канала @TheElderScrollsRu,
а при правке уже опубликованной статьи редактирует ранее отправленное сообщение.

Запускается из GitHub Actions после успешного деплоя. Workflow передаёт два
аргумента-списка (через переводы строк): added (новые .md) и modified
(изменённые .md). Скрипт держит mapping slug → {message_id, kind} в файле
.telegram-sent.json в корне репо; этот файл коммитится самим workflow обратно.

Env vars (через GitHub Secrets):
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_THREAD_ID, SITE_URL

Если хоть одного из них нет — скрипт молча выходит с кодом 0.
"""
from __future__ import annotations

import argparse
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
INDEX_PATH = Path(".telegram-sent.json")
MAX_NOTIFICATIONS_PER_RUN = 5  # safeguard от взрывного коммита
MAX_EDITS_PER_RUN = 10         # правок может быть больше — менее опасно
CAPTION_LIMIT = 1024
TEXT_LIMIT = 4096
EXCERPT_TARGET = 600


def env(name: str) -> str | None:
    v = os.environ.get(name, "").strip()
    return v or None


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
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
    body = re.sub(r"<https?://[^>]+>", "", body)
    body = re.sub(r"\s+", " ", body).strip()
    if len(body) <= limit:
        return body
    cut = body[:limit]
    for stop in ("\n\n", ". ", "! ", "? "):
        idx = cut.rfind(stop)
        if idx > limit * 0.6:
            return cut[: idx + 1].rstrip() + " …"
    return cut.rsplit(" ", 1)[0] + " …"


def build_message(meta: dict[str, Any], body: str, site_url: str) -> tuple[str, str | None, str]:
    """Возвращает (html_text, cover_url_or_None, post_url). Title-fallback на первое
    предложение тела, как и в PostCard.astro."""
    raw_title = (meta.get("title") or "").strip()
    cat = meta.get("category", "Прочее")
    clean_body = re.sub(r"<https?://[^>]+>", "", body)
    clean_body = re.sub(r"\s+", " ", clean_body).strip()
    fallback_title = (clean_body[:80] + ("…" if len(clean_body) > 80 else "")) or cat
    display_title = raw_title or fallback_title

    excerpt_budget = (CAPTION_LIMIT if meta.get("cover") else TEXT_LIMIT) - 200
    excerpt_source = body if raw_title else body[len(fallback_title):]
    excerpt = html.escape(make_excerpt(excerpt_source, min(EXCERPT_TARGET, excerpt_budget)))

    post_url = f"{site_url.rstrip('/')}/posts/{Path(meta['_path']).stem}/"

    parts = [
        f"<b>{html.escape(display_title)}</b>",
        f"<i>#{html.escape(cat).replace(' ', '_').replace('/', '_')}</i>",
        "",
        excerpt,
    ]
    text = "\n".join(parts)

    cover_url = None
    if meta.get("cover"):
        cover_path = str(meta["cover"]).lstrip("/")
        cover_url = f"{site_url.rstrip('/')}/{cover_path}"
    return text, cover_url, post_url


def reply_markup_for(post_url: str) -> str:
    return json.dumps({
        "inline_keyboard": [[{"text": "📖 Читать в Апокрифе", "url": post_url}]]
    }, ensure_ascii=False)


def tg_call(token: str, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send_new(token: str, chat_id: str, thread_id: str, text: str,
             cover_url: str | None, post_url: str) -> dict[str, Any]:
    markup = reply_markup_for(post_url)
    if cover_url:
        return tg_call(token, "sendPhoto", {
            "chat_id": chat_id,
            "message_thread_id": thread_id,
            "photo": cover_url,
            "caption": text,
            "parse_mode": "HTML",
            "reply_markup": markup,
        })
    return tg_call(token, "sendMessage", {
        "chat_id": chat_id,
        "message_thread_id": thread_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
        "reply_markup": markup,
    })


def edit_existing(token: str, chat_id: str, message_id: int, kind: str,
                  text: str, cover_url: str | None, post_url: str) -> dict[str, Any]:
    """Редактирует уже отправленное сообщение.

    kind = 'photo' — было sendPhoto, редактируем caption (и саму картинку через
                     editMessageMedia, если в frontmatter сейчас есть cover).
    kind = 'text'  — было sendMessage, редактируем text.
    Сменить тип (photo → text или наоборот) Telegram не позволяет: если cover
    добавили/убрали уже после публикации, оставляем тип каким был. Caption и
    подпись всё равно обновятся.
    """
    markup = reply_markup_for(post_url)
    base = {"chat_id": chat_id, "message_id": message_id, "reply_markup": markup}

    if kind == "photo":
        if cover_url:
            media = json.dumps({
                "type": "photo",
                "media": cover_url,
                "caption": text,
                "parse_mode": "HTML",
            }, ensure_ascii=False)
            return tg_call(token, "editMessageMedia", {**base, "media": media})
        return tg_call(token, "editMessageCaption", {
            **base, "caption": text, "parse_mode": "HTML",
        })
    return tg_call(token, "editMessageText", {
        **base, "text": text, "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    })


def load_index() -> dict[str, dict]:
    if INDEX_PATH.exists():
        try:
            return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_index(idx: dict[str, dict]) -> None:
    INDEX_PATH.write_text(
        json.dumps(idx, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser()
    ap.add_argument("--added", default="")
    ap.add_argument("--modified", default="")
    args = ap.parse_args()

    commit_msg = os.environ.get("COMMIT_MESSAGE", "")
    if "[skip-notify]" in commit_msg or "[skip notify]" in commit_msg:
        print("[notify] [skip-notify] в commit message — пропускаю")
        return 0

    token = env("TELEGRAM_BOT_TOKEN")
    chat = env("TELEGRAM_CHAT_ID")
    thread = env("TELEGRAM_THREAD_ID")
    site = env("SITE_URL")
    if not (token and chat and thread and site):
        print("[notify] секреты не настроены — пропускаю")
        return 0

    added = [Path(p) for p in args.added.split() if p.strip()]
    modified = [Path(p) for p in args.modified.split() if p.strip()]
    if not added and not modified:
        print("[notify] нечего отправлять / редактировать")
        return 0

    if len(added) > MAX_NOTIFICATIONS_PER_RUN:
        print(f"[notify] {len(added)} новых > лимита {MAX_NOTIFICATIONS_PER_RUN} — пропускаю added")
        added = []
    if len(modified) > MAX_EDITS_PER_RUN:
        print(f"[notify] {len(modified)} правок > лимита {MAX_EDITS_PER_RUN} — пропускаю edited")
        modified = []

    index = load_index()
    dirty = False

    def process(path: Path, is_new: bool) -> None:
        nonlocal dirty
        if not path.exists():
            print(f"[notify] {path.name}: файл не существует — пропускаю")
            return
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        meta["_path"] = str(path)
        text, cover, post_url = build_message(meta, body, site)
        slug = path.stem

        try:
            if is_new:
                result = send_new(token, chat, thread, text, cover, post_url)
                if result.get("ok"):
                    msg = result["result"]
                    index[slug] = {
                        "message_id": msg["message_id"],
                        "kind": "photo" if cover else "text",
                    }
                    dirty = True
                    print(f"[notify] + {path.name}: msg_id={msg['message_id']}")
                else:
                    print(f"[notify] + {path.name}: FAILED {result}")
            else:
                entry = index.get(slug)
                if not entry:
                    print(f"[notify] ~ {path.name}: не было отправлено раньше — пропускаю")
                    return
                result = edit_existing(
                    token, chat, entry["message_id"], entry["kind"],
                    text, cover, post_url,
                )
                if result.get("ok"):
                    print(f"[notify] ~ {path.name}: edited msg_id={entry['message_id']}")
                else:
                    # частый кейс: Telegram говорит «message is not modified» — это OK
                    desc = result.get("description", "")
                    if "not modified" in desc:
                        print(f"[notify] ~ {path.name}: без изменений ({desc})")
                    else:
                        print(f"[notify] ~ {path.name}: FAILED {result}")
        except Exception as e:  # noqa: BLE001
            print(f"[notify] {path.name}: EXCEPTION — {e}")
        time.sleep(4)

    for p in added:
        process(p, is_new=True)
    for p in modified:
        process(p, is_new=False)

    if dirty:
        save_index(index)
        print(f"[notify] обновлён {INDEX_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
