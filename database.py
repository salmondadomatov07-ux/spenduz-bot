"""SpendUZ Pro — database.py v2.0"""
import sqlite3
import random
import string
from pathlib import Path
from datetime import datetime, timedelta

DB = Path(__file__).resolve().parent / "spenduz.db"

def con():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    db = con()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        user_id       INTEGER PRIMARY KEY,
        lang          TEXT DEFAULT 'uz',
        is_premium    INTEGER DEFAULT 0,
        premium_until TEXT DEFAULT NULL,
        referral_code TEXT DEFAULT NULL,
        referred_by   INTEGER DEFAULT NULL,
        joined_at     TEXT,
        last_txn_date TEXT DEFAULT NULL
    );
    CREATE TABLE IF NOT EXISTS transactions(
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER,
        tx_type    TEXT,
        amount     REAL,
        note       TEXT DEFAULT '',
        category   TEXT DEFAULT 'other',
        currency   TEXT DEFAULT 'UZS',
        date       TEXT,
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS goals(
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER,
        name         TEXT,
        target       REAL,
        current      REAL DEFAULT 0,
        deadline     TEXT DEFAULT '',
        notified_pct INTEGER DEFAULT 0,
        created_at   TEXT
    );
    CREATE TABLE IF NOT EXISTS cards(
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER,
        card_name  TEXT DEFAULT '',
        last4      TEXT,
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS referrals(
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referred_id INTEGER,
        created_at  TEXT,
        UNIQUE(referrer_id, referred_id)
    );
    """)
    # Migrate: add missing columns
    try:
        db.execute("ALTER TABLE users ADD COLUMN last_txn_date TEXT DEFAULT NULL")
    except: pass
    try:
        db.execute("ALTER TABLE cards ADD COLUMN card_name TEXT DEFAULT ''")
    except: pass
    try:
        db.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER DEFAULT NULL")
    except: pass
    db.commit()
    db.close()

# ── USERS ──────────────────────────────────────────────────────────────────────
def add_user(uid: int, lang: str = "uz"):
    db = con()
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    db.execute(
        "INSERT OR IGNORE INTO users(user_id,lang,referral_code,joined_at) VALUES(?,?,?,?)",
        (uid, lang, code, datetime.now().isoformat()))
    db.commit(); db.close()

def get_user(uid: int):
    db = con()
    r = db.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
    db.close()
    return dict(r) if r else None

def get_lang(uid: int) -> str:
    db = con()
    r = db.execute("SELECT lang FROM users WHERE user_id=?", (uid,)).fetchone()
    db.close()
    return r["lang"] if r else "uz"

def set_lang(uid: int, lang: str):
    db = con()
    db.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, uid))
    db.commit(); db.close()

def all_users() -> list:
    db = con()
    rows = db.execute("SELECT user_id FROM users").fetchall()
    db.close()
    return [r["user_id"] for r in rows]

def is_premium(uid: int) -> bool:
    db = con()
    r = db.execute("SELECT is_premium, premium_until FROM users WHERE user_id=?", (uid,)).fetchone()
    db.close()
    if not r or not r["is_premium"]: return False
    if r["premium_until"]:
        try:
            return datetime.fromisoformat(r["premium_until"]) > datetime.now()
        except: return False
    return True

def get_premium_until(uid: int) -> str:
    db = con()
    r = db.execute("SELECT premium_until FROM users WHERE user_id=?", (uid,)).fetchone()
    db.close()
    return r["premium_until"] if r else None

def set_premium(uid: int, days: int):
    db = con()
    r = db.execute("SELECT premium_until, is_premium FROM users WHERE user_id=?", (uid,)).fetchone()
    now = datetime.now()
    if r and r["is_premium"] and r["premium_until"]:
        try:
            existing = datetime.fromisoformat(r["premium_until"])
            if existing > now:
                until = (existing + timedelta(days=days)).isoformat()
            else:
                until = (now + timedelta(days=days)).isoformat()
        except:
            until = (now + timedelta(days=days)).isoformat()
    else:
        until = (now + timedelta(days=days)).isoformat()
    db.execute("UPDATE users SET is_premium=1, premium_until=? WHERE user_id=?", (until, uid))
    db.commit(); db.close()

def get_referral_code(uid: int) -> str:
    db = con()
    r = db.execute("SELECT referral_code FROM users WHERE user_id=?", (uid,)).fetchone()
    db.close()
    return r["referral_code"] if r else ""

def get_referral_count(uid: int) -> int:
    db = con()
    r = db.execute("SELECT COUNT(*) as c FROM referrals WHERE referrer_id=?", (uid,)).fetchone()
    db.close()
    return r["c"] if r else 0

def use_referral(code: str, new_uid: int) -> int:
    """Returns referrer uid or 0. Each pair can only refer once."""
    db = con()
    # Find referrer by code
    r = db.execute("SELECT user_id FROM users WHERE referral_code=?", (code,)).fetchone()
    if not r or r["user_id"] == new_uid:
        db.close(); return 0
    referrer = r["user_id"]
    # Check if this pair already used referral
    ex = db.execute("SELECT id FROM referrals WHERE referrer_id=? AND referred_id=?",
                    (referrer, new_uid)).fetchone()
    if ex:
        db.close(); return 0
    # Check if new user already has a referrer
    me = db.execute("SELECT referred_by FROM users WHERE user_id=?", (new_uid,)).fetchone()
    if me and me["referred_by"]:
        db.close(); return 0
    # Record referral
    db.execute("INSERT OR IGNORE INTO referrals(referrer_id,referred_id,created_at) VALUES(?,?,?)",
               (referrer, new_uid, datetime.now().isoformat()))
    db.execute("UPDATE users SET referred_by=? WHERE user_id=?", (referrer, new_uid))
    db.commit(); db.close()
    return referrer

# ── TRANSACTIONS ───────────────────────────────────────────────────────────────
def add_txn(uid, tx_type, amount, note, currency, category) -> int:
    db = con()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    cur = db.execute(
        "INSERT INTO transactions(user_id,tx_type,amount,note,category,currency,date,created_at)"
        " VALUES(?,?,?,?,?,?,?,?)",
        (uid, tx_type, amount, note, currency, category, today, now.isoformat()))
    # Update last_txn_date
    db.execute("UPDATE users SET last_txn_date=? WHERE user_id=?", (today, uid))
    db.commit(); tid = cur.lastrowid; db.close()
    return tid

def get_txns(uid: int, limit: int = 0) -> list:
    db = con()
    if limit:
        rows = db.execute("SELECT * FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT ?",
                         (uid, limit)).fetchall()
    else:
        rows = db.execute("SELECT * FROM transactions WHERE user_id=? ORDER BY id DESC",
                         (uid,)).fetchall()
    db.close()
    return [dict(r) for r in rows]

def get_txn(tid: int, uid: int):
    db = con()
    r = db.execute("SELECT * FROM transactions WHERE id=? AND user_id=?", (tid, uid)).fetchone()
    db.close()
    return dict(r) if r else None

def update_txn(tid: int, uid: int, amount: float, note: str, category: str, tx_type: str) -> bool:
    db = con()
    cur = db.execute(
        "UPDATE transactions SET amount=?,note=?,category=?,tx_type=? WHERE id=? AND user_id=?",
        (amount, note, category, tx_type, tid, uid))
    db.commit(); ok = cur.rowcount > 0; db.close()
    return ok

def delete_txn(tid: int, uid: int) -> bool:
    db = con()
    cur = db.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (tid, uid))
    db.commit(); ok = cur.rowcount > 0; db.close()
    return ok

def get_summary(uid: int, month: str = None) -> dict:
    if not month:
        month = datetime.now().strftime("%Y-%m")
    db = con()
    rows = db.execute(
        "SELECT tx_type, SUM(amount) as total FROM transactions"
        " WHERE user_id=? AND date LIKE ? GROUP BY tx_type",
        (uid, f"{month}%")).fetchall()
    db.close()
    res = {"income": 0, "expense": 0, "debt_given": 0, "debt_taken": 0}
    for r in rows:
        if r["tx_type"] in res:
            res[r["tx_type"]] = r["total"] or 0
    res["balance"] = res["income"] + res["debt_taken"] - res["expense"] - res["debt_given"]
    return res

def get_cat_breakdown(uid: int, month: str = None) -> dict:
    if not month:
        month = datetime.now().strftime("%Y-%m")
    db = con()
    rows = db.execute(
        "SELECT category, SUM(amount) as total FROM transactions"
        " WHERE user_id=? AND date LIKE ? AND tx_type='expense'"
        " GROUP BY category ORDER BY total DESC",
        (uid, f"{month}%")).fetchall()
    db.close()
    return {r["category"]: r["total"] for r in rows}

def has_txn_today(uid: int) -> bool:
    today = datetime.now().strftime("%Y-%m-%d")
    db = con()
    r = db.execute("SELECT id FROM transactions WHERE user_id=? AND date=? LIMIT 1",
                  (uid, today)).fetchone()
    db.close()
    return r is not None

def had_txn_yesterday(uid: int) -> bool:
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    db = con()
    r = db.execute("SELECT id FROM transactions WHERE user_id=? AND date=? LIMIT 1",
                  (uid, yesterday)).fetchone()
    db.close()
    return r is not None

# ── GOALS ──────────────────────────────────────────────────────────────────────
def add_goal(uid: int, name: str, target: float, deadline: str = "") -> int:
    db = con()
    cur = db.execute(
        "INSERT INTO goals(user_id,name,target,current,deadline,created_at) VALUES(?,?,?,0,?,?)",
        (uid, name, target, deadline, datetime.now().isoformat()))
    db.commit(); gid = cur.lastrowid; db.close()
    return gid

def get_goals(uid: int) -> list:
    db = con()
    rows = db.execute("SELECT * FROM goals WHERE user_id=? ORDER BY id DESC", (uid,)).fetchall()
    db.close()
    return [dict(r) for r in rows]

def get_goal(gid: int, uid: int):
    db = con()
    r = db.execute("SELECT * FROM goals WHERE id=? AND user_id=?", (gid, uid)).fetchone()
    db.close()
    return dict(r) if r else None

def update_goal(gid: int, uid: int, name: str, target: float, deadline: str):
    db = con()
    db.execute("UPDATE goals SET name=?,target=?,deadline=? WHERE id=? AND user_id=?",
               (name, target, deadline, gid, uid))
    db.commit(); db.close()

def add_to_goal(gid: int, uid: int, amount: float):
    db = con()
    db.execute("UPDATE goals SET current=MIN(target,current+?) WHERE id=? AND user_id=?",
               (amount, gid, uid))
    db.commit()
    r = db.execute("SELECT * FROM goals WHERE id=?", (gid,)).fetchone()
    db.close()
    return dict(r) if r else None

def delete_goal(gid: int, uid: int) -> bool:
    db = con()
    cur = db.execute("DELETE FROM goals WHERE id=? AND user_id=?", (gid, uid))
    db.commit(); ok = cur.rowcount > 0; db.close()
    return ok

# ── CARDS ──────────────────────────────────────────────────────────────────────
def add_card(uid: int, card_name: str, last4: str) -> int:
    db = con()
    cur = db.execute(
        "INSERT INTO cards(user_id,card_name,last4,created_at) VALUES(?,?,?,?)",
        (uid, card_name, last4, datetime.now().isoformat()))
    db.commit(); cid = cur.lastrowid; db.close()
    return cid

def get_cards(uid: int) -> list:
    db = con()
    rows = db.execute("SELECT * FROM cards WHERE user_id=? ORDER BY id DESC", (uid,)).fetchall()
    db.close()
    return [dict(r) for r in rows]

def delete_card(cid: int, uid: int) -> bool:
    db = con()
    cur = db.execute("DELETE FROM cards WHERE id=? AND user_id=?", (cid, uid))
    db.commit(); ok = cur.rowcount > 0; db.close()
    return ok