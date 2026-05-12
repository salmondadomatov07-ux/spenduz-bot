"""
SpendUZ Pro — main.py
@Spend_uz_bot
"""
import asyncio, logging, os, re, tempfile
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo,
)
from database import (
    init_db, add_user, get_lang, set_lang, all_users,
    add_txn, get_txns, get_txn, update_txn, delete_txn,
    get_summary, get_cat_breakdown, has_txn_today,
    add_goal, get_goals, add_to_goal, set_goal_notified, delete_goal,
    create_group, join_group, get_group_members, get_user_group,
)

# ── Optional deps ──────────────────────────────────────────────────────────────
try:
    import speech_recognition as sr
    from pydub import AudioSegment
    VOICE_OK = True
except ImportError:
    VOICE_OK = False

try:
    from PIL import Image
    import pytesseract
    OCR_OK = True
except ImportError:
    OCR_OK = False

try:
    import aiohttp
    HTTP_OK = True
except ImportError:
    HTTP_OK = False

# ── Config ─────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BOT_TOKEN   = os.getenv("BOT_TOKEN",   "8651989569:AAEGRKv4os3HFolPrw6kRvinjMGT7e6BGuI")
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://salmondadomatov07-ux.github.io/spend-app/")

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher()

# Edit state: uid → {"action":"edit","tid":int}
states: dict[int, dict] = {}

# ── Translations ───────────────────────────────────────────────────────────────
T = {
"uz": {
    "start":        "👋 Assalomu alaykum!\n\nTilni tanlang:",
    "lang_set":     "✅ Til saqlandi! Endi xarajatlaringizni yozing.",
    "menu":         "🏠 Asosiy menyu",
    "help":         (
        "📝 <b>Qanday yozish:</b>\n\n"
        "💸 Xarajat: <code>20000 ovqat</code>\n"
        "💰 Daromad: <code>3mln oylik</code>\n"
        "💸 Qarz berdim: <code>qarz 50000 Jasur</code>\n"
        "💰 Qarz oldim: <code>oldim 100000 Ali</code>\n\n"
        "🎤 Yoki ovoz yuboring!\n"
        "📸 Chek rasmini yuboring!"
    ),
    "saved_exp":    "✅ <b>Xarajat saqlandi!</b>\n\n💸 {amount} {cur}\n📝 {note}\n🏷 {cat}",
    "saved_inc":    "✅ <b>Daromad saqlandi!</b>\n\n💰 {amount} {cur}\n📝 {note}\n🏷 {cat}",
    "saved_dg":     "✅ <b>Qarz berdim!</b>\n\n💸 {amount} {cur}\n👤 {note}",
    "saved_dt":     "✅ <b>Qarz oldim!</b>\n\n💰 {amount} {cur}\n👤 {note}",
    "edit_btn":     "✏️ Tahrirlash",
    "del_btn":      "🗑 O'chirish",
    "deleted":      "🗑 O'chirildi!",
    "edit_ask":     "✏️ Yangi summani yozing (faqat raqam):\nMasalan: <code>25000</code>",
    "edit_done":    "✅ Yangilandi! Yangi summa: <b>{amount} so'm</b>",
    "report":       (
        "📊 <b>{month} hisoboti:</b>\n\n"
        "⬆️ Daromad:     <b>{income}</b>\n"
        "⬇️ Xarajat:     <b>{expense}</b>\n"
        "💸 Qarz berdim: <b>{dg}</b>\n"
        "💰 Qarz oldim:  <b>{dt}</b>\n"
        "━━━━━━━━━━━━\n"
        "📈 Balans: <b>{balance}</b>"
    ),
    "history":      "📋 <b>So'nggi {n} ta tranzaksiya:</b>\n\n{rows}",
    "no_txn":       "📭 Hali tranzaksiya yo'q.",
    "weekly":       "📊 <b>Haftalik hisobot:</b>\n\n⬆️ Daromad: <b>{inc}</b>\n⬇️ Xarajat: <b>{exp}</b>\n📈 Balans: <b>{bal}</b>",
    "reminder":     "⏰ Bugungi xarajatlarni yozmadingiz! Yozib qo'ying 💸",
    "voice_wait":   "🎤 Ovoz tahlil qilinmoqda...",
    "voice_done":   "🎤 Eshitildi: <i>«{text}»</i>",
    "voice_fail":   "😕 Ovozni tushunmadim. Qayta yuboring yoki matn yozing.",
    "voice_off":    "🎤 Voice hozir ishlamayapti.",
    "ocr_wait":     "📸 Chek o'qilmoqda...",
    "ocr_done":     "📸 Chekdan topildi: <b>{amount} so'm</b> — saqlandi!",
    "ocr_fail":     "😕 Chekdan ma'lumot topa olmadim.",
    "ocr_off":      "📸 OCR hozir ishlamayapti.",
    "rate_title":   "💱 <b>Bugungi kurs (CBU):</b>\n",
    "rate_fail":    "😕 Kursni yuklab bo'lmadi.",
    "unknown":      "🤔 Tushunmadim.\n\n<b>Misol:</b> <code>20000 ovqat</code>\n🎤 Yoki ovoz yuboring",
    "goals_empty":  "🎯 Hali maqsad yo'q.\n\n<code>/addgoal MacBook 10000000</code>",
    "goal_added":   "🎯 Maqsad qo'shildi!\n\n📌 <b>{name}</b>\n💰 {target} so'm",
    "goal_fmt":     "Format: <code>/addgoal MacBook 10000000</code>",
    "goal_list":    "🎯 <b>Maqsadlaringiz:</b>\n\n{items}",
    "goal_item":    "• <b>{name}</b>: {cur}/{tgt} ({pct}%)\n  {bar}",
    "motivation":   "🏆 <b>«{name}»</b> maqsadingiz <b>{pct}%</b> bajarildi! 💪",
    "goal_done_msg":"🎉 <b>«{name}»</b> maqsadiga yetdingiz! Tabriklaymiz!",
    "group_made":   "👥 Guruh yaratildi!\n\nID: <code>{gid}</code>\nBoshqalar: <code>/join {gid}</code>",
    "group_joined": "👥 Guruhga qo'shildingiz!",
    "group_nf":     "❌ Guruh topilmadi.",
    "group_rep":    "👥 <b>Guruh hisoboti:</b>\n\n{rows}",
    "no_group":     "❌ Guruhga a'zo emassiz.\n/group bilan yarating.",
    "btn_add":      "➕ Qo'shish",
    "btn_report":   "📊 Hisobot",
    "btn_history":  "📋 Tarix",
    "btn_goals":    "🎯 Maqsadlar",
    "btn_group":    "👥 Guruh",
    "btn_app":      "🚀 App ochish",
    "btn_settings": "⚙️ Sozlamalar",
    "btn_back":     "⬅️ Orqaga",
    "btn_lang":     "🌍 Tilni o'zgartirish",
    "open_app":     "🚀 SpendUZ Pro ni ochish",
},
"ru": {
    "start":        "👋 Привет!\n\nВыберите язык:",
    "lang_set":     "✅ Язык сохранён! Теперь пишите расходы.",
    "menu":         "🏠 Главное меню",
    "help":         (
        "📝 <b>Как писать:</b>\n\n"
        "💸 Расход: <code>20000 еда</code>\n"
        "💰 Доход: <code>3млн зарплата</code>\n"
        "💸 Дал в долг: <code>долг 50000 Жасур</code>\n"
        "💰 Взял в долг: <code>взял 100000 Али</code>\n\n"
        "🎤 Или отправьте голосовое!\n"
        "📸 Фото чека!"
    ),
    "saved_exp":    "✅ <b>Расход сохранён!</b>\n\n💸 {amount} {cur}\n📝 {note}\n🏷 {cat}",
    "saved_inc":    "✅ <b>Доход сохранён!</b>\n\n💰 {amount} {cur}\n📝 {note}\n🏷 {cat}",
    "saved_dg":     "✅ <b>Дал в долг!</b>\n\n💸 {amount} {cur}\n👤 {note}",
    "saved_dt":     "✅ <b>Взял в долг!</b>\n\n💰 {amount} {cur}\n👤 {note}",
    "edit_btn":     "✏️ Изменить",
    "del_btn":      "🗑 Удалить",
    "deleted":      "🗑 Удалено!",
    "edit_ask":     "✏️ Введите новую сумму:\nНапример: <code>25000</code>",
    "edit_done":    "✅ Обновлено! Новая сумма: <b>{amount}</b>",
    "report":       (
        "📊 <b>Отчёт {month}:</b>\n\n"
        "⬆️ Доход:       <b>{income}</b>\n"
        "⬇️ Расход:      <b>{expense}</b>\n"
        "💸 Дал в долг:  <b>{dg}</b>\n"
        "💰 Взял в долг: <b>{dt}</b>\n"
        "━━━━━━━━━━━━\n"
        "📈 Баланс: <b>{balance}</b>"
    ),
    "history":      "📋 <b>Последние {n} транзакций:</b>\n\n{rows}",
    "no_txn":       "📭 Транзакций пока нет.",
    "weekly":       "📊 <b>Недельный отчёт:</b>\n\n⬆️ Доход: <b>{inc}</b>\n⬇️ Расход: <b>{exp}</b>\n📈 Баланс: <b>{bal}</b>",
    "reminder":     "⏰ Сегодня не записали расходы! Запишите 💸",
    "voice_wait":   "🎤 Анализирую голос...",
    "voice_done":   "🎤 Услышал: <i>«{text}»</i>",
    "voice_fail":   "😕 Не понял. Попробуйте снова или напишите текстом.",
    "voice_off":    "🎤 Голос недоступен.",
    "ocr_wait":     "📸 Читаю чек...",
    "ocr_done":     "📸 С чека: <b>{amount} сум</b> — сохранено!",
    "ocr_fail":     "😕 Не смог прочитать чек.",
    "ocr_off":      "📸 OCR недоступен.",
    "rate_title":   "💱 <b>Курс валют (ЦБУ):</b>\n",
    "rate_fail":    "😕 Не удалось загрузить курс.",
    "unknown":      "🤔 Не понял.\n\n<b>Пример:</b> <code>20000 еда</code>\n🎤 Или голосовое",
    "goals_empty":  "🎯 Целей пока нет.\n\n<code>/addgoal MacBook 10000000</code>",
    "goal_added":   "🎯 Цель добавлена!\n\n📌 <b>{name}</b>\n💰 {target}",
    "goal_fmt":     "Формат: <code>/addgoal MacBook 10000000</code>",
    "goal_list":    "🎯 <b>Ваши цели:</b>\n\n{items}",
    "goal_item":    "• <b>{name}</b>: {cur}/{tgt} ({pct}%)\n  {bar}",
    "motivation":   "🏆 Цель <b>«{name}»</b> выполнена на <b>{pct}%</b>! 💪",
    "goal_done_msg":"🎉 Цель <b>«{name}»</b> достигнута! Поздравляем!",
    "group_made":   "👥 Группа создана!\n\nID: <code>{gid}</code>\nПрисоединиться: <code>/join {gid}</code>",
    "group_joined": "👥 Вы присоединились к группе!",
    "group_nf":     "❌ Группа не найдена.",
    "group_rep":    "👥 <b>Отчёт группы:</b>\n\n{rows}",
    "no_group":     "❌ Не в группе.\n/group чтобы создать.",
    "btn_add":      "➕ Добавить",
    "btn_report":   "📊 Отчёт",
    "btn_history":  "📋 История",
    "btn_goals":    "🎯 Цели",
    "btn_group":    "👥 Группа",
    "btn_app":      "🚀 Открыть App",
    "btn_settings": "⚙️ Настройки",
    "btn_back":     "⬅️ Назад",
    "btn_lang":     "🌍 Изменить язык",
    "open_app":     "🚀 Открыть SpendUZ Pro",
},
"en": {
    "start":        "👋 Hello!\n\nChoose language:",
    "lang_set":     "✅ Language saved! Start logging your expenses.",
    "menu":         "🏠 Main menu",
    "help":         (
        "📝 <b>How to write:</b>\n\n"
        "💸 Expense: <code>20000 food</code>\n"
        "💰 Income: <code>3mln salary</code>\n"
        "💸 Lent: <code>lent 50000 Jasur</code>\n"
        "💰 Borrowed: <code>borrowed 100000 Ali</code>\n\n"
        "🎤 Or send voice!\n"
        "📸 Send receipt photo!"
    ),
    "saved_exp":    "✅ <b>Expense saved!</b>\n\n💸 {amount} {cur}\n📝 {note}\n🏷 {cat}",
    "saved_inc":    "✅ <b>Income saved!</b>\n\n💰 {amount} {cur}\n📝 {note}\n🏷 {cat}",
    "saved_dg":     "✅ <b>Lent money!</b>\n\n💸 {amount} {cur}\n👤 {note}",
    "saved_dt":     "✅ <b>Borrowed money!</b>\n\n💰 {amount} {cur}\n👤 {note}",
    "edit_btn":     "✏️ Edit",
    "del_btn":      "🗑 Delete",
    "deleted":      "🗑 Deleted!",
    "edit_ask":     "✏️ Enter new amount:\nExample: <code>25000</code>",
    "edit_done":    "✅ Updated! New amount: <b>{amount}</b>",
    "report":       (
        "📊 <b>Report {month}:</b>\n\n"
        "⬆️ Income:   <b>{income}</b>\n"
        "⬇️ Expense:  <b>{expense}</b>\n"
        "💸 Lent:     <b>{dg}</b>\n"
        "💰 Borrowed: <b>{dt}</b>\n"
        "━━━━━━━━━━━━\n"
        "📈 Balance: <b>{balance}</b>"
    ),
    "history":      "📋 <b>Last {n} transactions:</b>\n\n{rows}",
    "no_txn":       "📭 No transactions yet.",
    "weekly":       "📊 <b>Weekly report:</b>\n\n⬆️ Income: <b>{inc}</b>\n⬇️ Expense: <b>{exp}</b>\n📈 Balance: <b>{bal}</b>",
    "reminder":     "⏰ You forgot to log today's expenses! 💸",
    "voice_wait":   "🎤 Analyzing voice...",
    "voice_done":   "🎤 Heard: <i>«{text}»</i>",
    "voice_fail":   "😕 Could not understand. Try again or type.",
    "voice_off":    "🎤 Voice unavailable.",
    "ocr_wait":     "📸 Reading receipt...",
    "ocr_done":     "📸 From receipt: <b>{amount}</b> — saved!",
    "ocr_fail":     "😕 Could not read receipt.",
    "ocr_off":      "📸 OCR unavailable.",
    "rate_title":   "💱 <b>Exchange rates (CBU):</b>\n",
    "rate_fail":    "😕 Could not load rates.",
    "unknown":      "🤔 Did not understand.\n\n<b>Example:</b> <code>20000 food</code>\n🎤 Or send voice",
    "goals_empty":  "🎯 No goals yet.\n\n<code>/addgoal MacBook 10000000</code>",
    "goal_added":   "🎯 Goal added!\n\n📌 <b>{name}</b>\n💰 {target}",
    "goal_fmt":     "Format: <code>/addgoal MacBook 10000000</code>",
    "goal_list":    "🎯 <b>Your goals:</b>\n\n{items}",
    "goal_item":    "• <b>{name}</b>: {cur}/{tgt} ({pct}%)\n  {bar}",
    "motivation":   "🏆 Goal <b>«{name}»</b> is <b>{pct}%</b> done! 💪",
    "goal_done_msg":"🎉 Goal <b>«{name}»</b> achieved! Congratulations!",
    "group_made":   "👥 Group created!\n\nID: <code>{gid}</code>\nJoin: <code>/join {gid}</code>",
    "group_joined": "👥 Joined the group!",
    "group_nf":     "❌ Group not found.",
    "group_rep":    "👥 <b>Group report:</b>\n\n{rows}",
    "no_group":     "❌ Not in a group.\n/group to create.",
    "btn_add":      "➕ Add",
    "btn_report":   "📊 Report",
    "btn_history":  "📋 History",
    "btn_goals":    "🎯 Goals",
    "btn_group":    "👥 Group",
    "btn_app":      "🚀 Open App",
    "btn_settings": "⚙️ Settings",
    "btn_back":     "⬅️ Back",
    "btn_lang":     "🌍 Change language",
    "open_app":     "🚀 Open SpendUZ Pro",
},
"tj": {
    "start":        "👋 Салом!\n\nЗабонро интихоб кунед:",
    "lang_set":     "✅ Забон сабт шуд! Хароҷотро нависед.",
    "menu":         "🏠 Менюи асосӣ",
    "help":         (
        "📝 <b>Чӣ тавр навиштан:</b>\n\n"
        "💸 Хароҷот: <code>20000 хурок</code>\n"
        "💰 Даромад: <code>3млн маош</code>\n\n"
        "🎤 Ё овоз фиристед!\n"
        "📸 Акси чек!"
    ),
    "saved_exp":    "✅ <b>Хароҷот сабт шуд!</b>\n\n💸 {amount} {cur}\n📝 {note}\n🏷 {cat}",
    "saved_inc":    "✅ <b>Даромад сабт шуд!</b>\n\n💰 {amount} {cur}\n📝 {note}\n🏷 {cat}",
    "saved_dg":     "✅ <b>Қарз додам!</b>\n\n💸 {amount} {cur}\n👤 {note}",
    "saved_dt":     "✅ <b>Қарз гирифтам!</b>\n\n💰 {amount} {cur}\n👤 {note}",
    "edit_btn":     "✏️ Таҳрир",
    "del_btn":      "🗑 Нест",
    "deleted":      "🗑 Нест шуд!",
    "edit_ask":     "✏️ Маблағи навро ворид кунед:",
    "edit_done":    "✅ Навсозӣ шуд! Маблағи нав: <b>{amount}</b>",
    "report":       (
        "📊 <b>Ҳисоботи {month}:</b>\n\n"
        "⬆️ Даромад:  <b>{income}</b>\n"
        "⬇️ Хароҷот: <b>{expense}</b>\n"
        "━━━━━━━━━━━━\n"
        "📈 Баланс: <b>{balance}</b>"
    ),
    "history":      "📋 <b>{n} транзаксияи охир:</b>\n\n{rows}",
    "no_txn":       "📭 Транзаксия нест.",
    "weekly":       "📊 <b>Ҳисоботи ҳафтаӣ:</b>\n\n⬆️ Даромад: <b>{inc}</b>\n⬇️ Хароҷот: <b>{exp}</b>\n📈 Баланс: <b>{bal}</b>",
    "reminder":     "⏰ Имрӯз хароҷотро нанавиштед! 💸",
    "voice_wait":   "🎤 Овоз таҳлил мешавад...",
    "voice_done":   "🎤 Шунидам: <i>«{text}»</i>",
    "voice_fail":   "😕 Нафаҳмидам. Дубора фиристед.",
    "voice_off":    "🎤 Овоз дастрас нест.",
    "ocr_wait":     "📸 Чек хонда мешавад...",
    "ocr_done":     "📸 Аз чек: <b>{amount}</b> — сабт шуд!",
    "ocr_fail":     "😕 Чекро хонда натавонистам.",
    "ocr_off":      "📸 OCR дастрас нест.",
    "rate_title":   "💱 <b>Нархи асъор (БМТ):</b>\n",
    "rate_fail":    "😕 Нарх бор нашуд.",
    "unknown":      "🤔 Нафаҳмидам.\n\n<b>Мисол:</b> <code>20000 хурок</code>",
    "goals_empty":  "🎯 Мақсад нест.\n\n<code>/addgoal MacBook 10000000</code>",
    "goal_added":   "🎯 Мақсад илова шуд!\n\n📌 <b>{name}</b>\n💰 {target}",
    "goal_fmt":     "Формат: <code>/addgoal MacBook 10000000</code>",
    "goal_list":    "🎯 <b>Мақсадҳои шумо:</b>\n\n{items}",
    "goal_item":    "• <b>{name}</b>: {cur}/{tgt} ({pct}%)\n  {bar}",
    "motivation":   "🏆 Мақсади <b>«{name}»</b> {pct}% иҷро шуд! 💪",
    "goal_done_msg":"🎉 Мақсади <b>«{name}»</b> иҷро шуд! Муборак!",
    "group_made":   "👥 Гурух сохта шуд!\n\nID: <code>{gid}</code>",
    "group_joined": "👥 Ба гуруҳ ҳамроҳ шудед!",
    "group_nf":     "❌ Гурӯҳ ёфт нашуд.",
    "group_rep":    "👥 <b>Ҳисоботи гурӯҳ:</b>\n\n{rows}",
    "no_group":     "❌ Дар гурӯҳ нестед.\n/group барои сохтан.",
    "btn_add":      "➕ Илова",
    "btn_report":   "📊 Ҳисобот",
    "btn_history":  "📋 Таърих",
    "btn_goals":    "🎯 Мақсадҳо",
    "btn_group":    "👥 Гурӯҳ",
    "btn_app":      "🚀 Кушодани App",
    "btn_settings": "⚙️ Танзимот",
    "btn_back":     "⬅️ Бозгашт",
    "btn_lang":     "🌍 Иваз кардани забон",
    "open_app":     "🚀 Кушодани SpendUZ Pro",
},
}

def tx(uid, key, **kw):
    lang = get_lang(uid)
    s = T.get(lang, T["uz"]).get(key, T["uz"].get(key, key))
    for k, v in kw.items():
        s = s.replace("{" + k + "}", str(v))
    return s

# ── Category detection ─────────────────────────────────────────────────────────
CATS = {
    "food":      ["ovqat","taom","osh","non","gosht","sabzavot","meva","tushlik","nonushta",
                  "somsa","manti","lagman","shurva","burger","pizza","lavash","doner",
                  "bozor","bazar","supermarket","magazin","dukon","dokon","oziq","mahsulot",
                  "restoran","kafe","choyxona","stolovaya",
                  "еда","продукты","магазин","рынок","базар","обед","ужин","завтрак",
                  "хлеб","мясо","овощи","ресторан","столовая",
                  "food","grocery","supermarket","market","lunch","dinner","breakfast",
                  "restaurant","bakery","shop","store","meal",
                  "хурок","бозор","магоза"],
    "transport": ["taxi","taksi","yandex","uber","avto","mashina","bus","avtobus","metro",
                  "benzin","gaz","yoqilgi","moy","marshrutka","poyezd","tramvay",
                  "такси","машина","бензин","метро","автобус","маршрутка","поезд","заправка",
                  "taxi","uber","fuel","gas","car","parking","train","transport",
                  "нақлиёт","таксӣ"],
    "home":      ["ijara","kvartira","uy","xona","arenda","rent","kommunal","remont",
                  "mebel","elektr","isitish","santexnik","chilangar",
                  "аренда","квартира","ремонт","мебель","коммунальные","свет","вода",
                  "rent","repair","furniture","electricity","water","apartment","иҷора"],
    "health":    ["dori","dorixona","apteka","shifokor","doktor","klinika","kasalxona",
                  "tahlil","analiz","tish","koz","rentgen","massaj","vitamin","ukol",
                  "аптека","лекарство","врач","клиника","больница","анализ",
                  "pharmacy","medicine","doctor","hospital","clinic","vitamin","дорӯ"],
    "clothes":   ["kiyim","koylak","shim","kurtka","palto","poyabzal","botinka","krossovka",
                  "sviter","paypoq","sumka","belbog","qolqop",
                  "одежда","рубашка","штаны","куртка","обувь","кроссовки","сумка",
                  "clothes","shirt","pants","jacket","shoes","sneakers","bag","либос"],
    "cafe":      ["kofe","coffee","kapuchino","latte","espresso","choy","tea","sharbat",
                  "tort","konfet","shokolad","pechenye","bulochka","juice","smoothie",
                  "кофе","чай","торт","сок","шоколад","конфеты",
                  "cake","candy","pastry","chocolate"],
    "tech":      ["telefon","smartfon","iphone","samsung","xiaomi","laptop","noutbuk",
                  "kompyuter","planshet","ipad","naushnik","kolonka","kamera","printer",
                  "zaryadka","kabel","flesh","monitor","router",
                  "телефон","смартфон","ноутбук","компьютер","наушники",
                  "phone","computer","tablet","earphones","camera"],
    "entertainment":["kino","film","concert","teatr","muzey","park","zoo","game","netflix",
                     "bilyard","bowling","karaoke","youtube","spotify",
                     "кино","концерт","театр","игра","парк",
                     "cinema","movie","concert","entertainment"],
    "education": ["kurs","trening","kitob","darslik","seminar","univer","maktab","kollej",
                  "repetitor","sertifikat","imtihon","talim",
                  "образование","курс","книга","университет","школа","репетитор",
                  "course","book","university","school","training","tutor","маълумот"],
    "sport":     ["sport","gym","fitnes","trenajer","basketball","futbol","tennis",
                  "suzish","velosiped","yugurish","boks","karate","yoga","crossfit",
                  "спорт","тренажёр","фитнес","бассейн","бокс","футбол",
                  "fitness","swimming","running","boxing","варзиш"],
    "travel":    ["sayohat","avia","aviabilet","samolyot","hotel","mehmonxona",
                  "hostel","viza","ekskursiya","tur","dam",
                  "путешествие","билет","самолёт","отель","гостиница","виза",
                  "flight","ticket","hotel","visa","tour","trip","vacation","сафар"],
    "bills":     ["elektr","yoruglik","internet","wifi","gaz","suv","kommunal","sug'urta",
                  "obuna","subscription","insurance",
                  "электричество","интернет","коммунальные","страховка",
                  "electricity","bills","коммуналӣ"],
    "beauty":    ["sartarosh","soch","soqol","manikyur","pedikyur","kosmetika","parfum",
                  "atir","krem","shampun","salon","spa",
                  "парикмахер","маникюр","косметика","духи","крем","салон",
                  "haircut","manicure","cosmetics","perfume","salon"],
    "gift":      ["sovga","present","gift","bayram","tugilgan","birthday","toy","nikoh",
                  "подарок","праздник","день рождения","свадьба",
                  "gift","present","birthday","wedding","holiday"],
    "income":    ["maosh","oylik","ish haqi","salary","daromad","bonus","mukofot",
                  "зарплата","премия","доход","получил","заработал",
                  "salary","income","bonus","earned","wage","маош","даромад"],
}

CAT_EMOJI = {
    "food":"🍔","transport":"🚗","home":"🏠","health":"💊","clothes":"👗",
    "cafe":"☕","tech":"💻","entertainment":"🎮","education":"📚","sport":"⚽",
    "travel":"✈️","bills":"💡","beauty":"💅","gift":"🎁",
    "income":"💰","debt_given":"💸","debt_taken":"💰","other":"📦",
}

CAT_NAME = {
    "uz":  {"food":"Oziq-ovqat","transport":"Transport","home":"Uy-joy","health":"Salomatlik",
            "clothes":"Kiyim","cafe":"Kafe","tech":"Texnologiya","entertainment":"Ko'ngil ochish",
            "education":"Ta'lim","sport":"Sport","travel":"Sayohat","bills":"Kommunal",
            "beauty":"Go'zallik","gift":"Sovga","income":"Daromad","other":"Boshqa"},
    "ru":  {"food":"Еда","transport":"Транспорт","home":"Жильё","health":"Здоровье",
            "clothes":"Одежда","cafe":"Кафе","tech":"Технологии","entertainment":"Развлечения",
            "education":"Образование","sport":"Спорт","travel":"Путешествие","bills":"Коммунальные",
            "beauty":"Красота","gift":"Подарки","income":"Доход","other":"Другое"},
    "en":  {"food":"Food","transport":"Transport","home":"Housing","health":"Health",
            "clothes":"Clothes","cafe":"Cafe","tech":"Technology","entertainment":"Entertainment",
            "education":"Education","sport":"Sport","travel":"Travel","bills":"Bills",
            "beauty":"Beauty","gift":"Gifts","income":"Income","other":"Other"},
    "tj":  {"food":"Хурок","transport":"Нақлиёт","home":"Манзил","health":"Саломатӣ",
            "clothes":"Либос","cafe":"Кафе","tech":"Технология","entertainment":"Вақтгузаронӣ",
            "education":"Маълумот","sport":"Варзиш","travel":"Сафар","bills":"Коммуналӣ",
            "beauty":"Зебоӣ","gift":"Тӯҳфа","income":"Даромад","other":"Дигар"},
}

INCOME_KW = [
    "maosh","oylik","ish haqi","daromad","bonus","mukofot","foyda","topdi","topildi",
    "зарплата","премия","доход","бонус","получил","заработал","прибыль",
    "salary","income","bonus","earned","received","profit",
    "маош","даромад","бонус","фоида",
]
DEBT_GIVEN_KW = [
    "qarz berdim","qarz ber","berdim","qarz","долг дал","дал в долг","lent","gave",
    "қарз додам","берди",
]
DEBT_TAKEN_KW = [
    "qarz oldim","qarz ol","oldim","взял в долг","взял","borrowed","took loan",
    "қарз гирифтам","гирифтам",
]

def detect_cat(text: str) -> str:
    low = text.lower()
    for cat, words in CATS.items():
        if any(w in low for w in words):
            return cat
    return "other"

def detect_type(text: str) -> str:
    low = text.lower()
    if any(w in low for w in DEBT_GIVEN_KW): return "debt_given"
    if any(w in low for w in DEBT_TAKEN_KW): return "debt_taken"
    if any(w in low for w in INCOME_KW):     return "income"
    return "expense"

def cat_label(uid: int, cat: str) -> str:
    lang = get_lang(uid)
    return CAT_NAME.get(lang, CAT_NAME["uz"]).get(cat, cat)

def fmt(v) -> str:
    try: return f"{int(v):,}".replace(",", " ")
    except: return str(v)

def progress_bar(pct: int) -> str:
    f = min(10, pct // 10)
    return "█" * f + "░" * (10 - f) + f" {pct}%"


# ── Smart voice amount parser ──────────────────────────────────────────────────
def parse_amount(text: str) -> tuple[int | None, str]:
    """
    Parses amount from text in any language.
    Returns (amount, currency).
    Examples:
      "264 ming taksiga"   → (264000, "UZS")
      "2 million oylik"    → (2000000, "UZS")
      "32500"              → (32500, "UZS")
      "1050000"            → (1050000, "UZS")
      "50 dollar"          → (50, "USD")
    """
    low = text.lower().strip()

    # Currency detection
    cur = "UZS"
    if any(x in low for x in ["$", "dollar", "usd"]):  cur = "USD"
    elif any(x in low for x in ["€", "euro", "eur"]):  cur = "EUR"
    elif any(x in low for x in ["₽", "рубл", "rub"]):  cur = "RUB"

    # Extract all number groups
    nums = re.findall(r"\d+", text)
    if not nums:
        return None, cur

    # Check for written-out numbers first (UZ words)
    # e.g. "yigirma to'rt ming" - hard to parse, just take digits
    base = int(nums[0])
    second = int(nums[1]) if len(nums) > 1 else 0

    # Multiplier detection using word boundaries
    words = re.split(r"[\s,.\-]+", low)

    has_mln     = any(w in ["million","mln","mlrd","milliard","миллион","млн"] for w in words)
    has_ming    = any(w in ["ming","min","мин","тысяч","тыс","thousand"] for w in words)
    has_k       = any(w == "k" for w in words)
    has_hundred = any(w in ["yuz","сот","hundred"] for w in words)

    if has_mln:
        # "2 million" or "2.5 million"
        result = base * 1_000_000
        if second > 0 and second < 1000:
            result += second * 1000  # "2 million 500 ming" → 2,500,000
        return result, cur

    if has_ming or has_k:
        # "264 ming" → 264,000
        result = base * 1000
        if second > 0 and second < 1000:
            result += second  # "264 ming 500" → 264,500
        return result, cur

    if has_hundred:
        result = base * 100
        if second > 0:
            result += second
        return result, cur

    # No multiplier words - pure numbers
    # Handle case where STT splits: "1050000" → ["1050", "000"]
    if len(nums) > 1:
        # Check if second part is all zeros (e.g., "1050" + "000")
        if nums[1].strip("0") == "" or all(d == "0" for d in nums[1]):
            # Join them: "1050" + "000" = 1050000
            combined = int("".join(nums[:2]))
            return combined, cur
        # Otherwise just take first number
        return base, cur

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
        [KeyboardButton(text=T[l]["btn_add"]),     KeyboardButton(text=T[l]["btn_report"])],
        [KeyboardButton(text=T[l]["btn_history"]), KeyboardButton(text=T[l]["btn_goals"])],
        [KeyboardButton(text=T[l]["btn_group"]),   KeyboardButton(text=T[l]["btn_app"])],
        [KeyboardButton(text=T[l]["btn_settings"])],
    ], resize_keyboard=True)

def settings_kb(uid: int):
    l = get_lang(uid)
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=T[l]["btn_lang"])],
        [KeyboardButton(text=T[l]["btn_back"])],
    ], resize_keyboard=True)

def app_kb(uid: int):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=tx(uid,"open_app"), web_app=WebAppInfo(url=WEB_APP_URL))
    ]])

def action_kb(uid: int, tid: int):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=tx(uid,"edit_btn"), callback_data=f"edit_{tid}"),
        InlineKeyboardButton(text=tx(uid,"del_btn"),  callback_data=f"del_{tid}"),
    ]])


# ── Save & reply ───────────────────────────────────────────────────────────────
async def save_and_reply(msg: Message, uid: int, tx_type: str,
                         amount: int, currency: str, note: str):
    cat = detect_cat(note) if tx_type not in ("debt_given","debt_taken") else "other"
    if tx_type == "income" and cat == "other":
        cat = "income"
    tid = add_txn(uid, tx_type, amount, note, currency, cat)
    cl  = cat_label(uid, cat)
    em  = CAT_EMOJI.get(cat, "📦")

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
    await check_motivation(uid)


# ── Voice processing ───────────────────────────────────────────────────────────
async def voice_to_text(ogg_path: str) -> str | None:
    if not VOICE_OK:
        return None
    loop = asyncio.get_event_loop()
    def _run():
        try:
            audio = AudioSegment.from_ogg(ogg_path)
            wav   = ogg_path.replace(".ogg", ".wav")
            audio.export(wav, format="wav")
            r = sr.Recognizer()
            with sr.AudioFile(wav) as src:
                data = r.record(src)
            # Try 4 languages
            for lc in ["uz-UZ", "ru-RU", "en-US", "tg-TG"]:
                try:
                    result = r.recognize_google(data, language=lc)
                    if result:
                        return result
                except:
                    continue
            return None
        except Exception as e:
            log.error(f"voice: {e}")
            return None
    return await loop.run_in_executor(None, _run)


# ── OCR processing ─────────────────────────────────────────────────────────────
async def ocr_receipt(img_path: str) -> int | None:
    if not OCR_OK:
        return None
    loop = asyncio.get_event_loop()
    def _run():
        try:
            img  = Image.open(img_path)
            text = pytesseract.image_to_string(img, lang="uzb+rus+eng")
            nums = re.findall(r"\b(\d[\d ]{2,})\b", text)
            vals = []
            for n in nums:
                try: vals.append(int(n.replace(" ", "")))
                except: pass
            return max(vals) if vals else None
        except Exception as e:
            log.error(f"ocr: {e}")
            return None
    return await loop.run_in_executor(None, _run)


# ── CBU Rates ──────────────────────────────────────────────────────────────────
async def fetch_rates() -> dict | None:
    if not HTTP_OK:
        return None
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://cbu.uz/uz/arkhiv-kursov-valyut/json/",
                             timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json(content_type=None)
                return {x["Ccy"]: float(x["Rate"]) for x in data}
    except Exception as e:
        log.error(f"cbu: {e}")
        return None


# ── Motivation check ───────────────────────────────────────────────────────────
async def check_motivation(uid: int):
    for g in get_goals(uid):
        if g["target"] <= 0:
            continue
        pct  = round((g["current"] / g["target"]) * 100)
        last = g["notified_pct"]
        for milestone in [50, 80, 100]:
            if pct >= milestone > last:
                set_goal_notified(g["id"], milestone)
                if pct >= 100:
                    await bot.send_message(uid,
                        tx(uid, "goal_done_msg", name=g["name"]), parse_mode="HTML")
                else:
                    await bot.send_message(uid,
                        tx(uid, "motivation", name=g["name"], pct=pct), parse_mode="HTML")
                break


# ── Handlers ───────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(msg: Message):
    add_user(msg.from_user.id)
    await msg.answer(T["uz"]["start"], reply_markup=lang_kb())

@dp.callback_query(F.data.startswith("lang_"))
async def cb_lang(cb: CallbackQuery):
    uid  = cb.from_user.id
    lang = cb.data.split("_")[1]
    add_user(uid, lang)
    set_lang(uid, lang)
    await cb.message.edit_text(tx(uid, "lang_set"))
    await cb.message.answer(tx(uid, "menu"), reply_markup=main_kb(uid))
    await cb.message.answer("📱 App:", reply_markup=app_kb(uid))
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

@dp.message(Command("report"))
async def cmd_report(msg: Message):
    uid = msg.from_user.id
    s   = get_summary(uid)
    mon = datetime.now().strftime("%Y-%m")
    await msg.answer(tx(uid, "report",
        month=mon,
        income  = fmt(s["income"])   + " UZS",
        expense = fmt(s["expense"])  + " UZS",
        dg      = fmt(s["debt_given"])  + " UZS",
        dt      = fmt(s["debt_taken"])  + " UZS",
        balance = fmt(s["balance"])  + " UZS",
    ), parse_mode="HTML")

@dp.message(Command("history"))
async def cmd_history(msg: Message):
    uid  = msg.from_user.id
    txns = get_txns(uid, limit=10)
    if not txns:
        await msg.answer(tx(uid, "no_txn"))
        return
    rows = []
    for t in txns:
        em   = CAT_EMOJI.get(t["category"], "📦")
        sign = "+" if t["tx_type"] in ("income","debt_taken") else "-"
        rows.append(f"{em} <b>{sign}{fmt(t['amount'])}</b> {t['currency']} — {t['note'] or '-'} <i>({t['date']})</i>")
    await msg.answer(tx(uid,"history",n=len(rows),rows="\n".join(rows)), parse_mode="HTML")

@dp.message(Command("rate"))
async def cmd_rate(msg: Message):
    uid   = msg.from_user.id
    rates = await fetch_rates()
    if not rates:
        await msg.answer(tx(uid,"rate_fail"))
        return
    lines = [tx(uid,"rate_title")]
    for code in ["USD","EUR","RUB","GBP","CNY","KZT","TRY"]:
        if code in rates:
            lines.append(f"• <b>{code}</b>: {rates[code]:,.0f} so'm")
    await msg.answer("\n".join(lines), parse_mode="HTML")

@dp.message(Command("goals"))
async def cmd_goals(msg: Message):
    uid   = msg.from_user.id
    goals = get_goals(uid)
    if not goals:
        await msg.answer(tx(uid,"goals_empty"), parse_mode="HTML")
        return
    items = []
    for g in goals:
        pct = round((g["current"]/g["target"])*100) if g["target"] > 0 else 0
        items.append(tx(uid,"goal_item",
            name=g["name"],
            cur=fmt(g["current"]),
            tgt=fmt(g["target"]),
            pct=pct, bar=progress_bar(pct)))
    await msg.answer(tx(uid,"goal_list",items="\n".join(items)), parse_mode="HTML")

@dp.message(Command("addgoal"))
async def cmd_addgoal(msg: Message):
    uid  = msg.from_user.id
    args = (msg.text or "").split(maxsplit=2)
    if len(args) < 3:
        await msg.answer(tx(uid,"goal_fmt"), parse_mode="HTML")
        return
    name = args[1]
    amount, _ = parse_amount(args[2])
    if not amount:
        await msg.answer(tx(uid,"goal_fmt"), parse_mode="HTML")
        return
    add_goal(uid, name, amount)
    await msg.answer(tx(uid,"goal_added",name=name,target=fmt(amount)+" so'm"), parse_mode="HTML")

@dp.message(Command("group"))
async def cmd_group(msg: Message):
    uid = msg.from_user.id
    gid = create_group(uid)
    await msg.answer(tx(uid,"group_made",gid=gid), parse_mode="HTML")

@dp.message(Command("join"))
async def cmd_join(msg: Message):
    uid  = msg.from_user.id
    args = (msg.text or "").split()
    if len(args) < 2:
        await msg.answer("Format: /join <group_id>")
        return
    ok = join_group(args[1], uid)
    await msg.answer(tx(uid,"group_joined" if ok else "group_nf"))

@dp.message(Command("groupreport"))
async def cmd_grouprep(msg: Message):
    uid = msg.from_user.id
    gid = get_user_group(uid)
    if not gid:
        await msg.answer(tx(uid,"no_group"))
        return
    members = get_group_members(gid)
    rows = []
    for mid in members:
        s = get_summary(mid)
        rows.append(f"👤 <code>{mid}</code>:\n  💸 {fmt(s['expense'])} / 💰 {fmt(s['income'])} UZS")
    await msg.answer(tx(uid,"group_rep",rows="\n\n".join(rows)), parse_mode="HTML")


# ── Voice handler ──────────────────────────────────────────────────────────────
@dp.message(F.voice)
async def voice_handler(msg: Message):
    uid = msg.from_user.id
    add_user(uid)
    if not VOICE_OK:
        await msg.answer(tx(uid,"voice_off"))
        return
    wait = await msg.answer(tx(uid,"voice_wait"))
    try:
        f      = await bot.get_file(msg.voice.file_id)
        ogg    = str(Path(tempfile.gettempdir()) / f"v_{uid}.ogg")
        await bot.download_file(f.file_path, destination=ogg)
        text   = await voice_to_text(ogg)
        for p in [ogg, ogg.replace(".ogg",".wav")]:
            try: Path(p).unlink(missing_ok=True)
            except: pass
        if not text:
            await wait.delete()
            await msg.answer(tx(uid,"voice_fail"))
            return
        await wait.edit_text(tx(uid,"voice_done",text=text), parse_mode="HTML")
        # Parse
        amount, currency = parse_amount(text)
        if not amount:
            await msg.answer(tx(uid,"voice_fail"))
            return
        tx_type = detect_type(text)
        await save_and_reply(msg, uid, tx_type, amount, currency, text)
    except Exception as e:
        log.error(f"voice handler: {e}")
        try: await wait.delete()
        except: pass
        await msg.answer(tx(uid,"voice_fail"))


# ── Photo / OCR handler ────────────────────────────────────────────────────────
@dp.message(F.photo)
async def photo_handler(msg: Message):
    uid = msg.from_user.id
    add_user(uid)
    if not OCR_OK:
        await msg.answer(tx(uid,"ocr_off"))
        return
    wait = await msg.answer(tx(uid,"ocr_wait"))
    try:
        photo = msg.photo[-1]
        f     = await bot.get_file(photo.file_id)
        img   = str(Path(tempfile.gettempdir()) / f"r_{uid}.jpg")
        await bot.download_file(f.file_path, destination=img)
        amount = await ocr_receipt(img)
        try: Path(img).unlink(missing_ok=True)
        except: pass
        if not amount:
            await wait.delete()
            await msg.answer(tx(uid,"ocr_fail"))
            return
        await wait.delete()
        tid = add_txn(uid, "expense", amount, "Chek", "UZS", "other")
        await msg.answer(tx(uid,"ocr_done",amount=fmt(amount)), parse_mode="HTML",
                         reply_markup=action_kb(uid, tid))
    except Exception as e:
        log.error(f"photo: {e}")
        try: await wait.delete()
        except: pass
        await msg.answer(tx(uid,"ocr_fail"))


# ── Text handler ───────────────────────────────────────────────────────────────
@dp.message(F.text)
async def text_handler(msg: Message):
    uid  = msg.from_user.id
    lang = get_lang(uid)
    text = (msg.text or "").strip()
    add_user(uid)

    # Handle edit state
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
        else:
            del states[uid]

    # Menu buttons — check all langs
    btn_map = {
        "btn_add":      lambda: msg.answer(tx(uid,"help"), parse_mode="HTML"),
        "btn_report":   lambda: cmd_report(msg),
        "btn_history":  lambda: cmd_history(msg),
        "btn_goals":    lambda: cmd_goals(msg),
        "btn_group":    lambda: cmd_group(msg),
        "btn_app":      lambda: msg.answer("📱", reply_markup=app_kb(uid)),
        "btn_settings": lambda: msg.answer(tx(uid,"menu"), reply_markup=settings_kb(uid)),
        "btn_back":     lambda: msg.answer(tx(uid,"menu"), reply_markup=main_kb(uid)),
        "btn_lang":     lambda: msg.answer(T["uz"]["start"], reply_markup=lang_kb()),
    }
    for key, action in btn_map.items():
        all_vals = [T[l][key] for l in ["uz","ru","en","tj"] if key in T[l]]
        if text in all_vals:
            await action()
            return

    if text.startswith("/"):
        return

    # Parse transaction
    amount, currency = parse_amount(text)
    if not amount:
        await msg.answer(tx(uid,"unknown"), parse_mode="HTML")
        return

    tx_type = detect_type(text)
    await save_and_reply(msg, uid, tx_type, amount, currency, text)


# ── Scheduled tasks ────────────────────────────────────────────────────────────
async def smart_reminder():
    """Every day at 21:00 — only for users who haven't logged today"""
    while True:
        now = datetime.now()
        if now.hour == 21 and now.minute == 0:
            for uid in all_users():
                if not has_txn_today(uid):
                    try:
                        await bot.send_message(uid, tx(uid,"reminder"))
                    except:
                        pass
            await asyncio.sleep(61)
        await asyncio.sleep(20)

async def weekly_report():
    """Every Monday at 09:00"""
    while True:
        now = datetime.now()
        if now.weekday() == 0 and now.hour == 9 and now.minute == 0:
            for uid in all_users():
                s = get_summary(uid)
                if s["income"] == 0 and s["expense"] == 0:
                    continue
                try:
                    await bot.send_message(uid, tx(uid,"weekly",
                        inc=fmt(s["income"])+"  UZS",
                        exp=fmt(s["expense"])+" UZS",
                        bal=fmt(s["balance"])+" UZS"), parse_mode="HTML")
                except:
                    pass
            await asyncio.sleep(61)
        await asyncio.sleep(20)

async def daily_rates():
    """Every day at 09:00 — CBU rates"""
    while True:
        now = datetime.now()
        if now.hour == 9 and now.minute == 1:
            rates = await fetch_rates()
            if rates:
                lines = ["💱 <b>Bugungi kurs (CBU):</b>"]
                for code in ["USD","EUR","RUB"]:
                    if code in rates:
                        lines.append(f"• <b>{code}</b>: {rates[code]:,.0f} so'm")
                text = "\n".join(lines)
                for uid in all_users():
                    try:
                        await bot.send_message(uid, text, parse_mode="HTML")
                    except:
                        pass
            await asyncio.sleep(61)
        await asyncio.sleep(20)


# ── Main ───────────────────────────────────────────────────────────────────────
async def main():
    init_db()
    log.info("✅ Database initialized")
    log.info(f"🎤 Voice: {'ON' if VOICE_OK else 'OFF'}")
    log.info(f"📸 OCR:   {'ON' if OCR_OK  else 'OFF'}")
    log.info(f"🌐 HTTP:  {'ON' if HTTP_OK  else 'OFF'}")
    log.info("🚀 Bot started!")

    asyncio.create_task(smart_reminder())
    asyncio.create_task(weekly_report())
    asyncio.create_task(daily_rates())

    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())