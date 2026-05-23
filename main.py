"""
SpendUZ Pro — main.py v2.0
@Spend_uz_bot
"""
import asyncio
import logging
import os
import re
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    WebAppInfo, LabeledPrice, PreCheckoutQuery,
    BufferedInputFile,
)
from database import (
    init_db, add_user, get_user, get_lang, set_lang, all_users,
    add_txn, get_txns, get_txn, update_txn, delete_txn,
    get_summary, get_cat_breakdown, has_txn_today, had_txn_yesterday,
    add_goal, get_goals, get_goal, update_goal, add_to_goal, delete_goal,
    is_premium, set_premium, get_premium_until,
    get_referral_code, get_referral_count, use_referral,
    add_card, get_cards, delete_card,
)

try:
    import aiohttp
    HTTP_OK = True
except ImportError:
    HTTP_OK = False

try:
    from pydub import AudioSegment
    import speech_recognition as sr
    VOICE_OK = True
except ImportError:
    VOICE_OK = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── CONFIG ─────────────────────────────────────────────────────────────────────
BOT_TOKEN    = os.getenv("BOT_TOKEN",    "8651989569:AAEGRKv4os3HFolPrw6kRvinjMGT7e6BGuI")
WEB_APP_URL  = os.getenv("WEB_APP_URL",  "https://salmondadomatov07-ux.github.io/spend-app/")
PREMIUM_STARS = 85
PREMIUM_DAYS  = 30
ADMIN_IDS     = [8651989569, 5522700870]

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher()

# States
states: dict[int, dict] = {}

def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

# ── TRANSLATIONS ───────────────────────────────────────────────────────────────
T = {
"uz": {
    "start_msg": (
        "💸 <b>SpendUZ Pro ga xush kelibsiz!</b>\n\n"
        "Tilni tanlang:"
    ),
    "lang_saved": "✅ Til saqlandi! Endi ilovani oching 👇",
    "open_app": "🚀 SpendUZ Pro ni ochish",
    "help": (
        "📝 <b>Qanday yozish:</b>\n\n"
        "💸 Xarajat: <code>20000 ovqat</code>\n"
        "💰 Daromad: <code>3mln oylik</code>\n"
        "💸 Qarz berdim: <code>qarz 50000 Ali</code>\n"
        "💰 Qarz oldim: <code>oldim 100000 Doniyor</code>\n\n"
        "🎤 Yoki ovoz yuboring! (Premium)\n"
        "📊 Hisobot: /report\n"
        "🎯 Maqsadlar: /goals"
    ),
    "saved_exp":  "✅ <b>Xarajat saqlandi!</b>\n💸 {amount} {cur} — {note}",
    "saved_inc":  "✅ <b>Daromad saqlandi!</b>\n💰 {amount} {cur} — {note}",
    "saved_dg":   "✅ <b>Qarz berdim!</b>\n💸 {amount} {cur}\n👤 Kimga: {note}",
    "saved_dt":   "✅ <b>Qarz oldim!</b>\n💰 {amount} {cur}\n👤 Kimdan: {note}",
    "edit_btn":   "✏️ Tahrirlash",
    "del_btn":    "🗑 O'chirish",
    "deleted":    "🗑 O'chirildi!",
    "edit_ask":   "✏️ Yangi summani yozing:",
    "edit_done":  "✅ Yangilandi! {amount} so'm",
    "report": (
        "📊 <b>{month} hisoboti:</b>\n\n"
        "⬆️ Daromad:     <b>{income}</b>\n"
        "⬇️ Xarajat:     <b>{expense}</b>\n"
        "💸 Qarz berdim: <b>{dg}</b>\n"
        "💰 Qarz oldim:  <b>{dt}</b>\n"
        "━━━━━━━━━━━\n"
        "📈 Balans: <b>{balance}</b>"
    ),
    "no_txn":     "📭 Hali tranzaksiya yo'q.",
    "reminder":   "⏰ <b>Eslatma!</b>\n\nBugun hali xarajat yozmadingiz. Hozir yozing 💸",
    "daily_rate": "💱 <b>Bugungi kurs (CBU):</b>\n\n{rates}",
    "rate_fail":  "😕 Kursni yuklab bo'lmadi.",
    "voice_wait": "🎤 Tahlil qilinmoqda...",
    "voice_done": "🎤 Eshitildi: <i>«{text}»</i>",
    "voice_fail": "😕 Ovozni tushunmadim.",
    "unknown":    "🤔 Tushunmadim.\n\n<b>Misol:</b> <code>20000 ovqat</code>",

    # GOALS
    "goals_empty": (
        "🎯 <b>Hali maqsad yo'q!</b>\n\n"
        "Maqsad qo'shish uchun:\n"
        "<code>/addgoal MacBook 10000000</code>\n\n"
        "Bu yerda:\n"
        "• <b>MacBook</b> — olmoqchi bo'lgan narsa nomi\n"
        "• <b>10000000</b> — kerakli summa"
    ),
    "goal_list_header": "🎯 <b>Sizning maqsadlaringiz:</b>\n\n",
    "goal_item": (
        "{emoji} <b>{name}</b>\n"
        "💰 {current} / {target}\n"
        "{bar} {pct}%\n"
        "{deadline}\n"
    ),
    "goal_add_prompt": (
        "🎯 <b>Yangi maqsad qo'shish</b>\n\n"
        "Quyidagi formatda yozing:\n"
        "<code>/addgoal [nomi] [summa]</code>\n\n"
        "<b>Misol:</b>\n"
        "<code>/addgoal iPhone 17 15000000</code>\n"
        "<code>/addgoal Avtomobil 50000000</code>\n"
        "<code>/addgoal Uy 300000000</code>\n\n"
        "📅 Muddat qo'shish uchun:\n"
        "<code>/addgoal iPhone 17 15000000 2026-12-31</code>"
    ),
    "goal_added": "✅ <b>Maqsad qo'shildi!</b>\n\n🎯 {name}\n💰 {target} so'm\n\n/goals — barcha maqsadlar",
    "goal_add_btn":    "➕ Jamg'arma qo'shish",
    "goal_edit_btn":   "✏️ Tahrirlash",
    "goal_delete_btn": "🗑 O'chirish",
    "goal_add_amount": "💰 Qancha qo'shmoqchisiz? Summani yozing:\nMasalan: <code>500000</code>",
    "goal_added_amount": "✅ {amount} so'm qo'shildi!\n\n🎯 {name}: {current} / {target} ({pct}%)",
    "goal_done":  "🎉 <b>Maqsadga yetdingiz!</b>\n\n🏆 {name} — Tabriklaymiz!",
    "goal_edit_prompt": "✏️ Tahrirlash uchun yangi nom va summani yozing:\n<code>nom|summa</code>\nMasalan: <code>iPhone 17|18000000</code>",
    "goal_deleted": "🗑 Maqsad o'chirildi.",
    "goal_limit":  (
        "🎯 <b>Maqsad limiti: 3 ta!</b>\n\n"
        "Bepul foydalanuvchilar uchun maksimal 3 ta maqsad.\n\n"
        "💎 Cheksiz maqsadlar uchun Premium oling!\n"
        "🎁 Yoki do'stingizni taklif qiling → 3 kun bepul!"
    ),

    # CARDS
    "cards_empty": "💳 Hali karta qo'shilmagan.",
    "card_add_step1": "💳 <b>Karta qo'shish</b>\n\nAvval karta nomini yozing:\nMasalan: <code>Humo asosiy</code>",
    "card_add_step2": "✅ Nom saqlandi!\n\nEndi karta raqamining <b>oxirgi 4 raqamini</b> yozing:\nMasalan: <code>1234</code>",
    "card_added":  "✅ <b>Karta qo'shildi!</b>\n\n💳 {name}\n**** **** **** {last4}",
    "card_deleted": "💳 Karta o'chirildi.",
    "card_limit": (
        "💳 <b>Karta limiti: 3 ta!</b>\n\n"
        "Bepul foydalanuvchilar uchun maksimal 3 ta karta.\n\n"
        "💎 Cheksiz kartalar uchun Premium oling!"
    ),
    "card_del_btn": "🗑 O'chirish",
    "card_add_btn": "➕ Karta qo'shish",
    "enter_4digits": "❌ Faqat 4 ta raqam kiriting!",

    # PREMIUM
    "premium_txt": (
        "╔══════════════════════╗\n"
        "║   💎 SpendUZ Premium   ║\n"
        "╚══════════════════════╝\n\n"
        "🚀 <b>Barcha imkoniyatlar sizniki!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎯 Cheksiz maqsadlar\n"
        "📊 PDF hisobot\n"
        "💱 Barcha valyutalar\n"
        "💳 Cheksiz kartalar\n"
        "🎤 Ovoz bilan yozish\n"
        "📈 Kategoriya tahlili\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💰 Narxi: <b>85 ⭐ Stars / oy</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎁 <b>Bepul olish:</b>\n"
        "Do'stingizni taklif qiling → 3 kun bepul!\n"
        "/ref — Referal havolangiz"
    ),
    "premium_btn": "⭐ 85 Stars bilan obuna",
    "premium_ok":  "🎉 <b>Premium faollashtirildi!</b>\n\n✅ 30 kun davomida barcha funksiyalar mavjud.\n\nRahmat! 💎",
    "premium_already": "💎 <b>Siz allaqachon Premium!</b>\n\nPremium muddati: {until}",
    "need_premium": (
        "🔒 <b>Bu funksiya Premium uchun!</b>\n\n"
        "💎 Premium olish: /premium\n"
        "🎁 Bepul olish: /ref — do'st taklif qiling!"
    ),

    # REFERRAL
    "ref_info": (
        "🎁 <b>Do'stingizni taklif qiling!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👥 Har bir do'st uchun:\n"
        "→ <b>Siz 3 kun bepul Premium!</b>\n"
        "→ <b>Do'stingiz 1 kun bepul Premium!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔥 5 do'st = 15 kun Premium!\n"
        "🔥 10 do'st = 1 oy Premium!\n\n"
        "👥 Taklif qilinganlar: <b>{count}</b> ta\n\n"
        "👇 Havolangiz:\n"
        "<code>https://t.me/Spend_uz_bot?start={code}</code>"
    ),
    "ref_share_btn": "🔗 Do'stlarga yuborish",
    "ref_open_btn":  "🚀 Havolani ochish",
    "ref_thanks":   "🎁 Taklif orqali kelganingiz uchun <b>1 kun bepul Premium</b> oldingiz!",
    "ref_bonus":    "🎉 Do'stingiz qo'shildi! Siz <b>3 kun bepul Premium</b> oldingiz!",
    "ref_already":  "❌ Bu referal havola allaqachon ishlatilgan!",

    # MENU BUTTONS
    "btn_report":   "📊 Hisobot",
    "btn_pdf":      "📥 Hisobot PDF",
    "btn_goals":    "🎯 Maqsadlar",
    "btn_cards":    "💳 Kartalar",
    "btn_premium":  "💎 Premium",
    "btn_ref":      "🎁 Taklif",
    "btn_rate":     "💱 Valyuta kursi",
    "btn_settings": "⚙️ Sozlamalar",

    # WEEKLY REF AD
    "ref_ad": (
        "🎁 <b>Do'stingizni taklif qiling!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👥 Har bir do'st uchun:\n"
        "→ <b>Siz 3 kun bepul Premium!</b>\n"
        "→ <b>Do'st 1 kun bepul Premium!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔥 5 do'st = 15 kun!\n"
        "🔥 10 do'st = 1 oy!\n\n"
        "👇 Havolangiz:\n"
        "<code>https://t.me/Spend_uz_bot?start={code}</code>"
    ),
},
"ru": {
    "start_msg": "💸 <b>Добро пожаловать в SpendUZ Pro!</b>\n\nВыберите язык:",
    "lang_saved": "✅ Язык сохранён! Откройте приложение 👇",
    "open_app": "🚀 Открыть SpendUZ Pro",
    "help": (
        "📝 <b>Как писать:</b>\n\n"
        "💸 Расход: <code>20000 еда</code>\n"
        "💰 Доход: <code>3млн зарплата</code>\n"
        "💸 Дал в долг: <code>долг 50000 Али</code>\n"
        "💰 Взял в долг: <code>взял 100000 Дониёр</code>\n\n"
        "🎤 Или голосовое! (Premium)\n"
        "📊 Отчёт: /report\n"
        "🎯 Цели: /goals"
    ),
    "saved_exp":  "✅ <b>Расход сохранён!</b>\n💸 {amount} {cur} — {note}",
    "saved_inc":  "✅ <b>Доход сохранён!</b>\n💰 {amount} {cur} — {note}",
    "saved_dg":   "✅ <b>Дал в долг!</b>\n💸 {amount} {cur}\n👤 Кому: {note}",
    "saved_dt":   "✅ <b>Взял в долг!</b>\n💰 {amount} {cur}\n👤 От кого: {note}",
    "edit_btn":   "✏️ Изменить",
    "del_btn":    "🗑 Удалить",
    "deleted":    "🗑 Удалено!",
    "edit_ask":   "✏️ Введите новую сумму:",
    "edit_done":  "✅ Обновлено! {amount}",
    "report": (
        "📊 <b>Отчёт {month}:</b>\n\n"
        "⬆️ Доход:       <b>{income}</b>\n"
        "⬇️ Расход:      <b>{expense}</b>\n"
        "💸 Дал в долг:  <b>{dg}</b>\n"
        "💰 Взял в долг: <b>{dt}</b>\n"
        "━━━━━━━━━━━\n"
        "📈 Баланс: <b>{balance}</b>"
    ),
    "no_txn":     "📭 Транзакций пока нет.",
    "reminder":   "⏰ <b>Напоминание!</b>\n\nСегодня ещё не записали расходы. Запишите сейчас 💸",
    "daily_rate": "💱 <b>Курс валют сегодня (ЦБУ):</b>\n\n{rates}",
    "rate_fail":  "😕 Не удалось загрузить курс.",
    "voice_wait": "🎤 Анализирую...",
    "voice_done": "🎤 Услышал: <i>«{text}»</i>",
    "voice_fail": "😕 Не понял голос.",
    "unknown":    "🤔 Не понял.\n\n<b>Пример:</b> <code>20000 еда</code>",
    "goals_empty": (
        "🎯 <b>Целей пока нет!</b>\n\n"
        "Добавить цель:\n"
        "<code>/addgoal MacBook 10000000</code>\n\n"
        "Где:\n"
        "• <b>MacBook</b> — название\n"
        "• <b>10000000</b> — нужная сумма"
    ),
    "goal_list_header": "🎯 <b>Ваши цели:</b>\n\n",
    "goal_item": "{emoji} <b>{name}</b>\n💰 {current} / {target}\n{bar} {pct}%\n{deadline}\n",
    "goal_add_prompt": (
        "🎯 <b>Добавить цель</b>\n\n"
        "Формат: <code>/addgoal [название] [сумма]</code>\n\n"
        "<b>Примеры:</b>\n"
        "<code>/addgoal iPhone 17 15000000</code>\n"
        "<code>/addgoal Автомобиль 50000000</code>"
    ),
    "goal_added": "✅ <b>Цель добавлена!</b>\n\n🎯 {name}\n💰 {target}\n\n/goals — все цели",
    "goal_add_btn":    "➕ Добавить накопления",
    "goal_edit_btn":   "✏️ Изменить",
    "goal_delete_btn": "🗑 Удалить",
    "goal_add_amount": "💰 Сколько добавить? Введите сумму:\nНапример: <code>500000</code>",
    "goal_added_amount": "✅ {amount} добавлено!\n\n🎯 {name}: {current} / {target} ({pct}%)",
    "goal_done":  "🎉 <b>Цель достигнута!</b>\n\n🏆 {name} — Поздравляем!",
    "goal_edit_prompt": "✏️ Введите новое название и сумму:\n<code>название|сумма</code>",
    "goal_deleted": "🗑 Цель удалена.",
    "goal_limit": "🎯 <b>Лимит целей: 3!</b>\n\nДля безлимитных целей нужен Premium.\n💎 /premium\n🎁 /ref",
    "cards_empty": "💳 Карт пока нет.",
    "card_add_step1": "💳 <b>Добавить карту</b>\n\nВведите название карты:\nНапример: <code>Humo основная</code>",
    "card_add_step2": "✅ Название сохранено!\n\nВведите <b>последние 4 цифры</b> карты:",
    "card_added":  "✅ <b>Карта добавлена!</b>\n\n💳 {name}\n**** **** **** {last4}",
    "card_deleted": "💳 Карта удалена.",
    "card_limit": "💳 <b>Лимит карт: 3!</b>\n\nДля большего количества нужен Premium.",
    "card_del_btn": "🗑 Удалить",
    "card_add_btn": "➕ Добавить карту",
    "enter_4digits": "❌ Введите только 4 цифры!",
    "premium_txt": (
        "╔══════════════════════╗\n"
        "║   💎 SpendUZ Premium   ║\n"
        "╚══════════════════════╝\n\n"
        "🚀 <b>Все возможности для вас!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎯 Безлимитные цели\n"
        "📊 PDF отчёты\n"
        "💱 Все валюты\n"
        "💳 Безлимитные карты\n"
        "🎤 Голосовой ввод\n"
        "📈 Анализ категорий\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💰 Цена: <b>85 ⭐ Stars / мес</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎁 <b>Бесплатно:</b>\n"
        "Пригласите друга → 3 дня бесплатно!\n"
        "/ref — Реферальная ссылка"
    ),
    "premium_btn": "⭐ Подписаться за 85 Stars",
    "premium_ok":  "🎉 <b>Premium активирован!</b>\n\n✅ 30 дней все функции доступны. Спасибо! 💎",
    "premium_already": "💎 <b>Вы уже Premium!</b>\n\nДо: {until}",
    "need_premium": "🔒 <b>Это функция Premium!</b>\n\n💎 /premium\n🎁 /ref — пригласите друга!",
    "ref_info": (
        "🎁 <b>Пригласите друзей!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👥 За каждого друга:\n"
        "→ <b>Вам 3 дня Premium!</b>\n"
        "→ <b>Другу 1 день Premium!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔥 5 друзей = 15 дней!\n"
        "🔥 10 друзей = 1 месяц!\n\n"
        "👥 Приглашено: <b>{count}</b>\n\n"
        "👇 Ваша ссылка:\n"
        "<code>https://t.me/Spend_uz_bot?start={code}</code>"
    ),
    "ref_share_btn": "🔗 Поделиться с друзьями",
    "ref_open_btn":  "🚀 Открыть ссылку",
    "ref_thanks":   "🎁 За приглашение вы получили <b>1 день бесплатного Premium</b>!",
    "ref_bonus":    "🎉 Друг присоединился! Вы получили <b>3 дня Premium</b>!",
    "ref_already":  "❌ Эта реферальная ссылка уже была использована!",
    "btn_report":   "📊 Отчёт",
    "btn_pdf":      "📥 Отчёт PDF",
    "btn_goals":    "🎯 Цели",
    "btn_cards":    "💳 Карты",
    "btn_premium":  "💎 Premium",
    "btn_ref":      "🎁 Реферал",
    "btn_rate":     "💱 Курс валют",
    "btn_settings": "⚙️ Настройки",
    "ref_ad": (
        "🎁 <b>Пригласите друзей!</b>\n\n"
        "→ <b>Вам 3 дня Premium!</b>\n"
        "→ <b>Другу 1 день Premium!</b>\n\n"
        "<code>https://t.me/Spend_uz_bot?start={code}</code>"
    ),
},
"en": {
    "start_msg": "💸 <b>Welcome to SpendUZ Pro!</b>\n\nChoose language:",
    "lang_saved": "✅ Language saved! Open the app 👇",
    "open_app": "🚀 Open SpendUZ Pro",
    "help": (
        "📝 <b>How to write:</b>\n\n"
        "💸 Expense: <code>20000 food</code>\n"
        "💰 Income: <code>3mln salary</code>\n"
        "💸 Lent: <code>lent 50000 Ali</code>\n"
        "💰 Borrowed: <code>borrowed 100000 Doniyor</code>\n\n"
        "🎤 Or voice! (Premium)\n"
        "📊 Report: /report\n"
        "🎯 Goals: /goals"
    ),
    "saved_exp":  "✅ <b>Expense saved!</b>\n💸 {amount} {cur} — {note}",
    "saved_inc":  "✅ <b>Income saved!</b>\n💰 {amount} {cur} — {note}",
    "saved_dg":   "✅ <b>Lent money!</b>\n💸 {amount} {cur}\n👤 To: {note}",
    "saved_dt":   "✅ <b>Borrowed!</b>\n💰 {amount} {cur}\n👤 From: {note}",
    "edit_btn":   "✏️ Edit",
    "del_btn":    "🗑 Delete",
    "deleted":    "🗑 Deleted!",
    "edit_ask":   "✏️ Enter new amount:",
    "edit_done":  "✅ Updated! {amount}",
    "report": (
        "📊 <b>Report {month}:</b>\n\n"
        "⬆️ Income:   <b>{income}</b>\n"
        "⬇️ Expense:  <b>{expense}</b>\n"
        "💸 Lent:     <b>{dg}</b>\n"
        "💰 Borrowed: <b>{dt}</b>\n"
        "━━━━━━━━━━━\n"
        "📈 Balance: <b>{balance}</b>"
    ),
    "no_txn":     "📭 No transactions yet.",
    "reminder":   "⏰ <b>Reminder!</b>\n\nYou haven't logged expenses today. Log now 💸",
    "daily_rate": "💱 <b>Today's rates (CBU):</b>\n\n{rates}",
    "rate_fail":  "😕 Could not load rates.",
    "voice_wait": "🎤 Analyzing...",
    "voice_done": "🎤 Heard: <i>«{text}»</i>",
    "voice_fail": "😕 Could not understand voice.",
    "unknown":    "🤔 Did not understand.\n\n<b>Example:</b> <code>20000 food</code>",
    "goals_empty": (
        "🎯 <b>No goals yet!</b>\n\n"
        "Add a goal:\n"
        "<code>/addgoal MacBook 10000000</code>\n\n"
        "Where:\n"
        "• <b>MacBook</b> — item name\n"
        "• <b>10000000</b> — target amount"
    ),
    "goal_list_header": "🎯 <b>Your goals:</b>\n\n",
    "goal_item": "{emoji} <b>{name}</b>\n💰 {current} / {target}\n{bar} {pct}%\n{deadline}\n",
    "goal_add_prompt": (
        "🎯 <b>Add goal</b>\n\n"
        "Format: <code>/addgoal [name] [amount]</code>\n\n"
        "<b>Examples:</b>\n"
        "<code>/addgoal iPhone 17 15000000</code>\n"
        "<code>/addgoal Car 50000000</code>"
    ),
    "goal_added": "✅ <b>Goal added!</b>\n\n🎯 {name}\n💰 {target}\n\n/goals — all goals",
    "goal_add_btn":    "➕ Add savings",
    "goal_edit_btn":   "✏️ Edit",
    "goal_delete_btn": "🗑 Delete",
    "goal_add_amount": "💰 How much to add?\nExample: <code>500000</code>",
    "goal_added_amount": "✅ {amount} added!\n\n🎯 {name}: {current} / {target} ({pct}%)",
    "goal_done":  "🎉 <b>Goal achieved!</b>\n\n🏆 {name} — Congratulations!",
    "goal_edit_prompt": "✏️ Enter new name and amount:\n<code>name|amount</code>",
    "goal_deleted": "🗑 Goal deleted.",
    "goal_limit": "🎯 <b>Goal limit: 3!</b>\n\nUnlimited goals require Premium.\n💎 /premium\n🎁 /ref",
    "cards_empty": "💳 No cards yet.",
    "card_add_step1": "💳 <b>Add card</b>\n\nEnter card name:\nExample: <code>Humo main</code>",
    "card_add_step2": "✅ Name saved!\n\nEnter <b>last 4 digits</b> of your card:",
    "card_added":  "✅ <b>Card added!</b>\n\n💳 {name}\n**** **** **** {last4}",
    "card_deleted": "💳 Card deleted.",
    "card_limit": "💳 <b>Card limit: 3!</b>\n\nUnlimited cards require Premium.",
    "card_del_btn": "🗑 Delete",
    "card_add_btn": "➕ Add card",
    "enter_4digits": "❌ Enter only 4 digits!",
    "premium_txt": (
        "╔══════════════════════╗\n"
        "║   💎 SpendUZ Premium   ║\n"
        "╚══════════════════════╝\n\n"
        "🚀 <b>All features for you!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎯 Unlimited goals\n"
        "📊 PDF reports\n"
        "💱 All currencies\n"
        "💳 Unlimited cards\n"
        "🎤 Voice input\n"
        "📈 Category analysis\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💰 Price: <b>85 ⭐ Stars / month</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎁 <b>Get free:</b>\n"
        "Invite a friend → 3 days free!\n"
        "/ref — Your referral link"
    ),
    "premium_btn": "⭐ Subscribe for 85 Stars",
    "premium_ok":  "🎉 <b>Premium activated!</b>\n\n✅ 30 days all features. Thank you! 💎",
    "premium_already": "💎 <b>You are already Premium!</b>\n\nUntil: {until}",
    "need_premium": "🔒 <b>Premium feature!</b>\n\n💎 /premium\n🎁 /ref — invite a friend!",
    "ref_info": (
        "🎁 <b>Invite your friends!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👥 For each friend:\n"
        "→ <b>You get 3 days Premium!</b>\n"
        "→ <b>Friend gets 1 day Premium!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔥 5 friends = 15 days!\n"
        "🔥 10 friends = 1 month!\n\n"
        "👥 Invited: <b>{count}</b>\n\n"
        "👇 Your link:\n"
        "<code>https://t.me/Spend_uz_bot?start={code}</code>"
    ),
    "ref_share_btn": "🔗 Share with friends",
    "ref_open_btn":  "🚀 Open link",
    "ref_thanks":   "🎁 You got <b>1 day free Premium</b> for joining via referral!",
    "ref_bonus":    "🎉 Friend joined! You got <b>3 days Premium</b>!",
    "ref_already":  "❌ This referral link has already been used!",
    "btn_report":   "📊 Report",
    "btn_pdf":      "📥 Report PDF",
    "btn_goals":    "🎯 Goals",
    "btn_cards":    "💳 Cards",
    "btn_premium":  "💎 Premium",
    "btn_ref":      "🎁 Referral",
    "btn_rate":     "💱 Exchange rates",
    "btn_settings": "⚙️ Settings",
    "ref_ad": (
        "🎁 <b>Invite your friends!</b>\n\n"
        "→ <b>You get 3 days Premium!</b>\n"
        "→ <b>Friend gets 1 day Premium!</b>\n\n"
        "<code>https://t.me/Spend_uz_bot?start={code}</code>"
    ),
},
"tj": {
    "start_msg": "💸 <b>Ba SpendUZ Pro xush omaded!</b>\n\nZabonro intihob kuned:",
    "lang_saved": "\u2705 \u0417\u0430\u0431\u043e\u043d \u0441\u0430\u0431\u0442 \u0448\u0443\u0434! \u0411\u0430\u0440\u043d\u043e\u043c\u0430\u0440\u043e \u043a\u0443\u0448\u043e\u0435\u0434 \ud83d\udc47",
    "open_app": "\ud83d\ude80 \u041a\u0443\u0448\u043e\u0434\u0430\u043d\u0438 SpendUZ Pro",
    "help": "\ud83d\udcdd <b>\u0427\u04e3 \u0442\u0430\u0432\u0440 \u043d\u0430\u0432\u0438\u0448\u0442\u0430\u043d:</b>\n\n\ud83d\udcb8 \u0425\u0430\u0440\u043e\u04b7\u043e\u0442: <code>20000 \u0445\u0443\u0440\u043e\u049b</code>\n\ud83d\udcb0 \u0414\u0430\u0440\u043e\u043c\u0430\u0434: <code>3\u043c\u043b\u043d \u043c\u0430\u043e\u0448</code>",
    "saved_exp":  "\u2705 <b>\u0425\u0430\u0440\u043e\u04b7\u043e\u0442 \u0441\u0430\u0431\u0442 \u0448\u0443\u0434!</b>\n\ud83d\udcb8 {amount} {cur} \u2014 {note}",
    "saved_inc":  "\u2705 <b>\u0414\u0430\u0440\u043e\u043c\u0430\u0434 \u0441\u0430\u0431\u0442 \u0448\u0443\u0434!</b>\n\ud83d\udcb0 {amount} {cur} \u2014 {note}",
    "saved_dg":   "\u2705 <b>\u049a\u0430\u0440\u0437 \u0434\u043e\u0434\u0430\u043c!</b>\n\ud83d\udcb8 {amount} {cur}\n\ud83d\udc64 \u0411\u0430 \u043a\u04e3: {note}",
    "saved_dt":   "\u2705 <b>\u049a\u0430\u0440\u0437 \u0433\u0438\u0440\u0438\u0444\u0442\u0430\u043c!</b>\n\ud83d\udcb0 {amount} {cur}\n\ud83d\udc64 \u0410\u0437 \u043a\u04e3: {note}",
    "edit_btn":   "\u270f\ufe0f \u0422\u0430\u04b3\u0440\u0438\u0440",
    "del_btn":    "\ud83d\uddd1 \u041d\u0435\u0441\u0442",
    "deleted":    "\ud83d\uddd1 \u041d\u0435\u0441\u0442 \u0448\u0443\u0434!",
    "edit_ask":   "\u270f\ufe0f \u041c\u0430\u0431\u043b\u0430\u0493\u0438 \u043d\u0430\u0432\u0440\u043e \u0432\u043e\u0440\u0438\u0434 \u043a\u0443\u043d\u0435\u0434:",
    "edit_done":  "\u2705 \u041d\u0430\u0432\u0441\u043e\u0437\u04e3 \u0448\u0443\u0434! {amount}",
    "report": "\ud83d\udcca <b>\u04b2\u0438\u0441\u043e\u0431\u043e\u0442\u0438 {month}:</b>\n\n\u2b06\ufe0f \u0414\u0430\u0440\u043e\u043c\u0430\u0434: <b>{income}</b>\n\u2b07\ufe0f \u0425\u0430\u0440\u043e\u04b7\u043e\u0442: <b>{expense}</b>\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\ud83d\udcc8 \u0411\u0430\u043b\u0430\u043d\u0441: <b>{balance}</b>",
    "no_txn": "\ud83d\udcad \u04b2\u043e\u043b\u043e \u0442\u0440\u0430\u043d\u0437\u0430\u043a\u0441\u0438\u044f \u043d\u0435\u0441\u0442.",
    "reminder": "\u23f0 \u0418\u043c\u0440\u04ef\u0437 \u0445\u0430\u0440\u043e\u04b7\u043e\u0442 \u043d\u0430\u043d\u0430\u0432\u0438\u0448\u0442\u0435\u0434! \u04b2\u043e\u0437\u0438\u0440 \u043d\u0430\u0432\u0438\u0441\u0435\u0434 \ud83d\udcb8",
    "daily_rate": "\ud83d\udcb1 <b>\u041d\u0430\u0440\u0445\u0438 \u0430\u043c\u0440\u04ef\u0437\u0430 (CBU):</b>\n\n{rates}",
    "rate_fail": "\ud83d\ude15 \u041d\u0430\u0440\u0445 \u0431\u043e\u0440 \u043d\u0430\u0448\u0443\u0434.",
    "voice_wait": "\ud83c\udfa4 \u0422\u0430\u04b3\u043b\u0438\u043b...",
    "voice_done": "\ud83c\udfa4 \u0428\u0443\u043d\u0438\u0434\u0430\u043c: <i>\u00ab{text}\u00bb</i>",
    "voice_fail": "\ud83d\ude15 \u041d\u0430\u0444\u0430\u04b3\u043c\u0438\u0434\u0430\u043c.",
    "unknown": "\ud83e\udd14 \u041d\u0430\u0444\u0430\u04b3\u043c\u0438\u0434\u0430\u043c.",
    "goals_empty": "\ud83c\udfaf \u04b2\u043e\u043b\u043e \u043c\u0430\u049b\u0441\u0430\u0434 \u043d\u0435\u0441\u0442.\n<code>/addgoal MacBook 10000000</code>",
    "goal_list_header": "\ud83c\udfaf <b>\u041c\u0430\u049b\u0441\u0430\u0434\u04b3\u043e\u0438 \u0448\u0443\u043c\u043e:</b>\n\n",
    "goal_item": "{emoji} <b>{name}</b>\n\ud83d\udcb0 {current} / {target}\n{bar} {pct}%\n{deadline}\n",
    "goal_add_prompt": "\ud83c\udfaf \u0424\u043e\u0440\u043c\u0430\u0442: <code>/addgoal [\u043d\u043e\u043c] [\u043c\u0430\u0431\u043b\u0430\u0493]</code>",
    "goal_added": "\u2705 <b>\u041c\u0430\u049b\u0441\u0430\u0434 \u0438\u043b\u043e\u0432\u0430 \u0448\u0443\u0434!</b>\n\n\ud83c\udfaf {name}\n\ud83d\udcb0 {target}",
    "goal_add_btn": "\u2795 \u0410\u043d\u0434\u043e\u0445\u0442 \u0438\u043b\u043e\u0432\u0430",
    "goal_edit_btn": "\u270f\ufe0f \u0422\u0430\u04b3\u0440\u0438\u0440",
    "goal_delete_btn": "\ud83d\uddd1 \u041d\u0435\u0441\u0442",
    "goal_add_amount": "\ud83d\udcb0 \u0427\u0430\u043d\u0434 \u0438\u043b\u043e\u0432\u0430?",
    "goal_added_amount": "\u2705 {amount} \u0438\u043b\u043e\u0432\u0430 \u0448\u0443\u0434!\n\ud83c\udfaf {name}: {current} / {target} ({pct}%)",
    "goal_done": "\ud83c\udf89 <b>\u041c\u0430\u049b\u0441\u0430\u0434 \u0438\u04b7\u0440\u043e \u0448\u0443\u0434!</b>\n\ud83c\udfc6 {name}",
    "goal_edit_prompt": "\u270f\ufe0f \u043d\u043e\u043c|\u043c\u0430\u0431\u043b\u0430\u0493",
    "goal_deleted": "\ud83d\uddd1 \u041c\u0430\u049b\u0441\u0430\u0434 \u043d\u0435\u0441\u0442 \u0448\u0443\u0434.",
    "goal_limit": "\ud83c\udfaf \u041b\u0438\u043c\u0438\u0442\u0438 3 \u043c\u0430\u049b\u0441\u0430\u0434!\n\ud83d\udcce /premium",
    "cards_empty": "\ud83d\udcb3 \u041a\u043e\u0440\u0442 \u043d\u0435\u0441\u0442.",
    "card_add_step1": "\ud83d\udcb3 \u041d\u043e\u043c\u0438 \u043a\u043e\u0440\u0442\u0440\u043e \u0432\u043e\u0440\u0438\u0434 \u043a\u0443\u043d\u0435\u0434:",
    "card_add_step2": "\u2705 \u041d\u043e\u043c \u0441\u0430\u0431\u0442!\n\n4 \u0440\u0430\u049b\u0430\u043c\u0438 \u043e\u0445\u0438\u0440\u0438 \u043a\u043e\u0440\u0442\u0440\u043e \u0432\u043e\u0440\u0438\u0434 \u043a\u0443\u043d\u0435\u0434:",
    "card_added": "\u2705 <b>\u041a\u043e\u0440\u0442 \u0438\u043b\u043e\u0432\u0430 \u0448\u0443\u0434!</b>\n\ud83d\udcb3 {name}\n**** **** **** {last4}",
    "card_deleted": "\ud83d\udcb3 \u041a\u043e\u0440\u0442 \u043d\u0435\u0441\u0442 \u0448\u0443\u0434.",
    "card_limit": "\ud83d\udcb3 \u041b\u0438\u043c\u0438\u0442\u0438 3 \u043a\u043e\u0440\u0442!",
    "card_del_btn": "\ud83d\uddd1 \u041d\u0435\u0441\u0442",
    "card_add_btn": "\u2795 \u041a\u043e\u0440\u0442 \u0438\u043b\u043e\u0432\u0430",
    "enter_4digits": "\u274c \u0424\u0430\u049b\u0430\u0442 4 \u0440\u0430\u049b\u0430\u043c!",
    "premium_txt": "\ud83d\udcce <b>SpendUZ Premium</b>\n\n\ud83d\udcb0 85 \u2b50 Stars / \u043c\u043e\u04b3",
    "premium_btn": "\u2b50 85 Stars",
    "premium_ok": "\ud83c\udf89 <b>Premium \u0444\u0430\u044a\u043e\u043b \u0448\u0443\u0434!</b>",
    "premium_already": "\ud83d\udcce <b>\u0428\u0443\u043c\u043e \u0430\u043b\u043b\u0430\u043a\u0430\u0445 Premium!</b>",
    "need_premium": "\ud83d\udd12 <b>Premium \u043b\u043e\u0437\u0438\u043c \u0430\u0441\u0442!</b>\n\ud83d\udcce /premium",
    "ref_info": "\ud83c\udf81 \ud83c\udf81 <b>\u0414\u04ef\u0441\u0442\u043e\u043d\u0440\u043e \u0434\u0430\u044a\u0432\u0430\u0442 \u043a\u0443\u043d\u0435\u0434!</b>\n\n\ud83d\udc65 \u04b2\u0430\u0440 \u0434\u04ef\u0441\u0442:\n\u2192 <b>\u0428\u0443\u043c\u043e 3 \u0440\u04ef\u0437 Premium!</b>\n\u2192 <b>\u0414\u04ef\u0441\u0442 1 \u0440\u04ef\u0437 Premium!</b>\n\n<code>https://t.me/Spend_uz_bot?start={code}</code>",
    "ref_share_btn": "\ud83d\udd17 \u041c\u0443\u0431\u043e\u0434\u0438\u043b\u0430",
    "ref_open_btn": "\ud83d\ude80 \u041a\u0443\u0448\u043e\u0434\u0430\u043d",
    "ref_thanks": "\ud83c\udf81 1 \u0440\u04ef\u0437\u0438 Premium \u0433\u0438\u0440\u0438\u0444\u0442\u0435\u0434!",
    "ref_bonus": "\ud83c\udf89 \u0414\u04ef\u0441\u0442\u0430\u0442\u043e\u043d \u043e\u043c\u0430\u0434! 3 \u0440\u04ef\u0437\u0438 Premium!",
    "ref_already": "\u274c \u0410\u043b\u043b\u0430\u043a\u0430\u0445 \u0438\u0441\u0442\u0438\u0444\u043e\u0434\u0430 \u0448\u0443\u0434\u0430\u0430\u0441\u0442!",
    "btn_report":   "\ud83d\udcca \u04b2\u0438\u0441\u043e\u0431\u043e\u0442",
    "btn_pdf":      "\ud83d\udce5 PDF",
    "btn_goals":    "\ud83c\udfaf \u041c\u0430\u049b\u0441\u0430\u0434\u04b3\u043e",
    "btn_cards":    "\ud83d\udcb3 \u041a\u043e\u0440\u0442\u04b3\u043e",
    "btn_premium":  "\ud83d\udc8e Premium",
    "btn_ref":      "\ud83c\udf81 \u0414\u0430\u044a\u0432\u0430\u0442",
    "btn_rate":     "\ud83d\udcb1 \u041d\u0430\u0440\u0445\u0438 \u0430\u0441\u044a\u043e\u0440",
    "btn_settings": "\u2699\ufe0f \u0422\u0430\u043d\u0437\u0438\u043c\u043e\u0442",
    "ref_ad": "\ud83c\udf81 <b>\u0414\u04ef\u0441\u0442\u043e\u043d\u0440\u043e \u0434\u0430\u044a\u0432\u0430\u0442 \u043a\u0443\u043d\u0435\u0434!</b>\n\n<code>https://t.me/Spend_uz_bot?start={code}</code>",
},
}

def tx(uid, key, **kw):
    lang = get_lang(uid)
    s = T.get(lang, T["uz"]).get(key, T["uz"].get(key, key))
    for k, v in kw.items():
        s = s.replace("{" + k + "}", str(v))
    return s

# ── CATEGORY ───────────────────────────────────────────────────────────────────
CAT_EMOJI = {
    "c_food":"🍔","c_trans":"🚗","c_home":"🏠","c_health":"💊","c_cloth":"👗",
    "c_enter":"🎮","c_edu":"📚","c_cafe":"☕","c_tech":"💻","c_sport":"⚽",
    "c_travel":"✈️","c_bills":"💡","c_beauty":"💅","c_gift":"🎁",
    "c_salary":"💰","c_free":"💻","c_biz":"🏢","c_invest":"📈","other":"📦",
}
CAT_NAMES = {
    "uz":  {"c_food":"Oziq-ovqat","c_trans":"Transport","c_home":"Uy-joy","c_health":"Salomatlik","c_cloth":"Kiyim","c_enter":"Ko'nil ochish","c_edu":"Ta'lim","c_cafe":"Kafe","c_tech":"Texnologiya","c_sport":"Sport","c_travel":"Sayohat","c_bills":"Kommunal","c_beauty":"Go'zallik","c_gift":"Sovg'a","c_salary":"Maosh","c_free":"Frilanss","c_biz":"Biznes","c_invest":"Investitsiya","other":"Boshqa"},
    "ru":  {"c_food":"Еда","c_trans":"Транспорт","c_home":"Жильё","c_health":"Здоровье","c_cloth":"Одежда","c_enter":"Развлечения","c_edu":"Образование","c_cafe":"Кафе","c_tech":"Технологии","c_sport":"Спорт","c_travel":"Путешествие","c_bills":"Коммунальные","c_beauty":"Красота","c_gift":"Подарки","c_salary":"Зарплата","c_free":"Фриланс","c_biz":"Бизнес","c_invest":"Инвестиции","other":"Другое"},
    "en":  {"c_food":"Food","c_trans":"Transport","c_home":"Housing","c_health":"Health","c_cloth":"Clothes","c_enter":"Entertainment","c_edu":"Education","c_cafe":"Cafe","c_tech":"Technology","c_sport":"Sport","c_travel":"Travel","c_bills":"Bills","c_beauty":"Beauty","c_gift":"Gifts","c_salary":"Salary","c_free":"Freelance","c_biz":"Business","c_invest":"Investment","other":"Other"},
    "tj":  {"c_food":"Хурок","c_trans":"Нақлиёт","c_health":"Саломатӣ","c_salary":"Маош","other":"Дигар"},
}
AI_KW = {
    "c_food":   ["ovqat","taom","osh","non","gosht","sabzavot","meva","tushlik","nonushta","somsa","manti","lagman","burger","pizza","lavash","doner","bozor","bazar","supermarket","magazin","dukon","dokon","restoran","kafe","choyxona","еда","продукты","магазин","рынок","базар","ресторан","food","grocery","market","lunch","dinner","breakfast","restaurant"],
    "c_trans":  ["taxi","taksi","yandex","uber","avto","mashina","bus","avtobus","metro","benzin","gaz","marshrutka","poyezd","такси","машина","бензин","метро","автобус","поезд","fuel","car","parking","train"],
    "c_home":   ["ijara","kvartira","uy","arenda","rent","kommunal","remont","mebel","аренда","квартира","ремонт","мебель","коммунальные","repair"],
    "c_health": ["dori","dorixona","apteka","shifokor","doktor","klinika","kasalxona","vitamin","аптека","лекарство","врач","клиника","больница","pharmacy","medicine","doctor"],
    "c_cloth":  ["kiyim","koylak","shim","kurtka","palto","poyabzal","botinka","krossovka","sumka","одежда","рубашка","штаны","куртка","обувь","кроссовки","clothes","shoes"],
    "c_enter":  ["kino","film","concert","teatr","park","zoo","game","netflix","bilyard","bowling","karaoke","кино","концерт","театр","игра","парк","cinema","movie"],
    "c_edu":    ["kurs","trening","kitob","darslik","seminar","univer","maktab","kollej","repetitor","образование","курс","книга","университет","школа","course","book","school"],
    "c_cafe":   ["kofe","coffee","kapuchino","latte","espresso","choy","tea","tort","konfet","shokolad","juice","кофе","чай","торт","шоколад","cake","candy"],
    "c_tech":   ["telefon","smartfon","iphone","samsung","xiaomi","laptop","noutbuk","kompyuter","planshet","naushnik","kamera","printer","телефон","смартфон","ноутбук","компьютер","phone","computer"],
    "c_sport":  ["sport","gym","fitnes","trenajer","basketball","futbol","tennis","suzish","velosiped","yugurish","boks","yoga","спорт","тренажёр","фитнес","бассейн","fitness","swimming"],
    "c_travel": ["sayohat","avia","aviabilet","samolyot","hotel","mehmonxona","hostel","viza","tur","путешествие","билет","самолёт","отель","гостиница","flight","ticket","hotel","visa"],
    "c_bills":  ["elektr","yoruglik","internet","wifi","kommunal","obuna","электричество","интернет","коммунальные","electricity","bills","subscription"],
    "c_beauty": ["sartarosh","soch","soqol","manikyur","pedikyur","kosmetika","parfum","salon","spa","парикмахер","маникюр","косметика","духи","haircut","salon"],
    "c_gift":   ["sovga","present","gift","bayram","tugilgan","birthday","toy","nikoh","подарок","праздник","день рождения","свадьба","wedding"],
    "c_salary": ["maosh","oylik","ish haqi","salary","daromad","bonus","mukofot","зарплата","премия","доход","income","earned"],
    "c_free":   ["frilanss","freelance","loyiha","project","dizayn","фриланс","проект","дизайн","design"],
    "c_biz":    ["biznes","savdo","tovar","foyda","firma","sotish","бизнес","торговля","товар","прибыль","business","sales","profit"],
    "c_invest": ["invest","aksiya","fond","crypto","bitcoin","depozit","foiz","dividend","инвестиции","акции","крипта","депозит","investment","stock","crypto"],
}
INCOME_KW  = ["maosh","oylik","ish haqi","daromad","bonus","mukofot","зарплата","премия","доход","salary","income","earned","frilanss","freelance","foyda","profit","biznes","business"]
DEBT_GIVEN = ["qarz berdim","qarz ber","berdim","долг дал","дал в долг","lent","gave","берди"]
DEBT_TAKEN = ["qarz oldim","qarz ol","oldim","взял в долг","взял","borrowed","гирифтам"]

def cat_label(uid, cat_id):
    lang = get_lang(uid)
    return CAT_NAMES.get(lang, CAT_NAMES["uz"]).get(cat_id, cat_id)

def cat_emoji(cat_id):
    return CAT_EMOJI.get(cat_id, "📦")

def detect_cat(text):
    low = text.lower()
    for cid, words in AI_KW.items():
        if any(w in low for w in words):
            return cid
    return "other"

def detect_type(text):
    low = text.lower()
    if any(w in low for w in DEBT_GIVEN): return "debt_given"
    if any(w in low for w in DEBT_TAKEN): return "debt_taken"
    if any(w in low for w in INCOME_KW):  return "income"
    return "expense"

def fmt(val) -> str:
    try: return f"{int(val):,}".replace(",", " ")
    except: return str(val)

def progress_bar(pct: int) -> str:
    f = min(10, pct // 10)
    return "█" * f + "░" * (10 - f)

# ── AMOUNT PARSER ──────────────────────────────────────────────────────────────
def parse_amount(text: str) -> tuple:
    low  = text.lower().strip()
    nums = re.findall(r"\d+", text)
    cur  = "UZS"
    if "$" in text or "dollar" in low or "usd" in low:  cur = "USD"
    elif "€" in text or "euro" in low or "eur" in low:  cur = "EUR"
    elif "₽" in text or "rubl" in low or "rub" in low:  cur = "RUB"
    if not nums: return None, cur

    base   = int(nums[0])
    second = int(nums[1]) if len(nums) > 1 else 0
    words  = re.split(r"[\s,.\-]+", low)

    # Million keywords (uz/ru/en/tj)
    MLN_KW  = ["million","mln","mlrd","milliard","миллион","млн","миллиона","миллионов","mlrd","миллиард","milyon","млрд"]
    # Thousand keywords (uz/ru/en/tj)
    MING_KW = ["ming","тысяч","тыс","thousand","тысячи","тысяча","минг","хазор"]
    # K keyword
    hasMln  = any(w in MLN_KW for w in words) or any(kw in low for kw in ["mln","млн","million","миллион"])
    hasMing = any(w in MING_KW for w in words) or "ming" in low or "тысяч" in low
    hasK    = any(w == "k" for w in words) and not any(x in low for x in ["ok","ak","ek","ok"])

    if hasMln:
        res = base * 1_000_000
        if 0 < second < 1000: res += second * 1000
        return res, cur
    if hasMing or hasK:
        res = base * 1000
        if 0 < second < 1000: res += second
        return res, cur
    # "4 000 000" style - joined zeros
    if len(nums) > 1 and all(re.match(r"^0+$", n) for n in nums[1:]):
        return int("".join(nums)), cur
    # "4 000" style
    if len(nums) == 2 and nums[1] in ["000"]:
        return int(nums[0]) * 1000, cur
    if len(nums) == 3 and nums[1] == "000" and nums[2] == "000":
        return int(nums[0]) * 1_000_000, cur
    return base, cur

# ── KEYBOARDS ──────────────────────────────────────────────────────────────────
def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbek",  callback_data="lang_uz"),
         InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
         InlineKeyboardButton(text="🇹🇯 Тоҷикӣ",  callback_data="lang_tj")],
    ])

def main_kb(uid: int):
    l = get_lang(uid)
    t_btn = T.get(l, T["uz"])
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t_btn["btn_report"]),  KeyboardButton(text=t_btn["btn_pdf"])],
        [KeyboardButton(text=t_btn["btn_goals"]),   KeyboardButton(text=t_btn["btn_cards"])],
        [KeyboardButton(text=t_btn["btn_premium"]), KeyboardButton(text=t_btn["btn_ref"])],
        [KeyboardButton(text=t_btn["btn_rate"]),    KeyboardButton(text=t_btn["btn_settings"])],
    ], resize_keyboard=True)

def app_kb(uid: int):
    l = get_lang(uid)
    # Add premium info to URL
    prem = "1" if is_premium(uid) else "0"
    until = ""
    if is_premium(uid):
        u = get_premium_until(uid)
        if u: until = u[:10]  # YYYY-MM-DD
    app_url = f"{WEB_APP_URL}?premium={prem}&until={until}"
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=T.get(l,T["uz"])["open_app"], web_app=WebAppInfo(url=app_url))
    ]])

def action_kb(uid: int, tid: int):
    l = get_lang(uid)
    t_btn = T.get(l, T["uz"])
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t_btn["edit_btn"], callback_data=f"edit_{tid}"),
        InlineKeyboardButton(text=t_btn["del_btn"],  callback_data=f"del_{tid}"),
    ]])

def premium_kb(uid: int):
    l = get_lang(uid)
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=T.get(l,T["uz"])["premium_btn"], callback_data="buy_premium")
    ]])

def goal_kb(uid: int, gid: int):
    l = get_lang(uid)
    t_btn = T.get(l, T["uz"])
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t_btn["goal_add_btn"],    callback_data=f"gadd_{gid}"),
        InlineKeyboardButton(text=t_btn["goal_edit_btn"],   callback_data=f"gedit_{gid}"),
        InlineKeyboardButton(text=t_btn["goal_delete_btn"], callback_data=f"gdel_{gid}"),
    ]])

def cards_kb(uid: int):
    l = get_lang(uid)
    t_btn = T.get(l, T["uz"])
    cards = get_cards(uid)
    rows = []
    for c in cards:
        rows.append([InlineKeyboardButton(
            text=f"💳 {c['card_name']} *{c['last4']}",
            callback_data=f"card_info_{c['id']}"
        )])
    rows.append([InlineKeyboardButton(text=t_btn["card_add_btn"], callback_data="card_add")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ── RATES ──────────────────────────────────────────────────────────────────────
async def fetch_rates() -> dict | None:
    if not HTTP_OK: return None
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://cbu.uz/uz/arkhiv-kursov-valyut/json/",
                            timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json(content_type=None)
                return {x["Ccy"]: float(x["Rate"]) for x in data}
    except Exception as e:
        log.error(f"cbu: {e}")
        return None

def format_rates(rates: dict) -> str:
    codes = ["USD","EUR","RUB","GBP","CNY","JPY","KZT","TRY","AED","KGS"]
    flags = {"USD":"🇺🇸","EUR":"🇪🇺","RUB":"🇷🇺","GBP":"🇬🇧","CNY":"🇨🇳",
             "JPY":"🇯🇵","KZT":"🇰🇿","TRY":"🇹🇷","AED":"🇦🇪","KGS":"🇰🇬"}
    lines = []
    for code in codes:
        if code in rates:
            lines.append(f"{flags.get(code,'•')} <b>{code}</b>: {rates[code]:,.0f} so'm")
    return "\n".join(lines)

# ── VOICE ──────────────────────────────────────────────────────────────────────
async def voice_to_text(ogg_path: str) -> str | None:
    # Try Groq Whisper first
    if GROQ_API_KEY and "XXXX" not in GROQ_API_KEY:
        try:
            import httpx
            wav = ogg_path.replace(".ogg", ".wav")
            if VOICE_OK:
                audio = AudioSegment.from_ogg(ogg_path)
                audio.export(wav, format="wav")
                audio_file = wav
            else:
                audio_file = ogg_path
            async with httpx.AsyncClient(timeout=30) as client:
                with open(audio_file, "rb") as f:
                    resp = await client.post(
                        "https://api.groq.com/openai/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                        files={"file": (audio_file, f, "audio/wav")},
                        data={"model": "whisper-large-v3", "response_format": "text"}
                    )
                if resp.status_code == 200:
                    text = resp.text.strip()
                    if text: return text
        except Exception as e:
            log.error(f"groq: {e}")
    # Fallback Google STT
    if not VOICE_OK: return None
    loop = asyncio.get_event_loop()
    def _run():
        try:
            audio = AudioSegment.from_ogg(ogg_path)
            wav   = ogg_path.replace(".ogg", ".wav")
            audio.export(wav, format="wav")
            r = sr.Recognizer()
            with sr.AudioFile(wav) as src:
                data = r.record(src)
            for lc in ["uz-UZ","ru-RU","en-US","tg-TG"]:
                try:
                    result = r.recognize_google(data, language=lc)
                    if result: return result
                except: continue
        except Exception as e:
            log.error(f"stt: {e}")
        return None
    return await loop.run_in_executor(None, _run)

# ── SAVE TXN ───────────────────────────────────────────────────────────────────
async def save_and_reply(msg: Message, uid: int, tx_type: str, amount: int, currency: str, note: str):
    cat = detect_cat(note) if tx_type not in ("debt_given","debt_taken") else "c_other_e"
    if tx_type == "income" and cat == "other": cat = "c_salary"
    tid = add_txn(uid, tx_type, amount, note, currency, cat)
    em  = cat_emoji(cat)
    key_map = {"income":"saved_inc","expense":"saved_exp","debt_given":"saved_dg","debt_taken":"saved_dt"}
    text = tx(uid, key_map.get(tx_type,"saved_exp"), amount=fmt(amount), cur=currency, note=note or "-")
    await msg.answer(text, parse_mode="HTML", reply_markup=action_kb(uid, tid))

# ── PDF REPORT ─────────────────────────────────────────────────────────────────
async def generate_pdf(uid: int) -> bytes | None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        import io
        txns   = get_txns(uid, limit=100)
        s      = get_summary(uid)
        cats   = get_cat_breakdown(uid)
        now    = datetime.now()
        months = ["Yanvar","Fevral","Mart","Aprel","May","Iyun","Iyul","Avgust","Sentabr","Oktabr","Noyabr","Dekabr"]
        mname  = months[now.month-1] + " " + str(now.year)
        buf    = io.BytesIO()
        doc    = SimpleDocTemplate(buf, pagesize=A4,
                    rightMargin=1.5*cm, leftMargin=1.5*cm,
                    topMargin=1.5*cm, bottomMargin=1.5*cm)
        styles = getSampleStyleSheet()
        title_s = ParagraphStyle("t", parent=styles["Normal"],
                    fontSize=20, fontName="Helvetica-Bold",
                    textColor=colors.HexColor("#00b87d"), spaceAfter=4)
        sub_s   = ParagraphStyle("s", parent=styles["Normal"],
                    fontSize=10, fontName="Helvetica", textColor=colors.gray)
        elems = []
        u = get_user(uid)
        uname = u.get("name","") if u else ""
        tg_user = ""
        try:
            chat = await bot.get_chat(uid)
            tg_user = chat.first_name or ""
        except: pass
        display_name = tg_user or uname or str(uid)
        elems.append(Paragraph("SpendUZ Pro", title_s))
        elems.append(Paragraph(f"{mname} hisoboti  |  {display_name}", sub_s))
        elems.append(Spacer(1, 0.4*cm))
        # Summary
        sum_data = [
            ["Ko'rsatkich", "Summa"],
            ["⬆️ Daromad",   f"{fmt(s['income'])} UZS"],
            ["⬇️ Xarajat",   f"{fmt(s['expense'])} UZS"],
            ["💸 Qarz berdim",f"{fmt(s['debt_given'])} UZS"],
            ["💰 Qarz oldim", f"{fmt(s['debt_taken'])} UZS"],
            ["📈 Balans",     f"{fmt(s['balance'])} UZS"],
        ]
        t_sum = Table(sum_data, colWidths=[9*cm, 7*cm])
        t_sum.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#00b87d")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1),10),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f5f5f5")]),
            ("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#dddddd")),
            ("ALIGN",(1,0),(1,-1),"RIGHT"),
            ("BOTTOMPADDING",(0,0),(-1,-1),6),
            ("TOPPADDING",(0,0),(-1,-1),6),
        ]))
        elems.append(t_sum)
        elems.append(Spacer(1, 0.4*cm))
        # Transactions
        # Category breakdown
        if cats:
            elems.append(Paragraph("Kategoriyalar bo'yicha xarajat:", ParagraphStyle("hc",
                parent=styles["Normal"],fontSize=12,fontName="Helvetica-Bold",
                textColor=colors.HexColor("#1a1e2e"),spaceAfter=4)))
            cat_data = [["Kategoriya", "Summa"]]
            for cid, val in sorted(cats.items(), key=lambda x: -x[1])[:10]:
                em   = cat_emoji(cid)
                name = CAT_NAMES.get("uz",{}).get(cid, cid)
                cat_data.append([f"{em} {name}", f"{fmt(val)} UZS"])
            t_cat = Table(cat_data, colWidths=[10*cm, 6*cm])
            t_cat.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#7C6DFA")),
                ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                ("FONTSIZE",(0,0),(-1,-1),9),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f5f5f5")]),
                ("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#dddddd")),
                ("ALIGN",(1,0),(1,-1),"RIGHT"),
                ("BOTTOMPADDING",(0,0),(-1,-1),5),
                ("TOPPADDING",(0,0),(-1,-1),5),
            ]))
            elems.append(t_cat)
            elems.append(Spacer(1, 0.3*cm))

        if txns:
            elems.append(Paragraph("Tranzaksiyalar (so'nggi 50):", ParagraphStyle("h",
                parent=styles["Normal"],fontSize=12,fontName="Helvetica-Bold",
                textColor=colors.HexColor("#1a1e2e"),spaceAfter=4)))
            tx_data = [["Sana","Tur","Izoh","Summa"]]
            type_names = {"income":"Daromad","expense":"Xarajat","debt_given":"Qarz berdim","debt_taken":"Qarz oldim"}
            for t in txns[:50]:
                sign    = "+" if t["tx_type"] in ("income","debt_taken") else "-"
                em      = cat_emoji(t["category"])
                cat_name= CAT_NAMES.get("uz",{}).get(t["category"], t["category"])
                type_n  = type_names.get(t["tx_type"], t["tx_type"])
                tx_data.append([
                    t["date"],
                    f"{em} {cat_name}",
                    (t["note"] or "-")[:25],
                    f"{sign}{fmt(t['amount'])} {t['currency']}"
                ])
            t_tx = Table(tx_data, colWidths=[2.5*cm,3.5*cm,7*cm,3*cm])
            t_tx.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1a1e2e")),
                ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                ("FONTSIZE",(0,0),(-1,-1),8),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f5f5f5")]),
                ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#dddddd")),
                ("ALIGN",(3,0),(3,-1),"RIGHT"),
                ("BOTTOMPADDING",(0,0),(-1,-1),4),
                ("TOPPADDING",(0,0),(-1,-1),4),
            ]))
            elems.append(t_tx)
        elems.append(Spacer(1, 0.3*cm))
        elems.append(Paragraph(
            f"SpendUZ Pro · @Spend_uz_bot · {now.strftime('%Y-%m-%d %H:%M')}",
            ParagraphStyle("f",parent=styles["Normal"],fontSize=8,
                fontName="Helvetica",textColor=colors.gray)))
        doc.build(elems)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        log.error(f"pdf: {e}")
        return None

# ── HANDLERS ───────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(msg: Message):
    uid  = msg.from_user.id
    args = msg.text.split()
    # Auto-fill name from Telegram
    add_user(uid)
    u = get_user(uid)
    if u and msg.from_user.first_name and not u.get("name"):
        from database import con
        db = con()
        db.execute("ALTER TABLE users ADD COLUMN name TEXT DEFAULT NULL") if False else None
        db.close()

    # Referral
    referrer_uid = 0
    if len(args) > 1:
        referrer_uid = use_referral(args[1], uid)

    if referrer_uid:
        set_premium(uid, 1)
        await msg.answer(tx(uid, "ref_thanks"), parse_mode="HTML")
        try:
            set_premium(referrer_uid, 3)
            await bot.send_message(referrer_uid, tx(referrer_uid, "ref_bonus"), parse_mode="HTML")
        except: pass

    l = get_lang(uid)
    await msg.answer(T.get(l, T["uz"])["start_msg"], reply_markup=lang_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("lang_"))
async def cb_lang(cb: CallbackQuery):
    uid  = cb.from_user.id
    lang = cb.data.split("_")[1]
    add_user(uid, lang)
    set_lang(uid, lang)
    await cb.message.edit_text(T.get(lang,T["uz"])["lang_saved"], parse_mode="HTML")
    await cb.message.answer("📱", reply_markup=app_kb(uid))
    await cb.message.answer("📋", reply_markup=main_kb(uid))
    await cb.answer()

@dp.callback_query(F.data.startswith("edit_"))
async def cb_edit(cb: CallbackQuery):
    uid = cb.from_user.id
    tid = int(cb.data.split("_")[1])
    states[uid] = {"action": "edit", "tid": tid}
    await cb.message.answer(tx(uid, "edit_ask"), parse_mode="HTML")
    await cb.answer()

@dp.callback_query(F.data.startswith("del_"))
async def cb_del(cb: CallbackQuery):
    uid = cb.from_user.id
    tid = int(cb.data.split("_")[1])
    if delete_txn(tid, uid):
        await cb.message.edit_text(tx(uid, "deleted"))
    await cb.answer()

@dp.callback_query(F.data == "buy_premium")
async def cb_buy_premium(cb: CallbackQuery):
    uid = cb.from_user.id
    if is_premium(uid):
        until = get_premium_until(uid)
        try:
            until_fmt = datetime.fromisoformat(until).strftime("%Y-%m-%d")
        except:
            until_fmt = until or "?"
        await cb.answer(tx(uid,"premium_already",until=until_fmt), show_alert=True)
        return
    await bot.send_invoice(
        chat_id=uid,
        title="SpendUZ Premium",
        description="30 kunlik Premium — barcha funksiyalar!",
        payload=f"premium_{uid}",
        currency="XTR",
        prices=[LabeledPrice(label="Premium 30 kun", amount=PREMIUM_STARS)],
        provider_token="",
    )
    await cb.answer()

@dp.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await q.answer(ok=True)

@dp.message(F.successful_payment)
async def on_payment(msg: Message):
    uid = msg.from_user.id
    if msg.successful_payment.invoice_payload.startswith("premium_"):
        set_premium(uid, PREMIUM_DAYS)
        await msg.answer(tx(uid, "premium_ok"), parse_mode="HTML", reply_markup=main_kb(uid))

# GOALS callbacks
@dp.callback_query(F.data.startswith("gadd_"))
async def cb_goal_add(cb: CallbackQuery):
    uid = cb.from_user.id
    gid = int(cb.data.split("_")[1])
    states[uid] = {"action": "goal_add_amount", "gid": gid}
    await cb.message.answer(tx(uid, "goal_add_amount"), parse_mode="HTML")
    await cb.answer()

@dp.callback_query(F.data.startswith("gedit_"))
async def cb_goal_edit(cb: CallbackQuery):
    uid = cb.from_user.id
    gid = int(cb.data.split("_")[1])
    states[uid] = {"action": "goal_edit", "gid": gid}
    await cb.message.answer(tx(uid, "goal_edit_prompt"), parse_mode="HTML")
    await cb.answer()

@dp.callback_query(F.data.startswith("gdel_"))
async def cb_goal_del(cb: CallbackQuery):
    uid = cb.from_user.id
    gid = int(cb.data.split("_")[1])
    if delete_goal(gid, uid):
        await cb.message.edit_text(tx(uid, "goal_deleted"))
    await cb.answer()

# CARDS callbacks
@dp.callback_query(F.data == "card_add")
async def cb_card_add(cb: CallbackQuery):
    uid = cb.from_user.id
    cards = get_cards(uid)
    if not is_premium(uid) and len(cards) >= 3:
        await cb.message.answer(tx(uid,"card_limit"), parse_mode="HTML", reply_markup=premium_kb(uid))
        await cb.answer(); return
    states[uid] = {"action": "card_add_name"}
    await cb.message.answer(tx(uid, "card_add_step1"), parse_mode="HTML")
    await cb.answer()

@dp.callback_query(F.data.startswith("card_info_"))
async def cb_card_info(cb: CallbackQuery):
    uid = cb.from_user.id
    cid = int(cb.data.split("_")[2])
    cards = get_cards(uid)
    card  = next((c for c in cards if c["id"] == cid), None)
    if not card:
        await cb.answer("Topilmadi"); return
    l = get_lang(uid)
    del_btn = T.get(l,T["uz"])["card_del_btn"]
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=del_btn, callback_data=f"card_del_{cid}")
    ]])
    await cb.message.answer(
        f"💳 <b>{card['card_name']}</b>\n**** **** **** {card['last4']}",
        parse_mode="HTML", reply_markup=kb)
    await cb.answer()

@dp.callback_query(F.data.startswith("card_del_"))
async def cb_card_del(cb: CallbackQuery):
    uid = cb.from_user.id
    cid = int(cb.data.split("_")[2])
    if delete_card(cid, uid):
        await cb.message.edit_text(tx(uid, "card_deleted"))
    await cb.answer()

# COMMANDS
@dp.message(Command("report"))
async def cmd_report(msg: Message):
    uid = msg.from_user.id
    s   = get_summary(uid)
    mon = datetime.now().strftime("%Y-%m")
    await msg.answer(tx(uid,"report",
        month=mon, income=fmt(s["income"])+" UZS", expense=fmt(s["expense"])+" UZS",
        dg=fmt(s["debt_given"])+" UZS", dt=fmt(s["debt_taken"])+" UZS",
        balance=fmt(s["balance"])+" UZS"), parse_mode="HTML")

@dp.message(Command("goals"))
async def cmd_goals(msg: Message):
    uid   = msg.from_user.id
    goals = get_goals(uid)
    if not goals:
        await msg.answer(tx(uid, "goals_empty"), parse_mode="HTML")
        await msg.answer(tx(uid, "goal_add_prompt"), parse_mode="HTML")
        return
    text = tx(uid, "goal_list_header")
    for g in goals:
        pct = round((g["current"]/g["target"])*100) if g["target"] > 0 else 0
        bar = progress_bar(pct)
        dl  = f"📅 {g['deadline']}" if g.get("deadline") else ""
        item = tx(uid,"goal_item",
            emoji=g.get("emoji","🎯"), name=g["name"],
            current=fmt(g["current"]), target=fmt(g["target"]),
            bar=bar, pct=pct, deadline=dl)
        await msg.answer(text + item, parse_mode="HTML", reply_markup=goal_kb(uid, g["id"]))
        text = ""
    await msg.answer(tx(uid,"goal_add_prompt"), parse_mode="HTML")

@dp.message(Command("addgoal"))
async def cmd_addgoal(msg: Message):
    uid  = msg.from_user.id
    if not is_premium(uid):
        goals = get_goals(uid)
        if len(goals) >= 3:
            await msg.answer(tx(uid,"goal_limit"), parse_mode="HTML", reply_markup=premium_kb(uid))
            return
    args = (msg.text or "").split(maxsplit=2)
    if len(args) < 3:
        await msg.answer(tx(uid,"goal_add_prompt"), parse_mode="HTML"); return
    name    = args[1]
    amount, _ = parse_amount(args[2])
    if not amount:
        await msg.answer(tx(uid,"goal_add_prompt"), parse_mode="HTML"); return
    # Check for deadline
    deadline = ""
    parts = args[2].split()
    for p in parts:
        if re.match(r"\d{4}-\d{2}-\d{2}", p):
            deadline = p; break
    add_goal(uid, name, amount, deadline)
    await msg.answer(tx(uid,"goal_added",name=name,target=fmt(amount)+" UZS"), parse_mode="HTML")

@dp.message(Command("cards"))
async def cmd_cards(msg: Message):
    uid   = msg.from_user.id
    cards = get_cards(uid)
    if not cards:
        l = get_lang(uid)
        add_btn = T.get(l,T["uz"])["card_add_btn"]
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=add_btn, callback_data="card_add")
        ]])
        await msg.answer(tx(uid,"cards_empty"), parse_mode="HTML", reply_markup=kb)
        return
    await msg.answer(f"💳 <b>{len(cards)} ta karta</b>", parse_mode="HTML", reply_markup=cards_kb(uid))

@dp.message(Command("premium"))
async def cmd_premium(msg: Message):
    uid = msg.from_user.id
    if is_premium(uid):
        until = get_premium_until(uid)
        try:
            until_fmt = datetime.fromisoformat(until).strftime("%Y-%m-%d")
        except:
            until_fmt = until or "?"
        await msg.answer(tx(uid,"premium_already",until=until_fmt), parse_mode="HTML")
        return
    l = get_lang(uid)
    await msg.answer(T.get(l,T["uz"])["premium_txt"], parse_mode="HTML", reply_markup=premium_kb(uid))

@dp.message(Command("ref"))
async def cmd_ref(msg: Message):
    uid   = msg.from_user.id
    code  = get_referral_code(uid)
    count = get_referral_count(uid)
    l     = get_lang(uid)
    t_btn = T.get(l, T["uz"])
    ref_link  = f"https://t.me/Spend_uz_bot?start={code}"
    share_url = f"https://t.me/share/url?url={ref_link}&text=SpendUZ+Pro+-+moliya+treker!"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t_btn["ref_share_btn"], url=share_url)],
        [InlineKeyboardButton(text=t_btn["ref_open_btn"],  url=ref_link)],
    ])
    await msg.answer(tx(uid,"ref_info",code=code,count=count), parse_mode="HTML", reply_markup=kb)

@dp.message(Command("rate"))
async def cmd_rate(msg: Message):
    uid   = msg.from_user.id
    rates = await fetch_rates()
    if not rates:
        await msg.answer(tx(uid,"rate_fail")); return
    await msg.answer(tx(uid,"daily_rate",rates=format_rates(rates)), parse_mode="HTML")

@dp.message(Command("settings"))
async def cmd_settings(msg: Message):
    uid = msg.from_user.id
    l   = get_lang(uid)
    prem = "✅ Premium" if is_premium(uid) else "❌ Bepul"
    txns  = get_txns(uid)
    goals = get_goals(uid)
    cards = get_cards(uid)
    text = (
        f"⚙️ <b>Sozlamalar</b>\n\n"
        f"👤 {msg.from_user.first_name or 'Foydalanuvchi'}\n"
        f"💎 {prem}\n"
        f"🌍 Til: {l.upper()}\n"
        f"📊 Tranzaksiyalar: {len(txns)}\n"
        f"🎯 Maqsadlar: {len(goals)}\n"
        f"💳 Kartalar: {len(cards)}\n\n"
        f"Tilni o'zgartirish uchun 👇"
    )
    await msg.answer(text, parse_mode="HTML", reply_markup=lang_kb())

@dp.message(Command("report_pdf"))
async def cmd_report_pdf(msg: Message):
    uid = msg.from_user.id
    if not is_premium(uid):
        await msg.answer(tx(uid,"need_premium"), parse_mode="HTML", reply_markup=premium_kb(uid))
        return
    wait = await msg.answer("📊 PDF tayyorlanmoqda...")
    pdf_bytes = await generate_pdf(uid)
    await wait.delete()
    if pdf_bytes:
        fname = f"SpendUZ_{datetime.now().strftime('%Y%m%d')}.pdf"
        await msg.answer_document(
            BufferedInputFile(pdf_bytes, filename=fname),
            caption=f"📊 <b>SpendUZ Pro hisoboti</b>\n{datetime.now().strftime('%B %Y')}",
            parse_mode="HTML"
        )
    else:
        await msg.answer("😕 PDF yaratishda xato.")

# ADMIN commands
@dp.message(Command("givepremium"))
async def cmd_give_premium(msg: Message):
    uid = msg.from_user.id
    if not is_admin(uid):
        await msg.answer("❌ Ruxsat yo'q!"); return
    args = (msg.text or "").split()
    if len(args) < 3:
        await msg.answer("Format: /givepremium <user_id> <kunlar>"); return
    try:
        target_uid = int(args[1])
        days       = int(args[2])
    except:
        await msg.answer("❌ Noto'g'ri format!"); return
    set_premium(target_uid, days)
    await msg.answer(f"✅ <b>Premium berildi!</b>\n👤 <code>{target_uid}</code>\n📅 {days} kun", parse_mode="HTML")
    try:
        await bot.send_message(target_uid,
            f"🎉 <b>Sizga {days} kun Premium berildi!</b>\n\nBarcha funksiyalardan foydalaning! 💎",
            parse_mode="HTML")
    except: pass

@dp.message(Command("users"))
async def cmd_users(msg: Message):
    uid = msg.from_user.id
    if not is_admin(uid):
        await msg.answer("❌ Ruxsat yo'q!"); return
    all_u      = all_users()
    prem_count = sum(1 for u in all_u if is_premium(u))
    await msg.answer(
        f"📊 <b>Statistika:</b>\n\n"
        f"👥 Jami: <b>{len(all_u)}</b>\n"
        f"💎 Premium: <b>{prem_count}</b>\n"
        f"🆓 Bepul: <b>{len(all_u)-prem_count}</b>",
        parse_mode="HTML")

@dp.message(Command("broadcast"))
async def cmd_broadcast(msg: Message):
    uid = msg.from_user.id
    if not is_admin(uid):
        await msg.answer("❌ Ruxsat yo'q!"); return
    text = (msg.text or "").split(maxsplit=1)
    if len(text) < 2:
        await msg.answer("Format: /broadcast <xabar>"); return
    sent = 0; failed = 0
    for u in all_users():
        try:
            await bot.send_message(u, text[1], parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)
        except: failed += 1
    await msg.answer(f"✅ Yuborildi: {sent}\n❌ Xato: {failed}")

# VOICE
@dp.message(F.voice)
async def voice_handler(msg: Message):
    uid = msg.from_user.id
    add_user(uid)
    if not is_premium(uid):
        await msg.answer(tx(uid,"need_premium"), parse_mode="HTML", reply_markup=premium_kb(uid))
        return
    wait = await msg.answer(tx(uid,"voice_wait"))
    try:
        f   = await bot.get_file(msg.voice.file_id)
        ogg = str(Path(tempfile.gettempdir()) / f"v_{uid}.ogg")
        await bot.download_file(f.file_path, destination=ogg)
        text = await voice_to_text(ogg)
        for p in [ogg, ogg.replace(".ogg",".wav")]:
            try: Path(p).unlink(missing_ok=True)
            except: pass
        if not text:
            await wait.delete()
            await msg.answer(tx(uid,"voice_fail")); return
        await wait.edit_text(tx(uid,"voice_done",text=text), parse_mode="HTML")
        amount, currency = parse_amount(text)
        if not amount:
            await msg.answer(tx(uid,"voice_fail")); return
        tx_type = detect_type(text)
        await save_and_reply(msg, uid, tx_type, amount, currency, text)
    except Exception as e:
        log.error(f"voice: {e}")
        try: await wait.delete()
        except: pass
        await msg.answer(tx(uid,"voice_fail"))

# TEXT handler
@dp.message(F.text)
async def text_handler(msg: Message):
    uid  = msg.from_user.id
    text = (msg.text or "").strip()
    add_user(uid)
    l    = get_lang(uid)
    t_btn = T.get(l, T["uz"])

    # State machine
    if uid in states:
        st = states[uid]

        if st.get("action") == "edit":
            amount, _ = parse_amount(text)
            if amount:
                t = get_txn(st["tid"], uid)
                if t:
                    update_txn(st["tid"], uid, amount, t["note"], t["category"], t["tx_type"])
                    await msg.answer(tx(uid,"edit_done",amount=fmt(amount)+" so'm"), parse_mode="HTML")
            del states[uid]; return

        if st.get("action") == "goal_add_amount":
            amount, _ = parse_amount(text)
            if amount:
                g = add_to_goal(st["gid"], uid, amount)
                if g:
                    pct = round((g["current"]/g["target"])*100) if g["target"] > 0 else 0
                    if g["current"] >= g["target"]:
                        await msg.answer(tx(uid,"goal_done",name=g["name"]), parse_mode="HTML")
                    else:
                        await msg.answer(tx(uid,"goal_added_amount",
                            amount=fmt(amount)+" so'm",name=g["name"],
                            current=fmt(g["current"]),target=fmt(g["target"]),pct=pct), parse_mode="HTML")
            del states[uid]; return

        if st.get("action") == "goal_edit":
            parts = text.split("|")
            if len(parts) >= 2:
                new_name = parts[0].strip()
                amount, _ = parse_amount(parts[1])
                if new_name and amount:
                    update_goal(st["gid"], uid, new_name, amount, "")
                    await msg.answer(f"✅ Yangilandi: {new_name} — {fmt(amount)} so'm", parse_mode="HTML")
            del states[uid]; return

        if st.get("action") == "card_add_name":
            states[uid] = {"action": "card_add_number", "card_name": text}
            await msg.answer(tx(uid,"card_add_step2"), parse_mode="HTML"); return

        if st.get("action") == "card_add_number":
            digits = re.findall(r"\d+", text)
            if not digits or len("".join(digits)) < 4:
                await msg.answer(tx(uid,"enter_4digits"), parse_mode="HTML"); return
            last4 = "".join(digits)[-4:]
            card_name = st.get("card_name","Mening kartam")
            add_card(uid, card_name, last4)
            await msg.answer(tx(uid,"card_added",name=card_name,last4=last4), parse_mode="HTML")
            del states[uid]
            await msg.answer("💳", reply_markup=cards_kb(uid)); return

    # Menu buttons
    if text == t_btn.get("btn_report"):
        await cmd_report(msg); return
    if text == t_btn.get("btn_pdf"):
        await cmd_report_pdf(msg); return
    if text == t_btn.get("btn_goals"):
        await cmd_goals(msg); return
    if text == t_btn.get("btn_cards"):
        await cmd_cards(msg); return
    if text == t_btn.get("btn_premium"):
        await cmd_premium(msg); return
    if text == t_btn.get("btn_ref"):
        await cmd_ref(msg); return
    if text == t_btn.get("btn_rate"):
        await cmd_rate(msg); return
    if text == t_btn.get("btn_settings"):
        await cmd_settings(msg); return

    # Check other languages buttons too
    for lang_code in ["uz","ru","en","tj"]:
        lb = T.get(lang_code, T["uz"])
        if text == lb.get("btn_report"):   await cmd_report(msg); return
        if text == lb.get("btn_pdf"):      await cmd_report_pdf(msg); return
        if text == lb.get("btn_goals"):    await cmd_goals(msg); return
        if text == lb.get("btn_cards"):    await cmd_cards(msg); return
        if text == lb.get("btn_premium"):  await cmd_premium(msg); return
        if text == lb.get("btn_ref"):      await cmd_ref(msg); return
        if text == lb.get("btn_rate"):     await cmd_rate(msg); return
        if text == lb.get("btn_settings"): await cmd_settings(msg); return

    if text.startswith("/"): return

    # Parse transaction
    amount, currency = parse_amount(text)
    if not amount:
        await msg.answer(tx(uid,"unknown"), parse_mode="HTML"); return
    tx_type = detect_type(text)
    await save_and_reply(msg, uid, tx_type, amount, currency, text)

# ── SCHEDULED TASKS ────────────────────────────────────────────────────────────
async def smart_reminder():
    """Bugun yozmagan, kecha yozgan userlarga 21:00 da eslatma"""
    while True:
        now = datetime.now()
        if now.hour == 21 and now.minute == 0:
            for uid in all_users():
                if not has_txn_today(uid) and had_txn_yesterday(uid):
                    try:
                        await bot.send_message(uid, tx(uid,"reminder"), parse_mode="HTML")
                    except: pass
            await asyncio.sleep(61)
        await asyncio.sleep(20)

async def daily_rate_task():
    """Har kuni ertalab 09:00 da valyuta kursi"""
    while True:
        now = datetime.now()
        if now.hour == 9 and now.minute == 0:
            rates = await fetch_rates()
            if rates:
                for uid in all_users():
                    try:
                        await bot.send_message(uid, tx(uid,"daily_rate",rates=format_rates(rates)),
                            parse_mode="HTML")
                    except: pass
            await asyncio.sleep(61)
        await asyncio.sleep(20)

async def weekly_ref_reminder():
    """Har hafta shanba 12:00 da referal eslatma (faqat bepul userlarga)"""
    while True:
        now = datetime.now()
        if now.weekday() == 5 and now.hour == 12 and now.minute == 0:
            for uid in all_users():
                if is_premium(uid): continue
                code = get_referral_code(uid)
                if not code: continue
                l    = get_lang(uid)
                text = T.get(l,T["uz"])["ref_ad"].replace("{code}", code)
                ref_link  = f"https://t.me/Spend_uz_bot?start={code}"
                share_url = f"https://t.me/share/url?url={ref_link}&text=SpendUZ+Pro!"
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=T.get(l,T["uz"])["ref_share_btn"], url=share_url)]
                ])
                try:
                    await bot.send_message(uid, text, parse_mode="HTML", reply_markup=kb)
                except: pass
            await asyncio.sleep(61)
        await asyncio.sleep(20)

async def premium_ad_task():
    """Har 10 kunda bir marta Premium reklama (faqat bepul userlarga)"""
    last_sent: dict[int, datetime] = {}
    while True:
        now = datetime.now()
        if now.hour == 18 and now.minute == 0:
            for uid in all_users():
                if is_premium(uid): continue
                last = last_sent.get(uid)
                if last and (now - last).days < 10: continue
                l    = get_lang(uid)
                try:
                    await bot.send_message(uid, T.get(l,T["uz"])["premium_txt"],
                        parse_mode="HTML", reply_markup=premium_kb(uid))
                    last_sent[uid] = now
                except: pass
            await asyncio.sleep(61)
        await asyncio.sleep(20)

# ── MAIN ───────────────────────────────────────────────────────────────────────
async def main():
    init_db()
    log.info("✅ Database initialized")
    log.info(f"🎤 Voice: {'ON' if VOICE_OK else 'OFF'}")
    log.info(f"🌐 HTTP:  {'ON' if HTTP_OK  else 'OFF'}")
    log.info("🚀 SpendUZ Bot started!")

    asyncio.create_task(smart_reminder())
    asyncio.create_task(daily_rate_task())
    asyncio.create_task(weekly_ref_reminder())
    asyncio.create_task(premium_ad_task())

    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())