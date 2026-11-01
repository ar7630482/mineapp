"""Parivaar shared-family finance and learning app.

Run with: streamlit run parivaar_vip_super_app.py

For durable hosted storage, set DATABASE_URL to a persistent PostgreSQL URL
(for example, a Supabase or Neon connection string) in the host's secrets.
Optional integrations: YOUTUBE_API_KEY and OPENAI_API_KEY. Keep all keys on the
server; never put them in browser code or commit them to a public repository.
"""

from __future__ import annotations

import calendar
import html
import io
import json
import os
import random
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    import qrcode
except ImportError:
    qrcode = None

try:
    from sqlalchemy import create_engine, text

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    create_engine = None
    text = None
    SQLALCHEMY_AVAILABLE = False


# -----------------------------------------------------------------------------
# Page, shared account and app defaults
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Parivaar | Shared Family Money",
    page_icon="🏡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PRIMARY_INCOME = 23_000.0
SPOUSE_INCOME = 15_000.0
DEFAULT_FAMILY_INCOME = PRIMARY_INCOME + SPOUSE_INCOME
SAVINGS_TARGET = 15_000.0
DEFAULT_SHOPPING_BUDGET = 6_000.0
DB_FILENAME = "parivaar_vip_v3.db"  # Reuses the original local database.

DEFAULT_USERS = [
    ("Ajay", "52729211", "Chief Admin", 1, "👑"),
    ("Meenakshi", "2345", "Family Member", 0, "👩‍💼"),
    ("Ajeet", "3456", "Family Member", 0, "🧑‍🎓"),
]

CATEGORIES = {
    "🍲 Food & Mess": [
        "Tea / snacks", "Office lunch / tiffin", "Milk / curd / bread",
        "Chicken / fish / eggs", "Mess / ration", "Other food",
    ],
    "🛒 Sabzi & Kirana": [
        "Vegetables", "Rice / flour / pulses / oil", "Kitchen supplies", "LPG", "Other grocery",
    ],
    "🏠 Rent & Bills": ["Room rent", "Electricity / water", "Internet / mobile", "Repairs", "Other bill"],
    "👪 Family Support": ["Parents support", "Village transfer", "Family need", "Other transfer"],
    "🩺 Medical": ["Ear treatment", "Medicines", "Tests / check-up", "Other medical"],
    "🚌 Travel": ["Metro / bus", "Auto / e-rickshaw", "Fuel", "Vehicle care", "Other travel"],
    "📚 Learning & Career": ["Course / book", "Exam / form fee", "Internet for study", "Other learning"],
    "🧺 Shopping": ["Clothing", "Household item", "Personal item", "Other shopping"],
    "✨ Other": ["Essential", "Unplanned", "Other"],
}

THEMES = {
    "👑 Maharaja Gold": {"bg": "#090b12", "card": "#151a27", "accent": "#f6c453", "sub": "#ffe6a1"},
    "⚡ Emerald": {"bg": "#061310", "card": "#10211e", "accent": "#42d6a4", "sub": "#b4f3d8"},
    "🌊 Calm Blue": {"bg": "#08111c", "card": "#111d2c", "accent": "#6bc8f2", "sub": "#c3eaff"},
    "🟣 Amethyst": {"bg": "#110c19", "card": "#1c1427", "accent": "#d89cff", "sub": "#efd3ff"},
    "🔥 Agni": {"bg": "#170d0c", "card": "#251512", "accent": "#ff9b55", "sub": "#ffdab9"},
}

MOTIVATION = [
    ("छोटी बचत, बड़े सपने। आज का समझदारी वाला फैसला कल का अपना घर बनाता है।", "आज का कदम: खर्च दर्ज करें और परिवार का साझा लक्ष्य साथ देखें।"),
    ("पैसा परिवार की टीम से मजबूत होता है—हर आमदनी और हर खर्च एक ही साझा हिसाब में।", "आज का कदम: खरीदारी से पहले बजट तय करें।"),
    ("हर रुपये को दिशा दें: ज़रूरत, बचत या सपना।", "आज का कदम: एक अनियोजित खर्च को टालकर लक्ष्य में जोड़ें।"),
    ("नियमितता ही असली तरक्की है। छोटे कदम भी घर के सपने को आगे बढ़ाते हैं।", "आज का कदम: 15 मिनट सीखने या हिसाब अपडेट करने में लगाएं।"),
    ("साथ मिलकर बनाया गया बजट, परिवार के हर सदस्य को साफ तस्वीर देता है।", "आज का कदम: अगली खरीदारी की अनुमानित लागत लिखें।"),
]

PROMPT_DOMAINS = {
    "🗣️ Spoken English & Office": [
        "Daily office meeting practice", "Polite client update", "Interview self-introduction",
        "Explaining a data report", "Confident phone conversation", "Professional email writing",
    ],
    "🐍 Python, SQL & Excel": [
        "Pandas Excel automation", "SQL window functions", "Excel XLOOKUP and pivots",
        "Python debugging for beginners", "Power Query cleanup", "Streamlit dashboard project",
    ],
    "🤖 AI & Productivity": [
        "Use AI to learn a new skill", "Build a useful prompt", "AI-assisted spreadsheet analysis",
        "Plan a small automation project", "Practice explaining AI simply", "Prepare for a technology interview",
    ],
    "🍲 Food & Home Cooking": [
        "Dal makhani at home", "Low-cost family dinner", "Quick chicken curry", "Crispy fish fry",
        "One-pot rice meal", "High-protein vegetarian dish",
    ],
}

CAREER_SKILLS = [
    ("english", "Daily spoken English practice"),
    ("python", "Python fundamentals and small automation"),
    ("excel", "Excel, XLOOKUP and Power Query"),
    ("sql", "SQL queries and database basics"),
    ("ai", "AI tools and prompt practice"),
    ("portfolio", "Build one project for a portfolio"),
]


def read_secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, default)
        if value:
            return str(value).strip()
    except Exception:
        pass
    return os.environ.get(name, default).strip()


DATABASE_URL = read_secret("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
if DATABASE_URL and not SQLALCHEMY_AVAILABLE:
    st.error("DATABASE_URL is set, but SQLAlchemy is missing. Install sqlalchemy and psycopg2-binary for PostgreSQL.")
    st.stop()

if os.environ.get("PARIVAAR_DB_PATH"):
    DB_FILE = Path(os.environ["PARIVAAR_DB_PATH"]).expanduser()
elif (Path.cwd() / DB_FILENAME).exists():
    DB_FILE = Path.cwd() / DB_FILENAME
else:
    DB_FILE = Path(__file__).resolve().parent / DB_FILENAME
DB_FILE.parent.mkdir(parents=True, exist_ok=True)


@st.cache_resource(show_spinner=False)
def get_engine(url: str):
    if not url:
        return None
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800, future=True)


ENGINE = get_engine(DATABASE_URL)
IS_POSTGRES = bool(DATABASE_URL)


@contextmanager
def open_db(write: bool = False):
    if ENGINE is not None:
        manager = ENGINE.begin() if write else ENGINE.connect()
        with manager as conn:
            yield conn
        return

    conn = sqlite3.connect(str(DB_FILE), timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    if write:
        conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        if write:
            conn.commit()
    except Exception:
        if write:
            conn.rollback()
        raise
    finally:
        conn.close()


def _execute(conn, sql: str, params: dict | None = None):
    params = params or {}
    if ENGINE is not None:
        return conn.execute(text(sql), params)
    return conn.execute(sql, params)


def db_rows(sql: str, params: dict | None = None) -> list[dict]:
    with open_db() as conn:
        result = _execute(conn, sql, params)
        if ENGINE is not None:
            return [dict(row) for row in result.mappings().all()]
        return [dict(row) for row in result.fetchall()]


def db_write(sql: str, params: dict | None = None) -> None:
    with open_db(write=True) as conn:
        _execute(conn, sql, params)


def db_insert_id(conn, sql: str, params: dict) -> int:
    if IS_POSTGRES:
        result = _execute(conn, sql + " RETURNING id", params)
        return int(result.scalar_one())
    return int(_execute(conn, sql, params).lastrowid)


def init_db() -> None:
    id_type = "BIGSERIAL PRIMARY KEY" if IS_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"
    statements = [
        f"""CREATE TABLE IF NOT EXISTS app_users (
            username TEXT PRIMARY KEY, password TEXT NOT NULL, role TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0, avatar TEXT DEFAULT '👤')""",
        f"""CREATE TABLE IF NOT EXISTS expenses (
            id {id_type}, timestamp TEXT NOT NULL, date_only TEXT NOT NULL,
            month_year TEXT NOT NULL, logged_by TEXT NOT NULL, spent_by TEXT NOT NULL,
            category TEXT NOT NULL, item_name TEXT NOT NULL, description TEXT,
            payment_mode TEXT, upi_app TEXT, need_level TEXT, amount REAL NOT NULL,
            is_bad_expense INTEGER DEFAULT 0, upi_id TEXT, notes TEXT)""",
        f"""CREATE TABLE IF NOT EXISTS vault_deposits (
            id {id_type}, timestamp TEXT NOT NULL, month_year TEXT NOT NULL,
            deposited_by TEXT NOT NULL, vault_bucket TEXT NOT NULL,
            amount REAL NOT NULL, notes TEXT)""",
        """CREATE TABLE IF NOT EXISTS career_progress (
            skill_key TEXT PRIMARY KEY, completed INTEGER DEFAULT 0, updated_at TEXT)""",
        """CREATE TABLE IF NOT EXISTS app_settings (
            setting_key TEXT PRIMARY KEY, setting_value TEXT NOT NULL)""",
        f"""CREATE TABLE IF NOT EXISTS income_entries (
            id {id_type}, timestamp TEXT NOT NULL, month_year TEXT NOT NULL,
            income_source TEXT NOT NULL, recorded_by TEXT NOT NULL,
            amount REAL NOT NULL, notes TEXT)""",
        f"""CREATE TABLE IF NOT EXISTS shopping_plans (
            id {id_type}, created_at TEXT NOT NULL, month_year TEXT NOT NULL,
            created_by TEXT NOT NULL, plan_name TEXT NOT NULL,
            budget REAL NOT NULL)""",
        f"""CREATE TABLE IF NOT EXISTS shopping_items (
            id {id_type}, plan_id BIGINT NOT NULL REFERENCES shopping_plans(id) ON DELETE CASCADE,
            item_name TEXT NOT NULL, expected_amount REAL NOT NULL, notes TEXT)""",
        f"""CREATE TABLE IF NOT EXISTS shopping_actuals (
            id {id_type}, item_id BIGINT NOT NULL REFERENCES shopping_items(id) ON DELETE CASCADE,
            expense_id BIGINT NOT NULL REFERENCES expenses(id), recorded_at TEXT NOT NULL,
            amount REAL NOT NULL)""",
    ]
    with open_db(write=True) as conn:
        for statement in statements:
            _execute(conn, statement)
        for username, password, role, is_admin, avatar in DEFAULT_USERS:
            if IS_POSTGRES:
                _execute(
                    conn,
                    "INSERT INTO app_users (username,password,role,is_admin,avatar) "
                    "VALUES (:u,:p,:r,:a,:v) ON CONFLICT (username) DO NOTHING",
                    {"u": username, "p": password, "r": role, "a": is_admin, "v": avatar},
                )
            else:
                _execute(
                    conn,
                    "INSERT OR IGNORE INTO app_users (username,password,role,is_admin,avatar) "
                    "VALUES (:u,:p,:r,:a,:v)",
                    {"u": username, "p": password, "r": role, "a": is_admin, "v": avatar},
                )
        _execute(conn, "UPDATE app_users SET is_admin=1, avatar='👑' WHERE username='Ajay'")
        if IS_POSTGRES:
            _execute(
                conn,
                "INSERT INTO app_settings (setting_key,setting_value) VALUES ('family_monthly_income','38000') "
                "ON CONFLICT (setting_key) DO NOTHING",
            )
        else:
            _execute(
                conn,
                "INSERT OR IGNORE INTO app_settings (setting_key,setting_value) "
                "VALUES ('family_monthly_income','38000')",
            )


try:
    init_db()
except Exception as exc:
    st.error(f"Database could not be opened or initialized: {exc}")
    st.stop()


def get_setting(key: str, default: str) -> str:
    rows = db_rows("SELECT setting_value FROM app_settings WHERE setting_key=:k", {"k": key})
    return str(rows[0]["setting_value"]) if rows else default


def set_setting(key: str, value: str) -> None:
    sql = (
        "INSERT INTO app_settings (setting_key,setting_value) VALUES (:k,:v) "
        "ON CONFLICT (setting_key) DO UPDATE SET setting_value=:v"
    )
    db_write(sql, {"k": key, "v": str(value)})


def users_dict() -> dict[str, dict]:
    rows = db_rows("SELECT username,password,role,is_admin,avatar FROM app_users ORDER BY is_admin DESC,username")
    return {
        str(r["username"]): {
            "password": str(r["password"]), "role": str(r["role"]),
            "is_admin": bool(r["is_admin"]), "avatar": str(r["avatar"] or "👤"),
        }
        for r in rows
    }


def upsert_user(name: str, password: str, role: str, admin: bool, avatar: str) -> None:
    sql = (
        "INSERT INTO app_users (username,password,role,is_admin,avatar) VALUES (:u,:p,:r,:a,:v) "
        "ON CONFLICT (username) DO UPDATE SET password=:p,role=:r,is_admin=:a,avatar=:v"
    )
    db_write(sql, {"u": name.strip(), "p": password.strip(), "r": role.strip(), "a": int(admin), "v": avatar})


def delete_user(name: str) -> None:
    if name.lower() != "ajay":
        db_write("DELETE FROM app_users WHERE username=:u", {"u": name})


def fetch_df(table: str, order: str = "id DESC") -> pd.DataFrame:
    allowed = {"expenses", "vault_deposits", "income_entries", "shopping_plans", "shopping_items", "shopping_actuals"}
    if table not in allowed:
        return pd.DataFrame()
    return pd.DataFrame(db_rows(f"SELECT * FROM {table} ORDER BY {order}"))


def insert_expense(conn, data: dict) -> int:
    columns = [
        "timestamp", "date_only", "month_year", "logged_by", "spent_by", "category", "item_name",
        "description", "payment_mode", "upi_app", "need_level", "amount", "is_bad_expense", "upi_id", "notes",
    ]
    sql = f"INSERT INTO expenses ({','.join(columns)}) VALUES ({','.join(':'+c for c in columns)})"
    return db_insert_id(conn, sql, data)


def add_expense(data: dict) -> int:
    now = datetime.now()
    values = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date_only": now.strftime("%Y-%m-%d"),
        "month_year": now.strftime("%Y-%m"),
        "logged_by": data.get("logged_by", ""),
        "spent_by": data.get("spent_by", "Joint Family"),
        "category": data.get("category", "✨ Other"),
        "item_name": data.get("item_name", "Expense"),
        "description": data.get("description", ""),
        "payment_mode": data.get("payment_mode", "Cash"),
        "upi_app": data.get("upi_app", ""),
        "need_level": data.get("need_level", "Essential"),
        "amount": float(data["amount"]),
        "is_bad_expense": int(bool(data.get("is_bad_expense", False))),
        "upi_id": data.get("upi_id", ""),
        "notes": data.get("notes", ""),
    }
    with open_db(write=True) as conn:
        return insert_expense(conn, values)


def add_income(source: str, recorded_by: str, amount: float, notes: str) -> None:
    now = datetime.now()
    db_write(
        "INSERT INTO income_entries (timestamp,month_year,income_source,recorded_by,amount,notes) "
        "VALUES (:ts,:m,:s,:u,:a,:n)",
        {"ts": now.strftime("%Y-%m-%d %H:%M:%S"), "m": now.strftime("%Y-%m"),
         "s": source, "u": recorded_by, "a": float(amount), "n": notes},
    )


def add_vault_deposit(who: str, bucket: str, amount: float, notes: str) -> None:
    now = datetime.now()
    db_write(
        "INSERT INTO vault_deposits (timestamp,month_year,deposited_by,vault_bucket,amount,notes) "
        "VALUES (:ts,:m,:u,:b,:a,:n)",
        {"ts": now.strftime("%Y-%m-%d %H:%M:%S"), "m": now.strftime("%Y-%m"),
         "u": who, "b": bucket, "a": float(amount), "n": notes},
    )


def create_shopping_plan(name: str, budget: float, created_by: str) -> int:
    now = datetime.now()
    with open_db(write=True) as conn:
        return db_insert_id(
            conn,
            "INSERT INTO shopping_plans (created_at,month_year,created_by,plan_name,budget) "
            "VALUES (:ts,:m,:u,:n,:b)",
            {"ts": now.strftime("%Y-%m-%d %H:%M:%S"), "m": now.strftime("%Y-%m"),
             "u": created_by, "n": name.strip(), "b": float(budget)},
        )


def add_shopping_item(plan_id: int, name: str, expected: float, notes: str) -> None:
    db_write(
        "INSERT INTO shopping_items (plan_id,item_name,expected_amount,notes) VALUES (:p,:n,:e,:x)",
        {"p": int(plan_id), "n": name.strip(), "e": float(expected), "x": notes},
    )


def add_shopping_actual(item_id: int, amount: float, paid_by: str, payment_mode: str, notes: str, logged_by: str) -> int:
    item_rows = db_rows(
        "SELECT i.item_name,p.plan_name FROM shopping_items i JOIN shopping_plans p ON p.id=i.plan_id WHERE i.id=:id",
        {"id": int(item_id)},
    )
    if not item_rows:
        raise ValueError("Shopping item not found")
    item = item_rows[0]
    now = datetime.now()
    expense = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "date_only": now.strftime("%Y-%m-%d"),
        "month_year": now.strftime("%Y-%m"), "logged_by": logged_by, "spent_by": paid_by,
        "category": "🧺 Shopping", "item_name": item["item_name"],
        "description": f"Shopping plan: {item['plan_name']}", "payment_mode": payment_mode,
        "upi_app": "", "need_level": "Planned shopping", "amount": float(amount),
        "is_bad_expense": 0, "upi_id": "", "notes": notes,
    }
    with open_db(write=True) as conn:
        expense_id = insert_expense(conn, expense)
        _execute(
            conn,
            "INSERT INTO shopping_actuals (item_id,expense_id,recorded_at,amount) VALUES (:i,:e,:t,:a)",
            {"i": int(item_id), "e": expense_id, "t": now.strftime("%Y-%m-%d %H:%M:%S"), "a": float(amount)},
        )
    return expense_id


def update_expense(expense_id: int, spent_by: str, category: str, item: str, amount: float, bad: bool, notes: str) -> None:
    params = {"u": spent_by, "c": category, "i": item, "a": float(amount), "b": int(bad), "n": notes, "id": int(expense_id)}
    with open_db(write=True) as conn:
        _execute(
            conn,
            "UPDATE expenses SET spent_by=:u,category=:c,item_name=:i,amount=:a,is_bad_expense=:b,notes=:n WHERE id=:id",
            params,
        )
        # Keep the shopping planner's actual total aligned with an admin correction.
        _execute(conn, "UPDATE shopping_actuals SET amount=:a WHERE expense_id=:id", {"a": float(amount), "id": int(expense_id)})


def delete_expense(expense_id: int) -> None:
    with open_db(write=True) as conn:
        _execute(conn, "DELETE FROM shopping_actuals WHERE expense_id=:id", {"id": int(expense_id)})
        _execute(conn, "DELETE FROM expenses WHERE id=:id", {"id": int(expense_id)})


def set_skill(skill_key: str, complete: bool) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db_write(
        "INSERT INTO career_progress (skill_key,completed,updated_at) VALUES (:k,:v,:t) "
        "ON CONFLICT (skill_key) DO UPDATE SET completed=:v,updated_at=:t",
        {"k": skill_key, "v": int(complete), "t": now},
    )


def get_skills() -> dict[str, bool]:
    return {r["skill_key"]: bool(r["completed"]) for r in db_rows("SELECT skill_key,completed FROM career_progress")}


def money(value: float) -> str:
    return f"₹{float(value):,.0f}"


def get_month_sum(df: pd.DataFrame, month: str, column: str = "amount") -> float:
    if df.empty or column not in df or "month_year" not in df:
        return 0.0
    return float(pd.to_numeric(df.loc[df["month_year"] == month, column], errors="coerce").fillna(0).sum())


def theme_css(theme_name: str) -> None:
    palette = THEMES.get(theme_name, THEMES["👑 Maharaja Gold"])
    st.markdown(
        f"""<style>
        #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {{visibility:hidden;}}
        .stApp {{background:radial-gradient(circle at 8% 0%, {palette['card']} 0%, {palette['bg']} 50%, #07090d 100%); color:#f8fafc;}}
        .block-container {{max-width:1180px; padding-top:1rem; padding-bottom:4rem;}}
        h1,h2,h3,h4,p,label,span {{color:#f8fafc;}}
        .hero {{background:linear-gradient(125deg,{palette['card']},#17283a);border:1px solid {palette['accent']};
          border-radius:22px;padding:22px 24px;margin:8px 0 16px;box-shadow:0 14px 35px #0006;}}
        .hero-kicker {{color:{palette['accent']};font-size:.78rem;letter-spacing:.12em;font-weight:900;text-transform:uppercase;}}
        .hero-quote {{font-size:1.2rem;font-weight:800;line-height:1.5;margin:8px 0;}}
        .hero-goal {{color:{palette['sub']};font-size:.94rem;}}
        div[data-testid="stMetric"] {{background:{palette['card']};border:1px solid #ffffff22;border-radius:16px;padding:14px;}}
        div[data-testid="stMetricValue"] {{color:{palette['accent']};font-weight:900;}}
        div[data-testid="stTabs"] button {{border-radius:12px 12px 0 0;font-weight:800;}}
        div.stButton>button,div.stFormSubmitButton>button,div.stDownloadButton>button {{border-radius:12px;min-height:42px;font-weight:800;}}
        div[data-testid="stExpander"] {{background:{palette['card']}66;border-radius:14px;}}
        .stProgress > div > div {{background:{palette['accent']};}}
        @media(max-width:700px){{.block-container{{padding-left:1rem;padding-right:1rem;}}.hero{{padding:17px;}}}}
        </style>""",
        unsafe_allow_html=True,
    )


def motivation_banner() -> None:
    day_index = date.today().toordinal() % len(MOTIVATION)
    quote, goal = MOTIVATION[day_index]
    st.markdown(
        f"<div class='hero'><div class='hero-kicker'>🏡 PARIVAAR • {date.today():%A, %d %b %Y}</div>"
        f"<div class='hero-quote'>“{html.escape(quote)}”</div>"
        f"<div class='hero-goal'>{html.escape(goal)}</div></div>",
        unsafe_allow_html=True,
    )


def get_video_api_key() -> str:
    return read_secret("YOUTUBE_API_KEY")


def get_openai_api_key() -> str:
    return read_secret("OPENAI_API_KEY")


def youtube_queries(query: str, mode: str) -> list[tuple[str, str]]:
    q = query.strip()
    food_terms = (
        "recipe", "food", "curry", "dal", "makhani", "chicken", "fish", "paneer", "biryani",
        "rice", "roti", "sabzi", "dosa", "idli", "egg", "cook", "khana", "रेसिपी", "दाल",
        "मक्खनी", "चिकन", "मछली", "पनीर", "खाना", "सब्जी",
    )
    food = mode == "Food" or (mode == "Auto" and any(term in q.lower() for term in food_terms))
    if food:
        return [
            ("🍳 Recipe / कैसे बनाएं", f"{q} recipe how to make Hindi #shorts"),
            ("⏱️ Preparation time / कितनी देर", f"{q} cooking time preparation quick recipe #shorts"),
            ("🧾 Ingredients & cost / सामग्री और खर्च", f"{q} ingredients cost budget price India #shorts"),
        ]
    return [
        ("🔎 Quick overview / परिचय", f"{q} explained overview #shorts"),
        ("🛠️ How-to / तरीका", f"{q} how to beginner guide #shorts"),
        ("💡 Tips & cost / सुझाव और खर्च", f"{q} tips price cost comparison #shorts"),
    ]


@st.cache_data(ttl=1800, show_spinner=False)
def youtube_search(api_key: str, search_text: str) -> dict:
    params = urllib.parse.urlencode(
        {"part": "snippet", "type": "video", "maxResults": 1, "videoEmbeddable": "true",
         "videoDuration": "short", "q": search_text, "key": api_key}
    )
    req = urllib.request.Request(
        f"https://www.googleapis.com/youtube/v3/search?{params}",
        headers={"Accept": "application/json", "User-Agent": "ParivaarApp/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
        items = []
        for row in data.get("items", []):
            video_id = row.get("id", {}).get("videoId", "")
            snippet = row.get("snippet", {})
            if video_id:
                items.append({"id": video_id, "title": snippet.get("title", "YouTube Short"),
                              "channel": snippet.get("channelTitle", "YouTube")})
        return {"items": items}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"items": [], "error": str(exc)}


def get_response_text(data: dict) -> str:
    if data.get("output_text"):
        return str(data["output_text"]).strip()
    chunks = []
    for item in data.get("output", []):
        for part in item.get("content", []):
            if part.get("type") in ("output_text", "text") and part.get("text"):
                chunks.append(part["text"])
    return "\n".join(chunks).strip()


def ai_overview(query: str, video_titles: list[str]) -> tuple[str | None, str | None]:
    api_key = get_openai_api_key()
    if not api_key:
        return None, "OPENAI_API_KEY is not configured. Add it in the app host's server-side secrets to enable the live AI overview."
    model = read_secret("OPENAI_MODEL", "gpt-6-astra")
    context = "\n".join(f"- {title}" for title in video_titles[:6]) or "No video results are available."
    prompt = (
        f"Give a concise, useful overview in simple Hindi/Hinglish for this search: {query!r}. "
        "Use headings: Summary, Useful next steps, Cost/time caveat. Do not invent live prices, exact cooking times, "
        "or facts from videos you have not watched. Treat the video titles below only as search clues. "
        "If it is a recipe, cover what to compare in recipes, preparation/cooking time, and how to estimate local ingredient cost. "
        f"Search-result title clues:\n{context}"
    )
    payload = json.dumps({"model": model, "input": prompt, "max_output_tokens": 500, "store": False}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses", data=payload, method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
        result = get_response_text(data)
        return (result or None), (None if result else "The AI response did not contain text.")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:700]
        return None, f"AI API returned HTTP {exc.code}: {detail}"
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return None, f"AI overview could not connect: {exc}"


def backup_zip() -> bytes:
    tables = ["expenses", "vault_deposits", "income_entries", "shopping_plans", "shopping_items", "shopping_actuals", "career_progress", "app_settings"]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for table in tables:
            rows = db_rows(f"SELECT * FROM {table}")
            archive.writestr(f"{table}.csv", pd.DataFrame(rows).to_csv(index=False))
    return buffer.getvalue()


# -----------------------------------------------------------------------------
# Theme and sign-in
# -----------------------------------------------------------------------------
if "selected_theme" not in st.session_state:
    st.session_state.selected_theme = "👑 Maharaja Gold"
theme_css(st.session_state.selected_theme)

USERS = users_dict()
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

if not st.session_state.authenticated_user or st.session_state.authenticated_user not in USERS:
    motivation_banner()
    st.markdown("## 👑 Parivaar — one family, one shared money pool")
    st.caption("Expenses and savings are tracked together for the household. Member names only show who recorded or made a transaction.")
    with st.form("login_form"):
        chosen_user = st.selectbox("Choose your profile", list(USERS), format_func=lambda n: f"{USERS[n]['avatar']} {n} · {USERS[n]['role']}")
        pin = st.text_input("Password / PIN", type="password")
        login = st.form_submit_button("🔓 Sign in", use_container_width=True)
    if login:
        if pin.strip() == USERS.get(chosen_user, {}).get("password"):
            st.session_state.authenticated_user = chosen_user
            st.rerun()
        else:
            st.error("That password did not match. Please try again.")
    st.stop()

CURRENT_USER = st.session_state.authenticated_user
CURRENT_INFO = USERS[CURRENT_USER]
IS_ADMIN = bool(CURRENT_INFO["is_admin"])

head_left, head_mid, head_right = st.columns([2.2, 1.4, 0.8])
with head_left:
    theme_name = st.selectbox("🎨 App theme", list(THEMES), index=list(THEMES).index(st.session_state.selected_theme))
    if theme_name != st.session_state.selected_theme:
        st.session_state.selected_theme = theme_name
        st.rerun()
with head_mid:
    st.markdown(f"<div style='padding-top:29px;font-weight:800'>{CURRENT_INFO['avatar']} {html.escape(CURRENT_USER)} · {'ADMIN' if IS_ADMIN else 'FAMILY'}</div>", unsafe_allow_html=True)
with head_right:
    st.markdown("<div style='padding-top:18px'></div>", unsafe_allow_html=True)
    if st.button("🔒 Log out", use_container_width=True):
        st.session_state.authenticated_user = None
        st.rerun()

motivation_banner()

if ENGINE is None:
    st.warning(
        f"Local SQLite storage is active at `{DB_FILE}`. It survives app sleep and normal restarts on this same persistent disk. "
        "A hosted service with an ephemeral filesystem can reset local files on redeploy; set DATABASE_URL to persistent PostgreSQL for hosted use."
    )
else:
    st.success("Persistent PostgreSQL storage is connected. Family expenses, shopping plans, and savings are stored centrally.")


# -----------------------------------------------------------------------------
# Current shared-household totals
# -----------------------------------------------------------------------------
TODAY = date.today()
MONTH = TODAY.strftime("%Y-%m")
ALL_EXPENSES = fetch_df("expenses")
ALL_INCOME = fetch_df("income_entries")
ALL_VAULT = fetch_df("vault_deposits")
ALL_PLANS = fetch_df("shopping_plans")

if not ALL_EXPENSES.empty:
    ALL_EXPENSES["amount"] = pd.to_numeric(ALL_EXPENSES["amount"], errors="coerce").fillna(0.0)
    ALL_EXPENSES["parsed_date"] = pd.to_datetime(ALL_EXPENSES["timestamp"], errors="coerce").dt.date
if not ALL_INCOME.empty:
    ALL_INCOME["amount"] = pd.to_numeric(ALL_INCOME["amount"], errors="coerce").fillna(0.0)
if not ALL_VAULT.empty:
    ALL_VAULT["amount"] = pd.to_numeric(ALL_VAULT["amount"], errors="coerce").fillna(0.0)

MONTH_SPEND = get_month_sum(ALL_EXPENSES, MONTH)
MONTH_INCOME_ACTUAL = get_month_sum(ALL_INCOME, MONTH)
MONTH_SAVED = get_month_sum(ALL_VAULT, MONTH)
ALL_SAVED = float(ALL_VAULT["amount"].sum()) if not ALL_VAULT.empty else 0.0
EXPECTED_INCOME = float(get_setting("family_monthly_income", str(DEFAULT_FAMILY_INCOME)))
INCOME_BASIS = MONTH_INCOME_ACTUAL if MONTH_INCOME_ACTUAL > 0 else EXPECTED_INCOME
INCOME_LABEL = "Recorded income" if MONTH_INCOME_ACTUAL > 0 else "Expected family income"
PLANNED_SPENDING_LIMIT = max(0.0, INCOME_BASIS - SAVINGS_TARGET)
SPENDING_LEFT = PLANNED_SPENDING_LIMIT - MONTH_SPEND
POOL_LEFT = INCOME_BASIS - MONTH_SPEND - MONTH_SAVED
DAYS_LEFT = max(1, calendar.monthrange(TODAY.year, TODAY.month)[1] - TODAY.day + 1)
SAFE_DAILY_SPEND = max(0.0, SPENDING_LEFT / DAYS_LEFT)

tabs = st.tabs([
    "🏠 Home", "💸 Add expense", "🛍️ Shopping", "🏦 Family money",
    "📊 Records", "▶️ YouTube Shorts & AI", "🚀 Learning & Admin",
])
tab_home, tab_expense, tab_shopping, tab_money, tab_records, tab_explore, tab_growth = tabs


# -----------------------------------------------------------------------------
# Home dashboard
# -----------------------------------------------------------------------------
with tab_home:
    st.subheader("🏡 Shared family snapshot")
    st.caption("Ajay's ₹23,000 and Meenakshi's ₹15,000 are sources feeding one ₹38,000 household pool—not separate spending accounts.")
    a, b, c, d = st.columns(4)
    a.metric("Family pool this month", money(INCOME_BASIS), INCOME_LABEL)
    b.metric("Spent", money(MONTH_SPEND), f"{money(SPENDING_LEFT)} planned spending room")
    c.metric("Moved to savings", money(MONTH_SAVED), f"Target {money(SAVINGS_TARGET)}")
    d.metric("Pool left after spend + savings", money(POOL_LEFT), "Estimate from records")

    use_pct = (MONTH_SPEND / PLANNED_SPENDING_LIMIT * 100) if PLANNED_SPENDING_LIMIT else (100 if MONTH_SPEND else 0)
    st.progress(min(1.0, max(0.0, MONTH_SPEND / PLANNED_SPENDING_LIMIT)) if PLANNED_SPENDING_LIMIT else 0.0,
                text=f"Shared spending limit: {money(MONTH_SPEND)} used of {money(PLANNED_SPENDING_LIMIT)} · {use_pct:.0f}%")
    save_pct = MONTH_SAVED / SAVINGS_TARGET if SAVINGS_TARGET else 0
    st.progress(min(1.0, max(0.0, save_pct)), text=f"Monthly savings goal: {money(MONTH_SAVED)} of {money(SAVINGS_TARGET)}")
    if SPENDING_LEFT < 0:
        st.error(f"The shared spending plan is over by {money(abs(SPENDING_LEFT))}. Review the Records and Shopping tabs together.")
    elif SPENDING_LEFT < PLANNED_SPENDING_LIMIT * 0.15:
        st.warning(f"The remaining planned spending room is {money(SPENDING_LEFT)}. Average safe amount for the remaining days: {money(SAFE_DAILY_SPEND)}/day.")
    else:
        st.info(f"Average planned spending room for the remaining {DAYS_LEFT} days: {money(SAFE_DAILY_SPEND)}/day.")

    left, right = st.columns(2)
    with left:
        st.markdown("#### Where the shared pool went")
        if not ALL_EXPENSES.empty:
            month_exp = ALL_EXPENSES[ALL_EXPENSES["month_year"] == MONTH]
            if not month_exp.empty:
                category_totals = month_exp.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
                fig = px.pie(category_totals, names="category", values="amount", hole=0.52)
                fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", font_color="#fff", margin=dict(t=15,b=10,l=5,r=5))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No expenses have been added for this month yet.")
        else:
            st.info("Log your first expense to see the family spending breakdown.")
    with right:
        st.markdown("#### Recent family activity")
        if not ALL_EXPENSES.empty:
            show = ALL_EXPENSES.head(7).copy()
            show["amount"] = show["amount"].map(money)
            st.dataframe(show[["timestamp", "spent_by", "category", "item_name", "amount"]], use_container_width=True, hide_index=True)
        else:
            st.caption("New expenses will appear here.")
        st.caption("Member names are transaction attribution only; all balances and limits above are shared.")


# -----------------------------------------------------------------------------
# Add expense and UPI helper
# -----------------------------------------------------------------------------
with tab_expense:
    st.subheader("💸 Record a family expense")
    st.info("One universal household account: choose who made the purchase for the record; it still counts against the same shared pool.")
    st.session_state.setdefault("expense_category", list(CATEGORIES)[0])
    st.session_state.setdefault("expense_item", CATEGORIES[list(CATEGORIES)[0]][0])
    st.session_state.setdefault("expense_amount", 50.0)

    quick_cols = st.columns(4)
    presets = [
        ("☕ Tea · ₹15", "🍲 Food & Mess", "Tea / snacks", 15.0),
        ("🚇 Metro · ₹40", "🚌 Travel", "Metro / bus", 40.0),
        ("🥛 Milk · ₹66", "🍲 Food & Mess", "Milk / curd / bread", 66.0),
        ("🥦 Sabzi · ₹80", "🛒 Sabzi & Kirana", "Vegetables", 80.0),
    ]
    for col, (label, cat, item, amount) in zip(quick_cols, presets):
        if col.button(label, use_container_width=True):
            st.session_state["expense_category"] = cat
            st.session_state["expense_item"] = item
            st.session_state["expense_amount"] = amount

    with st.form("expense_form", clear_on_submit=True):
        row1, row2 = st.columns(2)
        with row1:
            spent_by = st.selectbox("Who made the purchase?", list(USERS) + ["Joint Family"], index=(list(USERS) + ["Joint Family"]).index(CURRENT_USER), key="expense_spent_by")
            category = st.selectbox("Category", list(CATEGORIES), key="expense_category")
            default_item = CATEGORIES.get(category, ["Other"])[0]
            item = st.text_input("What was it?", key="expense_item", help=f"Suggested category example: {default_item}")
            amount = st.number_input("Amount (₹)", min_value=1.0, max_value=1_000_000.0, step=10.0, key="expense_amount")
        with row2:
            payment = st.selectbox("Payment method", ["Cash", "UPI", "Bank / Card"])
            upi_id = st.text_input("Merchant UPI ID (optional)", placeholder="merchant@bank")
            bad = st.checkbox("Mark as an unplanned / avoidable expense")
            notes = st.text_input("Note (optional)")
        save_expense = st.form_submit_button("✅ Save expense to the shared ledger", use_container_width=True)
    if save_expense:
        if not item.strip():
            st.error("Please enter an item name.")
        else:
            new_id = add_expense({
                "logged_by": CURRENT_USER, "spent_by": spent_by, "category": category,
                "item_name": item.strip(), "description": item.strip(), "payment_mode": payment,
                "upi_app": "", "need_level": "Unplanned" if bad else "Essential", "amount": amount,
                "is_bad_expense": bad, "upi_id": upi_id.strip(), "notes": notes.strip(),
            })
            st.session_state["last_expense_id"] = new_id
            st.session_state["last_payment"] = {"amount": float(amount), "item": item.strip(), "upi_id": upi_id.strip()}
            st.success(f"Saved {money(amount)} for {item.strip()} to the one shared family ledger.")
            st.rerun()

    receipt = st.session_state.get("last_payment")
    if receipt:
        st.markdown("#### 📲 Optional UPI payment handoff")
        if receipt.get("upi_id") and "@" in receipt["upi_id"]:
            params = urllib.parse.urlencode({"pa": receipt["upi_id"], "pn": receipt["item"][:40], "am": f"{receipt['amount']:.2f}", "cu": "INR", "tn": receipt["item"][:40]})
            upi_url = f"upi://pay?{params}"
            st.link_button("Open the UPI app with amount filled", upi_url, use_container_width=True)
            if qrcode:
                qr_image = qrcode.make(upi_url)
                st.image(qr_image, caption="Scan to pay the merchant", width=210)
        else:
            st.caption("Add a valid merchant UPI ID before saving if you want a real payment QR. No fake payment QR is generated.")


# -----------------------------------------------------------------------------
# Expected vs actual shopping planner
# -----------------------------------------------------------------------------
with tab_shopping:
    st.subheader("🛍️ Shopping plan: decide first, compare actuals as you go")
    st.caption("Each actual purchase is also added to the shared expense ledger, so it is counted once in family spending.")
    with st.expander("➕ Create a shopping trip / budget", expanded=ALL_PLANS.empty):
        with st.form("create_plan_form", clear_on_submit=True):
            trip_name = st.text_input("Shopping trip", placeholder="Monthly clothes, groceries, market trip…")
            trip_budget = st.number_input("Total expected budget (₹)", min_value=1.0, value=DEFAULT_SHOPPING_BUDGET, step=100.0)
            create_plan = st.form_submit_button("Create plan", use_container_width=True)
        if create_plan:
            if not trip_name.strip():
                st.error("Give this shopping plan a name.")
            else:
                create_shopping_plan(trip_name, trip_budget, CURRENT_USER)
                st.success("Shopping plan created.")
                st.rerun()

    if not ALL_PLANS.empty:
        plan_rows = db_rows("SELECT * FROM shopping_plans ORDER BY id DESC")
        plan_options = {f"#{p['id']} · {p['plan_name']} · {p['month_year']} · budget {money(p['budget'])}": p for p in plan_rows}
        selected_plan_label = st.selectbox("Choose a plan", list(plan_options))
        selected_plan = plan_options[selected_plan_label]
        plan_id = int(selected_plan["id"])
        items_df = pd.DataFrame(db_rows(
            "SELECT i.id,i.item_name,i.expected_amount,i.notes,COALESCE(SUM(a.amount),0) AS actual "
            "FROM shopping_items i LEFT JOIN shopping_actuals a ON a.item_id=i.id "
            "WHERE i.plan_id=:p GROUP BY i.id,i.item_name,i.expected_amount,i.notes ORDER BY i.id",
            {"p": plan_id},
        ))
        actual_total = float(items_df["actual"].sum()) if not items_df.empty else 0.0
        expected_items = float(items_df["expected_amount"].sum()) if not items_df.empty else 0.0
        budget = float(selected_plan["budget"])
        remaining = budget - actual_total
        utilization = (actual_total / budget * 100) if budget else 0.0
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Trip budget", money(budget))
        p2.metric("Actual spent", money(actual_total), f"{utilization:.1f}% used")
        p3.metric("Budget remaining", money(remaining), "Over budget" if remaining < 0 else "Available")
        p4.metric("Planned items", money(expected_items), "Sum of item estimates")
        st.progress(min(1.0, max(0.0, actual_total / budget)) if budget else 0.0,
                    text=f"{utilization:.1f}% of this trip's budget used · {money(max(0, remaining))} remains")
        if remaining < 0:
            st.error(f"Over budget by {money(abs(remaining))}. The trip actual is highlighted in the records.")
        elif utilization >= 80:
            st.warning("80% or more of the trip budget is used. Check what is still on the list.")
        else:
            st.success("The plan is within its expected budget so far.")

        st.markdown("#### Items and progress")
        if not items_df.empty:
            show_items = items_df.copy()
            show_items["remaining"] = show_items["expected_amount"] - show_items["actual"]
            show_items["used %"] = show_items.apply(lambda r: (r["actual"] / r["expected_amount"] * 100) if r["expected_amount"] else 0, axis=1).round(1)
            show_items["Status"] = show_items["used %"].apply(
                lambda pct: "🔴 Over estimate" if pct > 100 else ("🟠 Nearly used" if pct >= 80 else "🟢 Within estimate")
            )
            show_items = show_items.rename(columns={"item_name": "Item", "expected_amount": "Expected ₹", "actual": "Actual ₹", "remaining": "Item budget left ₹", "notes": "Notes"})
            st.dataframe(show_items[["Item", "Expected ₹", "Actual ₹", "Item budget left ₹", "used %", "Status", "Notes"]], use_container_width=True, hide_index=True)
        else:
            st.info("Add the expected items below, such as Saree ₹2,000, footwear ₹1,200, and accessories ₹800.")

        item_c1, item_c2 = st.columns(2)
        with item_c1:
            st.markdown("#### Add an expected item")
            with st.form(f"add_item_{plan_id}", clear_on_submit=True):
                new_item = st.text_input("Item name", placeholder="Saree")
                expected_item = st.number_input("Expected item cost (₹)", min_value=1.0, value=2_000.0, step=100.0)
                item_note = st.text_input("Item note (optional)")
                add_item_btn = st.form_submit_button("Add to plan", use_container_width=True)
            if add_item_btn:
                if new_item.strip():
                    add_shopping_item(plan_id, new_item, expected_item, item_note)
                    st.rerun()
                else:
                    st.error("Enter an item name.")
        with item_c2:
            st.markdown("#### Record an actual purchase")
            if not items_df.empty:
                item_lookup = {f"{r.item_name} · expected {money(r.expected_amount)}": int(r.id) for r in items_df.itertuples()}
                with st.form(f"actual_item_{plan_id}", clear_on_submit=True):
                    actual_item_label = st.selectbox("Purchased item", list(item_lookup))
                    actual_amount = st.number_input("Amount paid now (₹)", min_value=1.0, value=500.0, step=50.0)
                    actual_by = st.selectbox("Who paid?", list(USERS) + ["Joint Family"], key=f"actual_by_{plan_id}")
                    actual_mode = st.selectbox("Payment method", ["Cash", "UPI", "Bank / Card"], key=f"actual_mode_{plan_id}")
                    actual_note = st.text_input("Receipt / note (optional)", key=f"actual_note_{plan_id}")
                    record_actual = st.form_submit_button("Record actual + add to expenses", use_container_width=True)
                if record_actual:
                    add_shopping_actual(item_lookup[actual_item_label], actual_amount, actual_by, actual_mode, actual_note, CURRENT_USER)
                    st.success("Actual purchase saved and counted once in the family expense ledger.")
                    st.rerun()
            else:
                st.caption("Add an expected item first.")

        actual_rows = db_rows(
            "SELECT a.recorded_at,i.item_name,a.amount,e.spent_by,e.id AS expense_id "
            "FROM shopping_actuals a JOIN shopping_items i ON i.id=a.item_id "
            "JOIN expenses e ON e.id=a.expense_id WHERE i.plan_id=:p ORDER BY a.id DESC",
            {"p": plan_id},
        )
        if actual_rows:
            with st.expander("Actual entries for this trip"):
                st.dataframe(pd.DataFrame(actual_rows).rename(columns={"recorded_at":"Date", "item_name":"Item", "amount":"Actual ₹", "spent_by":"Paid by", "expense_id":"Ledger ID"}), use_container_width=True, hide_index=True)
    else:
        st.info("Create a plan to start with an expected budget—for example, ₹6,000 for a shopping trip.")


# -----------------------------------------------------------------------------
# Shared money, income and savings vault
# -----------------------------------------------------------------------------
with tab_money:
    st.subheader("🏦 Family money: one account view")
    st.caption("The app does not split the pool into Ajay's and Meenakshi's separate accounts. Their salaries can be recorded by source, then are summed here.")
    col_a, col_b = st.columns(2)
    with col_a:
        with st.form("family_income_target"):
            income_target = st.number_input("Expected household income per month (₹)", min_value=0.0, value=EXPECTED_INCOME, step=500.0)
            save_target = st.form_submit_button("Save shared income estimate", use_container_width=True)
        if save_target:
            set_setting("family_monthly_income", str(float(income_target)))
            st.success("Updated the shared household income estimate.")
            st.rerun()
    with col_b:
        with st.form("record_income_form", clear_on_submit=True):
            income_source = st.selectbox("Income source", list(USERS) + ["Other household income"])
            income_amount = st.number_input("Income received (₹)", min_value=1.0, value=23_000.0, step=500.0)
            income_note = st.text_input("Reference / note", placeholder="Salary credited, date, etc.")
            add_income_btn = st.form_submit_button("Add income to shared pool", use_container_width=True)
        if add_income_btn:
            add_income(income_source, CURRENT_USER, income_amount, income_note)
            st.success("Income recorded in the universal household pool.")
            st.rerun()

    st.markdown("#### Monthly household statement")
    income_df = ALL_INCOME[ALL_INCOME["month_year"] == MONTH] if not ALL_INCOME.empty else pd.DataFrame()
    vault_df = ALL_VAULT[ALL_VAULT["month_year"] == MONTH] if not ALL_VAULT.empty else pd.DataFrame()
    inc1, inc2, inc3, inc4 = st.columns(4)
    inc1.metric("Expected family pool", money(EXPECTED_INCOME), "One shared pool")
    inc2.metric("Income recorded", money(MONTH_INCOME_ACTUAL), f"{len(income_df)} entries")
    inc3.metric("Shared spending", money(MONTH_SPEND), f"{money(SPENDING_LEFT)} spending room")
    inc4.metric("Unallocated after spending + savings", money(POOL_LEFT), "Based on recorded income if present; otherwise expected")
    st.progress(min(1.0, max(0.0, MONTH_SAVED / SAVINGS_TARGET)) if SAVINGS_TARGET else 0,
                text=f"Savings vault: {money(MONTH_SAVED)} this month / {money(SAVINGS_TARGET)} target · {money(ALL_SAVED)} all-time")
    st.caption("This is a ledger estimate, not a live bank balance. Cash or bank money not recorded here will not be reflected.")

    money_left, money_right = st.columns(2)
    with money_left:
        st.markdown("#### Record savings moved to a goal")
        with st.form("vault_form", clear_on_submit=True):
            deposit_by = st.selectbox("Deposited by", list(USERS) + ["Joint Family"])
            bucket = st.selectbox("Savings goal", ["🏡 Dream home", "🩺 Medical reserve", "🛡️ Emergency fund", "🎯 Other goal"])
            deposit_amount = st.number_input("Deposit amount (₹)", min_value=1.0, value=1_000.0, step=500.0)
            deposit_note = st.text_input("Bank / reference note (optional)")
            deposit_btn = st.form_submit_button("🔐 Record savings deposit", use_container_width=True)
        if deposit_btn:
            add_vault_deposit(deposit_by, bucket, deposit_amount, deposit_note)
            st.success("Savings deposit added to the family vault ledger.")
            st.rerun()
    with money_right:
        st.markdown("#### Savings by goal")
        if not ALL_VAULT.empty:
            by_goal = ALL_VAULT.groupby("vault_bucket", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
            fig = px.bar(by_goal, x="vault_bucket", y="amount", color="vault_bucket")
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#fff", showlegend=False, margin=dict(t=10,b=10,l=5,r=5))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Savings deposits by goal will appear here.")

    if not ALL_INCOME.empty:
        with st.expander("Income entries for this month"):
            st.dataframe(income_df[["timestamp", "income_source", "recorded_by", "amount", "notes"]], use_container_width=True, hide_index=True)
    if not ALL_VAULT.empty:
        with st.expander("Savings deposit history"):
            st.dataframe(ALL_VAULT[["id", "timestamp", "deposited_by", "vault_bucket", "amount", "notes"]], use_container_width=True, hide_index=True)
            if IS_ADMIN:
                del_vault_id = st.number_input("Admin: savings entry ID to remove", min_value=1, step=1, key="del_vault_id")
                if st.button("Delete this savings entry"):
                    db_write("DELETE FROM vault_deposits WHERE id=:id", {"id": int(del_vault_id)})
                    st.rerun()


# -----------------------------------------------------------------------------
# Records, charts and administrator corrections
# -----------------------------------------------------------------------------
with tab_records:
    st.subheader("📊 Shared expense records")
    period = st.selectbox("Choose a period", ["This month", "Today", "Last 7 days", "Last 30 days", "All time", "Custom dates"])
    start_date = TODAY - timedelta(days=30)
    end_date = TODAY
    if period == "Custom dates":
        date_range = st.date_input("Date range", (TODAY - timedelta(days=15), TODAY))
        if isinstance(date_range, (tuple, list)):
            if len(date_range) >= 2:
                start_date, end_date = date_range[0], date_range[1]
            elif len(date_range) == 1:
                start_date = end_date = date_range[0]
        elif date_range:
            start_date = end_date = date_range

    shown = ALL_EXPENSES.copy()
    if not shown.empty:
        if period == "This month":
            shown = shown[shown["month_year"] == MONTH]
        elif period == "Today":
            shown = shown[shown["parsed_date"] == TODAY]
        elif period == "Last 7 days":
            shown = shown[shown["parsed_date"] >= TODAY - timedelta(days=6)]
        elif period == "Last 30 days":
            shown = shown[shown["parsed_date"] >= TODAY - timedelta(days=29)]
        elif period == "Custom dates":
            if isinstance(start_date, tuple):
                start_date, end_date = start_date
            shown = shown[(shown["parsed_date"] >= start_date) & (shown["parsed_date"] <= end_date)]
    period_spend = float(shown["amount"].sum()) if not shown.empty else 0.0
    period_bad = float(shown.loc[shown["is_bad_expense"] == 1, "amount"].sum()) if not shown.empty and "is_bad_expense" in shown else 0.0
    r1, r2, r3 = st.columns(3)
    r1.metric("Period spending", money(period_spend), f"{len(shown)} entries")
    r2.metric("Unplanned spending", money(period_bad), "Target: keep intentional")
    r3.metric("Shared monthly budget left", money(SPENDING_LEFT), f"Safe daily guide {money(SAFE_DAILY_SPEND)}")

    if not shown.empty:
        shown_display = shown.copy()
        shown_display["status"] = shown_display["is_bad_expense"].apply(lambda x: "Review" if int(x or 0) else "Planned / essential")
        view_cols = [c for c in ["id", "timestamp", "logged_by", "spent_by", "category", "item_name", "amount", "payment_mode", "status", "notes"] if c in shown_display]
        st.dataframe(shown_display[view_cols], use_container_width=True, hide_index=True)
        st.download_button("⬇️ Download visible expenses as CSV", shown_display[view_cols].to_csv(index=False).encode("utf-8-sig"), "parivaar_expenses.csv", "text/csv")
        cc1, cc2 = st.columns(2)
        with cc1:
            group = shown.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
            fig = px.pie(group, names="category", values="amount", hole=0.45, title="Spending by category")
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", font_color="#fff")
            st.plotly_chart(fig, use_container_width=True)
        with cc2:
            group = shown.groupby("spent_by", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
            fig = px.bar(group, x="spent_by", y="amount", color="spent_by", title="Purchase attribution (not separate accounts)")
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#fff", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No expenses in the selected period.")

    if IS_ADMIN and not ALL_EXPENSES.empty:
        with st.expander("👑 Admin: correct or delete a ledger entry"):
            ids = ALL_EXPENSES["id"].astype(int).tolist()
            selected_id = st.selectbox("Expense ID", ids, key="admin_expense_id")
            row = ALL_EXPENSES.loc[ALL_EXPENSES["id"] == selected_id].iloc[0]
            with st.form("admin_edit_expense"):
                edit_by = st.selectbox("Who made the purchase?", list(USERS) + ["Joint Family"], index=(list(USERS) + ["Joint Family"]).index(row["spent_by"]) if row["spent_by"] in list(USERS) + ["Joint Family"] else 0)
                edit_cat = st.selectbox("Category", list(CATEGORIES), index=list(CATEGORIES).index(row["category"]) if row["category"] in CATEGORIES else 0)
                edit_item = st.text_input("Item", value=str(row["item_name"]))
                edit_amount = st.number_input("Amount (₹)", min_value=1.0, value=float(row["amount"]), step=10.0)
                edit_bad = st.checkbox("Unplanned / avoidable", value=bool(row.get("is_bad_expense", 0)))
                edit_notes = st.text_input("Notes", value=str(row.get("notes", "") or ""))
                update_btn = st.form_submit_button("Save correction")
            if update_btn:
                update_expense(int(selected_id), edit_by, edit_cat, edit_item, edit_amount, edit_bad, edit_notes)
                st.success("Expense updated.")
                st.rerun()
            if st.button("🗑️ Delete selected expense", key="delete_admin_expense"):
                delete_expense(int(selected_id))
                st.success("Expense and any linked shopping actual were removed.")
                st.rerun()
    elif not IS_ADMIN:
        st.caption("Only the family admin can correct or delete an expense record.")


# -----------------------------------------------------------------------------
# YouTube Shorts discovery and AI overview
# -----------------------------------------------------------------------------
with tab_explore:
    st.subheader("▶️ Search YouTube Shorts by different angles")
    st.caption("A recipe query can return separate results for the method, preparation time, and ingredient cost. Instagram is not included.")
    with st.form("shorts_search_form"):
        search_query = st.text_input("What do you want to explore?", placeholder="Dal makhani, Python, budget trip…", key="search_query")
        search_mode = st.selectbox("Search style", ["Auto", "Food", "General"])
        search_button = st.form_submit_button("🔎 Find varied Shorts", use_container_width=True)
    if search_button:
        if not search_query.strip():
            st.warning("Enter a topic first.")
        else:
            queries = youtube_queries(search_query, search_mode)
            api_key = get_video_api_key()
            results = []
            if api_key:
                with st.spinner("Searching YouTube for relevant Shorts…"):
                    for label, query_text in queries:
                        results.append({"label": label, "query": query_text, **youtube_search(api_key, query_text)})
            st.session_state["shorts_results"] = {"query": search_query.strip(), "items": results, "queries": queries, "has_key": bool(api_key)}
            st.session_state["overview_query"] = search_query.strip()

    result_bundle = st.session_state.get("shorts_results")
    if result_bundle:
        st.markdown(f"#### Results for: {result_bundle['query']}")
        if result_bundle["has_key"]:
            for result in result_bundle["items"]:
                with st.container(border=True):
                    st.markdown(f"### {result['label']}")
                    if result.get("error"):
                        st.warning(f"YouTube search could not complete: {result['error']}")
                    elif result.get("items"):
                        video = result["items"][0]
                        st.write(f"**{video['title']}** · {video['channel']}")
                        video_id = video["id"]
                        if len(video_id) == 11 and all(ch.isalnum() or ch in "_-" for ch in video_id):
                            st.components.v1.iframe(f"https://www.youtube-nocookie.com/embed/{video_id}?rel=0", height=430, scrolling=False)
                            st.link_button("Open this Short on YouTube", f"https://www.youtube.com/shorts/{video_id}")
                    else:
                        st.info("No embeddable result was returned for this angle. Try a shorter or more specific query.")
        else:
            st.info("Set YOUTUBE_API_KEY in the app host's server-side secrets to show playable search results here. Without that key, use these direct YouTube searches:")
            for label, query_text in result_bundle["queries"]:
                search_url = "https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": query_text})
                st.link_button(f"{label} · Search YouTube Shorts", search_url, use_container_width=True)

    st.markdown("---")
    st.markdown("#### ✨ AI overview")
    if "overview_query" not in st.session_state:
        st.session_state["overview_query"] = result_bundle["query"] if result_bundle else ""
    overview_query = st.text_input("Topic for overview", key="overview_query")
    if st.button("✨ Generate AI overview", use_container_width=True):
        if not overview_query.strip():
            st.warning("Enter a topic first.")
        else:
            titles = []
            if result_bundle and result_bundle.get("items"):
                titles = [video["title"] for block in result_bundle["items"] for video in block.get("items", [])]
            with st.spinner("Preparing a concise overview…"):
                overview, error = ai_overview(overview_query.strip(), titles)
            if overview:
                st.markdown(overview)
                st.caption("AI answers can be incomplete. Video titles are search clues, not verified video contents; prices and cooking times vary by location and method.")
            else:
                st.info(error or "The live AI service is unavailable.")
                st.markdown(
                    f"**Offline starting point for _{overview_query.strip()}_**\n\n"
                    "- Compare more than one how-to result before following a method.\n"
                    "- Check preparation time separately from cooking time.\n"
                    "- For cost, price the ingredients you will actually use at your local shop.\n"
                    "- Add your chosen estimate to the Shopping tab to compare it with what you spend."
                )
    st.caption("Inline playback needs a YouTube Data API key and embeddable results. The API's short-duration filter means under 4 minutes, while #shorts is used to target Shorts; YouTube does not provide a strict Shorts-only flag in this search response. Some results may open as regular short videos, and creators or regions can restrict playback.")


# -----------------------------------------------------------------------------
# Learning, practical prompts, games and family admin
# -----------------------------------------------------------------------------
with tab_growth:
    st.subheader("🚀 Learning, ideas and family settings")
    learn_tab, prompt_tab, games_tab, admin_tab = st.tabs(["🗺️ Career progress", "✨ Prompt mixer", "🎮 Quick challenge", "👑 Admin & backup"])

    with learn_tab:
        st.markdown("#### One small step at a time")
        skills = get_skills()
        completed_count = 0
        for key, label in CAREER_SKILLS:
            value = st.checkbox(label, value=skills.get(key, False), key=f"career_{key}")
            if value != skills.get(key, False):
                set_skill(key, value)
                st.rerun()
            completed_count += int(value)
        st.progress(completed_count / len(CAREER_SKILLS), text=f"{completed_count} of {len(CAREER_SKILLS)} milestones complete")
        st.markdown("**Daily micro-plan:** 10 minutes of spoken English · 25 minutes on one learning task · record today's spending.")

    with prompt_tab:
        if "prompt_roll" not in st.session_state:
            st.session_state.prompt_roll = date.today().toordinal()
        if st.button("🎲 Mix another prompt"):
            st.session_state.prompt_roll = random.randint(1, 10_000_000)
            st.rerun()
        domain = st.selectbox("Choose a prompt area", list(PROMPT_DOMAINS))
        topic_options = PROMPT_DOMAINS[domain]
        topic_index = st.session_state.prompt_roll % len(topic_options)
        topic = st.selectbox("Choose a topic", topic_options, index=topic_index)
        styles = ["Simple Hinglish with examples", "Step by step for a beginner", "Short practice plan for today", "Practical examples and common mistakes"]
        context = st.selectbox("Choose a style", styles, index=(st.session_state.prompt_roll // 7) % len(styles))
        prompt_text = f"Help me with {topic}. Explain it {context.lower()} and give me one action I can finish today."
        st.text_area("Your editable prompt", value=prompt_text, height=115)
        st.caption("Use the prompt in the AI assistant of your choice; results depend on that service and its account settings.")

    with games_tab:
        st.markdown("#### 🔢 Quick mental-math challenge")
        if "mind_game_score" not in st.session_state:
            st.session_state.mind_game_score = 0
        st.metric("Brain-game points", st.session_state.mind_game_score)
        if "math_pair" not in st.session_state:
            x, y = random.randint(14, 49), random.randint(8, 39)
            st.session_state.math_pair = (x, y, x + y)
        x, y, answer = st.session_state.math_pair
        st.markdown(f"### What is **{x} + {y}**?")
        guess = st.number_input("Your answer", min_value=0, max_value=500, step=1, key="math_guess")
        g1, g2 = st.columns(2)
        if g1.button("Check answer"):
            if int(guess) == answer:
                st.success("Correct! A small win counts. 🎉")
                st.session_state.mind_game_score += 10
                st.session_state.math_pair = (random.randint(14, 49), random.randint(8, 39), 0)
                x2, y2, _ = st.session_state.math_pair
                st.session_state.math_pair = (x2, y2, x2 + y2)
                st.session_state.pop("math_guess", None)
                st.rerun()
            else:
                st.warning("Not quite—try once more.")
        if g2.button("New question"):
            x2, y2 = random.randint(14, 49), random.randint(8, 39)
            st.session_state.math_pair = (x2, y2, x2 + y2)
            st.session_state.pop("math_guess", None)
            st.rerun()

    with admin_tab:
        st.markdown("#### Data backup")
        st.caption("The export includes household financial and learning records, but leaves out user passwords.")
        st.download_button("⬇️ Download a family data backup", backup_zip(), "parivaar_backup.zip", "application/zip", use_container_width=True)
        st.markdown("#### User access")
        if IS_ADMIN:
            rows = [{"Name": u, "Role": v["role"], "Admin": v["is_admin"], "Avatar": v["avatar"]} for u, v in USERS.items()]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            admin_left, admin_right = st.columns(2)
            with admin_left:
                with st.form("admin_user_form", clear_on_submit=True):
                    user_name = st.text_input("Name / user ID")
                    user_password = st.text_input("New password / PIN", type="password")
                    user_role = st.text_input("Family role", value="Family Member")
                    user_avatar = st.selectbox("Avatar", ["👑", "👨‍💻", "👩‍💼", "🧑‍🎓", "👴", "👵", "👦", "👧"])
                    user_admin = st.checkbox("Grant admin access")
                    save_user = st.form_submit_button("Save / update user", use_container_width=True)
                if save_user:
                    if not user_name.strip() or not user_password.strip():
                        st.error("Enter both a user name and a password.")
                    else:
                        upsert_user(user_name, user_password, user_role, user_admin or user_name.lower() == "ajay", user_avatar)
                        st.success("User updated.")
                        st.rerun()
            with admin_right:
                removable = [name for name in USERS if name.lower() != "ajay"]
                if removable:
                    remove_name = st.selectbox("Remove a user's access", removable)
                    if st.button("Remove selected user"):
                        delete_user(remove_name)
                        st.rerun()
                st.markdown("#### Storage location")
                if ENGINE is None:
                    st.code(str(DB_FILE))
                    st.caption("Keep a copy of this file or use persistent PostgreSQL before moving to a hosted ephemeral disk.")
                else:
                    st.success("PostgreSQL is the active shared database.")
        else:
            st.info("Only the family admin can change user access or remove ledger entries.")

st.caption("Parivaar • Shared family ledger • Member names are labels for transactions, never separate household budgets.")
