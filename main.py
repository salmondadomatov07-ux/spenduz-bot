"""
SpendUZ Pro — main.py
@Spend_uz_bot — To'liq bot
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
    get_summary, get_cat_breakdown, has_txn_today,
    add_goal, get_goals, add_to_goal, delete_goal,
    create_group, join_group, get_group_members, get_user_group,
    is_premium, set_premium, get_referral_code, use_referral,
    add_card, get_cards, delete_card,
)

# ── Optional deps ──────────────────────────────────────────────────────────────
try:
    import speech_recognition as sr
    from pydub import AudioSegment
    VOICE_OK = True
except ImportError:
    VOICE_OK = False

try:
    import aiohttp
    HTTP_OK = True
except ImportError:
    HTTP_OK = False

# ── Config ─────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger(__name__)

BOT_TOKEN   = os.getenv("BOT_TOKEN",   "8651989569:AAEGRKv4os3HFolPrw6kRvinjMGT7e6BGuI")
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://salmondadomatov07-ux.github.io/spend-app/")
  # Telegram Stars uchun bo'sh

PREMIUM_STARS  = 85   # 85 Stars = 1 oy Premium
PREMIUM_DAYS   = 30


# ── ADMIN ──────────────────────────────────────────────────────────────────────
ADMIN_IDS = [8651989569, 5522700870]  # Admin IDlar

def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher()

# Edit state
states: dict[int, dict] = {}

# ── Translations ───────────────────────────────────────────────────────────────
T = {
"uz": {
    "start": (
        "👋 <b>Assalomu alaykum!</b>\n\n"
        "💸 <b>SpendUZ Pro</b> — moliyaviy yordamchingiz!\n\n"
        "Tilni tanlang:"
    ),
    "lang_saved": (
        "✅ Til saqlandi!\n\n"
        "📱 <b>SpendUZ Pro</b> ilovasini oching va xarajatlaringizni boshqaring!"
    ),
    "help": (
        "📝 <b>Qanday yozish:</b>\n\n"
        "💸 Xarajat: <code>20000 ovqat</code>\n"
        "💰 Daromad: <code>3mln oylik</code>\n"
        "💸 Qarz berdim: <code>qarz 50000 Ali</code>\n"
        "💰 Qarz oldim: <code>oldim 100000 Doniyor</code>\n\n"
        "🎤 Yoki ovoz yuboring!\n"
        "📸 Chek rasmini yuboring!"
    ),
    "open_app":   "🚀 SpendUZ Pro ni ochish",
    "saved_exp":  "✅ <b>Xarajat saqlandi!</b>\n\n💸 {amount} {cur}\n📝 {note}\n🏷 {cat}",
    "saved_inc":  "✅ <b>Daromad saqlandi!</b>\n\n💰 {amount} {cur}\n📝 {note}\n🏷 {cat}",
    "saved_dg":   "✅ <b>Qarz berdim!</b>\n\n💸 {amount} {cur}\n👤 Kimga: {note}",
    "saved_dt":   "✅ <b>Qarz oldim!</b>\n\n💰 {amount} {cur}\n👤 Kimdan: {note}",
    "edit_btn":   "✏️ Tahrirlash",
    "del_btn":    "🗑 O'chirish",
    "deleted":    "🗑 O'chirildi!",
    "edit_ask":   "✏️ Yangi summani yozing:\nMasalan: <code>25000</code>",
    "edit_done":  "✅ Yangilandi! Yangi summa: <b>{amount} so'm</b>",
    "report": (
        "📊 <b>{month} hisoboti:</b>\n\n"
        "⬆️ Daromad:     <b>{income}</b>\n"
        "⬇️ Xarajat:     <b>{expense}</b>\n"
        "💸 Qarz berdim: <b>{dg}</b>\n"
        "💰 Qarz oldim:  <b>{dt}</b>\n"
        "━━━━━━━━━━━\n"
        "📈 Balans: <b>{balance}</b>"
    ),
    "history":    "📋 <b>So'nggi {n} ta tranzaksiya:</b>\n\n{rows}",
    "no_txn":     "📭 Hali tranzaksiya yo'q.",
    "weekly": (
        "📊 <b>Haftalik hisobot:</b>\n\n"
        "⬆️ Daromad: <b>{inc}</b>\n"
        "⬇️ Xarajat: <b>{exp}</b>\n"
        "📈 Balans:  <b>{bal}</b>"
    ),
    "reminder":   "⏰ Bugun xarajat yozmadingiz! Hozir yozing 💸",
    "voice_wait": "🎤 Ovoz tahlil qilinmoqda...",
    "voice_done": "🎤 Eshitildi: <i>«{text}»</i>",
    "voice_fail": "😕 Ovozni tushunmadim. Qayta yuboring.",
    "voice_off":  "🎤 Voice hozir ishlamayapti.",
    "rate_title": "💱 <b>Bugungi kurs (CBU):</b>\n",
    "rate_fail":  "😕 Kursni yuklab bo'lmadi.",
    "unknown":    "🤔 Tushunmadim.\n\n<b>Misol:</b> <code>20000 ovqat</code>\n🎤 Yoki ovoz yuboring",
    "goals_empty":"🎯 Hali maqsad yo'q.\n\n<code>/addgoal MacBook 10000000</code>",
    "goal_added": "🎯 <b>Maqsad qo'shildi!</b>\n\n📌 {name}\n💰 {target} so'm",
    "goal_fmt":   "Format: <code>/addgoal MacBook 10000000</code>",
    "goal_list":  "🎯 <b>Maqsadlaringiz:</b>\n\n{items}",
    "goal_item":  "• <b>{name}</b>\n  {cur} / {tgt} ({pct}%)\n  {bar}",
    "motivation": "🏆 <b>«{name}»</b> maqsadingiz <b>{pct}%</b> bajarildi! 💪",
    "goal_done":  "🎉 <b>«{name}»</b> maqsadiga yetdingiz! Tabriklaymiz! 🎊",
    "group_made": "👥 <b>Guruh yaratildi!</b>\n\nID: <code>{gid}</code>\nBoshqalar: <code>/join {gid}</code>",
    "group_joined":"👥 Guruhga qo'shildingiz!",
    "group_nf":   "❌ Guruh topilmadi.",
    "group_rep":  "👥 <b>Guruh hisoboti:</b>\n\n{rows}",
    "no_group":   "❌ Guruhga a'zo emassiz.\n/group bilan yarating.",
    "card_added": "💳 Karta saqlandi!\n\n**** **** **** {last4}",
    "card_list":  "💳 <b>Kartalaringiz:</b>\n\n{items}",
    "no_cards":   "💳 Hali karta qo'shilmagan.\n\n<code>/cards qoshish 1234</code>",
    "card_fmt":   "Format: <code>/cards qoshish 1234</code>",
    "card_del":   "💳 Karta o'chirildi.",
    "card_16":    "❌ Faqat 16 xonali karta raqami kiriting!",
    "premium_txt":(
        "╔══════════════════════╗\n"
        "║   💎 SpendUZ Premium   ║\n"
        "╚══════════════════════╝\n\n"
        "🚀 <b>Moliyangizni PRO darajada boshqaring!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "✨ <b>PREMIUM IMKONIYATLAR</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎯 Cheksiz maqsadlar\n"
        "👥 Guruh byudjeti\n"
        "📥 PDF hisobot yuklash\n"
        "💱 Barcha valyutalar\n"
        "💳 Karta saqlash\n"
        "📊 Haftalik hisobot\n"
        "🔍 Kategoriya tahlili\n"
        "🎤 Voice (ovoz bilan yozish)\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💰 Narxi: <b>85 ⭐ Stars / oy</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎁 <b>Bepul olish:</b> Do'stingizni taklif qiling → 3 kun bepul! /ref"
    ),
    "premium_btn": "⭐ 85 Stars bilan obuna",
    "premium_ok":  "🎉 Premium faollashtirildi! 30 kun davomida barcha funksiyalar mavjud.",
    "premium_already": "💎 Siz allaqachon Premium foydalanuvchisiz!",
    "ref_info": (
        "🎁 <b>Do'stingizni taklif qiling!</b>\n\n"
        "Har bir do'stingiz uchun:\n"
        "→ Siz <b>3 kun bepul Premium</b> olasiz!\n"
        "→ Do'stingiz ham <b>1 kun bepul Premium</b> oladi!\n\n"
        "Sizning referal havolangiz:\n"
        "<code>https://t.me/Spend_uz_bot?start={code}</code>\n\n"
        "👥 Taklif qilinganlar: <b>{count}</b> ta"
    ),
    "ref_thanks": "🎁 Do'stingiz taklifi orqali kelganligi uchun 1 kun bepul Premium oldiniz!",
    "ref_bonus":  "🎉 Do'stingiz qo'shildi! Siz 3 kun bepul Premium oldingiz!",
    "share_txt": (
        "💸 <b>SpendUZ Pro</b> — eng yaxshi moliya treker!\n\n"
        "✅ Daromad va xarajatlarni kuzating\n"
        "✅ Maqsadlar qo'ying\n"
        "✅ AI tahlil\n\n"
        "🚀 Boshlash: t.me/Spend_uz_bot"
    ),
    "settings_txt": (
        "⚙️ <b>Sozlamalar:</b>\n\n"
        "🌍 Til: {lang}\n"
        "💎 Premium: {premium}\n"
        "📊 Tranzaksiyalar: {txn_count} ta\n"
        "🎯 Maqsadlar: {goal_count} ta"
    ),
    "currency_rates": "💱 <b>Valyuta kurslari (CBU):</b>\n\n{rates}",
    "btn_report":  "📊 Hisobot",
    "btn_history": "📋 Tarix",
    "btn_goals":   "🎯 Maqsadlar",
    "btn_group":   "👥 Guruh",
    "btn_premium": "💎 Premium",
    "btn_share":   "🔗 Ulashish",
    "btn_ref":     "🎁 Taklif",
    "btn_lang":    "🌍 Til",
    "btn_back":    "⬅️ Orqaga",
    "need_premium_voice":  "🎤 <b>Voice — Premium funksiya!</b>\n\n🎤 Ovoz bilan yozish faqat Premium foydalanuvchilar uchun.\n\n🎁 <b>Bepul olish:</b> Do'stingizni taklif qiling → 3 kun bepul Premium!\n\n/ref — Referal havola olish\n/premium — Premium olish",
    "need_premium_goals":  "🎯 <b>Maqsad limiti: 3 ta!</b>\n\nBepul foydalanuvchilar uchun maksimal 3 ta maqsad.\n\n💎 Cheksiz maqsadlar uchun Premium oling!\n\n🎁 <b>Bepul olish:</b> /ref — do'st taklif qiling!\n/premium — Premium olish",
    "need_premium_group":  "👥 <b>Guruh byudjeti — Premium!</b>\n\nGuruh funksiyasi faqat Premium foydalanuvchilar uchun.\n\n🎁 <b>Bepul olish:</b> /ref — do'st taklif qiling!\n/premium — Premium olish",
    "need_premium_cards":  "💳 <b>Karta saqlash — Premium!</b>\n\nKarta saqlash faqat Premium foydalanuvchilar uchun.\n\n🎁 <b>Bepul olish:</b> /ref — do'st taklif qiling!\n/premium — Premium olish",
    "need_premium_pdf":    "📥 <b>PDF yuklash — Premium!</b>\n\nHisobot yuklash faqat Premium foydalanuvchilar uchun.\n\n🎁 <b>Bepul olish:</b> /ref — do'st taklif qiling!\n/premium — Premium olish",
    "ref_ad": (
        "🎁 <b>Do'stingizni taklif qiling!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👥 Har bir do'st uchun:\n"
        "→ <b>Siz 3 kun bepul Premium!</b>\n"
        "→ <b>Do'stingiz 1 kun bepul Premium!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔥 5 do'st = 15 kun bepul Premium!\n"
        "🔥 10 do'st = 1 oy bepul Premium!\n\n"
        "👇 Havolangiz:\n"
        "<code>https://t.me/Spend_uz_bot?start={code}</code>"
    ),
    "ref_ad_btn": "🔗 Do'stlarga ulashish",
},
"ru": {
    "start": (
        "👋 <b>Привет!</b>\n\n"
        "💸 <b>SpendUZ Pro</b> — ваш финансовый помощник!\n\n"
        "Выберите язык:"
    ),
    "lang_saved": (
        "✅ Язык сохранён!\n\n"
        "📱 Откройте <b>SpendUZ Pro</b> и управляйте финансами!"
    ),
    "help": (
        "📝 <b>Как писать:</b>\n\n"
        "💸 Расход: <code>20000 еда</code>\n"
        "💰 Доход: <code>3млн зарплата</code>\n"
        "💸 Дал в долг: <code>долг 50000 Али</code>\n"
        "💰 Взял в долг: <code>взял 100000 Дониёр</code>\n\n"
        "🎤 Или голосовое!\n"
        "📸 Фото чека!"
    ),
    "open_app":   "🚀 Открыть SpendUZ Pro",
    "saved_exp":  "✅ <b>Расход сохранён!</b>\n\n💸 {amount} {cur}\n📝 {note}\n🏷 {cat}",
    "saved_inc":  "✅ <b>Доход сохранён!</b>\n\n💰 {amount} {cur}\n📝 {note}\n🏷 {cat}",
    "saved_dg":   "✅ <b>Дал в долг!</b>\n\n💸 {amount} {cur}\n👤 Кому: {note}",
    "saved_dt":   "✅ <b>Взял в долг!</b>\n\n💰 {amount} {cur}\n👤 От кого: {note}",
    "edit_btn":   "✏️ Изменить",
    "del_btn":    "🗑 Удалить",
    "deleted":    "🗑 Удалено!",
    "edit_ask":   "✏️ Введите новую сумму:\nНапример: <code>25000</code>",
    "edit_done":  "✅ Обновлено! Новая сумма: <b>{amount}</b>",
    "report": (
        "📊 <b>Отчёт {month}:</b>\n\n"
        "⬆️ Доход:       <b>{income}</b>\n"
        "⬇️ Расход:      <b>{expense}</b>\n"
        "💸 Дал в долг:  <b>{dg}</b>\n"
        "💰 Взял в долг: <b>{dt}</b>\n"
        "━━━━━━━━━━━\n"
        "📈 Баланс: <b>{balance}</b>"
    ),
    "history":    "📋 <b>Последние {n} транзакций:</b>\n\n{rows}",
    "no_txn":     "📭 Транзакций пока нет.",
    "weekly": (
        "📊 <b>Недельный отчёт:</b>\n\n"
        "⬆️ Доход:  <b>{inc}</b>\n"
        "⬇️ Расход: <b>{exp}</b>\n"
        "📈 Баланс: <b>{bal}</b>"
    ),
    "reminder":   "⏰ Сегодня не записали расходы! Запишите сейчас 💸",
    "voice_wait": "🎤 Анализирую голос...",
    "voice_done": "🎤 Услышал: <i>«{text}»</i>",
    "voice_fail": "😕 Не понял голос. Попробуйте ещё раз.",
    "voice_off":  "🎤 Голос недоступен.",
    "rate_title": "💱 <b>Курс валют (ЦБУ):</b>\n",
    "rate_fail":  "😕 Не удалось загрузить курс.",
    "unknown":    "🤔 Не понял.\n\n<b>Пример:</b> <code>20000 еда</code>\n🎤 Или голосовое",
    "goals_empty":"🎯 Целей пока нет.\n\n<code>/addgoal MacBook 10000000</code>",
    "goal_added": "🎯 <b>Цель добавлена!</b>\n\n📌 {name}\n💰 {target}",
    "goal_fmt":   "Формат: <code>/addgoal MacBook 10000000</code>",
    "goal_list":  "🎯 <b>Ваши цели:</b>\n\n{items}",
    "goal_item":  "• <b>{name}</b>\n  {cur} / {tgt} ({pct}%)\n  {bar}",
    "motivation": "🏆 Цель <b>«{name}»</b> выполнена на <b>{pct}%</b>! 💪",
    "goal_done":  "🎉 Цель <b>«{name}»</b> достигнута! Поздравляем! 🎊",
    "group_made": "👥 <b>Группа создана!</b>\n\nID: <code>{gid}</code>\nПрисоединиться: <code>/join {gid}</code>",
    "group_joined":"👥 Вы присоединились к группе!",
    "group_nf":   "❌ Группа не найдена.",
    "group_rep":  "👥 <b>Отчёт группы:</b>\n\n{rows}",
    "no_group":   "❌ Не в группе.\n/group чтобы создать.",
    "card_added": "💳 Карта сохранена!\n\n**** **** **** {last4}",
    "card_list":  "💳 <b>Ваши карты:</b>\n\n{items}",
    "no_cards":   "💳 Карт пока нет.\n\n<code>/cards добавить 1234</code>",
    "card_fmt":   "Формат: <code>/cards добавить 1234</code>",
    "card_del":   "💳 Карта удалена.",
    "card_16":    "❌ Введите только 16 цифр номера карты!",
    "premium_txt":(
        "💎 <b>SpendUZ Premium</b>\n\n"
        "✅ Безлимитные цели\n"
        "✅ Групповой бюджет\n"
        "✅ PDF отчёты\n"
        "✅ Все валюты\n"
        "✅ Сохранение карт\n"
        "✅ Еженедельные отчёты\n"
        "✅ Анализ категорий\n\n"
        "💰 Цена: <b>85 Stars / мес</b>\n\n"
        "Нажмите для подписки!"
    ),
    "premium_btn":  "⭐ Подписаться за 85 Stars",
    "premium_ok":   "🎉 Premium активирован! 30 дней доступны все функции.",
    "premium_already": "💎 Вы уже Premium пользователь!",
    "ref_info": (
        "🎁 <b>Пригласите друзей!</b>\n\n"
        "За каждого друга:\n"
        "→ Вы получаете <b>3 дня Premium</b>!\n"
        "→ Друг получает <b>1 день Premium</b>!\n\n"
        "Ваша реферальная ссылка:\n"
        "<code>https://t.me/Spend_uz_bot?start={code}</code>\n\n"
        "👥 Приглашено: <b>{count}</b>"
    ),
    "ref_thanks": "🎁 Вы получили 1 день Premium за приглашение друга!",
    "ref_bonus":  "🎉 Друг присоединился! Вы получили 3 дня Premium!",
    "share_txt": (
        "💸 <b>SpendUZ Pro</b> — лучший финансовый трекер!\n\n"
        "✅ Доходы и расходы\n"
        "✅ Цели и бюджет\n"
        "✅ AI анализ\n\n"
        "🚀 Начать: t.me/Spend_uz_bot"
    ),
    "settings_txt": (
        "⚙️ <b>Настройки:</b>\n\n"
        "🌍 Язык: {lang}\n"
        "💎 Premium: {premium}\n"
        "📊 Транзакций: {txn_count}\n"
        "🎯 Целей: {goal_count}"
    ),
    "currency_rates": "💱 <b>Курсы валют (ЦБУ):</b>\n\n{rates}",
    "btn_report":  "📊 Отчёт",
    "btn_history": "📋 История",
    "btn_goals":   "🎯 Цели",
    "btn_group":   "👥 Группа",
    "btn_premium": "💎 Premium",
    "btn_share":   "🔗 Поделиться",
    "btn_ref":     "🎁 Реферал",
    "btn_lang":    "🌍 Язык",
    "btn_back":    "⬅️ Назад",
    "need_premium_voice":  "🎤 <b>Голос — Premium!</b>\n\nГолосовой ввод только для Premium пользователей.\n\n🎁 <b>Бесплатно:</b> Пригласите друга → 3 дня Premium!\n\n/ref — Реферальная ссылка\n/premium — Получить Premium",
    "need_premium_goals":  "🎯 <b>Лимит целей: 3!</b>\n\nДля безлимитных целей нужен Premium.\n\n🎁 <b>Бесплатно:</b> /ref — пригласите друга!\n/premium — Получить Premium",
    "need_premium_group":  "👥 <b>Группа — Premium!</b>\n\nГрупповой бюджет только для Premium.\n\n🎁 <b>Бесплатно:</b> /ref — пригласите друга!\n/premium — Получить Premium",
    "need_premium_cards":  "💳 <b>Карты — Premium!</b>\n\nСохранение карт только для Premium.\n\n🎁 <b>Бесплатно:</b> /ref — пригласите друга!\n/premium — Получить Premium",
    "need_premium_pdf":    "📥 <b>PDF — Premium!</b>\n\nСкачивание отчётов только для Premium.\n\n🎁 <b>Бесплатно:</b> /ref — пригласите друга!\n/premium — Получить Premium",
    "ref_ad": (
        "🎁 <b>Пригласите друзей!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👥 За каждого друга:\n"
        "→ <b>Вам 3 дня бесплатного Premium!</b>\n"
        "→ <b>Другу 1 день бесплатного Premium!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔥 5 друзей = 15 дней Premium!\n"
        "🔥 10 друзей = 1 месяц Premium!\n\n"
        "👇 Ваша ссылка:\n"
        "<code>https://t.me/Spend_uz_bot?start={code}</code>"
    ),
    "ref_ad_btn": "🔗 Поделиться с друзьями",
},
"en": {
    "start": (
        "👋 <b>Hello!</b>\n\n"
        "💸 <b>SpendUZ Pro</b> — your financial assistant!\n\n"
        "Choose language:"
    ),
    "lang_saved": (
        "✅ Language saved!\n\n"
        "📱 Open <b>SpendUZ Pro</b> and manage your finances!"
    ),
    "help": (
        "📝 <b>How to write:</b>\n\n"
        "💸 Expense: <code>20000 food</code>\n"
        "💰 Income: <code>3mln salary</code>\n"
        "💸 Lent: <code>lent 50000 Ali</code>\n"
        "💰 Borrowed: <code>borrowed 100000 Doniyor</code>\n\n"
        "🎤 Or send voice!\n"
        "📸 Send receipt photo!"
    ),
    "open_app":   "🚀 Open SpendUZ Pro",
    "saved_exp":  "✅ <b>Expense saved!</b>\n\n💸 {amount} {cur}\n📝 {note}\n🏷 {cat}",
    "saved_inc":  "✅ <b>Income saved!</b>\n\n💰 {amount} {cur}\n📝 {note}\n🏷 {cat}",
    "saved_dg":   "✅ <b>Lent money!</b>\n\n💸 {amount} {cur}\n👤 To: {note}",
    "saved_dt":   "✅ <b>Borrowed money!</b>\n\n💰 {amount} {cur}\n👤 From: {note}",
    "edit_btn":   "✏️ Edit",
    "del_btn":    "🗑 Delete",
    "deleted":    "🗑 Deleted!",
    "edit_ask":   "✏️ Enter new amount:\nExample: <code>25000</code>",
    "edit_done":  "✅ Updated! New amount: <b>{amount}</b>",
    "report": (
        "📊 <b>Report {month}:</b>\n\n"
        "⬆️ Income:   <b>{income}</b>\n"
        "⬇️ Expense:  <b>{expense}</b>\n"
        "💸 Lent:     <b>{dg}</b>\n"
        "💰 Borrowed: <b>{dt}</b>\n"
        "━━━━━━━━━━━\n"
        "📈 Balance: <b>{balance}</b>"
    ),
    "history":    "📋 <b>Last {n} transactions:</b>\n\n{rows}",
    "no_txn":     "📭 No transactions yet.",
    "weekly": (
        "📊 <b>Weekly report:</b>\n\n"
        "⬆️ Income:  <b>{inc}</b>\n"
        "⬇️ Expense: <b>{exp}</b>\n"
        "📈 Balance: <b>{bal}</b>"
    ),
    "reminder":   "⏰ You didn't log expenses today! Log them now 💸",
    "voice_wait": "🎤 Analyzing voice...",
    "voice_done": "🎤 Heard: <i>«{text}»</i>",
    "voice_fail": "😕 Could not understand. Try again.",
    "voice_off":  "🎤 Voice unavailable.",
    "rate_title": "💱 <b>Exchange rates (CBU):</b>\n",
    "rate_fail":  "😕 Could not load rates.",
    "unknown":    "🤔 Did not understand.\n\n<b>Example:</b> <code>20000 food</code>\n🎤 Or send voice",
    "goals_empty":"🎯 No goals yet.\n\n<code>/addgoal MacBook 10000000</code>",
    "goal_added": "🎯 <b>Goal added!</b>\n\n📌 {name}\n💰 {target}",
    "goal_fmt":   "Format: <code>/addgoal MacBook 10000000</code>",
    "goal_list":  "🎯 <b>Your goals:</b>\n\n{items}",
    "goal_item":  "• <b>{name}</b>\n  {cur} / {tgt} ({pct}%)\n  {bar}",
    "motivation": "🏆 Goal <b>«{name}»</b> is <b>{pct}%</b> done! 💪",
    "goal_done":  "🎉 Goal <b>«{name}»</b> achieved! Congratulations! 🎊",
    "group_made": "👥 <b>Group created!</b>\n\nID: <code>{gid}</code>\nJoin: <code>/join {gid}</code>",
    "group_joined":"👥 Joined the group!",
    "group_nf":   "❌ Group not found.",
    "group_rep":  "👥 <b>Group report:</b>\n\n{rows}",
    "no_group":   "❌ Not in a group.\n/group to create.",
    "card_added": "💳 Card saved!\n\n**** **** **** {last4}",
    "card_list":  "💳 <b>Your cards:</b>\n\n{items}",
    "no_cards":   "💳 No cards yet.\n\n<code>/cards add 1234</code>",
    "card_fmt":   "Format: <code>/cards add 1234</code>",
    "card_del":   "💳 Card deleted.",
    "card_16":    "❌ Enter only the last 4 digits of your card!",
    "premium_txt":(
        "💎 <b>SpendUZ Premium</b>\n\n"
        "✅ Unlimited goals\n"
        "✅ Group budget\n"
        "✅ PDF reports\n"
        "✅ All currencies\n"
        "✅ Card storage\n"
        "✅ Weekly reports\n"
        "✅ Category analysis\n\n"
        "💰 Price: <b>85 Stars / month</b>\n\n"
        "Click to subscribe!"
    ),
    "premium_btn":  "⭐ Subscribe for 85 Stars",
    "premium_ok":   "🎉 Premium activated! All features available for 30 days.",
    "premium_already": "💎 You are already a Premium user!",
    "ref_info": (
        "🎁 <b>Invite your friends!</b>\n\n"
        "For each friend:\n"
        "→ You get <b>3 days free Premium</b>!\n"
        "→ Friend gets <b>1 day free Premium</b>!\n\n"
        "Your referral link:\n"
        "<code>https://t.me/Spend_uz_bot?start={code}</code>\n\n"
        "👥 Invited: <b>{count}</b>"
    ),
    "ref_thanks": "🎁 You got 1 day free Premium for joining via referral!",
    "ref_bonus":  "🎉 Friend joined! You got 3 days free Premium!",
    "share_txt": (
        "💸 <b>SpendUZ Pro</b> — best finance tracker!\n\n"
        "✅ Track income & expenses\n"
        "✅ Set goals\n"
        "✅ AI analysis\n\n"
        "🚀 Start: t.me/Spend_uz_bot"
    ),
    "settings_txt": (
        "⚙️ <b>Settings:</b>\n\n"
        "🌍 Language: {lang}\n"
        "💎 Premium: {premium}\n"
        "📊 Transactions: {txn_count}\n"
        "🎯 Goals: {goal_count}"
    ),
    "currency_rates": "💱 <b>Exchange rates (CBU):</b>\n\n{rates}",
    "btn_report":  "📊 Report",
    "btn_history": "📋 History",
    "btn_goals":   "🎯 Goals",
    "btn_group":   "👥 Group",
    "btn_premium": "💎 Premium",
    "btn_share":   "🔗 Share",
    "btn_ref":     "🎁 Referral",
    "btn_lang":    "🌍 Language",
    "btn_back":    "⬅️ Back",
    "need_premium_voice":  "🎤 <b>Voice — Premium!</b>\n\nVoice input is for Premium users only.\n\n🎁 <b>Get free:</b> Invite a friend → 3 days Premium!\n\n/ref — Get referral link\n/premium — Get Premium",
    "need_premium_goals":  "🎯 <b>Goal limit: 3!</b>\n\nUnlimited goals require Premium.\n\n🎁 <b>Get free:</b> /ref — invite a friend!\n/premium — Get Premium",
    "need_premium_group":  "👥 <b>Group — Premium!</b>\n\nGroup budget is for Premium users only.\n\n🎁 <b>Get free:</b> /ref — invite a friend!\n/premium — Get Premium",
    "need_premium_cards":  "💳 <b>Cards — Premium!</b>\n\nCard storage is for Premium users only.\n\n🎁 <b>Get free:</b> /ref — invite a friend!\n/premium — Get Premium",
    "need_premium_pdf":    "📥 <b>PDF — Premium!</b>\n\nReport download is for Premium users only.\n\n🎁 <b>Get free:</b> /ref — invite a friend!\n/premium — Get Premium",
    "ref_ad": (
        "🎁 <b>Invite your friends!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👥 For each friend:\n"
        "→ <b>You get 3 days free Premium!</b>\n"
        "→ <b>Friend gets 1 day free Premium!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔥 5 friends = 15 days Premium!\n"
        "🔥 10 friends = 1 month Premium!\n\n"
        "👇 Your link:\n"
        "<code>https://t.me/Spend_uz_bot?start={code}</code>"
    ),
    "ref_ad_btn": "🔗 Share with friends",
},
"tj": {
    "start": "👋 <b>Салом!</b>\n\nЗабонро интихоб кунед:",
    "lang_saved": "✅ Забон сабт шуд!\n\n📱 SpendUZ Pro-ро кушоед!",
    "help": "📝 <b>Чӣ тавр навиштан:</b>\n\n💸 Хароҷот: <code>20000 хурок</code>\n💰 Даромад: <code>3млн маош</code>",
    "open_app":   "🚀 Кушодани SpendUZ Pro",
    "saved_exp":  "✅ <b>Хароҷот сабт шуд!</b>\n\n💸 {amount} {cur}\n📝 {note}\n🏷 {cat}",
    "saved_inc":  "✅ <b>Даромад сабт шуд!</b>\n\n💰 {amount} {cur}\n📝 {note}\n🏷 {cat}",
    "saved_dg":   "✅ <b>Қарз додам!</b>\n\n💸 {amount} {cur}\n👤 Ба кӣ: {note}",
    "saved_dt":   "✅ <b>Қарз гирифтам!</b>\n\n💰 {amount} {cur}\n👤 Аз кӣ: {note}",
    "edit_btn":   "✏️ Таҳрир",
    "del_btn":    "🗑 Нест",
    "deleted":    "🗑 Нест шуд!",
    "edit_ask":   "✏️ Маблағи навро ворид кунед:",
    "edit_done":  "✅ Навсозӣ шуд! Маблағи нав: <b>{amount}</b>",
    "report": "📊 <b>Ҳисоботи {month}:</b>\n\n⬆️ Даромад: <b>{income}</b>\n⬇️ Хароҷот: <b>{expense}</b>\n📈 Баланс: <b>{balance}</b>",
    "history":    "📋 <b>{n} транзаксияи охир:</b>\n\n{rows}",
    "no_txn":     "📭 Транзаксия нест.",
    "weekly":     "📊 <b>Ҳисоботи ҳафтаӣ:</b>\n\n⬆️ {inc}\n⬇️ {exp}\n📈 {bal}",
    "reminder":   "⏰ Имрӯз хароҷотро нанавиштед! 💸",
    "voice_wait": "🎤 Овоз таҳлил мешавад...",
    "voice_done": "🎤 Шунидам: <i>«{text}»</i>",
    "voice_fail": "😕 Нафаҳмидам.",
    "voice_off":  "🎤 Овоз дастрас нест.",
    "rate_title": "💱 <b>Нархи асъор:</b>\n",
    "rate_fail":  "😕 Нарх бор нашуд.",
    "unknown":    "🤔 Нафаҳмидам.\n\n<b>Мисол:</b> <code>20000 хурок</code>",
    "goals_empty":"🎯 Мақсад нест.",
    "goal_added": "🎯 <b>Мақсад илова шуд!</b>\n\n📌 {name}\n💰 {target}",
    "goal_fmt":   "Формат: <code>/addgoal MacBook 10000000</code>",
    "goal_list":  "🎯 <b>Мақсадҳои шумо:</b>\n\n{items}",
    "goal_item":  "• <b>{name}</b>\n  {cur} / {tgt} ({pct}%)\n  {bar}",
    "motivation": "🏆 Мақсади <b>«{name}»</b> {pct}% иҷро шуд! 💪",
    "goal_done":  "🎉 Мақсади <b>«{name}»</b> иҷро шуд! 🎊",
    "group_made": "👥 <b>Гурӯҳ сохта шуд!</b>\n\nID: <code>{gid}</code>",
    "group_joined":"👥 Ба гурӯҳ ҳамроҳ шудед!",
    "group_nf":   "❌ Гурӯҳ ёфт нашуд.",
    "group_rep":  "👥 <b>Ҳисоботи гурӯҳ:</b>\n\n{rows}",
    "no_group":   "❌ Дар гурӯҳ нестед.",
    "card_added": "💳 Корт сабт шуд!\n\n**** **** **** {last4}",
    "card_list":  "💳 <b>Кортҳои шумо:</b>\n\n{items}",
    "no_cards":   "💳 Корт нест.",
    "card_fmt":   "Формат: <code>/cards ilova 1234</code>",
    "card_del":   "💳 Корт нест шуд.",
    "card_16":    "❌ Танҳо 4 рақами охири корт!",
    "premium_txt":"💎 <b>SpendUZ Premium</b>\n\n✅ Мақсадҳои беҳудуд\n✅ Ҳисоботи PDF\n\n💰 Нарх: <b>85 Stars / моҳ</b>",
    "premium_btn":  "⭐ 85 Stars бо обуна",
    "premium_ok":   "🎉 Premium фаъол шуд!",
    "premium_already": "💎 Шумо аллакай Premium!",
    "ref_info": "🎁 <b>Дӯстонро даъват кунед!</b>\n\nКоди шумо:\n<code>https://t.me/Spend_uz_bot?start={code}</code>",
    "ref_thanks": "🎁 1 рӯзи Premium барои шумо!",
    "ref_bonus":  "🎉 Дӯстатон омад! 3 рӯзи Premium!",
    "share_txt": "💸 <b>SpendUZ Pro</b>\n\n🚀 t.me/Spend_uz_bot",
    "settings_txt": "⚙️ <b>Tanzimot:</b>\n\n🌍 Zabon: {lang}\n💎 Premium: {premium}",
    "currency_rates": "💱 <b>Нархи асъор:</b>\n\n{rates}",
    "btn_report":  "📊 Ҳисобот",
    "btn_history": "📋 Таърих",
    "btn_goals":   "🎯 Мақсадҳо",
    "btn_group":   "👥 Гурӯҳ",
    "btn_premium": "💎 Premium",
    "btn_share":   "🔗 Мубодила",
    "btn_ref":     "🎁 Даъват",
    "btn_lang":    "🌍 Забон",
    "btn_back":    "⬅️ Бозгашт",
    "need_premium_voice":  "🎤 <b>Овоз — Premium!</b>\n\n💎 Танҳо 85 Stars/моҳ!\n/premium",
    "need_premium_goals":  "🎯 <b>Лимити 3 мақсад!</b>\n\n💎 Танҳо 85 Stars/моҳ!\n/premium",
    "need_premium_group":  "👥 <b>Гурӯҳ — Premium!</b>\n\n💎 Танҳо 85 Stars/моҳ!\n/premium",
    "need_premium_cards":  "💳 <b>Корт — Premium!</b>\n\n💎 Танҳо 85 Stars/моҳ!\n/premium",
    "need_premium_pdf":    "📥 <b>PDF — Premium!</b>\n\n💎 Танҳо 85 Stars/моҳ!\n/premium",
    "ref_ad": (
        "🎁 <b>Дӯстонро даъват кунед!</b>\n\n"
        "→ <b>Шумо 3 рӯзи Premium!</b>\n"
        "→ <b>Дӯст 1 рӯзи Premium!</b>\n\n"
        "<code>https://t.me/Spend_uz_bot?start={code}</code>"
    ),
    "ref_ad_btn": "🔗 Мубодила",
},
}

def tx(uid, key, **kw):
    lang = get_lang(uid)
    s = T.get(lang, T["uz"]).get(key, T["uz"].get(key, key))
    for k, v in kw.items():
        s = s.replace("{" + k + "}", str(v))
    return s

# ── Category detection ─────────────────────────────────────────────────────────
CAT_LABELS = {
    "uz":  {"c_food":"Oziq-ovqat","c_trans":"Transport","c_home":"Uy-joy","c_health":"Salomatlik",
            "c_cloth":"Kiyim","c_enter":"Konil ochish","c_edu":"Talim","c_cafe":"Kafe",
            "c_tech":"Texnologiya","c_sport":"Sport","c_travel":"Sayohat","c_bills":"Kommunal",
            "c_beauty":"Gozallik","c_gift":"Sovga","c_salary":"Maosh","c_free":"Frilanss",
            "c_biz":"Biznes","c_invest":"Investitsiya","other":"Boshqa"},
    "ru":  {"c_food":"Еда","c_trans":"Транспорт","c_home":"Жильё","c_health":"Здоровье",
            "c_cloth":"Одежда","c_enter":"Развлечения","c_edu":"Образование","c_cafe":"Кафе",
            "c_tech":"Технологии","c_sport":"Спорт","c_travel":"Путешествие","c_bills":"Коммунальные",
            "c_beauty":"Красота","c_gift":"Подарки","c_salary":"Зарплата","c_free":"Фриланс",
            "c_biz":"Бизнес","c_invest":"Инвестиции","other":"Другое"},
    "en":  {"c_food":"Food","c_trans":"Transport","c_home":"Housing","c_health":"Health",
            "c_cloth":"Clothes","c_enter":"Entertainment","c_edu":"Education","c_cafe":"Cafe",
            "c_tech":"Technology","c_sport":"Sport","c_travel":"Travel","c_bills":"Bills",
            "c_beauty":"Beauty","c_gift":"Gifts","c_salary":"Salary","c_free":"Freelance",
            "c_biz":"Business","c_invest":"Investment","other":"Other"},
    "tj":  {"c_food":"Хурок","c_trans":"Нақлиёт","c_health":"Саломатии","c_edu":"Малумот",
            "c_salary":"Маош","other":"Диgar"},
}
CAT_EMOJI = {
    "c_food":"🍔","c_trans":"🚗","c_home":"🏠","c_health":"💊","c_cloth":"👗",
    "c_enter":"🎮","c_edu":"📚","c_cafe":"☕","c_tech":"💻","c_sport":"⚽",
    "c_travel":"✈️","c_bills":"💡","c_beauty":"💅","c_gift":"🎁",
    "c_salary":"💰","c_free":"💻","c_biz":"🏢","c_invest":"📈","other":"📦",
}
AI_KW = {
    "c_food":   ["ovqat","taom","osh","non","gosht","sabzavot","meva","tushlik","nonushta","somsa","manti","lagman","burger","pizza","lavash","doner","bozor","bazar","supermarket","magazin","dukon","dokon","restoran","kafe","choyxona","еда","продукты","магазин","рынок","базар","ресторан","food","grocery","market","lunch","dinner","breakfast","restaurant"],
    "c_trans":  ["taxi","taksi","yandex","uber","avto","mashina","bus","avtobus","metro","benzin","gaz","marshrutka","poyezd","такси","машина","бензин","метро","автобус","поезд","fuel","car","parking","train"],
    "c_home":   ["ijara","kvartira","uy","arenda","rent","kommunal","remont","mebel","аренда","квартира","ремонт","мебель","коммунальные","repair"],
    "c_health": ["dori","dorixona","apteka","shifokor","doktor","klinika","kasalxona","tahlil","vitamin","аптека","лекарство","врач","клиника","больница","pharmacy","medicine","doctor"],
    "c_cloth":  ["kiyim","koylak","shim","kurtka","palto","poyabzal","botinka","krossovka","sumka","одежда","рубашка","штаны","куртка","обувь","кроссовки","clothes","shoes","jacket"],
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
INCOME_KW   = ["maosh","oylik","ish haqi","daromad","bonus","mukofot","зарплата","премия","доход","salary","income","earned","frilanss","freelance","foyda","profit","biznes","business"]
DEBT_GIVEN  = ["qarz berdim","qarz ber","berdim","долг дал","дал в долг","lent","gave","берди"]
DEBT_TAKEN  = ["qarz oldim","qarz ol","oldim","взял в долг","взял","borrowed","гирифтам"]

def cat_label(uid, cat_id):
    lang = get_lang(uid)
    return CAT_LABELS.get(lang, CAT_LABELS["uz"]).get(cat_id, cat_id)

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
    if any(w in low for w in DEBT_GIVEN):  return "debt_given"
    if any(w in low for w in DEBT_TAKEN):  return "debt_taken"
    if any(w in low for w in INCOME_KW):   return "income"
    return "expense"

def fmt(val) -> str:
    try: return f"{int(val):,}".replace(",", " ")
    except: return str(val)


def S_profile_name(uid: int) -> str:
    u = get_user(uid)
    return u.get("name", str(uid)) if u else str(uid)

# ── Premium check helpers ──────────────────────────────────────────────────────
def prem_only(uid: int, msg_obj) -> bool:
    """Returns True if user is NOT premium (should be blocked)"""
    return not is_premium(uid)

async def send_premium_promo(msg, uid: int):
    """Send premium promo message"""
    l = get_lang(uid)
    await msg.answer(T[l]["premium_txt"], parse_mode="HTML", reply_markup=premium_kb(uid))

def progress_bar(pct: int) -> str:
    f = min(10, pct // 10)
    return "█" * f + "░" * (10 - f)

# ── Voice amount parser ────────────────────────────────────────────────────────
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

    hasMln  = any(w in ["million","mln","mlrd","milliard","миллион","млн"] for w in words)
    hasMing = any(w in ["ming","тысяч","тыс","thousand"] for w in words)
    hasK    = any(w == "k" for w in words) and not any(x in low for x in ["ok","ak","ek"])

    if hasMln:
        res = base * 1_000_000
        if 0 < second < 1000: res += second * 1000
        return res, cur
    if hasMing or hasK:
        res = base * 1000
        if 0 < second < 1000: res += second
        return res, cur
    if len(nums) > 1 and re.match(r"^0+$", nums[1]):
        return int("".join(nums[:2])), cur
    return base, cur

# ── Keyboards ──────────────────────────────────────────────────────────────────
def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbek",  callback_data="lang_uz"),
         InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
         InlineKeyboardButton(text="🇹🇯 Тоҷикӣ", callback_data="lang_tj")],
    ])

def main_kb(uid: int):
    l = get_lang(uid)
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=T[l]["btn_report"]),  KeyboardButton(text=T[l]["btn_history"])],
        [KeyboardButton(text=T[l]["btn_goals"]),   KeyboardButton(text=T[l]["btn_group"])],
        [KeyboardButton(text=T[l]["btn_premium"]), KeyboardButton(text=T[l]["btn_ref"])],
        [KeyboardButton(text=T[l]["btn_share"]),   KeyboardButton(text=T[l]["btn_lang"])],
    ], resize_keyboard=True)

def app_kb(uid: int):
    l = get_lang(uid)
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=T[l]["open_app"], web_app=WebAppInfo(url=WEB_APP_URL))
    ]])

def action_kb(uid: int, tid: int):
    l = get_lang(uid)
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=T[l]["edit_btn"], callback_data=f"edit_{tid}"),
        InlineKeyboardButton(text=T[l]["del_btn"],  callback_data=f"del_{tid}"),
    ]])

def premium_kb(uid: int):
    l = get_lang(uid)
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=T[l]["premium_btn"], callback_data="buy_premium")
    ]])

# ── Save & reply ───────────────────────────────────────────────────────────────
async def save_and_reply(msg: Message, uid: int, tx_type: str, amount: int, currency: str, note: str):
    cat   = detect_cat(note) if tx_type not in ("debt_given","debt_taken") else "c_other_e"
    if tx_type == "income" and cat == "other": cat = "c_salary"
    tid   = add_txn(uid, tx_type, amount, note, currency, cat)
    cl    = cat_label(uid, cat)
    em    = cat_emoji(cat)

    key_map = {
        "income":     "saved_inc",
        "expense":    "saved_exp",
        "debt_given": "saved_dg",
        "debt_taken": "saved_dt",
    }
    text = tx(uid, key_map.get(tx_type, "saved_exp"),
              amount=fmt(amount), cur=currency,
              note=note or "-", cat=f"{em} {cl}")

    await msg.answer(text, parse_mode="HTML", reply_markup=action_kb(uid, tid))
    await check_goal_motivation(uid)

# ── CBU Rates ──────────────────────────────────────────────────────────────────
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

# ── Goal motivation ────────────────────────────────────────────────────────────
async def check_goal_motivation(uid: int):
    for g in get_goals(uid):
        if g["target"] <= 0: continue
        pct = round((g["current"] / g["target"]) * 100)
        for milestone in [25, 50, 75, 100]:
            if pct >= milestone > (g["notified_pct"] or 0):
                from database import con
                db = con()
                db.execute("UPDATE goals SET notified_pct=? WHERE id=?", (milestone, g["id"]))
                db.commit(); db.close()
                if pct >= 100:
                    await bot.send_message(uid, tx(uid,"goal_done",name=g["name"]), parse_mode="HTML")
                else:
                    await bot.send_message(uid, tx(uid,"motivation",name=g["name"],pct=pct), parse_mode="HTML")
                break

# ── Voice processing ───────────────────────────────────────────────────────────
async def voice_to_text(ogg_path: str) -> str | None:
    """Groq Whisper bilan ovozni matnga aylantirish"""
    # Groq Whisper (birinchi tanlov)
    if GROQ_API_KEY and GROQ_API_KEY != "bu_yerga_groq_kalitingiz":
        try:
            import httpx
            wav = ogg_path.replace(".ogg", ".wav")
            # Convert ogg to wav
            if VOICE_OK:
                from pydub import AudioSegment
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
            log.error(f"groq whisper: {e}")

    # Fallback: Google STT
    if not VOICE_OK: return None
    loop = asyncio.get_event_loop()
    def _run():
        try:
            from pydub import AudioSegment
            import speech_recognition as sr
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
            log.error(f"google stt: {e}")
        return None
    return await loop.run_in_executor(None, _run)

# ── Handlers ───────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(msg: Message):
    uid  = msg.from_user.id
    args = msg.text.split()

    # Check referral
    referrer_uid = 0
    if len(args) > 1:
        ref_code = args[1]
        referrer_uid = use_referral(ref_code, uid)

    add_user(uid)

    if referrer_uid:
        set_premium(uid, 1)
        await msg.answer(tx(uid, "ref_thanks"), parse_mode="HTML")
        try:
            set_premium(referrer_uid, 3)
            await bot.send_message(referrer_uid, tx(referrer_uid,"ref_bonus"), parse_mode="HTML")
        except: pass

    l = get_lang(uid)
    # Inline Open tugmasi — chat ro'yxatida ko'rinadi
    open_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🚀 SpendUZ Pro ni ochish", web_app=WebAppInfo(url=WEB_APP_URL))
    ]])
    await msg.answer(T[l]["start"], reply_markup=lang_kb(), parse_mode="HTML")
    await msg.answer("💸 <b>SpendUZ Pro</b>\n\n👇 Ilovani ochish uchun bosing:", reply_markup=open_kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("lang_"))
async def cb_lang(cb: CallbackQuery):
    uid  = cb.from_user.id
    lang = cb.data.split("_")[1]
    add_user(uid, lang)
    set_lang(uid, lang)
    l = lang
    await cb.message.edit_text(T[l]["lang_saved"], parse_mode="HTML")
    # Menu keyboard (bot ichida)
    await cb.message.answer("📋", reply_markup=main_kb(uid))
    await cb.answer()

@dp.callback_query(F.data.startswith("edit_"))
async def cb_edit(cb: CallbackQuery):
    uid = cb.from_user.id
    tid = int(cb.data.split("_")[1])
    states[uid] = {"action":"edit","tid":tid}
    await cb.message.answer(tx(uid,"edit_ask"), parse_mode="HTML")
    await cb.answer()

@dp.callback_query(F.data.startswith("del_"))
async def cb_del(cb: CallbackQuery):
    uid = cb.from_user.id
    tid = int(cb.data.split("_")[1])
    if delete_txn(tid, uid):
        await cb.message.edit_text(tx(uid,"deleted"))
    await cb.answer()

@dp.callback_query(F.data == "buy_premium")
async def cb_buy_premium(cb: CallbackQuery):
    uid = cb.from_user.id
    if is_premium(uid):
        await cb.answer(tx(uid,"premium_already"), show_alert=True)
        return
    # Send Stars invoice
    await bot.send_invoice(
        chat_id=uid,
        title="SpendUZ Premium",
        description="30 kunlik Premium obuna — barcha funksiyalar!",
        payload=f"premium_{uid}",
        currency="XTR",  # Telegram Stars
        prices=[LabeledPrice(label="Premium 30 kun", amount=PREMIUM_STARS)],
        provider_token="",  # Stars uchun bo'sh
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
        await msg.answer(tx(uid,"premium_ok"), parse_mode="HTML")

@dp.message(Command("report"))
async def cmd_report(msg: Message):
    uid = msg.from_user.id
    s   = get_summary(uid)
    mon = datetime.now().strftime("%Y-%m")
    await msg.answer(tx(uid,"report",
        month=mon,
        income=fmt(s["income"])+" UZS",
        expense=fmt(s["expense"])+" UZS",
        dg=fmt(s["debt_given"])+" UZS",
        dt=fmt(s["debt_taken"])+" UZS",
        balance=fmt(s["balance"])+" UZS",
    ), parse_mode="HTML")

@dp.message(Command("history"))
async def cmd_history(msg: Message):
    uid  = msg.from_user.id
    txns = get_txns(uid, limit=10)
    if not txns:
        await msg.answer(tx(uid,"no_txn")); return
    rows = []
    for t in txns:
        em   = cat_emoji(t["category"])
        sign = "+" if t["tx_type"] in ("income","debt_taken") else "-"
        rows.append(f"{em} <b>{sign}{fmt(t['amount'])}</b> {t['currency']} — {t['note'] or '-'} <i>({t['date']})</i>")
    await msg.answer(tx(uid,"history",n=len(rows),rows="\n".join(rows)), parse_mode="HTML")

@dp.message(Command("rate"))
async def cmd_rate(msg: Message):
    uid   = msg.from_user.id
    rates = await fetch_rates()
    if not rates:
        await msg.answer(tx(uid,"rate_fail")); return
    lines = []
    for code in ["USD","EUR","RUB","GBP","CNY","KZT","TRY"]:
        if code in rates:
            lines.append(f"• <b>{code}</b>: {rates[code]:,.0f} so'm")
    rates_text = "\n".join(lines)
    await msg.answer(tx(uid,"currency_rates", rates=rates_text), parse_mode="HTML")

@dp.message(Command("goals"))
async def cmd_goals(msg: Message):
    uid   = msg.from_user.id
    goals = get_goals(uid)
    if not goals:
        await msg.answer(tx(uid,"goals_empty"), parse_mode="HTML"); return
    items = []
    for g in goals:
        pct = round((g["current"]/g["target"])*100) if g["target"] > 0 else 0
        items.append(tx(uid,"goal_item",
            name=g["name"], cur=fmt(g["current"]),
            tgt=fmt(g["target"]), pct=pct, bar=progress_bar(pct)))
    await msg.answer(tx(uid,"goal_list",items="\n\n".join(items)), parse_mode="HTML")

@dp.message(Command("addgoal"))
async def cmd_addgoal(msg: Message):
    uid  = msg.from_user.id
    # Premium check: max 3 goals for free users
    if not is_premium(uid):
        goals = get_goals(uid)
        if len(goals) >= 3:
            l = get_lang(uid)
            await msg.answer(T[l]["need_premium_goals"], parse_mode="HTML", reply_markup=premium_kb(uid))
            return
    args = (msg.text or "").split(maxsplit=2)
    if len(args) < 3:
        await msg.answer(tx(uid,"goal_fmt"), parse_mode="HTML"); return
    name   = args[1]
    amount, _ = parse_amount(args[2])
    if not amount:
        await msg.answer(tx(uid,"goal_fmt"), parse_mode="HTML"); return
    add_goal(uid, name, amount)
    await msg.answer(tx(uid,"goal_added",name=name,target=fmt(amount)), parse_mode="HTML")

@dp.message(Command("group"))
async def cmd_group(msg: Message):
    uid = msg.from_user.id
    if not is_premium(uid):
        l = get_lang(uid)
        await msg.answer(T[l]["need_premium_group"], parse_mode="HTML", reply_markup=premium_kb(uid))
        return
    gid = create_group(uid)
    await msg.answer(tx(uid,"group_made",gid=gid), parse_mode="HTML")

@dp.message(Command("join"))
async def cmd_join(msg: Message):
    uid  = msg.from_user.id
    args = (msg.text or "").split()
    if len(args) < 2:
        await msg.answer("Format: /join <group_id>"); return
    ok = join_group(args[1], uid)
    await msg.answer(tx(uid,"group_joined" if ok else "group_nf"))

@dp.message(Command("groupreport"))
async def cmd_grprep(msg: Message):
    uid = msg.from_user.id
    gid = get_user_group(uid)
    if not gid:
        await msg.answer(tx(uid,"no_group")); return
    members = get_group_members(gid)
    rows = []
    for mid in members:
        s = get_summary(mid)
        rows.append(f"👤 <code>{mid}</code>:\n  💸 {fmt(s['expense'])} / 💰 {fmt(s['income'])} UZS")
    await msg.answer(tx(uid,"group_rep",rows="\n\n".join(rows)), parse_mode="HTML")

@dp.message(Command("premium"))
async def cmd_premium(msg: Message):
    uid = msg.from_user.id
    if is_premium(uid):
        await msg.answer(tx(uid,"premium_already"), parse_mode="HTML"); return
    l = get_lang(uid)
    await msg.answer(T[l]["premium_txt"], parse_mode="HTML", reply_markup=premium_kb(uid))

@dp.message(Command("ref"))
async def cmd_ref(msg: Message):
    uid  = msg.from_user.id
    code = get_referral_code(uid)
    db   = __import__("database").con()
    cnt  = db.execute("SELECT COUNT(*) as c FROM users WHERE referred_by=?", (uid,)).fetchone()["c"]
    db.close()
    l = get_lang(uid)
    ref_link = f"https://t.me/Spend_uz_bot?start={code}"
    # Share button
    share_text = {
        "uz": f"SpendUZ Pro - eng yaxshi moliya treker! Yuklab ol:",
        "ru": f"SpendUZ Pro - лучший финансовый трекер! Скачай:",
        "en": f"SpendUZ Pro - best finance tracker! Download:",
        "tj": f"SpendUZ Pro - беҳтарин трекер! Зеркор кун:",
    }.get(l, "SpendUZ Pro:")
    share_url = f"https://t.me/share/url?url={ref_link}&text={share_text}"
    ref_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Do'stlarga yuborish", url=share_url)],
        [InlineKeyboardButton(text="🚀 Havolani ochish", url=ref_link)],
    ])
    await msg.answer(tx(uid,"ref_info",code=code,count=cnt), parse_mode="HTML", reply_markup=ref_kb)

@dp.message(Command("share"))
async def cmd_share(msg: Message):
    uid = msg.from_user.id
    l   = get_lang(uid)
    await msg.answer(T[l]["share_txt"], parse_mode="HTML")

@dp.message(Command("settings"))
async def cmd_settings(msg: Message):
    uid = msg.from_user.id
    l   = get_lang(uid)
    txns  = get_txns(uid)
    goals = get_goals(uid)
    prem  = "✅ Faol" if is_premium(uid) else "❌ Yo'q"
    lang_names = {"uz":"O'zbek","ru":"Русский","en":"English","tj":"Тоҷикӣ"}
    await msg.answer(T[l]["settings_txt"].format(
        lang=lang_names.get(l,l), premium=prem,
        txn_count=len(txns), goal_count=len(goals)
    ), parse_mode="HTML")
    await msg.answer(T[l]["start"], reply_markup=lang_kb(), parse_mode="HTML")

@dp.message(Command("cards"))
async def cmd_cards(msg: Message):
    uid  = msg.from_user.id
    if not is_premium(uid):
        l = get_lang(uid)
        await msg.answer(T[l]["need_premium_cards"], parse_mode="HTML", reply_markup=premium_kb(uid))
        return
    args = (msg.text or "").split(maxsplit=2)

    if len(args) < 2:
        cards = get_cards(uid)
        if not cards:
            await msg.answer(tx(uid,"no_cards"), parse_mode="HTML"); return
        items = []
        for i, c in enumerate(cards, 1):
            label = f" ({c['label']})" if c["label"] else ""
            items.append(f"{i}. **** **** **** {c['last4']}{label} — /delcard_{c['id']}")
        await msg.answer(tx(uid,"card_list",items="\n".join(items)), parse_mode="HTML"); return

    action = args[1].lower()
    if action in ("qoshish","добавить","add","ilova"):
        if len(args) < 3:
            await msg.answer(tx(uid,"card_fmt"), parse_mode="HTML"); return
        digits = re.findall(r"\d+", args[2])
        if not digits:
            await msg.answer(tx(uid,"card_16"), parse_mode="HTML"); return
        card_num = "".join(digits)
        last4 = card_num[-4:] if len(card_num) >= 4 else card_num
        add_card(uid, last4)
        await msg.answer(tx(uid,"card_added",last4=last4), parse_mode="HTML")
    else:
        await msg.answer(tx(uid,"card_fmt"), parse_mode="HTML")

@dp.message(F.text.regexp(r"^/delcard_(\d+)$"))
async def cmd_delcard(msg: Message):
    uid = msg.from_user.id
    cid = int(msg.text.split("_")[1])
    if delete_card(cid, uid):
        await msg.answer(tx(uid,"card_del"))

@dp.message(Command("currency"))
async def cmd_currency(msg: Message):
    await cmd_rate(msg)

@dp.message(Command("download_report"))
async def cmd_download_report(msg: Message):
    uid = msg.from_user.id
    if not is_premium(uid):
        l = get_lang(uid)
        await msg.answer(T[l]["need_premium_pdf"], parse_mode="HTML", reply_markup=premium_kb(uid))
        return
    txns = get_txns(uid, limit=100)
    if not txns:
        await msg.answer(tx(uid,"no_txn")); return

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import io

        s       = get_summary(uid)
        now     = datetime.now()
        months  = ["Yanvar","Fevral","Mart","Aprel","May","Iyun","Iyul","Avgust","Sentabr","Oktabr","Noyabr","Dekabr"]
        month_name = months[now.month - 1] + " " + str(now.year)
        cats    = get_cat_breakdown(uid)

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
            rightMargin=1.5*cm, leftMargin=1.5*cm,
            topMargin=1.5*cm, bottomMargin=1.5*cm)

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("title", parent=styles["Normal"],
            fontSize=18, fontName="Helvetica-Bold",
            textColor=colors.HexColor("#00b87d"), spaceAfter=6)
        sub_style = ParagraphStyle("sub", parent=styles["Normal"],
            fontSize=10, fontName="Helvetica", textColor=colors.gray)
        normal = ParagraphStyle("norm", parent=styles["Normal"],
            fontSize=10, fontName="Helvetica")

        elems = []
        elems.append(Paragraph("SpendUZ Pro", title_style))
        elems.append(Paragraph(f"{month_name} hisoboti  |  {S_profile_name(uid)}", sub_style))
        elems.append(Spacer(1, 0.4*cm))

        # Summary table
        sum_data = [
            ["Ko'rsatkich", "Summa"],
            ["Daromad", f"{fmt(s['income'])} UZS"],
            ["Xarajat",  f"{fmt(s['expense'])} UZS"],
            ["Qarz berdim", f"{fmt(s['debt_given'])} UZS"],
            ["Qarz oldim",  f"{fmt(s['debt_taken'])} UZS"],
            ["Balans",   f"{fmt(s['balance'])} UZS"],
        ]
        t_sum = Table(sum_data, colWidths=[8*cm, 8*cm])
        t_sum.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (-1,0), colors.HexColor("#00b87d")),
            ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
            ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",     (0,0), (-1,-1), 10),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#f2f4f8")]),
            ("GRID",         (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
            ("ALIGN",        (1,0), (1,-1), "RIGHT"),
            ("BOTTOMPADDING",(0,0), (-1,-1), 6),
            ("TOPPADDING",   (0,0), (-1,-1), 6),
        ]))
        elems.append(t_sum)
        elems.append(Spacer(1, 0.4*cm))

        # Category breakdown
        if cats:
            elems.append(Paragraph("Kategoriyalar bo'yicha xarajat:", ParagraphStyle("h2",
                parent=styles["Normal"], fontSize=12, fontName="Helvetica-Bold",
                textColor=colors.HexColor("#1a1e2e"), spaceAfter=4)))
            cat_data = [["Kategoriya", "Summa"]]
            for cid, val in sorted(cats.items(), key=lambda x: -x[1])[:10]:
                em = cat_emoji(cid)
                cat_data.append([f"{em} {cid}", f"{fmt(val)} UZS"])
            t_cat = Table(cat_data, colWidths=[10*cm, 6*cm])
            t_cat.setStyle(TableStyle([
                ("BACKGROUND",   (0,0), (-1,0), colors.HexColor("#7C6DFA")),
                ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
                ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",     (0,0), (-1,-1), 9),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#f2f4f8")]),
                ("GRID",         (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
                ("ALIGN",        (1,0), (1,-1), "RIGHT"),
                ("BOTTOMPADDING",(0,0), (-1,-1), 5),
                ("TOPPADDING",   (0,0), (-1,-1), 5),
            ]))
            elems.append(t_cat)
            elems.append(Spacer(1, 0.4*cm))

        # Transactions
        elems.append(Paragraph("Tranzaksiyalar (so'nggi 50):", ParagraphStyle("h2",
            parent=styles["Normal"], fontSize=12, fontName="Helvetica-Bold",
            textColor=colors.HexColor("#1a1e2e"), spaceAfter=4)))
        tx_data = [["Sana", "Tur", "Izoh", "Summa"]]
        for t in txns[:50]:
            sign = "+" if t["tx_type"] in ("income","debt_taken") else "-"
            em   = cat_emoji(t["category"])
            tx_data.append([
                t["date"],
                em + " " + t["tx_type"],
                t["note"][:20] if t["note"] else "-",
                f"{sign}{fmt(t['amount'])} {t['currency']}"
            ])
        t_tx = Table(tx_data, colWidths=[2.5*cm, 3.5*cm, 6*cm, 4*cm])
        t_tx.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (-1,0), colors.HexColor("#1a1e2e")),
            ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
            ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",     (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#f2f4f8")]),
            ("GRID",         (0,0), (-1,-1), 0.3, colors.HexColor("#dddddd")),
            ("ALIGN",        (3,0), (3,-1), "RIGHT"),
            ("BOTTOMPADDING",(0,0), (-1,-1), 4),
            ("TOPPADDING",   (0,0), (-1,-1), 4),
        ]))
        elems.append(t_tx)
        elems.append(Spacer(1, 0.4*cm))
        elems.append(Paragraph(
            f"SpendUZ Pro · @Spend_uz_bot · {now.strftime('%Y-%m-%d %H:%M')}",
            ParagraphStyle("foot", parent=styles["Normal"],
                fontSize=8, fontName="Helvetica", textColor=colors.gray)))

        doc.build(elems)
        buf.seek(0)
        fname = f"SpendUZ_{now.strftime('%Y%m%d')}.pdf"
        await msg.answer_document(
            BufferedInputFile(buf.read(), filename=fname),
            caption=f"📊 <b>SpendUZ Pro hisoboti</b>\n{month_name}",
            parse_mode="HTML"
        )

    except ImportError:
        # Fallback to TXT
        lines = ["SpendUZ Pro — Hisobot", "=" * 40]
        s2 = get_summary(uid)
        lines += [f"Daromad: {fmt(s2['income'])} UZS", f"Xarajat: {fmt(s2['expense'])} UZS",
                  f"Balans: {fmt(s2['balance'])} UZS", "=" * 40]
        for t in txns[:50]:
            sign = "+" if t["tx_type"] in ("income","debt_taken") else "-"
            lines.append(f"{t['date']} | {sign}{fmt(t['amount'])} {t['currency']} | {t['note'] or '-'}")
        content2 = "\n".join(lines).encode("utf-8")
        await msg.answer_document(BufferedInputFile(content2, filename="spenduz.txt"), caption="📊 Hisobot")

# ── Voice handler ──────────────────────────────────────────────────────────────

@dp.message(Command("givepremium"))
async def cmd_give_premium(msg: Message):
    uid = msg.from_user.id
    if not is_admin(uid):
        await msg.answer("❌ Ruxsat yo'q!"); return
    args = (msg.text or "").split()
    if len(args) < 3:
        await msg.answer("Format: /givepremium <user_id> <kunlar>\nMisol: /givepremium 123456789 30"); return
    try:
        target_uid = int(args[1])
        days       = int(args[2])
    except:
        await msg.answer("❌ Noto'g'ri format!"); return
    set_premium(target_uid, days)
    await msg.answer(f"✅ <b>Premium berildi!</b>\n\n👤 User: <code>{target_uid}</code>\n📅 Muddat: {days} kun", parse_mode="HTML")
    try:
        await bot.send_message(target_uid, f"🎉 <b>Sizga {days} kun Premium berildi!</b>\n\nBarcha funksiyalardan foydalaning!", parse_mode="HTML")
    except: pass

@dp.message(Command("users"))
async def cmd_users(msg: Message):
    uid = msg.from_user.id
    if not is_admin(uid):
        await msg.answer("❌ Ruxsat yo'q!"); return
    all_u = all_users()
    prem_count = sum(1 for u in all_u if is_premium(u))
    await msg.answer(
        f"📊 <b>Statistika:</b>\n\n"
        f"👥 Jami userlar: <b>{len(all_u)}</b>\n"
        f"💎 Premium: <b>{prem_count}</b>\n"
        f"🆓 Bepul: <b>{len(all_u) - prem_count}</b>",
        parse_mode="HTML"
    )

@dp.message(Command("broadcast"))
async def cmd_broadcast(msg: Message):
    uid = msg.from_user.id
    if not is_admin(uid):
        await msg.answer("❌ Ruxsat yo'q!"); return
    text = (msg.text or "").split(maxsplit=1)
    if len(text) < 2:
        await msg.answer("Format: /broadcast <xabar>"); return
    broadcast_text = text[1]
    sent = 0; failed = 0
    for u in all_users():
        try:
            await bot.send_message(u, broadcast_text, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)
        except: failed += 1
    await msg.answer(f"✅ Yuborildi: {sent}\n❌ Xato: {failed}")

@dp.message(F.voice)
async def voice_handler(msg: Message):
    uid = msg.from_user.id
    add_user(uid)
    # Premium check
    if not is_premium(uid):
        l = get_lang(uid)
        await msg.answer(T[l]["need_premium_voice"], parse_mode="HTML", reply_markup=premium_kb(uid))
        return
    if not VOICE_OK:
        await msg.answer(tx(uid,"voice_off")); return
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

# ── Text handler ───────────────────────────────────────────────────────────────
@dp.message(F.text)
async def text_handler(msg: Message):
    uid  = msg.from_user.id
    text = (msg.text or "").strip()
    add_user(uid)

    # Edit state
    if uid in states and states[uid].get("action") == "edit":
        amount, _ = parse_amount(text)
        if amount:
            tid = states[uid]["tid"]
            t   = get_txn(tid, uid)
            if t:
                update_txn(tid, uid, amount, t["note"], t["category"], t["tx_type"])
                await msg.answer(tx(uid,"edit_done",amount=fmt(amount)+" so'm"), parse_mode="HTML")
        del states[uid]
        return

    l = get_lang(uid)

    # All button texts for all langs
    for lang in ["uz","ru","en","tj"]:
        if text == T[lang]["btn_report"]:
            await cmd_report(msg); return
        if text == T[lang]["btn_history"]:
            await cmd_history(msg); return
        if text == T[lang]["btn_goals"]:
            await cmd_goals(msg); return
        if text == T[lang]["btn_group"]:
            await cmd_group(msg); return
        if text == T[lang]["btn_premium"]:
            await cmd_premium(msg); return
        if text == T[lang]["btn_ref"]:
            await cmd_ref(msg); return
        if text == T[lang]["btn_share"]:
            await cmd_share(msg); return
        if text == T[lang]["btn_lang"]:
            await msg.answer(T[l]["start"], reply_markup=lang_kb(), parse_mode="HTML"); return
        if text == T[lang]["btn_back"]:
            await msg.answer("📋", reply_markup=main_kb(uid)); return

    if text.startswith("/"): return

    # Parse transaction
    amount, currency = parse_amount(text)
    if not amount:
        await msg.answer(tx(uid,"unknown"), parse_mode="HTML")
        return
    tx_type = detect_type(text)
    await save_and_reply(msg, uid, tx_type, amount, currency, text)

# ── Scheduled tasks ────────────────────────────────────────────────────────────
async def smart_reminder():
    """Bugun yozmagan userlarga kech. 21:00 da eslatma"""
    while True:
        now = datetime.now()
        if now.hour == 21 and now.minute == 0:
            for uid in all_users():
                if not has_txn_today(uid):
                    try:
                        await bot.send_message(uid, tx(uid,"reminder"))
                    except: pass
            await asyncio.sleep(61)
        await asyncio.sleep(20)

async def weekly_report_task():
    """Har dushanba 09:00 da haftalik hisobot"""
    while True:
        now = datetime.now()
        if now.weekday() == 0 and now.hour == 9 and now.minute == 0:
            for uid in all_users():
                s = get_summary(uid)
                if s["income"] == 0 and s["expense"] == 0: continue
                try:
                    await bot.send_message(uid, tx(uid,"weekly",
                        inc=fmt(s["income"])+" UZS",
                        exp=fmt(s["expense"])+" UZS",
                        bal=fmt(s["balance"])+" UZS",
                    ), parse_mode="HTML")
                except: pass
            await asyncio.sleep(61)
        await asyncio.sleep(20)

async def weekly_referral_reminder():
    """Har hafta shanba 12:00 da referal reklama"""
    while True:
        now = datetime.now()
        if now.weekday() == 5 and now.hour == 12 and now.minute == 0:
            for uid in all_users():
                if is_premium(uid): continue  # Premiumlarga yubormaymiz
                code = get_referral_code(uid)
                if not code: continue
                l = get_lang(uid)
                ref_ad = T[l].get("ref_ad", T["uz"]["ref_ad"])
                text = ref_ad.replace("{code}", code)
                ref_kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text=T[l].get("ref_ad_btn", "🔗 Ulashish"),
                        url=f"https://t.me/share/url?url=https://t.me/Spend_uz_bot?start={code}&text=SpendUZ+Pro+-+moliya+treker"
                    )
                ]])
                try:
                    await bot.send_message(uid, text, parse_mode="HTML", reply_markup=ref_kb)
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
                if is_premium(uid): continue  # Premiumlarga yubormaymiz
                last = last_sent.get(uid)
                if last and (now - last).days < 10: continue
                l = get_lang(uid)
                ad_text = T[l].get("premium_txt", T["uz"]["premium_txt"])
                try:
                    await bot.send_message(uid, ad_text,
                        parse_mode="HTML", reply_markup=premium_kb(uid))
                    last_sent[uid] = now
                except: pass
            await asyncio.sleep(61)
        await asyncio.sleep(20)

# ── Main ───────────────────────────────────────────────────────────────────────
async def main():
    init_db()
    log.info("✅ Database initialized")
    log.info(f"🎤 Voice: {'ON' if VOICE_OK else 'OFF'}")
    log.info(f"🌐 HTTP:  {'ON' if HTTP_OK  else 'OFF'}")
    log.info("🚀 SpendUZ Bot started!")

    asyncio.create_task(smart_reminder())
    asyncio.create_task(weekly_report_task())
    asyncio.create_task(weekly_referral_reminder())
    asyncio.create_task(premium_ad_task())

    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())