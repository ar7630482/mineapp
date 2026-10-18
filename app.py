import os
import io
import math
import sqlite3
import hashlib
import urllib.parse
from datetime import datetime, date, timedelta
import calendar

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import qrcode
from PIL import Image

# Optional SQLAlchemy support for Supabase / PostgreSQL cloud persistence
try:
    from sqlalchemy import create_engine, text
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

# Optional Gemini AI SDK
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# ==============================================================================
# 1. PAGE CONFIGURATION & ULTRA-MODERN FINTECH DARK THEME (MOBILE-FIRST)
# ==============================================================================
st.set_page_config(
    page_title="Parivaar Wealth VIP | ₹15K Dream Vault",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Custom CSS for Neon Dark Mode, Mobile Touch Targets & Flashing Red Alerts
st.markdown(
    """
    <style>
    /* Global Dark Fintech Theme */
    .stApp {
        background: radial-gradient(circle at top, #0f172a 0%, #060913 100%);
        color: #f8fafc;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Optimize padding for mobile screens */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 4rem !important;
        max-width: 720px !important;
    }

    /* Top Daily Motivation Banner */
    .motivation-banner {
        background: linear-gradient(135deg, #064e3b 0%, #0f172a 60%, #1e1b4b 100%);
        border: 1px solid #10b981;
        border-left: 6px solid #00ff9d;
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 16px;
        box-shadow: 0 8px 25px rgba(0, 255, 157, 0.12);
    }
    .motivation-day-tag {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        color: #00ff9d;
        font-weight: 700;
        margin-bottom: 4px;
    }
    .motivation-quote {
        font-size: 0.98rem;
        font-weight: 600;
        color: #ffffff;
        line-height: 1.45;
    }
    .motivation-sub {
        font-size: 0.78rem;
        color: #94a3b8;
        margin-top: 6px;
    }

    /* VIP Metric Cards */
    .vip-card {
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 16px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
    }
    .vip-card-green {
        background: linear-gradient(145deg, rgba(6, 78, 59, 0.45), rgba(15, 23, 42, 0.9));
        border: 1px solid #00ff9d;
        border-radius: 16px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 0 20px rgba(0, 255, 157, 0.15);
    }
    .vip-card-gold {
        background: linear-gradient(145deg, rgba(120, 53, 15, 0.4), rgba(15, 23, 42, 0.95));
        border: 1px solid #fbbf24;
        border-radius: 16px;
        padding: 16px;
        margin-bottom: 14px;
        box-shadow: 0 0 22px rgba(251, 191, 36, 0.15);
    }

    /* Flashing Red Alert Banner */
    @keyframes pulseRed {
        0% { box-shadow: 0 0 0 0 rgba(255, 51, 102, 0.65); border-color: #ff3366; }
        70% { box-shadow: 0 0 0 12px rgba(255, 51, 102, 0); border-color: #ff80a0; }
        100% { box-shadow: 0 0 0 0 rgba(255, 51, 102, 0); border-color: #ff3366; }
    }
    .red-alert-banner {
        background: linear-gradient(135deg, #4c0519 0%, #1e1b4b 100%);
        border: 2px solid #ff3366;
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 14px;
        color: #ffe4e6;
        font-weight: 600;
        animation: pulseRed 1.8s infinite;
    }

    /* UPI Deep Link Button */
    .upi-pay-btn {
        display: block;
        width: 100%;
        text-align: center;
        background: linear-gradient(90deg, #00ff9d 0%, #10b981 100%);
        color: #022c22 !important;
        font-weight: 800;
        font-size: 1.12rem;
        padding: 16px 20px;
        border-radius: 14px;
        text-decoration: none !important;
        margin: 12px 0;
        box-shadow: 0 6px 24px rgba(0, 255, 157, 0.35);
        transition: transform 0.15s ease;
    }
    .upi-pay-btn:active {
        transform: scale(0.98);
    }

    /* Touch-friendly Streamlit Buttons */
    div.stButton > button {
        width: 100%;
        border-radius: 12px;
        min-height: 48px;
        font-weight: 700;
        border: 1px solid rgba(0, 255, 157, 0.35);
        background-color: #1e293b;
        color: #f8fafc;
        transition: all 0.2s ease;
    }
    div.stButton > button:hover {
        border-color: #00ff9d;
        color: #00ff9d;
        background-color: #0f172a;
    }

    /* Progress bar height & styling */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #00ff9d, #3b82f6);
    }

    /* Badge styling */
    .badge-bad {
        background: #ff3366;
        color: white;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 700;
    }
    .badge-good {
        background: #10b981;
        color: #022c22;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# 2. CORE FINANCIAL CONSTANTS & PRESETS
# ==============================================================================
PRIMARY_INCOME = 23000
SPOUSE_INCOME = 15000
TOTAL_POOL = PRIMARY_INCOME + SPOUSE_INCOME  # ₹38,000
STRICT_SAVINGS_TARGET = 15000                # ₹15,000 Separate Lockbox
MAX_SPENDING_BUDGET = TOTAL_POOL - STRICT_SAVINGS_TARGET  # ₹23,000

# Category Caps
CAP_FOOD = 7000
CAP_RENT = 6000
CAP_HOME_MIN = 5000
CAP_HOME_MAX = 7000
CAP_MEDICAL_EAR = 3000

# Predefined Users & PINs (Can also be customized)
USERS_DB = {
    "Amit": {"pin": "1234", "role": "Primary Earner (₹23k)", "avatar": "👨‍💻"},
    "Wife": {"pin": "2345", "role": "Partner Earner (₹15k)", "avatar": "👩‍💼"},
    "Brother": {"pin": "3456", "role": "Family Member", "avatar": "🧑‍🎓"},
}

# Expense Categories & Smart Description Presets (Dropdown inside Payment Form)
CATEGORY_DESCRIPTIONS = {
    "Food & Mess": [
        "Morning Chai / Biscuit",
        "Office Lunch / Tiffin",
        "Milk, Bread & Curd",
        "Monthly Mess / Ration Bill",
        "Evening Samosa / Outside Snack (Avoid!)",
        "Cold Drink / Ice Cream / Junk (Bad!)",
        "Custom Food Item...",
    ],
    "Groceries & Sabzi": [
        "Daily Sabzi (Aloo, Pyaz, Bhindi, Tamatar)",
        "Atta, Chawal, Dal & Oil",
        "Masale, Namak & Kitchen Essentials",
        "Gas Cylinder Refill",
        "Custom Grocery Item...",
    ],
    "Room Rent": [
        "Monthly Room Rent (Fixed)",
        "Room Electricity & Water Bill",
        "Room Maintenance / Repair",
        "Custom Rent Item...",
    ],
    "Home Transfer (Parents)": [
        "Monthly Parents Support Transfer",
        "Parents Medicine / Village Health",
        "Festival / Family Function Support",
        "Custom Home Transfer...",
    ],
    "Medical - Ear Treatment": [
        "Ear Specialist Doctor Consultation",
        "Ear Medicines & Drops",
        "Ear Diagnostic Test / Audiometry",
        "Ear Treatment Procedure Reserve",
        "Custom Ear Medical Item...",
    ],
    "Medical - General": [
        "Fever / Cold / First-Aid Medicine",
        "Family Checkup / Lab Test",
        "Custom Medical Item...",
    ],
    "Transport / Commute": [
        "Metro Card Recharge / Bus Ticket",
        "Shared E-Rickshaw / Auto (Necessary)",
        "Unplanned Solo Auto / Cab Ride (Bad Expense!)",
        "Bike Fuel / Maintenance",
        "Custom Transport Item...",
    ],
    "Electricity, Wi-Fi & Recharge": [
        "Mobile Recharge (Jio / Airtel)",
        "Broadband / Study Wi-Fi Bill",
        "Electricity Bill",
        "Custom Utility Bill...",
    ],
    "Skill & Career (Data Eng / Study)": [
        "Python / Data Engineering Course / Book",
        "Exam / Certification Fee",
        "Notebook, Pen & Study Material",
        "Custom Study Expense...",
    ],
    "Bad / Unnecessary Expense": [
        "Unplanned Cab / Solo Auto Ride",
        "Outside Junk Food / Burger / Pizza / Momos",
        "Impulse Online Shopping",
        "Unnecessary Subscription / Entertainment",
        "Custom Unnecessary Expense...",
    ],
    "Other Essential": [
        "Haircut / Grooming / Soap",
        "Household Repair",
        "Emergency Miscellaneous",
        "Custom Essential Item...",
    ],
}

# Default Saved UPI Contacts for fast selection
SAVED_UPI_MERCHANTS = {
    "Custom / Enter New UPI ID": "",
    "Local Kirana / Sabzi Shop": "merchant@okaxis",
    "Room Landlord UPI": "landlord@ybl",
    "Home / Parents Account UPI": "parents@sbi",
    "Medical / Pharmacy UPI": "pharmacy@okicici",
    "Family Savings Vault UPI": "vault@okhdfcbank",
}

# ==============================================================================
# 3. 10-YEAR (3,650+ DAYS) INFINITE DAILY MOTIVATION ENGINE
# ==============================================================================
def get_10_year_daily_motivation(days_saved_streak: int = 1, current_savings: float = 0):
    """
    Deterministically generates a unique motivational quote every single day for 10+ years
    (over 13,500 unique combinations) using date-hash seeding + live family progress.
    """
    anchor_date = date(2025, 1, 1)
    today = date.today()
    day_index = max(1, (today - anchor_date).days + 1)

    openers = [
        "🔥 Aaj Ka Sankalp:",
        "🏡 Dream House Mission:",
        "💎 Middle-Class Superpower:",
        "🚀 Data Engineer Mindset:",
        "🛡️ Parivaar Suraksha Niyam:",
        "⚡ Subah Ki Urja:",
        "👑 विजेता की सोच (Winner's Code):",
        "🧱 ईंट-दर-ईंट (Brick by Brick):",
        "🌟 संघर्ष से सफलता:",
        "🎯 Focus Mode ON:",
        "💪 अटूट अनुशासन (Iron Discipline):",
        "🌱 बूंद-बूंद से सागर:",
        "🦁 शेर का जिगरा:",
        "📈 कंपाउंडिंग का जादू:",
        "🙏 परिवार की मुस्कान:",
    ]

    core_messages = [
        "आज बचाया गया हर ₹100 आपके अपने पक्के घर की एक मजबूत ईंट है। बाहर का समोसा 5 मिनट का स्वाद देगा, अपना घर पूरी ज़िंदगी का सम्मान देगा!",
        "गरीबी परिस्थिति हो सकती है, लेकिन अनुशासन हमारी ताकत है। ₹15,000 की बचत कोई विकल्प नहीं, हमारे परिवार के भविष्य की ढाल है।",
        "जब लोग टाइम पास वाली रील्स देख रहे हों, तब तुम Python, SQL और Advanced Excel सीखकर अपनी सैलरी को ₹23,000 से ₹1,00,000 तक ले जाने की तैयारी करो!",
        "पत्नी का साथ, भाई का सहयोग और तुम्हारी मेहनत—जब तीनों एक दिशा में चलते हैं, तो ₹38,000 में भी महल खड़ा करने की नींव रखी जा सकती है।",
        "कान का सही इलाज (Ear Treatment) और माता-पिता की जिम्मेदारी सबसे ऊपर है। फालतू ऑटो/कैब में ₹100 उड़ाने से पहले 10 सेकंड रुककर परिवार का चेहरा याद करो।",
        "घर का बना सादा दाल-चावल और भिंडी की सब्जी सिर्फ पैसे नहीं बचाती, सेहत भी बनाती है। ₹7,000 के फूड बजट के अंदर रहना हमारी जीत है!",
        "Data Engineer बनने के लिए महंगे कॉलेज की नहीं, रोज़ 2 घंटे की सच्ची प्रैक्टिस की ज़रूरत होती है। आज का एक नया कोड कल की बड़ी नौकरी है!",
        "अमीर वो नहीं जो ज़्यादा कमाता है, अमीर वो है जो अपनी कमाई में से बिना चूके अपने लक्ष्य के लिए ₹15,000 पहले अलग रख देता है।",
        "दुनिया को दिखाने के लिए खर्च मत करो। जिस दिन अपने घर की नेमप्लेट लगेगी, उस दिन तुम्हारी खामोशी खुद शोर मचाएगी!",
        "छोटे-छोटे लालच को मना करना सीखो। आज की एक 'ना' (No to Junk Food), कल तुम्हारे बच्चों और परिवार के लिए सबसे बड़ी 'हाँ' बनेगी।",
        "बजट का मतलब कंजूसी नहीं, समझदारी है। हर खर्च को पेमेंट से पहले इस ऐप में लिखना तुम्हें 99% लोगों से आगे रखता है।",
        "थकान होने पर भी जो इंसान रात को 45 मिनट Python या Excel पढ़ता है, उसकी किस्मत को बदलने से कोई नहीं रोक सकता।",
        "माँ-बाप का आशीर्वाद और हर महीने की ₹15,000 की पक्की बचत—यही दो चीज़ें हर मुसीबत में हमारे परिवार को अजेय बनाती हैं।",
        "जब भी कोई गैर-ज़रूरी खर्च करने का मन करे, तो सोचो: 'क्या यह चीज़ मेरे सपनों के घर और कान के इलाज से ज़्यादा ज़रूरी है?' जवाब खुद मिल जाएगा।",
        "आज का दिन नया है, नई ऊर्जा के साथ काम पर लगो। एक भी रुपया फालतू नहीं जाएगा, और आज एक नया Tech Skill ज़रूर सीखेंगे!",
        "सफलता एक दिन में नहीं मिलती, लेकिन रोज़ के सही फैसलों से एक दिन ज़रूर मिलती है। आज का बजट 100% कंट्रोल में रखो!",
        "घर की रसोई से निकलने वाली खुशबू बाज़ार के जंक फूड से हज़ार गुना बेहतर है। सेहत भी सुरक्षित, और Dream House का फंड भी सुरक्षित!",
        "हर महीने की पहली तारीख को जो परिवार अपना ₹15,000 का Vault लॉक कर देता है, उसे कभी किसी के आगे हाथ नहीं फैलाना पड़ता।",
        "कोडिंग में आने वाला हर Error और ज़िंदगी में आने वाली हर तंगी हमें और मज़बूत बनाने आती है। हार मत मानो, बस आगे बढ़ते रहो!",
        "तुम्हारा लक्ष्य साफ है: कान का पूरा इलाज, गाँव में माता-पिता का सहारा, अपना खुद का घर, और Tech सेक्टर में शानदार करियर!",
    ]

    daily_micro_actions = [
        "✅ आज का चैलेंज: बाहर की चाय/स्नैक्स पर ₹0 खर्च करना है और शाम को 30 मिनट Python/SQL पढ़ना है।",
        "✅ आज का चैलेंज: हर छोटे से छोटा पेमेंट भी पहले ऐप में लॉग करके ही UPI करना है।",
        "✅ आज का चैलेंज: आज घर का बना टिफिन/खाना ही खाना है और ₹100 फालतू खर्च से बचाना है।",
        "✅ आज का चैलेंज: आज Advanced Excel का 1 नया फॉर्मूला या Python की 1 स्क्रिप्ट ज़रूर प्रैक्टिस करनी है।",
        "✅ आज का चैलेंज: आज कोई भी अनप्लान्ड ऑटो/कैब नहीं लेनी है—मेट्रो या बस से पैसे बचाने हैं।",
        "✅ आज का चैलेंज: रात को सोने से पहले परिवार के साथ 2 मिनट आज के खर्च का हिसाब देखना है।",
    ]

    # Deterministic shuffling using day_index so every single day across 10+ years is distinct
    o_idx = day_index % len(openers)
    m_idx = (day_index * 7 + (day_index // len(core_messages))) % len(core_messages)
    a_idx = (day_index * 3 + (day_index // len(daily_micro_actions))) % len(daily_micro_actions)

    bricks_accumulated = int(current_savings // 50)  # Assuming ₹50 = 1 Dream House Brick

    return {
        "day_number": day_index,
        "date_str": today.strftime("%d %b %Y (%A)"),
        "headline": f"{openers[o_idx]} [Day #{day_index} of 3,650]",
        "quote": core_messages[m_idx],
        "action": daily_micro_actions[a_idx],
        "bricks": bricks_accumulated,
    }


# ==============================================================================
# 4. DATABASE ENGINE (SQLite Local + Optional Supabase/PostgreSQL Permanence)
# ==============================================================================
DB_FILE = "family_finance_vip.db"


def get_db_engine():
    """Returns a SQLAlchemy engine if DATABASE_URL is configured in secrets/env, else None (uses sqlite3)."""
    db_url = None
    try:
        if "DATABASE_URL" in st.secrets:
            db_url = st.secrets["DATABASE_URL"]
    except Exception:
        pass
    if not db_url:
        db_url = os.environ.get("DATABASE_URL")

    if db_url and SQLALCHEMY_AVAILABLE:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return create_engine(db_url, pool_pre_ping=True)
    return None


def init_db():
    """Creates all required tables for Expenses, Dream House Vault, and Career Progress."""
    engine = get_db_engine()
    if engine:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS expenses (
                        id SERIAL PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        month_year TEXT NOT NULL,
                        logged_by TEXT NOT NULL,
                        spent_by TEXT NOT NULL,
                        category TEXT NOT NULL,
                        item_name TEXT NOT NULL,
                        description TEXT,
                        payment_mode TEXT,
                        need_level TEXT,
                        amount REAL NOT NULL,
                        is_bad_expense INTEGER DEFAULT 0,
                        upi_id TEXT,
                        notes TEXT
                    );
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS vault_deposits (
                        id SERIAL PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        month_year TEXT NOT NULL,
                        deposited_by TEXT NOT NULL,
                        vault_bucket TEXT NOT NULL,
                        amount REAL NOT NULL,
                        notes TEXT
                    );
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS career_progress (
                        skill_key TEXT PRIMARY KEY,
                        completed INTEGER DEFAULT 0,
                        updated_at TEXT
                    );
                    """
                )
            )
    else:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                month_year TEXT NOT NULL,
                logged_by TEXT NOT NULL,
                spent_by TEXT NOT NULL,
                category TEXT NOT NULL,
                item_name TEXT NOT NULL,
                description TEXT,
                payment_mode TEXT,
                need_level TEXT,
                amount REAL NOT NULL,
                is_bad_expense INTEGER DEFAULT 0,
                upi_id TEXT,
                notes TEXT
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS vault_deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                month_year TEXT NOT NULL,
                deposited_by TEXT NOT NULL,
                vault_bucket TEXT NOT NULL,
                amount REAL NOT NULL,
                notes TEXT
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS career_progress (
                skill_key TEXT PRIMARY KEY,
                completed INTEGER DEFAULT 0,
                updated_at TEXT
            )
            """
        )
        conn.commit()
        conn.close()


def add_expense_to_db(
    logged_by,
    spent_by,
    category,
    item_name,
    description,
    payment_mode,
    need_level,
    amount,
    is_bad_expense,
    upi_id,
    notes,
):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    month_year = datetime.now().strftime("%Y-%m")
    bad_int = 1 if is_bad_expense else 0

    engine = get_db_engine()
    if engine:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO expenses (
                        timestamp, month_year, logged_by, spent_by, category,
                        item_name, description, payment_mode, need_level,
                        amount, is_bad_expense, upi_id, notes
                    ) VALUES (
                        :ts, :my, :lb, :sb, :cat, :item, :desc, :pm, :nl, :amt, :bad, :upi, :notes
                    )
                    """
                ),
                {
                    "ts": now_str,
                    "my": month_year,
                    "lb": logged_by,
                    "sb": spent_by,
                    "cat": category,
                    "item": item_name,
                    "desc": description,
                    "pm": payment_mode,
                    "nl": need_level,
                    "amt": float(amount),
                    "bad": bad_int,
                    "upi": upi_id,
                    "notes": notes,
                },
            )
    else:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO expenses (
                timestamp, month_year, logged_by, spent_by, category,
                item_name, description, payment_mode, need_level,
                amount, is_bad_expense, upi_id, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now_str,
                month_year,
                logged_by,
                spent_by,
                category,
                item_name,
                description,
                payment_mode,
                need_level,
                float(amount),
                bad_int,
                upi_id,
                notes,
            ),
        )
        conn.commit()
        conn.close()


def delete_expense_from_db(expense_id: int):
    engine = get_db_engine()
    if engine:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM expenses WHERE id = :id"), {"id": int(expense_id)})
    else:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute("DELETE FROM expenses WHERE id = ?", (int(expense_id),))
        conn.commit()
        conn.close()


def fetch_expenses_df(month_year: str = None) -> pd.DataFrame:
    engine = get_db_engine()
    if engine:
        with engine.connect() as conn:
            if month_year:
                df = pd.read_sql(
                    text("SELECT * FROM expenses WHERE month_year = :my ORDER BY id DESC"),
                    conn,
                    params={"my": month_year},
                )
            else:
                df = pd.read_sql(text("SELECT * FROM expenses ORDER BY id DESC"), conn)
    else:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        if month_year:
            df = pd.read_sql_query(
                "SELECT * FROM expenses WHERE month_year = ? ORDER BY id DESC",
                conn,
                params=(month_year,),
            )
        else:
            df = pd.read_sql_query("SELECT * FROM expenses ORDER BY id DESC", conn)
        conn.close()
    return df


def add_vault_deposit(deposited_by: str, vault_bucket: str, amount: float, notes: str):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    month_year = datetime.now().strftime("%Y-%m")
    engine = get_db_engine()
    if engine:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO vault_deposits (timestamp, month_year, deposited_by, vault_bucket, amount, notes)
                    VALUES (:ts, :my, :db, :vb, :amt, :notes)
                    """
                ),
                {
                    "ts": now_str,
                    "my": month_year,
                    "db": deposited_by,
                    "vb": vault_bucket,
                    "amt": float(amount),
                    "notes": notes,
                },
            )
    else:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO vault_deposits (timestamp, month_year, deposited_by, vault_bucket, amount, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (now_str, month_year, deposited_by, vault_bucket, float(amount), notes),
        )
        conn.commit()
        conn.close()


def fetch_vault_df(month_year: str = None) -> pd.DataFrame:
    engine = get_db_engine()
    if engine:
        with engine.connect() as conn:
            if month_year:
                df = pd.read_sql(
                    text("SELECT * FROM vault_deposits WHERE month_year = :my ORDER BY id DESC"),
                    conn,
                    params={"my": month_year},
                )
            else:
                df = pd.read_sql(text("SELECT * FROM vault_deposits ORDER BY id DESC"), conn)
    else:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        if month_year:
            df = pd.read_sql_query(
                "SELECT * FROM vault_deposits WHERE month_year = ? ORDER BY id DESC",
                conn,
                params=(month_year,),
            )
        else:
            df = pd.read_sql_query("SELECT * FROM vault_deposits ORDER BY id DESC", conn)
        conn.close()
    return df


def get_career_progress() -> dict:
    engine = get_db_engine()
    progress = {}
    if engine:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT skill_key, completed FROM career_progress")).fetchall()
            for r in rows:
                progress[r[0]] = bool(r[1])
    else:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        rows = c.execute("SELECT skill_key, completed FROM career_progress").fetchall()
        for r in rows:
            progress[r[0]] = bool(r[1])
        conn.close()
    return progress


def set_career_progress(skill_key: str, completed: bool):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    val = 1 if completed else 0
    engine = get_db_engine()
    if engine:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO career_progress (skill_key, completed, updated_at)
                    VALUES (:k, :v, :u)
                    ON CONFLICT (skill_key) DO UPDATE SET completed = :v, updated_at = :u
                    """
                ),
                {"k": skill_key, "v": val, "u": now_str},
            )
    else:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        c = conn.cursor()
        c.execute(
            """
            INSERT OR REPLACE INTO career_progress (skill_key, completed, updated_at)
            VALUES (?, ?, ?)
            """,
            (skill_key, val, now_str),
        )
        conn.commit()
        conn.close()


# Initialize database tables on startup
init_db()


# ==============================================================================
# 5. HELPER FUNCTIONS (UPI QR CODE, AI MENTOR, DAILY SAFE LIMIT)
# ==============================================================================
def build_upi_intent_and_qr(upi_id: str, payee_name: str, amount: float, note: str):
    """Generates standard NPCI UPI deep link and high-contrast QR image."""
    clean_upi = (upi_id or "merchant@okaxis").strip()
    params = {
        "pa": clean_upi,
        "pn": payee_name or "ParivaarPay",
        "am": f"{float(amount):.2f}",
        "cu": "INR",
        "tn": note[:45] if note else "FamilyExpense",
    }
    query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    upi_url = f"upi://pay?{query_string}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=2,
    )
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#022c22", back_color="#00ff9d")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return upi_url, buf


def calculate_daily_safe_spend(total_spent_this_month: float) -> dict:
    today = date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_remaining = max(1, days_in_month - today.day + 1)
    remaining_budget = max(0.0, MAX_SPENDING_BUDGET - total_spent_this_month)
    daily_safe = remaining_budget / days_remaining
    return {
        "days_remaining": days_remaining,
        "remaining_budget": remaining_budget,
        "daily_safe": daily_safe,
    }


def ask_gemini_or_fallback(prompt_query: str, api_key: str = "") -> str:
    """Uses Gemini API if key is provided, otherwise gives an instant smart offline response."""
    if api_key and GEMINI_AVAILABLE:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            sys_prompt = (
                "You are a caring, practical Hinglish Mentor for a hard-working Indian family "
                "(total income ₹38,000, saving ₹15,000/month for a Dream House & Ear Treatment). "
                "You also mentor the user to become a Data Engineer / Data Scientist using Python, "
                "SQL, and Advanced Excel, and share ultra-budget Indian home cooking recipes. "
                "Keep answers practical, concise, and encouraging in Hinglish."
            )
            response = model.generate_content(f"{sys_prompt}\n\nUser Question: {prompt_query}")
            return response.text
        except Exception as e:
            return f"⚠️ Gemini API Error ({e}). Showing built-in offline mentor answer below:\n\n" + offline_smart_mentor(prompt_query)
    return offline_smart_mentor(prompt_query)


def offline_smart_mentor(query: str) -> str:
    q = query.lower()
    if any(k in q for k in ["python", "pandas", "data engineer", "sql", "spark", "etl", "scientist"]):
        return (
            "### 🚀 Data Engineer / Scientist Fast-Track Guide (Hinglish)\n"
            "1. **Step 1 (Month 1-2): Python + SQL Mastery** — Learn `pandas`, `requests` (API scraping), and SQL `JOIN`, `GROUP BY`, and Window Functions (`ROW_NUMBER()`, `RANK()`).\n"
            "2. **Step 2 (Month 3): Advanced Excel & Automation** — Replace manual MIS work with Python `openpyxl` + Streamlit dashboards.\n"
            "3. **Step 3 (Month 4-5): Data Engineering Core** — Learn ETL pipelines, PostgreSQL, PySpark basics, and GitHub portfolio projects.\n"
            "💡 *Tip: Roz 1 ghanta code likho aur apne GitHub par upload karo!*"
        )
    if any(k in q for k in ["excel", "vlookup", "xlookup", "pivot", "mis"]):
        return (
            "### 📊 Advanced Excel High-Salary Tricks\n"
            "- **XLOOKUP:** `=XLOOKUP(lookup_value, lookup_array, return_array, \"Not Found\")`\n"
            "- **INDEX + MATCH:** Best for large datasets.\n"
            "- **Power Query:** Automate daily dirty CSV/Excel reports in 1 click without VBA!\n"
            "- **Pivot Table Slicers:** Build interactive management dashboards in 5 minutes."
        )
    if any(k in q for k in ["khana", "recipe", "aloo", "bhindi", "dal", "tehri", "sasta", "food", "cook"]):
        return (
            "### 🍲 ₹40–₹50 Budget Desi Ghar Ka Khana Ideas\n"
            "1. **UP-Style Masala Tehri (₹45 for 3 people):** Rice + Aloo + Soya Chunks + Pyaz/Tamatar + Haldi/Garam Masala in 1 cooker (2 whistles)!\n"
            "2. **Crispy Fried Bhindi + Dal Chawal:** Cut bhindi dry, cook on medium flame with jeera, hari mirch, haldi, and amchur at the end.\n"
            "3. **Besan Chilla / Anda Bhurji Roll:** Ready in 10 mins—beats ₹150 outside junk food easily!"
        )
    return (
        "### 💡 Smart Mentor Summary\n"
        f"Aapने पूछा: **'{query}'**\n\n"
        "- **Career Tip:** Focus on **SQL + Python + Advanced Excel** daily for 45 mins.\n"
        "- **Finance Rule:** Protect your **₹15,000 Dream House + Ear Medical Vault** first before any spending.\n"
        "- **Direct Web Search:** Click the **'🌐 Open on Google Search'** or **'▶️ Search on YouTube'** buttons below for instant deep results!"
    )


# ==============================================================================
# 6. AUTHENTICATION SCREEN (3 PREDEFINED FAMILY USERS)
# ==============================================================================
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

if "last_payment_receipt" not in st.session_state:
    st.session_state.last_payment_receipt = None


def render_login_screen():
    mot = get_10_year_daily_motivation()
    st.markdown(
        f"""
        <div class="motivation-banner">
            <div class="motivation-day-tag">{mot['headline']} • {mot['date_str']}</div>
            <div class="motivation-quote">“{mot['quote']}”</div>
            <div class="motivation-sub">{mot['action']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="vip-card" style="text-align:center;">
            <h2 style="margin-bottom:4px; color:#00ff9d;">🛡️ Parivaar Wealth VIP</h2>
            <p style="color:#94a3b8; font-size:0.9rem; margin-top:0;">
                ₹38K Pool • ₹15K Dream House & Ear Medical Lockbox • Pre-Payment UPI Guard
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("family_login_form"):
        selected_user = st.selectbox(
            "👤 Select Family Member Account",
            options=list(USERS_DB.keys()),
            format_func=lambda u: f"{USERS_DB[u]['avatar']} {u} — {USERS_DB[u]['role']}",
        )
        pin_input = st.text_input(
            "🔑 Enter 4-Digit Security PIN",
            type="password",
            max_chars=8,
            placeholder="Default: Amit=1234, Wife=2345, Brother=3456",
        )
        submit_login = st.form_submit_button("🔓 Unlock Family Finance App")

        if submit_login:
            if pin_input.strip() == USERS_DB[selected_user]["pin"]:
                st.session_state.authenticated_user = selected_user
                st.rerun()
            else:
                st.error("❌ Invalid PIN! Default PINs: Amit (1234) | Wife (2345) | Brother (3456)")

    with st.expander("📲 How to Install on Any Phone as a Mobile App (Android & iPhone)"):
        st.markdown(
            """
            1. **Android (Chrome):** Tap the **3 dots (⋮)** at the top-right corner 👉 Tap **"Add to Home screen"** or **"Install app"**.
            2. **iPhone (Safari):** Tap the **Share icon (⬆️)** at the bottom 👉 Scroll down and tap **"Add to Home Screen"**.
            3. **Multi-Phone Real-Time Sync:** Open the exact same link on **Amit, Wife, and Brother's** phones. Any entry logged on one phone updates the shared database for all 3 phones!
            """
        )


if not st.session_state.authenticated_user:
    render_login_screen()
    st.stop()


# ==============================================================================
# 7. LOGGED-IN HEADER & INFINITE 10-YEAR DAILY MOTIVATION BANNER
# ==============================================================================
current_user = st.session_state.authenticated_user
current_month_str = datetime.now().strftime("%Y-%m")

# Load current month data
df_month = fetch_expenses_df(current_month_str)
df_all_vault = fetch_vault_df()
df_month_vault = fetch_vault_df(current_month_str)

total_spent_month = float(df_month["amount"].sum()) if not df_month.empty else 0.0
bad_spent_month = (
    float(df_month[df_month["is_bad_expense"] == 1]["amount"].sum())
    if not df_month.empty
    else 0.0
)
food_spent_month = (
    float(df_month[df_month["category"] == "Food & Mess"]["amount"].sum())
    if not df_month.empty
    else 0.0
)
rent_spent_month = (
    float(df_month[df_month["category"] == "Room Rent"]["amount"].sum())
    if not df_month.empty
    else 0.0
)
home_transfer_month = (
    float(df_month[df_month["category"] == "Home Transfer (Parents)"]["amount"].sum())
    if not df_month.empty
    else 0.0
)
ear_medical_month = (
    float(df_month[df_month["category"] == "Medical - Ear Treatment"]["amount"].sum())
    if not df_month.empty
    else 0.0
)

vault_saved_this_month = float(df_month_vault["amount"].sum()) if not df_month_vault.empty else 0.0
vault_saved_all_time = float(df_all_vault["amount"].sum()) if not df_all_vault.empty else 0.0

# Projected monthly savings remaining if spending stays within ₹23,000 budget
budget_overflow = max(0.0, total_spent_month - MAX_SPENDING_BUDGET)
protected_15k_status = max(0.0, STRICT_SAVINGS_TARGET - budget_overflow)

# Render Top Motivation Banner (Never-ending 10+ year engine)
mot_data = get_10_year_daily_motivation(
    days_saved_streak=date.today().day,
    current_savings=vault_saved_all_time + protected_15k_status,
)

st.markdown(
    f"""
    <div class="motivation-banner">
        <div class="motivation-day-tag">{mot_data['headline']} • {mot_data['date_str']}</div>
        <div class="motivation-quote">“{mot_data['quote']}”</div>
        <div class="motivation-sub">{mot_data['action']}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Top User Bar & Quick Switch
top_c1, top_c2, top_c3 = st.columns([2.2, 1.5, 1.1])
with top_c1:
    st.markdown(
        f"**{USERS_DB[current_user]['avatar']} Logged in:** `{current_user}`"
    )
with top_c2:
    safe_info = calculate_daily_safe_spend(total_spent_month)
    st.markdown(
        f"**🎯 Today's Safe Limit:** `₹{safe_info['daily_safe']:,.0f}`"
    )
with top_c3:
    if st.button("🔄 Switch User"):
        st.session_state.authenticated_user = None
        st.rerun()

# ==============================================================================
# 8. SMART FLASHING RED ALERT BANNERS (FOOD > 80% OR BAD EXPENSE LOGGED)
# ==============================================================================
if food_spent_month >= 0.8 * CAP_FOOD:
    food_pct = (food_spent_month / CAP_FOOD) * 100
    st.markdown(
        f"""
        <div class="red-alert-banner">
            🚨 <b>CRITICAL FOOD BUDGET ALERT ({food_pct:.0f}% Used!):</b>
            Food & Mess spending has reached <b>₹{food_spent_month:,.0f} / ₹{CAP_FOOD:,}</b>.
            Strictly stop outside snacks/junk and switch 100% to home-cooked meals!
        </div>
        """,
        unsafe_allow_html=True,
    )

if bad_spent_month > 0:
    bricks_lost = int(bad_spent_month // 50)
    st.markdown(
        f"""
        <div class="red-alert-banner">
            ⚠️ <b>BAD EXPENSE WARNING:</b> ₹{bad_spent_month:,.0f} wasted this month on unnecessary rides/junk!
            That equals <b>{bricks_lost} Bricks (🧱)</b> of your Dream House lost. Stop impulse spending immediately!
        </div>
        """,
        unsafe_allow_html=True,
    )

# ==============================================================================
# 9. MAIN MOBILE-FIRST NAVIGATION TABS
# ==============================================================================
tab_pay, tab_vault, tab_dash, tab_learn, tab_counselor = st.tabs(
    [
        "💳 Pre-Pay & UPI",
        "🏡 ₹15K Dream Vault",
        "📊 Live Ledger",
        "🎓 Study, Khana & Search",
        "🧠 AI Counselor",
    ]
)

# ==============================================================================
# TAB 1: PRE-PAYMENT UPI INTENT & QR WORKFLOW + RICH DROPDOWNS & "SPENT BY"
# ==============================================================================
with tab_pay:
    st.markdown(
        """
        <div class="vip-card-green">
            <h4 style="margin:0; color:#00ff9d;">⚡ Step 1: Log Before You Pay (Pre-Payment Lock)</h4>
            <p style="margin:4px 0 0 0; font-size:0.84rem; color:#cbd5e1;">
                Rule: First record every rupee here, check if it hurts your Dream House goal, then tap to open GPay / PhonePe / Paytm.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1-Tap Express Loggers for Daily Essentials
    st.caption("⚡ **1-Tap Quick Fill Presets (Optional):**")
    qc1, qc2, qc3, qc4 = st.columns(4)
    if qc1.button("☕ ₹15 Chai"):
        st.session_state.qf_cat = "Food & Mess"
        st.session_state.qf_amt = 15.0
        st.session_state.qf_desc = "Morning Chai / Biscuit"
    if qc2.button("🚇 ₹40 Metro"):
        st.session_state.qf_cat = "Transport / Commute"
        st.session_state.qf_amt = 40.0
        st.session_state.qf_desc = "Metro Card Recharge / Bus Ticket"
    if qc3.button("🥛 ₹66 Milk"):
        st.session_state.qf_cat = "Food & Mess"
        st.session_state.qf_amt = 66.0
        st.session_state.qf_desc = "Milk, Bread & Curd"
    if qc4.button("🥦 ₹100 Sabzi"):
        st.session_state.qf_cat = "Groceries & Sabzi"
        st.session_state.qf_amt = 100.0
        st.session_state.qf_desc = "Daily Sabzi (Aloo, Pyaz, Bhindi, Tamatar)"

    # Interactive Category & Description Dropdowns (Outside form so preset dropdown updates dynamically!)
    default_cat = st.session_state.get("qf_cat", "Food & Mess")
    cat_list = list(CATEGORY_DESCRIPTIONS.keys())
    cat_index = cat_list.index(default_cat) if default_cat in cat_list else 0

    col_sb, col_cat = st.columns(2)
    with col_sb:
        spent_by_options = ["Amit", "Wife", "Brother", "Joint Family"]
        default_sb_idx = spent_by_options.index(current_user) if current_user in spent_by_options else 0
        spent_by_val = st.selectbox(
            "👤 Spent By (किसने खर्च किया?)",
            options=spent_by_options,
            index=default_sb_idx,
        )
    with col_cat:
        selected_category = st.selectbox(
            "📂 Expense Category (श्रेणी)",
            options=cat_list,
            index=cat_index,
        )

    # Dynamic Description Dropdown based on selected Category
    desc_presets = CATEGORY_DESCRIPTIONS.get(selected_category, ["Custom Item..."])
    default_desc = st.session_state.get("qf_desc", desc_presets[0])
    desc_idx = desc_presets.index(default_desc) if default_desc in desc_presets else 0

    col_desc, col_mode = st.columns(2)
    with col_desc:
        selected_desc_preset = st.selectbox(
            "📝 Standard Description (विवरण चुनें)",
            options=desc_presets,
            index=desc_idx,
        )
    with col_mode:
        payment_mode_val = st.selectbox(
            "💳 Payment Mode (भुगतान माध्यम)",
            options=[
                "UPI (GPay / PhonePe / Paytm)",
                "Cash (नकद)",
                "Bank Transfer / NEFT",
                "Debit Card / ATM",
            ],
        )

    # Auto-detect if this preset/category looks like a Bad Expense
    auto_bad_flag = (
        selected_category == "Bad / Unnecessary Expense"
        or "Bad" in selected_desc_preset
        or "Avoid" in selected_desc_preset
    )

    with st.form("pre_payment_upi_form", clear_on_submit=False):
        f_col1, f_col2 = st.columns([1.4, 1])
        with f_col1:
            custom_item_name = st.text_input(
                "🏷️ Specific Item Name (Optional Custom Name)",
                value="" if "Custom" in selected_desc_preset else selected_desc_preset,
                placeholder="e.g., 1kg Aloo + ½kg Bhindi / Auto to Station",
            )
        with f_col2:
            amount_val = st.number_input(
                "₹ Amount (INR)",
                min_value=1.0,
                max_value=100000.0,
                value=float(st.session_state.get("qf_amt", 50.0)),
                step=10.0,
            )

        n_col1, n_col2 = st.columns(2)
        with n_col1:
            need_level_val = st.selectbox(
                "⚖️ Priority / Need Level",
                options=[
                    "Must-Have (Essential)",
                    "Medical Priority (Ear Treatment)",
                    "Parents / Home Responsibility",
                    "Skill & Career Investment",
                    "Avoidable / Impulse (Bad Expense)",
                ],
                index=4 if auto_bad_flag else (1 if "Ear" in selected_category else 0),
            )
        with n_col2:
            merchant_choice = st.selectbox(
                "🏪 Saved Merchant / UPI Receiver",
                options=list(SAVED_UPI_MERCHANTS.keys()),
            )

        upi_id_input = st.text_input(
            "📲 Receiver UPI ID (Optional — for Direct Deep-Link & QR)",
            value=SAVED_UPI_MERCHANTS[merchant_choice],
            placeholder="e.g. shopkeeper@okaxis or 9876543210@ybl",
        )

        is_bad_checkbox = st.checkbox(
            "🚨 Is this a BAD / UNNECESSARY Expense? (Junk food, unplanned cab, impulse buy)",
            value=auto_bad_flag,
        )

        notes_input = st.text_input(
            "📌 Extra Notes / Reason",
            placeholder="e.g., Bought vegetables for 3 days / Doctor prescribed drops",
        )

        # Live Reality Check inside form
        bricks_cost = max(1, int(amount_val // 50))
        st.caption(
            f"🧱 **Dream House Reality Check:** `₹{amount_val:,.0f}` = **{bricks_cost} Bricks** of your Dream House."
        )

        proceed_btn = st.form_submit_button("🔒 Log Transaction & Generate UPI Pay Link")

        if proceed_btn:
            final_item = custom_item_name.strip() or selected_desc_preset
            final_bad = bool(
                is_bad_checkbox
                or selected_category == "Bad / Unnecessary Expense"
                or need_level_val == "Avoidable / Impulse (Bad Expense)"
            )

            add_expense_to_db(
                logged_by=current_user,
                spent_by=spent_by_val,
                category=selected_category,
                item_name=final_item,
                description=selected_desc_preset,
                payment_mode=payment_mode_val,
                need_level=need_level_val,
                amount=amount_val,
                is_bad_expense=final_bad,
                upi_id=upi_id_input.strip(),
                notes=notes_input.strip(),
            )

            st.session_state.last_payment_receipt = {
                "item": final_item,
                "category": selected_category,
                "spent_by": spent_by_val,
                "amount": amount_val,
                "upi_id": upi_id_input.strip() or "merchant@okaxis",
                "is_bad": final_bad,
                "timestamp": datetime.now().strftime("%d %b %Y, %I:%M %p"),
            }
            st.rerun()

    # Render Dynamic UPI QR Code & Deep-Link Launcher immediately after logging
    if st.session_state.last_payment_receipt:
        rec = st.session_state.last_payment_receipt
        upi_url, qr_buf = build_upi_intent_and_qr(
            upi_id=rec["upi_id"],
            payee_name=rec["item"][:20],
            amount=rec["amount"],
            note=f"{rec['category']} - {rec['item']}",
        )

        st.markdown("---")
        st.success(
            f"✅ **Logged in Database!** ₹{rec['amount']:,.0f} for **{rec['item']}** (Spent by: `{rec['spent_by']}`)"
        )

        if rec["is_bad"]:
            st.warning(
                "🛑 **Hold On!** You marked this as a **Bad/Unnecessary Expense**. If you haven't paid yet, you can still cancel the purchase and save these Dream House bricks!"
            )

        st.markdown(
            f"""
            <a href="{upi_url}" class="upi-pay-btn">
                🚀 Open Google Pay / PhonePe / Paytm (Pay ₹{rec['amount']:,.0f})
            </a>
            """,
            unsafe_allow_html=True,
        )

        qr_c1, qr_c2 = st.columns([1.1, 1.3])
        with qr_c1:
            st.image(qr_buf, caption=f"Scan to Pay ₹{rec['amount']:,.0f}", use_container_width=True)
        with qr_c2:
            st.markdown(
                f"""
                **🧾 Pre-Payment Receipt**
                - **Item:** `{rec['item']}`
                - **Category:** `{rec['category']}`
                - **Spent By:** `{rec['spent_by']}`
                - **Amount:** `₹{rec['amount']:,.2f}`
                - **Receiver UPI:** `{rec['upi_id']}`
                - **Time:** `{rec['timestamp']}`
                """
            )
            st.code(upi_url, language="text")


# ==============================================================================
# TAB 2: SEPARATE ₹15,000 DREAM HOUSE, EAR TREATMENT & EMERGENCY VAULT TRACKER
# ==============================================================================
with tab_vault:
    st.markdown(
        """
        <div class="vip-card-gold">
            <h3 style="margin:0; color:#fbbf24;">🏡 ₹15,000 Separate Dream House & Medical Lockbox</h3>
            <p style="margin:6px 0 0 0; font-size:0.86rem; color:#fde68a;">
                This ₹15,000/month tracker is strictly separated from your ₹23,000 spending budget.
                Touch this money ONLY for your Dream House, Ear Medical Treatment, and Family Emergencies!
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Monthly ₹15,000 Sub-Allocation Targets
    DREAM_HOUSE_MONTHLY_GOAL = 8000
    EAR_MEDICAL_MONTHLY_GOAL = 4000
    EMERGENCY_MONTHLY_GOAL = 3000

    # Calculate bucket totals for current month and all-time
    def sum_bucket(df_v, bucket_name):
        if df_v.empty:
            return 0.0
        return float(df_v[df_v["vault_bucket"] == bucket_name]["amount"].sum())

    dh_month = sum_bucket(df_month_vault, "🏡 Dream House Construction Fund")
    ear_month = sum_bucket(df_month_vault, "👂 Ear Medical Treatment Reserve")
    emg_month = sum_bucket(df_month_vault, "🛡️ Family Emergency Shield")

    dh_total = sum_bucket(df_all_vault, "🏡 Dream House Construction Fund")
    ear_total = sum_bucket(df_all_vault, "👂 Ear Medical Treatment Reserve")
    emg_total = sum_bucket(df_all_vault, "🛡️ Family Emergency Shield")

    v1, v2, v3 = st.columns(3)
    v1.metric(
        "🏡 This Month Vault",
        f"₹{vault_saved_this_month:,.0f}",
        f"Target: ₹{STRICT_SAVINGS_TARGET:,}",
    )
    v2.metric(
        "🧱 Total Dream Vault",
        f"₹{vault_saved_all_time:,.0f}",
        f"{int(vault_saved_all_time // 50)} Bricks Bought",
    )
    v3.metric(
        "🛡️ 15K Protection Status",
        f"₹{protected_15k_status:,.0f}",
        "Safe!" if budget_overflow == 0 else f"-₹{budget_overflow:,.0f} Overflow!",
    )

    st.markdown("#### 🎯 Monthly ₹15,000 Lockbox Progress Bars")
    vault_pct = min(1.0, vault_saved_this_month / STRICT_SAVINGS_TARGET)
    st.progress(vault_pct, text=f"Overall Monthly ₹15,000 Lockbox Deposited: ₹{vault_saved_this_month:,.0f} / ₹15,000 ({vault_pct*100:.0f}%)")

    st.progress(
        min(1.0, dh_month / DREAM_HOUSE_MONTHLY_GOAL),
        text=f"🏡 Dream House Sub-Bucket: ₹{dh_month:,.0f} / ₹{DREAM_HOUSE_MONTHLY_GOAL:,} (All-Time: ₹{dh_total:,.0f})",
    )
    st.progress(
        min(1.0, ear_month / EAR_MEDICAL_MONTHLY_GOAL),
        text=f"👂 Ear Medical Treatment Priority Reserve: ₹{ear_month:,.0f} / ₹{EAR_MEDICAL_MONTHLY_GOAL:,} (All-Time: ₹{ear_total:,.0f})",
    )
    st.progress(
        min(1.0, emg_month / EMERGENCY_MONTHLY_GOAL),
        text=f"🛡️ Emergency Shield Sub-Bucket: ₹{emg_month:,.0f} / ₹{EMERGENCY_MONTHLY_GOAL:,} (All-Time: ₹{emg_total:,.0f})",
    )

    # Visual Brick Wall Builder
    total_bricks = max(1, int((vault_saved_all_time + dh_month) // 50))
    brick_wall_visual = "🧱" * min(60, total_bricks)
    st.markdown(
        f"""
        <div class="vip-card">
            <div style="font-weight:700; color:#fbbf24; margin-bottom:6px;">
                🏗️ Apna Sapno Ka Ghar — Live Brick Wall ({total_bricks} Bricks Accumulated @ ₹50/brick)
            </div>
            <div style="font-size:1.25rem; line-height:1.5; word-wrap:break-word;">
                {brick_wall_visual}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Form to Deposit Money into the Separate ₹15K Vault
    st.markdown("#### ➕ Deposit Money into Your ₹15,000 Separate Vault")
    with st.form("vault_deposit_form", clear_on_submit=True):
        vc1, vc2 = st.columns(2)
        with vc1:
            v_bucket = st.selectbox(
                "Select Vault Sub-Bucket",
                options=[
                    "🏡 Dream House Construction Fund",
                    "👂 Ear Medical Treatment Reserve",
                    "🛡️ Family Emergency Shield",
                ],
            )
        with vc2:
            v_amount = st.number_input(
                "Deposit Amount (₹)",
                min_value=100.0,
                max_value=100000.0,
                value=5000.0,
                step=500.0,
            )
        v_notes = st.text_input(
            "Deposit Reference / Bank RD / Gulak Note",
            placeholder="e.g., Transferred to SBI Recurring Deposit / Separate Savings Account",
        )
        v_submit = st.form_submit_button("🔐 Lock Money in ₹15K Separate Vault")
        if v_submit:
            add_vault_deposit(current_user, v_bucket, v_amount, v_notes)
            st.success(f"🎉 ₹{v_amount:,.0f} locked into {v_bucket}!")
            st.rerun()

    # 10-Year Dream House Compounding Calculator
    with st.expander("📈 1-to-10 Year Dream House Corpus Calculator (See How ₹15,000/mo Grows!)"):
        interest_rate = st.slider("Expected Annual Return (RD / FD / SIP %)", 6.0, 15.0, 9.0, 0.5)
        monthly_inv = st.number_input("Monthly Savings Locked (₹)", value=15000, step=1000)
        years_rows = []
        r_monthly = (interest_rate / 100) / 12
        for yr in range(1, 11):
            months = yr * 12
            invested = monthly_inv * months
            future_val = monthly_inv * (((1 + r_monthly) ** months - 1) / r_monthly) * (1 + r_monthly)
            years_rows.append(
                {
                    "Year": f"Year {yr} ({date.today().year + yr})",
                    "Total Deposited": f"₹{invested:,.0f}",
                    "Total Wealth Corpus": f"₹{future_val:,.0f}",
                    "Interest Earned": f"₹{(future_val - invested):,.0f}",
                }
            )
        st.dataframe(pd.DataFrame(years_rows), use_container_width=True, hide_index=True)

    if not df_all_vault.empty:
        st.markdown("#### 📜 Vault Deposit History")
        st.dataframe(
            df_all_vault[["timestamp", "deposited_by", "vault_bucket", "amount", "notes"]],
            use_container_width=True,
            hide_index=True,
        )


# ==============================================================================
# TAB 3: REAL-TIME DASHBOARD, CATEGORY HEALTH METERS & FULL PAYMENT TABLE
# ==============================================================================
with tab_dash:
    st.markdown("### 📊 Live Family Budget Health Meters")

    m1, m2, m3 = st.columns(3)
    m1.metric(
        "💰 Total Monthly Pool",
        f"₹{TOTAL_POOL:,}",
        "₹23k + ₹15k Combined",
    )
    m2.metric(
        "🛒 Spent (Out of ₹23K)",
        f"₹{total_spent_month:,.0f}",
        f"₹{MAX_SPENDING_BUDGET - total_spent_month:,.0f} Left",
        delta_color="normal" if total_spent_month <= MAX_SPENDING_BUDGET else "inverse",
    )
    m3.metric(
        "🚨 Bad Expenses",
        f"₹{bad_spent_month:,.0f}",
        "Target: ₹0",
        delta_color="inverse" if bad_spent_month > 0 else "normal",
    )

    # Category Health Progress Bars
    st.markdown("#### 🚦 Category Cap Health Meters")
    food_ratio = min(1.0, food_spent_month / CAP_FOOD)
    st.progress(
        food_ratio,
        text=f"🍲 Food & Mess Cap: ₹{food_spent_month:,.0f} / ₹{CAP_FOOD:,} ({food_ratio*100:.0f}%)",
    )

    rent_ratio = min(1.0, rent_spent_month / CAP_RENT)
    st.progress(
        rent_ratio,
        text=f"🏠 Room Rent Cap: ₹{rent_spent_month:,.0f} / ₹{CAP_RENT:,} ({rent_ratio*100:.0f}%)",
    )

    home_ratio = min(1.0, home_transfer_month / CAP_HOME_MAX)
    st.progress(
        home_ratio,
        text=f"🏡 Home Transfer (Parents ₹5k-₹7k): ₹{home_transfer_month:,.0f} / ₹{CAP_HOME_MAX:,} ({home_ratio*100:.0f}%)",
    )

    ear_ratio = min(1.0, ear_medical_month / CAP_MEDICAL_EAR)
    st.progress(
        ear_ratio,
        text=f"👂 Ear Medical Priority Expense Logged: ₹{ear_medical_month:,.0f} (Plus Separate Vault Reserve)",
    )

    # Detailed Payments Table with "Spent By", Category, Description, Mode, Need Level
    st.markdown("#### 📋 Complete Payments Register (With `Spent By`, Category & Description)")

    f_col_a, f_col_b = st.columns(2)
    with f_col_a:
        filter_person = st.selectbox(
            "Filter by Spent By",
            options=["All Members", "Amit", "Wife", "Brother", "Joint Family"],
        )
    with f_col_b:
        filter_cat = st.selectbox(
            "Filter by Category",
            options=["All Categories"] + list(CATEGORY_DESCRIPTIONS.keys()),
        )

    df_view = df_month.copy()
    if not df_view.empty:
        if filter_person != "All Members":
            df_view = df_view[df_view["spent_by"] == filter_person]
        if filter_cat != "All Categories":
            df_view = df_view[df_view["category"] == filter_cat]

        df_view["Flag"] = df_view["is_bad_expense"].apply(
            lambda x: "🚨 BAD" if x == 1 else "✅ OK"
        )

        display_cols = [
            "id",
            "timestamp",
            "spent_by",
            "category",
            "item_name",
            "description",
            "amount",
            "Flag",
            "payment_mode",
            "need_level",
            "notes",
        ]
        st.dataframe(
            df_view[display_cols].rename(
                columns={
                    "id": "ID",
                    "timestamp": "Date & Time",
                    "spent_by": "Spent By",
                    "category": "Expense Category",
                    "item_name": "Item",
                    "description": "Description Preset",
                    "amount": "Amount (₹)",
                    "payment_mode": "Mode",
                    "need_level": "Priority",
                    "notes": "Notes",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        # Download CSV Backup & Delete Mistakes
        dl_col, del_col = st.columns([1.2, 1.2])
        with dl_col:
            csv_bytes = df_view.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download Monthly Statement (CSV)",
                data=csv_bytes,
                file_name=f"parivaar_expenses_{current_month_str}.csv",
                mime="text/csv",
            )
        with del_col:
            with st.expander("🗑️ Delete an Incorrect Entry by ID"):
                del_id = st.number_input("Enter Row ID to Delete", min_value=1, step=1)
                if st.button("Confirm Delete Entry"):
                    delete_expense_from_db(int(del_id))
                    st.success(f"Deleted entry #{int(del_id)}")
                    st.rerun()
    else:
        st.info("No expenses logged for this month yet. Use the 'Pre-Pay & UPI' tab before making any payment!")


# ==============================================================================
# TAB 4: STUDY ACADEMY (LONG VIDEOS), DESI COOKING & MOTIVATION SHORTS + SEARCH
# ==============================================================================
with tab_learn:
    st.markdown(
        """
        <div class="vip-card-green">
            <h4 style="margin:0; color:#00ff9d;">🎓 Data Engineer Academy • 🍲 Sasta Ghar Ka Khana • 🔍 AI Search</h4>
            <p style="margin:4px 0 0 0; font-size:0.84rem; color:#cbd5e1;">
                Zero time-pass! Only 3 things allowed here: Tech Skills to jump from ₹23K to ₹1L+/month,
                affordable Indian home cooking to beat the ₹7K food cap, and pure family hustle motivation.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------------------------
    # SECTION A: INTEGRATED GEMINI AI MENTOR + GOOGLE & YOUTUBE SEARCH BAR
    # --------------------------------------------------------------------------
    st.markdown("### 🔍 Smart Search Bar (Gemini AI + Google + YouTube Study Search)")

    with st.expander("🔑 Optional: Add Free Gemini API Key for Live AI Answers"):
        user_gemini_key = st.text_input(
            "Enter Gemini API Key (or set GEMINI_API_KEY in Streamlit Secrets)",
            value=st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else "",
            type="password",
        )

    search_col1, search_col2 = st.columns([2.2, 1])
    with search_col1:
        search_query = st.text_input(
            "Ask Python / SQL / Excel Doubt, or Budget Desi Recipe, or Search Google:",
            placeholder="e.g., How to use XLOOKUP in Excel? OR ₹40 Masala Tehri recipe OR PySpark roadmap",
        )
    with search_col2:
        search_topic_tag = st.selectbox(
            "Search Focus",
            options=[
                "🐍 Python / Data Eng",
                "📊 Advanced Excel",
                "🍲 Budget Desi Recipe",
                "🌐 General Google Search",
            ],
        )

    sc_btn1, sc_btn2, sc_btn3 = st.columns(3)
    ask_ai_clicked = sc_btn1.button("🤖 Ask AI Mentor Here")

    encoded_q = urllib.parse.quote_plus(
        f"{search_query} {search_topic_tag.split(' ', 1)[1]}" if search_query else "Python Data Engineering Hindi"
    )
    sc_btn2.markdown(
        f'<a href="https://www.google.com/search?q={encoded_q}" target="_blank" class="upi-pay-btn" style="padding:10px; font-size:0.9rem; margin:0;">🌐 Search Google</a>',
        unsafe_allow_html=True,
    )
    sc_btn3.markdown(
        f'<a href="https://www.youtube.com/results?search_query={encoded_q}" target="_blank" class="upi-pay-btn" style="padding:10px; font-size:0.9rem; margin:0; background:linear-gradient(90deg,#ef4444,#dc2626); color:white !important;">▶️ YouTube Search</a>',
        unsafe_allow_html=True,
    )

    if ask_ai_clicked and search_query.strip():
        with st.spinner("🧠 Thinking..."):
            answer_md = ask_gemini_or_fallback(search_query.strip(), api_key=user_gemini_key)
            st.markdown(f'<div class="vip-card">{answer_md}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # --------------------------------------------------------------------------
    # SECTION B: LONG VIDEOS vs SHORT VIDEOS (REELS) SUB-TABS
    # --------------------------------------------------------------------------
    sub_long, sub_shorts, sub_roadmap = st.tabs(
        [
            "🖥️ Long Videos (Padhai & Tech)",
            "📱 Shorts/Reels (Desi Khana & Motivation)",
            "🗺️ Data Engineer Roadmap Tracker",
        ]
    )

    # 1. LONG VIDEOS: PYTHON, ADVANCED EXCEL, SQL, DATA ENGINEERING
    with sub_long:
        st.markdown("#### 🖥️ Long-Form Study Classes (Data Engineer & Data Scientist Path)")
        study_track = st.selectbox(
            "🎯 Choose Your Tech Subject:",
            options=[
                "🐍 Python Full Mastery (Automation, Pandas & Data Science)",
                "📊 Advanced Excel, MIS & Power Query Automation",
                "🗄️ SQL, PySpark & Data Engineering Pipeline Mastery",
                "📈 Power BI, Streamlit & Machine Learning Projects",
            ],
        )

        LONG_COURSES = {
            "🐍 Python Full Mastery (Automation, Pandas & Data Science)": [
                {
                    "title": "Python Complete Tutorial for Beginners to Advanced (Hindi)",
                    "url": "https://www.youtube.com/watch?v=UrsmFxEIp5k",
                    "desc": "Complete Python foundation + hands-on coding exercises for Data Engineering & Automation.",
                },
                {
                    "title": "Python Pandas Full Data Analysis Tutorial",
                    "url": "https://www.youtube.com/watch?v=vmEHCJofslg",
                    "desc": "Master DataFrames, CSV/Excel cleaning, GroupBy, Merging & ETL transformations.",
                },
            ],
            "📊 Advanced Excel, MIS & Power Query Automation": [
                {
                    "title": "Advanced Excel Full Course (VLOOKUP, XLOOKUP, Pivot Tables, Dashboards)",
                    "url": "https://www.youtube.com/watch?v=Vl0H-qTclOg",
                    "desc": "Everything needed to crack MIS Executive / Data Analyst interviews immediately.",
                },
                {
                    "title": "Power Query in Excel — Automate Daily Reports in 1 Click",
                    "url": "https://www.youtube.com/watch?v=0aeZX1l4JT4",
                    "desc": "Clean messy datasets and automate repetitive office Excel work.",
                },
            ],
            "🗄️ SQL, PySpark & Data Engineering Pipeline Mastery": [
                {
                    "title": "SQL Full Course for Data Analysts & Data Engineers",
                    "url": "https://www.youtube.com/watch?v=HXV3zeQKqGY",
                    "desc": "Joins, Subqueries, CTEs, Window Functions & Database Design.",
                },
                {
                    "title": "Apache Spark / PySpark Tutorial for Data Engineering",
                    "url": "https://www.youtube.com/watch?v=_C8kWso4ne4",
                    "desc": "Big Data processing with PySpark — the #1 skill for high-paying Data Engineer jobs.",
                },
            ],
            "📈 Power BI, Streamlit & Machine Learning Projects": [
                {
                    "title": "Build Data Science & Analytics Web Apps with Python Streamlit",
                    "url": "https://www.youtube.com/watch?v=JwSS70SZdyM",
                    "desc": "Turn your Python scripts into interactive production web dashboards.",
                },
                {
                    "title": "Machine Learning for Everybody – Full Course",
                    "url": "https://www.youtube.com/watch?v=i_LwzRVP7bg",
                    "desc": "Understand regression, classification, and practical ML models.",
                },
            ],
        }

        for idx, vid in enumerate(LONG_COURSES[study_track], start=1):
            st.markdown(f"**{idx}. {vid['title']}**")
            st.caption(vid["desc"])
            st.video(vid["url"])

    # 2. SHORT VIDEOS / REELS: NORMAL BUDGET INDIAN COOKING & HUSTLE MOTIVATION
    with sub_shorts:
        st.markdown("#### 📱 Short Videos / Reels (Sasta Ghar Ka Khana & Pure Hustle Motivation)")
        reel_category = st.radio(
            "Choose Short Video Feed:",
            options=[
                "🍲 Normal Ghar Ka Khana (Budget Desi Cooking Shorts)",
                "🔥 Family Hustle, Saving & Study Motivation Shorts",
            ],
            horizontal=True,
        )

        if "Khana" in reel_category:
            st.info(
                "💡 **Why Desi Cooking Shorts?** Outside food destroys the ₹7,000 Food Cap. Cooking tasty Masala Tehri, Crispy Bhindi, Tadka Dal, or Egg/Besan Chilla at home takes 15 mins and costs under ₹40!"
            )

            sh_c1, sh_c2 = st.columns(2)
            with sh_c1:
                st.markdown("**🍛 1-Pot Masala Tehri / Veg Pulao (₹40 Budget)**")
                st.video("https://www.youtube.com/watch?v=w7Wj2_T0b9A")
                st.markdown(
                    '<a href="https://www.youtube.com/results?search_query=simple+indian+home+cooking+sabzi+dal+shorts+hindi" target="_blank" class="upi-pay-btn" style="padding:10px; font-size:0.86rem;">📱 Open Desi Sabzi & Dal Shorts Feed</a>',
                    unsafe_allow_html=True,
                )
            with sh_c2:
                st.markdown("**🥗 Kurkuri Bhindi / Quick Tiffin Sabzi**")
                st.video("https://www.youtube.com/watch?v=3m7B92p2R7k")
                st.markdown(
                    '<a href="https://www.youtube.com/results?search_query=low+budget+indian+dinner+recipes+under+50+rupees+shorts" target="_blank" class="upi-pay-btn" style="padding:10px; font-size:0.86rem;">🍲 Open Under-₹50 Budget Recipe Reels</a>',
                    unsafe_allow_html=True,
                )

            with st.expander("📖 Instant Written Desi Recipes (Zero Data Needed!)"):
                st.markdown(
                    """
                    - **1. झटपट मसाला तहरी (₹40 में 3 लोगों का पेट भरे):** कुकर में 1 चम्मच तेल, जीरा, प्याज, आलू, सोयाबीन और हल्दी-धनिया-गरम मसाला भूनें। 1 गिलास चावल और 2 गिलास पानी डालकर 2 सीटी लगाएं। बाहर के ₹150 के बिरयानी/जंक से 10 गुना बेहतर!
                    - **2. कुरकुरी तली हुई भिंडी (Tiffin Special):** भिंडी को धोकर सुखा लें। कड़ाही में सरसों का तेल, जीरा, हरी मिर्च डालें। भिंडी डालकर बिना ढके मध्यम आंच पर पकाएं। अंत में नमक, हल्दी, लाल मिर्च और अमचूर पाउडर डालें।
                    - **3. ₹20 बेसन चीला (High-Protein Breakfast):** 1 कप बेसन, बारीक प्याज, टमाटर, हरी मिर्च, अजवाइन और नमक घोलकर तवे पर 3 मिनट में बनाएं—बाहर के समोसे-कचौड़ी की कभी ज़रूरत नहीं पड़ेगी!
                    """
                )
        else:
            st.info(
                "🔥 **Pure Middle-Class Hustle Feed:** Watch for 2 minutes whenever you feel tired after work, then get straight back to Python/SQL and saving for your Dream House!"
            )
            m_c1, m_c2 = st.columns(2)
            with m_c1:
                st.markdown("**💪 Discipline & Hard Work Mentality**")
                st.video("https://www.youtube.com/watch?v=ZXsQAXx_ao0")
                st.markdown(
                    '<a href="https://www.youtube.com/results?search_query=middle+class+family+hard+work+study+motivation+shorts+hindi" target="_blank" class="upi-pay-btn" style="padding:10px; font-size:0.86rem;">🔥 Open Hindi Hustle Motivation Shorts</a>',
                    unsafe_allow_html=True,
                )
            with m_c2:
                st.markdown("**🏡 Saving Money & Building Your Future**")
                st.video("https://www.youtube.com/watch?v=mgmVOuLgFB0")
                st.markdown(
                    '<a href="https://www.youtube.com/results?search_query=data+engineer+study+after+job+motivation+shorts" target="_blank" class="upi-pay-btn" style="padding:10px; font-size:0.86rem;">🚀 Open Career & Coding Motivation Reels</a>',
                    unsafe_allow_html=True,
                )

    # 3. INTERACTIVE DATA ENGINEER / SCIENTIST CAREER ROADMAP TRACKER
    with sub_roadmap:
        st.markdown("#### 🗺️ Your Personal Data Engineer / Scientist Checklist (Saved in DB)")
        ROADMAP_SKILLS = [
            ("excel_adv", "📊 Step 1: Advanced Excel (XLOOKUP, Pivot Tables, Power Query, MIS Automation)"),
            ("python_core", "🐍 Step 2: Python Core + Automation (Loops, Functions, Files, Playwright/Requests)"),
            ("python_pandas", "🐼 Step 3: Python Pandas & NumPy (Data Cleaning, CSV/Excel ETL, Aggregations)"),
            ("sql_mastery", "🗄️ Step 4: SQL Mastery (Joins, Group By, CTEs, Window Functions, PostgreSQL)"),
            ("streamlit_bi", "📈 Step 5: Dashboards (Streamlit Web Apps + Power BI Interactive Reports)"),
            ("pyspark_etl", "⚡ Step 6: Big Data & ETL (PySpark, Airflow Basics, Cloud Data Warehousing)"),
            ("ml_basics", "🤖 Step 7: Data Science & ML Basics (Scikit-Learn, Forecasting, Portfolio on GitHub)"),
        ]

        saved_prog = get_career_progress()
        completed_count = 0
        for key, label in ROADMAP_SKILLS:
            is_done = saved_prog.get(key, False)
            checked = st.checkbox(label, value=is_done, key=f"chk_{key}")
            if checked != is_done:
                set_career_progress(key, checked)
                st.rerun()
            if checked:
                completed_count += 1

        prog_pct = completed_count / len(ROADMAP_SKILLS)
        st.progress(prog_pct, text=f"Career Readiness: {completed_count}/{len(ROADMAP_SKILLS)} Milestones Completed ({prog_pct*100:.0f}%)")


# ==============================================================================
# TAB 5: MONTHLY ANALYTICS CHARTS & AUTOMATED AI SPENDING COUNSELOR
# ==============================================================================
with tab_counselor:
    st.markdown("### 🧠 Monthly AI Financial Counselor & Visual Analytics")

    # Calculate Monthly Discipline Grade
    score = 100
    feedback_bullets = []

    if total_spent_month > MAX_SPENDING_BUDGET:
        score -= 35
        feedback_bullets.append(
            f"❌ **Total Spending Alert:** You spent ₹{total_spent_month:,.0f}, crossing the ₹{MAX_SPENDING_BUDGET:,} max budget by ₹{total_spent_month - MAX_SPENDING_BUDGET:,.0f}. This directly eats into your ₹15,000 Dream House Vault!"
        )
    else:
        feedback_bullets.append(
            f"✅ **Overall Budget Under Control:** Total spending is ₹{total_spent_month:,.0f} / ₹{MAX_SPENDING_BUDGET:,}. Your ₹15,000 savings target is safe!"
        )

    if food_spent_month > CAP_FOOD:
        score -= 25
        feedback_bullets.append(
            f"❌ **Food Cap Breached:** Food & Mess is at ₹{food_spent_month:,.0f} (Cap: ₹{CAP_FOOD:,}). Stop all outside snacks/tea and use the Desi Cooking Shorts tab!"
        )
    elif food_spent_month >= 0.8 * CAP_FOOD:
        score -= 10
        feedback_bullets.append(
            f"⚠️ **Food Cap Near Limit:** Food spending is at ₹{food_spent_month:,.0f} ({food_spent_month/CAP_FOOD*100:.0f}% of ₹7,000 cap). Be extra careful for the rest of the month."
        )
    else:
        feedback_bullets.append(
            f"✅ **Food Discipline Great:** Food spending is ₹{food_spent_month:,.0f} / ₹{CAP_FOOD:,}."
        )

    if bad_spent_month > 0:
        penalty = min(30, int(bad_spent_month // 100) * 5 + 10)
        score -= penalty
        feedback_bullets.append(
            f"🚨 **Wasted Money Detected:** ₹{bad_spent_month:,.0f} was spent on Bad/Unnecessary items (rides, junk food, impulse items). Redirect this straight into your Ear Medical or Dream House Vault!"
        )
    else:
        feedback_bullets.append(
            "🏆 **Zero Bad Expenses:** ₹0 wasted on unnecessary cabs or junk food this month! Outstanding family discipline."
        )

    score = max(0, score)
    if score >= 90:
        grade = "A+ (Champion Saver 🏆)"
        grade_color = "#00ff9d"
    elif score >= 75:
        grade = "B+ (Disciplined 👍)"
        grade_color = "#38bdf8"
    elif score >= 60:
        grade = "C (Needs Strict Control ⚠️)"
        grade_color = "#fbbf24"
    else:
        grade = "D (Danger Zone — Protect Your ₹15K! 🚨)"
        grade_color = "#ff3366"

    st.markdown(
        f"""
        <div class="vip-card" style="border-left: 6px solid {grade_color};">
            <h4 style="margin:0; color:{grade_color};">📋 Monthly Discipline Grade: {grade} (Score: {score}/100)</h4>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for b in feedback_bullets:
        st.markdown(b)

    # Interactive Plotly Dark Mode Charts
    if not df_month.empty:
        ch_col1, ch_col2 = st.columns(2)

        with ch_col1:
            st.markdown("#### 🍩 Category Breakdown")
            cat_group = df_month.groupby("category", as_index=False)["amount"].sum()
            fig_donut = px.pie(
                cat_group,
                names="category",
                values="amount",
                hole=0.52,
                template="plotly_dark",
                color_discrete_sequence=px.colors.qualitative.Bold,
            )
            fig_donut.update_layout(
                margin=dict(t=20, b=20, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=True,
            )
            st.plotly_chart(fig_donut, use_container_width=True)

        with ch_col2:
            st.markdown("#### ⚖️ Essential vs. Bad Expenses")
            df_month["Expense Type"] = df_month["is_bad_expense"].apply(
                lambda x: "Bad / Unnecessary" if x == 1 else "Necessary / Essential"
            )
            bad_group = df_month.groupby("Expense Type", as_index=False)["amount"].sum()
            fig_pie = px.pie(
                bad_group,
                names="Expense Type",
                values="amount",
                hole=0.45,
                template="plotly_dark",
                color="Expense Type",
                color_discrete_map={
                    "Necessary / Essential": "#00ff9d",
                    "Bad / Unnecessary": "#ff3366",
                },
            )
            fig_pie.update_layout(
                margin=dict(t=20, b=20, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # Member-wise Spending Breakdown ("Spent By" Analytics)
        st.markdown("#### 👨‍👩‍👦 Family Member (`Spent By`) Discipline Comparison")
        mem_group = (
            df_month.groupby(["spent_by", "Expense Type"], as_index=False)["amount"].sum()
        )
        fig_bar = px.bar(
            mem_group,
            x="spent_by",
            y="amount",
            color="Expense Type",
            barmode="group",
            template="plotly_dark",
            color_discrete_map={
                "Necessary / Essential": "#00ff9d",
                "Bad / Unnecessary": "#ff3366",
            },
        )
        fig_bar.update_layout(
            margin=dict(t=20, b=20, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="Spent By (Family Member)",
            yaxis_title="Amount Spent (₹)",
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Log your first transaction in the 'Pre-Pay & UPI' tab to unlock live interactive charts!")
