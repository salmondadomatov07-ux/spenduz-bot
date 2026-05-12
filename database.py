"""SpendUZ Pro — database.py"""
import sqlite3
from pathlib import Path
from datetime import datetime

DB = Path(__file__).resolve().parent / "spenduz.db"


def con():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    db = con()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        user_id   INTEGER PRIMARY KEY,
        lang      TEXT DEFAULT 'uz',
        joined_at TEXT
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
    CREATE TABLE IF NOT EXISTS groups_tbl(
        group_id   TEXT PRIMARY KEY,
        owner_id   INTEGER,
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS group_members(
        group_id TEXT,
        user_id  INTEGER,
        PRIMARY KEY(group_id, user_id)
    );
    """)
    db.commit()
    db.close()


# ── USERS ──────────────────────────────────────────────────────────────────────
def add_user(uid: int, lang: str = "uz"):
    db = con()
    db.execute("INSERT OR IGNORE INTO users(user_id,lang,joined_at) VALUES(?,?,?)",
               (uid, lang, datetime.now().isoformat()))
    db.commit(); db.close()

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


# ── TRANSACTIONS ───────────────────────────────────────────────────────────────
def add_txn(uid, tx_type, amount, note, currency, category) -> int:
    db = con()
    now = datetime.now()
    cur = db.execute(
        "INSERT INTO transactions(user_id,tx_type,amount,note,category,currency,date,created_at)"
        " VALUES(?,?,?,?,?,?,?,?)",
        (uid, tx_type, amount, note, currency, category,
         now.strftime("%Y-%m-%d"), now.isoformat()))
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

def add_to_goal(gid: int, uid: int, amount: float):
    db = con()
    db.execute("UPDATE goals SET current=MIN(target,current+?) WHERE id=? AND user_id=?",
               (amount, gid, uid))
    db.commit()
    r = db.execute("SELECT * FROM goals WHERE id=?", (gid,)).fetchone()
    db.close()
    return dict(r) if r else None

def set_goal_notified(gid: int, pct: int):
    db = con()
    db.execute("UPDATE goals SET notified_pct=? WHERE id=?", (pct, gid))
    db.commit(); db.close()

def delete_goal(gid: int, uid: int) -> bool:
    db = con()
    cur = db.execute("DELETE FROM goals WHERE id=? AND user_id=?", (gid, uid))
    db.commit(); ok = cur.rowcount > 0; db.close()
    return ok


# ── GROUPS ─────────────────────────────────────────────────────────────────────
def create_group(uid: int) -> str:
    gid = f"g{uid}"
    db = con()
    db.execute("INSERT OR IGNORE INTO groups_tbl(group_id,owner_id,created_at) VALUES(?,?,?)",
               (gid, uid, datetime.now().isoformat()))
    db.execute("INSERT OR IGNORE INTO group_members(group_id,user_id) VALUES(?,?)", (gid, uid))
    db.commit(); db.close()
    return gid

def join_group(gid: str, uid: int) -> bool:
    db = con()
    r = db.execute("SELECT group_id FROM groups_tbl WHERE group_id=?", (gid,)).fetchone()
    if not r:
        db.close(); return False
    db.execute("INSERT OR IGNORE INTO group_members(group_id,user_id) VALUES(?,?)", (gid, uid))
    db.commit(); db.close()
    return True

def get_group_members(gid: str) -> list:
    db = con()
    rows = db.execute("SELECT user_id FROM group_members WHERE group_id=?", (gid,)).fetchall()
    db.close()
    return [r["user_id"] for r in rows]

def get_user_group(uid: int):
    db = con()
    r = db.execute("SELECT group_id FROM group_members WHERE user_id=? LIMIT 1", (uid,)).fetchone()
    db.close()
    return r["group_id"] if r else None