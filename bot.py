#!/usr/bin/env python3
"""
🐐 GoatBets — Bot uruchamiający Mini App
"""

import json
import logging
from datetime import datetime, timedelta
from telegram import Update, WebAppInfo, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

# ============================================================
# KONFIGURACJA — ZMIEŃ TE WARTOŚCI
# ============================================================
BOT_TOKEN    = "8262701551:AAGAqmd_v-6PWShkTimMHBo6_rb96n4fbJI"
ADMIN_ID     = 8122842950
MINI_APP_URL = "https://mncszymus.github.io/goatbets"  # URL GitHub Pages
TIPS_FILE    = "tips.json"   # lokalny plik tips.json (ten sam folder co bot.py)
CONTACT_URL  = "https://t.me/GoatBetsCEO"
# ============================================================

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)


def load_tips():
    with open(TIPS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_tips(data):
    with open(TIPS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def admin_only(func):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_ID:
            return
        await func(update, ctx)
    return wrapper

def open_app_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🐐 Otwórz GoatBets", web_app=WebAppInfo(url=MINI_APP_URL))]],
        resize_keyboard=True
    )


# ── START ──────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🐐 *Witaj w GoatBets, {user.first_name}!*\n\n"
        "Naciśnij przycisk poniżej, żeby otworzyć aplikację ⬇️",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=open_app_keyboard()
    )


# ── DODAJ TYP ─────────────────────────────────────────────
@admin_only
async def cmd_addtip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /addtip [free|vip] mecz | typ | kurs | stawka | sport
    Przykład:
    /addtip free Arsenal vs Chelsea | 1X | 1.85 | 2u | Piłka nożna
    /addtip vip PSG vs Lyon | Over 2.5 | 1.70 | 3u | Piłka nożna
    """
    raw = " ".join(ctx.args)
    if not raw:
        await update.message.reply_text(
            "❌ *Użycie:*\n`/addtip [free|vip] mecz | typ | kurs | stawka | sport`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    parts  = raw.split(" ", 1)
    is_vip = parts[0].lower() == "vip"
    fields = [f.strip() for f in parts[1].split("|")]

    match = fields[0] if len(fields) > 0 else "?"
    tip   = fields[1] if len(fields) > 1 else "?"
    odds  = fields[2] if len(fields) > 2 else None
    stake = fields[3] if len(fields) > 3 else "1u"
    sport = fields[4] if len(fields) > 4 else "Piłka nożna"
    today = datetime.now().strftime("%Y-%m-%d")

    data = load_tips()
    new_id = max((t["id"] for t in data["tips"]), default=0) + 1
    data["tips"].append({
        "id":     new_id,
        "match":  match,
        "tip":    tip,
        "odds":   odds,
        "stake":  stake,
        "sport":  sport,
        "is_vip": is_vip,
        "result": "pending",
        "date":   today
    })
    save_tips(data)

    tier = "VIP 👑" if is_vip else "FREE 🐐"
    await update.message.reply_text(
        f"✅ *Typ #{new_id} dodany!*\n"
        f"*Tier:* {tier}\n*Mecz:* {match}\n*Typ:* {tip}\n*Kurs:* {odds or '—'}\n\n"
        f"⚠️ Pamiętaj wgrać `tips.json` na GitHub Pages!",
        parse_mode=ParseMode.MARKDOWN
    )

    # Wyślij powiadomienie do wszystkich przez broadcast
    await update.message.reply_text(
        f"📢 Wyślij powiadomienie do użytkowników:\n"
        f"`/broadcast 🔔 Nowy typ {tier}! Otwórz aplikację GoatBets! 🐐`",
        parse_mode=ParseMode.MARKDOWN
    )


# ── AKTUALIZUJ WYNIK ───────────────────────────────────────
@admin_only
async def cmd_result(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /result [id] [win|loss|void]
    """
    if len(ctx.args) < 2:
        await update.message.reply_text("❌ Użycie: `/result [id] [win|loss|void]`",
                                        parse_mode=ParseMode.MARKDOWN)
        return

    tip_id = int(ctx.args[0])
    result = ctx.args[1].lower()
    if result not in ("win", "loss", "void"):
        await update.message.reply_text("❌ Wynik: `win`, `loss` lub `void`",
                                        parse_mode=ParseMode.MARKDOWN)
        return

    data = load_tips()
    found = False
    for tip in data["tips"]:
        if tip["id"] == tip_id:
            tip["result"] = result
            found = True
            name = tip["match"]
            break

    if not found:
        await update.message.reply_text(f"❌ Nie znaleziono typu #{tip_id}")
        return

    save_tips(data)
    emoji = {"win": "✅", "loss": "❌", "void": "↩️"}[result]
    await update.message.reply_text(
        f"{emoji} Typ #{tip_id} (*{name}*) → *{result.upper()}*\n\n"
        f"⚠️ Pamiętaj wgrać `tips.json` na GitHub Pages!",
        parse_mode=ParseMode.MARKDOWN
    )


# ── NADAJ VIP ─────────────────────────────────────────────
@admin_only
async def cmd_givevip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /givevip [user_id]
    """
    if not ctx.args:
        await update.message.reply_text("❌ Użycie: `/givevip [user_id]`",
                                        parse_mode=ParseMode.MARKDOWN)
        return

    uid = int(ctx.args[0])
    data = load_tips()
    if uid not in data["vip_users"]:
        data["vip_users"].append(uid)
        save_tips(data)

    await update.message.reply_text(
        f"✅ *VIP nadany!*\nUser ID: `{uid}`\n\n"
        "⚠️ Pamiętaj wgrać `tips.json` na GitHub Pages!",
        parse_mode=ParseMode.MARKDOWN
    )
    try:
        await ctx.bot.send_message(
            chat_id=uid,
            text="👑 *Twój GoatBets VIP został aktywowany!*\n\nOtwórz aplikację i ciesz się ekskluzywnymi typami! 🐐🎉",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=open_app_keyboard()
        )
    except Exception:
        pass


# ── ODBIERZ VIP ───────────────────────────────────────────
@admin_only
async def cmd_revokevip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("❌ Użycie: `/revokevip [user_id]`",
                                        parse_mode=ParseMode.MARKDOWN)
        return

    uid = int(ctx.args[0])
    data = load_tips()
    data["vip_users"] = [u for u in data["vip_users"] if u != uid]
    save_tips(data)

    await update.message.reply_text(
        f"✅ VIP odebrany użytkownikowi `{uid}`\n\n"
        "⚠️ Pamiętaj wgrać `tips.json` na GitHub Pages!",
        parse_mode=ParseMode.MARKDOWN
    )


# ── LISTA TYPÓW ────────────────────────────────────────────
@admin_only
async def cmd_listtips(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data  = load_tips()
    today = datetime.now().strftime("%Y-%m-%d")
    tips  = [t for t in data["tips"] if t["date"] == today]

    if not tips:
        await update.message.reply_text("📭 Brak typów na dziś")
        return

    text = "📋 *Typy na dziś:*\n\n"
    for t in tips:
        tier  = "VIP" if t["is_vip"] else "FREE"
        emoji = {"pending": "🔵", "win": "✅", "loss": "❌", "void": "↩️"}.get(t["result"], "❓")
        text += f"{emoji} ID:{t['id']} [{tier}] *{t['match']}* → `{t['tip']}`\n"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ── BROADCAST ──────────────────────────────────────────────
@admin_only
async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /broadcast wiadomość
    Wysyła wiadomość do wszystkich użytkowników którzy wcześniej użyli /start
    """
    msg = " ".join(ctx.args)
    if not msg:
        await update.message.reply_text("❌ Użycie: `/broadcast wiadomość`",
                                        parse_mode=ParseMode.MARKDOWN)
        return

    # Prosta implementacja — tutaj możesz dodać bazę użytkowników
    await update.message.reply_text(
        f"📢 Broadcast: _{msg}_\n\n"
        "ℹ️ Aby wysyłać do wszystkich użytkowników, dodaj bazę SQLite.\n"
        "Na razie możesz używać tego jako szablonu wiadomości.",
        parse_mode=ParseMode.MARKDOWN
    )


# ── POMOC ADMINA ───────────────────────────────────────────
@admin_only
async def cmd_adminhelp(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠 *Komendy Admina — GoatBets Mini App*\n\n"
        "*📌 Typy:*\n"
        "`/addtip [free|vip] mecz | typ | kurs | stawka | sport`\n"
        "`/listtips` — lista typów na dziś\n"
        "`/result [id] [win|loss|void]` — aktualizuj wynik\n\n"
        "*👑 VIP:*\n"
        "`/givevip [user_id]` — nadaj VIP\n"
        "`/revokevip [user_id]` — odbierz VIP\n\n"
        "*📢 Powiadomienia:*\n"
        "`/broadcast wiadomość`\n\n"
        "*⚠️ Po każdej zmianie typów/VIP — wgraj `tips.json` na GitHub Pages!*",
        parse_mode=ParseMode.MARKDOWN
    )


# ── MAIN ───────────────────────────────────────────────────
def main():
    if BOT_TOKEN == "WSTAW_TOKEN_Z_BOTFATHER":
        print("❌ BŁĄD: Wstaw token z BotFather do zmiennej BOT_TOKEN!")
        return
    if "TWOJNICK" in MINI_APP_URL:  # placeholder check (should not trigger now)
        print("❌ BŁĄD: Wstaw swój URL GitHub Pages do zmiennej MINI_APP_URL!")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",      cmd_start))
    app.add_handler(CommandHandler("addtip",     cmd_addtip))
    app.add_handler(CommandHandler("result",     cmd_result))
    app.add_handler(CommandHandler("givevip",    cmd_givevip))
    app.add_handler(CommandHandler("revokevip",  cmd_revokevip))
    app.add_handler(CommandHandler("listtips",   cmd_listtips))
    app.add_handler(CommandHandler("broadcast",  cmd_broadcast))
    app.add_handler(CommandHandler("adminhelp",  cmd_adminhelp))

    log.info("🐐 GoatBets Mini App Bot uruchomiony!")
    app.run_polling()

if __name__ == "__main__":
    main()
