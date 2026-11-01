import os
import io
import re
import json
import random
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, date, timedelta
import calendar

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import qrcode

# Optional SQLAlchemy for Cloud PostgreSQL (Supabase/Neon)
try:
    from sqlalchemy import create_engine, text
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

# ==============================================================================
# 1. PAGE SETUP & HIDE ALL DEFAULT STREAMLIT CHROME
# ==============================================================================
st.set_page_config(
    page_title="Parivaar OS 6.0 | 100x Interactive Super-App",
    page_icon="👑",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ==============================================================================
# 2. DEFAULT MASTER SETTINGS & USERS (ALL EDITABLE IN MASTER HUB!)
# ==============================================================================
DEFAULT_MASTER_SETTINGS = {
    "universal_pool": (38000.0, "🏦 कुल मासिक यूनिवर्सल पूल (Total Family Pool ₹)"),
    "savings_vault_target": (15000.0, "🔐 मासिक पक्की बचत तिजोरी (Monthly Vault Target ₹)"),
    "cap_food": (7000.0, "🍲 खाना और मेस कैप (Food Monthly Cap ₹)"),
    "cap_rent": (6000.0, "🏠 रूम रेंट और बिजली कैप (Rent Monthly Cap ₹)"),
    "cap_home_transfer": (7000.0, "🏡 गाँव / माता-पिता सपोर्ट कैप (Home Transfer Cap ₹)"),
    "cap_ear_medical": (3000.0, "👂 कान का इलाज प्राथमिकता कैप (Ear Medical Cap ₹)"),
    "default_shopping_budget": (6000.0, "🛍️ डिफ़ॉल्ट शॉपिंग ट्रिप बजट (Shopping Expected Limit ₹)"),
    "daily_reward_limit": (200.0, "🏆 डेली डोपामाइन रिवॉर्ड खर्च सीमा (Daily Safe Limit ₹)"),
    "brick_price": (50.0, "🧱 सपनों के घर की 1 ईंट की कीमत (Price per Brick ₹)"),
}

DEFAULT_CUSTOM_GOALS = [
    ("🏡 सपनों का अपना घर (Dream House Fund)", "🏡", 500000.0, 45000.0, "2028-12-31", "High Priority"),
    ("👂 कान का पूरा इलाज (Ear Medical Shield)", "👂", 25000.0, 8000.0, "2026-12-31", "Urgent Health"),
    ("💻 Data Analytics & Coding Setup", "💻", 45000.0, 12000.0, "2027-06-30", "Career Growth"),
    ("🛡️ परिवार इमरजेंसी सुरक्षा कवच", "🛡️", 100000.0, 22000.0, "2027-12-31", "Safety Net"),
]

DEFAULT_USERS = [
    ("Ajay", "52729211", "👑 Chief Admin • Universal Account", 1, "👑"),
    ("Meenakshi", "2345", "👩‍💼 Partner • Universal Account", 0, "👩‍💼"),
    ("Ajeet", "3456", "🧑‍🎓 Family Member • Universal Account", 0, "🧑‍🎓"),
]

CATEGORY_DESCRIPTIONS = {
    "Shopping & Clothes (साड़ी, कपड़े और शॉपिंग)": [
        "साड़ी / सूट / कुर्ती शॉपिंग (Saree & Ethnic)",
        "फॉर्मल शर्ट / ट्राउज़र / ऑफिस वियर",
        "जूते / सैंडल / फॉर्मल बूट्स (Footwear)",
        "स्किनकेयर / सनस्क्रीन / डेली केयर",
        "त्योहार या परिवार की शॉपिंग",
        "अन्य शॉपिंग सामान...",
    ],
    "Food & Mess (खाना, चिकन/मछली और टिफिन)": [
        "सुबह की चाय / बिस्किट (Morning Tea)",
        "ऑफिस लंच / टिफिन (Office Lunch)",
        "दूध, दही, ओट्स और केले (Milk, Oats & Fruits)",
        "ताज़ी मछली / चिकन / अंडे (Home Non-Veg)",
        "दाल मखनी / चना आलू / संडे डिनर",
        "महीने का मेस / राशन बिल (Mess/Ration)",
        "शाम का समोसा / बाहर का नाश्ता (Avoid!)",
        "बाहर का चाउमीन / मोमोज / जंक फूड (Bad Expense!)",
    ],
    "Sabzi & Kirana (सब्ज़ी और राशन)": [
        "रोज़ की हरी सब्ज़ी (आलू, प्याज, भिंडी, टमाटर)",
        "आटा, चावल, दाल, सत्तू और चना (Monthly Grocery)",
        "मसाले, तेल और रसोई का सामान",
        "रसोई गैस सिलेंडर (LPG Refill)",
    ],
    "Room Rent (कमरे का किराया)": [
        "महीने का रूम रेंट (Monthly Room Rent)",
        "बिजली और पानी का बिल (Electricity/Water)",
        "कमरे की मरम्मत / मेंटेनेंस",
    ],
    "Home Transfer (गाँव / माता-पिता)": [
        "माता-पिता के लिए महीने का खर्च (Parents Support)",
        "गाँव में दवाई / इलाज के लिए पैसे",
        "त्योहार / घर की ज़रूरत के लिए ट्रांसफर",
    ],
    "Ear Medical (कान का इलाज - Priority)": [
        "कान के डॉक्टर की फीस (Ear Specialist Fee)",
        "कान की दवाई और ड्रॉप्स (Ear Medicine)",
        "कान की जांच / टेस्ट (Ear Checkup/Test)",
    ],
    "Metro, Bus & Auto (आना-जाना)": [
        "DTC बस टिकट / मेट्रो रिचार्ज (Bus/Metro)",
        "शेयरिंग ई-रिक्शा / ऑटो (Necessary E-Rickshaw)",
        "अकेले रिज़र्व ऑटो / कैब (फालतू खर्च - Avoid!)",
    ],
    "Padhai, AI & English (पढ़ाई और करियर)": [
        "Python / Power Query / Data Analysis कोर्स या किताब",
        "Spoken English प्रैक्टिस / नोटबुक",
        "मोबाइल रिचार्ज / Wi-Fi इंटरनेट बिल",
    ],
    "Faltu / Bad Expense (गैर-ज़रूरी खर्च)": [
        "बिना सोचे-समझे ऑटो / कैब किया (Unplanned Ride)",
        "बाहर का महंगा फास्ट फूड / पिज़्ज़ा / बर्गर",
        "ऑनलाइन फालतू शॉपिंग (Impulse Buy)",
    ],
}

# ==============================================================================
# 3. ULTRA-INTERACTIVE INSTAGRAM / YOUTUBE / CRED NEO-GLASS THEMES
# ==============================================================================
THEMES = {
    "🔥 Insta-Reels Neon Glass (Instagram & YouTube Dark Mode)": {
        "bg_main": "radial-gradient(circle at 15% 10%, #1a0924 0%, #090a10 55%, #050508 100%)",
        "card_bg": "rgba(18, 21, 33, 0.88)",
        "card_border": "#ec4899",
        "accent": "#f43f5e",
        "accent_sec": "#fbbf24",
        "accent_green": "#10b981",
        "story_grad": "linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%)",
    },
    "💎 CRED Royal Obsidian Gold (प्रीमियम नियो-बैंक लक्ज़री)": {
        "bg_main": "radial-gradient(circle at 20% 0%, #241905 0%, #0b0e17 60%, #04060a 100%)",
        "card_bg": "rgba(17, 24, 39, 0.92)",
        "card_border": "#fbbf24",
        "accent": "#fbbf24",
        "accent_sec": "#00ff9d",
        "accent_green": "#00ff9d",
        "story_grad": "linear-gradient(135deg, #fbbf24 0%, #f59e0b 50%, #10b981 100%)",
    },
    "⚡ Cyber Emerald Matrix (पैसा और ग्रोथ फोकस)": {
        "bg_main": "radial-gradient(circle at 50% 0%, #042f2e 0%, #070b14 65%, #030509 100%)",
        "card_bg": "rgba(15, 23, 42, 0.90)",
        "card_border": "#00ff9d",
        "accent": "#00ff9d",
        "accent_sec": "#38bdf8",
        "accent_green": "#00ff9d",
        "story_grad": "linear-gradient(135deg, #00ff9d 0%, #06b6d4 50%, #3b82f6 100%)",
    },
    "🌌 Cosmic Creator Studio (डीप फोकस और कोडिंग नाइट)": {
        "bg_main": "radial-gradient(circle at 80% 10%, #1e1b4b 0%, #090d16 60%, #030408 100%)",
        "card_bg": "rgba(19, 17, 38, 0.90)",
        "card_border": "#818cf8",
        "accent": "#a855f7",
        "accent_sec": "#38bdf8",
        "accent_green": "#34d399",
        "story_grad": "linear-gradient(135deg, #a855f7 0%, #6366f1 50%, #38bdf8 100%)",
    },
}

if "selected_theme" not in st.session_state:
    st.session_state.selected_theme = "🔥 Insta-Reels Neon Glass (Instagram & YouTube Dark Mode)"


def apply_neo_interactive_css(theme_name: str):
    t = THEMES.get(theme_name, THEMES["🔥 Insta-Reels Neon Glass (Instagram & YouTube Dark Mode)"])
    st.markdown(
        f"""
        <style>
        #MainMenu {{visibility: hidden !important; display: none !important;}}
        header {{visibility: hidden !important; height: 0px !important; display: none !important;}}
        footer {{visibility: hidden !important; display: none !important;}}
        [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
        [data-testid="manage-app-button"], .stAppDeployButton, .stDeployButton {{
            display: none !important; visibility: hidden !important;
        }}

        .stApp {{
            background: {t['bg_main']} !important;
            color: #ffffff !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }}
        .block-container {{
            padding-top: 0.5rem !important;
            padding-bottom: 4.5rem !important;
            max-width: 850px !important;
        }}

        label, .stWidgetLabel, .stMarkdown p, .stMarkdown li, span, h1, h2, h3, h4, h5, h6 {{
            color: #ffffff !important;
        }}

        /* Inputs & Dropdowns */
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        div[data-baseweb="base-input"],
        input, textarea {{
            background-color: #161b26 !important;
            color: #ffffff !important;
            border: 1.5px solid rgba(255,255,255,0.18) !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
        }}
        div[data-baseweb="select"] > div:hover, input:focus {{
            border-color: {t['accent']} !important;
            box-shadow: 0 0 12px rgba(244, 63, 94, 0.35) !important;
        }}
        ul[data-baseweb="menu"], div[data-baseweb="popover"] div, li[role="option"] {{
            background-color: #0f172a !important;
            color: #ffffff !important;
            font-weight: 600 !important;
        }}
        li[role="option"]:hover {{
            background-color: {t['accent']} !important;
            color: #000000 !important;
        }}

        /* Metric Cards */
        div[data-testid="stMetric"] {{
            background: {t['card_bg']} !important;
            border: 1px solid rgba(255,255,255,0.14) !important;
            border-top: 3px solid {t['accent']} !important;
            border-radius: 16px !important;
            padding: 12px 14px !important;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5) !important;
            transition: transform 0.2s ease !important;
        }}
        div[data-testid="stMetric"]:hover {{
            transform: translateY(-3px) !important;
            border-color: {t['accent_sec']} !important;
        }}
        div[data-testid="stMetricLabel"] p {{
            color: #cbd5e1 !important;
            font-weight: 700 !important;
            font-size: 0.8rem !important;
        }}
        div[data-testid="stMetricValue"] div {{
            color: {t['accent_sec']} !important;
            font-weight: 900 !important;
            font-size: 1.32rem !important;
        }}

        /* Pill Navigation Tabs (YouTube / Instagram Chip Bar Style) */
        button[data-baseweb="tab"] {{
            background-color: rgba(30, 41, 59, 0.75) !important;
            color: #cbd5e1 !important;
            border-radius: 999px !important;
            padding: 7px 14px !important;
            margin-right: 6px !important;
            margin-bottom: 6px !important;
            font-weight: 700 !important;
            font-size: 0.84rem !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
            transition: all 0.2s ease !important;
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            background: {t['story_grad']} !important;
            color: #ffffff !important;
            font-weight: 900 !important;
            border: 1.5px solid #ffffff !important;
            box-shadow: 0 4px 15px rgba(244, 63, 94, 0.45) !important;
            transform: scale(1.03);
        }}
        button[data-baseweb="tab"][aria-selected="true"] p {{
            color: #ffffff !important;
            font-weight: 900 !important;
        }}

        /* Instagram Stories Goal Bar */
        .insta-story-bar {{
            display: flex;
            gap: 12px;
            overflow-x: auto;
            padding: 10px 4px 12px 4px;
            margin-bottom: 10px;
            scrollbar-width: none;
        }}
        .insta-story-item {{
            display: flex;
            flex-direction: column;
            align-items: center;
            min-width: 82px;
            text-align: center;
        }}
        .insta-ring {{
            width: 64px;
            height: 64px;
            border-radius: 50%;
            padding: 3px;
            background: {t['story_grad']};
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 14px rgba(220, 39, 67, 0.45);
            transition: transform 0.2s ease;
        }}
        .insta-ring:hover {{
            transform: scale(1.08);
        }}
        .insta-inner {{
            width: 100%;
            height: 100%;
            border-radius: 50%;
            background: #090d16;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            border: 2px solid #090d16;
        }}
        .insta-label {{
            font-size: 0.72rem;
            font-weight: 800;
            color: #f8fafc;
            margin-top: 5px;
            line-height: 1.15;
        }}
        .insta-sub {{
            font-size: 0.68rem;
            color: {t['accent_sec']};
            font-weight: 800;
        }}

        /* Glass Cards */
        .neo-card {{
            background: {t['card_bg']};
            backdrop-filter: blur(18px);
            border: 1px solid rgba(255,255,255,0.14);
            border-left: 5px solid {t['accent']};
            border-radius: 18px;
            padding: 15px 18px;
            margin-bottom: 12px;
            box-shadow: 0 10px 28px rgba(0,0,0,0.45);
        }}

        /* Expected vs Actual Highlight Badges */
        .badge-saved {{
            background: linear-gradient(90deg, rgba(16,185,129,0.25), rgba(5,150,105,0.4));
            border: 1.5px solid #10b981;
            color: #6ee7b7 !important;
            padding: 5px 12px;
            border-radius: 999px;
            font-weight: 900;
            font-size: 0.8rem;
            display: inline-block;
        }}
        .badge-over {{
            background: linear-gradient(90deg, rgba(239,68,68,0.28), rgba(185,28,28,0.45));
            border: 1.5px solid #ef4444;
            color: #fca5a5 !important;
            padding: 5px 12px;
            border-radius: 999px;
            font-weight: 900;
            font-size: 0.8rem;
            display: inline-block;
        }}
        .badge-wait {{
            background: rgba(251, 191, 36, 0.16);
            border: 1.5px solid #fbbf24;
            color: #fde68a !important;
            padding: 5px 12px;
            border-radius: 999px;
            font-weight: 800;
            font-size: 0.8rem;
            display: inline-block;
        }}

        /* Action Buttons */
        .upi-app-btn {{
            display: block; width: 100%; text-align: center;
            background: linear-gradient(90deg, #00ff9d 0%, #10b981 100%);
            color: #022c22 !important; font-weight: 900; font-size: 0.94rem;
            padding: 11px 14px; border-radius: 12px; text-decoration: none !important;
            margin: 5px 0; border: 1.5px solid #ffffff;
            box-shadow: 0 6px 18px rgba(16, 185, 129, 0.35);
        }}

        div.stButton > button, div.stFormSubmitButton > button, div.stDownloadButton > button {{
            width: 100%;
            border-radius: 12px !important;
            min-height: 44px !important;
            font-weight: 800 !important;
            border: 1.5px solid {t['accent']} !important;
            background: linear-gradient(135deg, #161f33 0%, #0f172a 100%) !important;
            color: #ffffff !important;
            transition: all 0.2s ease !important;
        }}
        div.stButton > button:hover, div.stFormSubmitButton > button:hover, div.stDownloadButton > button:hover {{
            background: {t['story_grad']} !important;
            color: #ffffff !important;
            border-color: #ffffff !important;
            transform: translateY(-2px);
            box-shadow: 0 6px 18px rgba(244, 63, 94, 0.4) !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_svg_ring_gauge(title: str, subtitle: str, pct: float, amount_str: str, color_hex: str = "#00ff9d") -> str:
    """Renders an Apple-Watch / CRED style animated circular SVG gauge."""
    clamped = max(0.0, min(100.0, pct))
    dash_array = f"{clamped:.1f}, 100"
    return f"""
    <div style="background:rgba(15,23,42,0.88); border:1.5px solid {color_hex}; border-radius:18px; padding:12px; text-align:center; box-shadow:0 8px 20px rgba(0,0,0,0.45);">
        <div style="font-size:0.78rem; font-weight:800; color:#cbd5e1; margin-bottom:6px;">{title}</div>
        <svg viewBox="0 0 36 36" style="width:88px; height:88px; display:block; margin:0 auto;">
            <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none" stroke="#1e293b" stroke-width="3.4"/>
            <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none" stroke="{color_hex}" stroke-width="3.4"
                  stroke-dasharray="{dash_array}" stroke-linecap="round"/>
            <text x="18" y="19.5" fill="#ffffff" font-size="7.2" font-weight="900" text-anchor="middle">{pct:.0f}%</text>
            <text x="18" y="25.5" fill="#fde68a" font-size="3.6" font-weight="700" text-anchor="middle">UTILIZED</text>
        </svg>
        <div style="font-size:1.0rem; font-weight:900; color:{color_hex}; margin-top:6px;">{amount_str}</div>
        <div style="font-size:0.73rem; color:#fde68a; font-weight:700;">{subtitle}</div>
    </div>
    """


# ==============================================================================
# 4. PERSISTENT DATABASE + MASTER SETTINGS + GOALS + AUTO MIRROR
# ==============================================================================
DB_FILE = "parivaar_vip_v6.db"
BACKUP_MIRROR_FILE = "parivaar_auto_mirror_v6.json"


def get_sqlite_conn():
    conn = sqlite3.connect(DB_FILE, timeout=30.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db():
    conn = get_sqlite_conn()
    c = conn.cursor()

    # 1. Users Table
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS app_users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            avatar TEXT DEFAULT '👤'
        )
        """
    )
    for u, p, r, adm, av in DEFAULT_USERS:
        c.execute(
            "INSERT OR IGNORE INTO app_users (username, password, role, is_admin, avatar) VALUES (?, ?, ?, ?, ?)",
            (u, p, r, adm, av),
        )
    c.execute("UPDATE app_users SET is_admin = 1, avatar = '👑' WHERE username = 'Ajay'")

    # 2. Master Settings Table (Editable Budget Constants)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS master_settings (
            setting_key TEXT PRIMARY KEY,
            setting_val REAL NOT NULL,
            label TEXT NOT NULL
        )
        """
    )
    for k, (val, lbl) in DEFAULT_MASTER_SETTINGS.items():
        c.execute(
            "INSERT OR IGNORE INTO master_settings (setting_key, setting_val, label) VALUES (?, ?, ?)",
            (k, float(val), lbl),
        )

    # 3. Custom Goals Table (Editable Life Goals)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS custom_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_title TEXT NOT NULL,
            icon TEXT DEFAULT '🎯',
            target_amt REAL NOT NULL,
            current_amt REAL DEFAULT 0,
            deadline TEXT,
            priority TEXT DEFAULT 'High'
        )
        """
    )
    existing_goals = c.execute("SELECT COUNT(*) FROM custom_goals").fetchone()[0]
    if existing_goals == 0:
        for g_title, g_ic, g_t, g_c, g_dl, g_pr in DEFAULT_CUSTOM_GOALS:
            c.execute(
                "INSERT INTO custom_goals (goal_title, icon, target_amt, current_amt, deadline, priority) VALUES (?, ?, ?, ?, ?, ?)",
                (g_title, g_ic, float(g_t), float(g_c), g_dl, g_pr),
            )

    # 4. Separate Expected vs Actual Shopping Table
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS shopping_planner (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_name TEXT NOT NULL,
            trip_budget REAL NOT NULL,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            expected_amt REAL NOT NULL,
            actual_amt REAL DEFAULT 0,
            status TEXT DEFAULT 'Pending',
            created_at TEXT NOT NULL
        )
        """
    )

    # 5. Expenses Passbook Table
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            date_only TEXT NOT NULL,
            month_year TEXT NOT NULL,
            logged_by TEXT NOT NULL,
            spent_by TEXT NOT NULL,
            category TEXT NOT NULL,
            item_name TEXT NOT NULL,
            description TEXT,
            payment_mode TEXT,
            upi_app TEXT,
            need_level TEXT,
            amount REAL NOT NULL,
            is_bad_expense INTEGER DEFAULT 0,
            upi_id TEXT,
            notes TEXT
        )
        """
    )

    # 6. Vault Deposits Table
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

    # 7. Psychological Urge Victories Table (Money saved by resisting impulse buys)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS urge_victories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_name TEXT NOT NULL,
            item_resisted TEXT NOT NULL,
            amount_saved REAL NOT NULL,
            goal_linked TEXT
        )
        """
    )

    conn.commit()
    conn.close()


init_db()


# ==============================================================================
# 5. DB HELPER FUNCTIONS (SETTINGS, GOALS, SHOPPING, PASSBOOK, MIRROR BACKUP)
# ==============================================================================
def get_master_settings_dict() -> dict:
    conn = get_sqlite_conn()
    rows = conn.execute("SELECT setting_key, setting_val, label FROM master_settings").fetchall()
    conn.close()
    res = {}
    for k, v, lbl in rows:
        res[k] = {"val": float(v), "label": lbl}
    for k, (def_v, def_lbl) in DEFAULT_MASTER_SETTINGS.items():
        if k not in res:
            res[k] = {"val": float(def_v), "label": def_lbl}
    return res


def update_master_setting_db(setting_key: str, new_val: float):
    conn = get_sqlite_conn()
    conn.execute("UPDATE master_settings SET setting_val = ? WHERE setting_key = ?", (float(new_val), setting_key))
    conn.commit()
    conn.close()
    export_full_backup_json()


def fetch_goals_df() -> pd.DataFrame:
    conn = get_sqlite_conn()
    df = pd.read_sql_query("SELECT * FROM custom_goals ORDER BY id ASC", conn)
    conn.close()
    return df


def add_custom_goal_db(title: str, icon: str, target_amt: float, current_amt: float, deadline: str, priority: str):
    conn = get_sqlite_conn()
    conn.execute(
        "INSERT INTO custom_goals (goal_title, icon, target_amt, current_amt, deadline, priority) VALUES (?, ?, ?, ?, ?, ?)",
        (title.strip(), icon, float(target_amt), float(current_amt), deadline, priority),
    )
    conn.commit()
    conn.close()
    export_full_backup_json()


def update_custom_goal_db(goal_id: int, title: str, icon: str, target_amt: float, current_amt: float, deadline: str, priority: str):
    conn = get_sqlite_conn()
    conn.execute(
        """
        UPDATE custom_goals
        SET goal_title = ?, icon = ?, target_amt = ?, current_amt = ?, deadline = ?, priority = ?
        WHERE id = ?
        """,
        (title.strip(), icon, float(target_amt), float(current_amt), deadline, priority, int(goal_id)),
    )
    conn.commit()
    conn.close()
    export_full_backup_json()


def boost_goal_saved_amount_db(goal_id: int, add_amount: float):
    conn = get_sqlite_conn()
    conn.execute("UPDATE custom_goals SET current_amt = current_amt + ? WHERE id = ?", (float(add_amount), int(goal_id)))
    conn.commit()
    conn.close()
    export_full_backup_json()


def delete_custom_goal_db(goal_id: int):
    conn = get_sqlite_conn()
    conn.execute("DELETE FROM custom_goals WHERE id = ?", (int(goal_id),))
    conn.commit()
    conn.close()
    export_full_backup_json()


def fetch_shopping_df() -> pd.DataFrame:
    conn = get_sqlite_conn()
    df = pd.read_sql_query("SELECT * FROM shopping_planner ORDER BY id DESC", conn)
    conn.close()
    return df


def add_expected_shopping_item_db(trip_name: str, trip_budget: float, item_name: str, category: str, expected_amt: float):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_sqlite_conn()
    conn.execute(
        """
        INSERT INTO shopping_planner (trip_name, trip_budget, item_name, category, expected_amt, actual_amt, status, created_at)
        VALUES (?, ?, ?, ?, ?, 0.0, 'Pending', ?)
        """,
        (trip_name.strip(), float(trip_budget), item_name.strip(), category, float(expected_amt), now_str),
    )
    conn.commit()
    conn.close()
    export_full_backup_json()


def edit_expected_shopping_item_db(item_id: int, item_name: str, category: str, expected_amt: float):
    conn = get_sqlite_conn()
    conn.execute(
        "UPDATE shopping_planner SET item_name = ?, category = ?, expected_amt = ? WHERE id = ?",
        (item_name.strip(), category, float(expected_amt), int(item_id)),
    )
    conn.commit()
    conn.close()
    export_full_backup_json()


def record_actual_shopping_spend_db(item_id: int, actual_amt: float):
    status = "Purchased" if actual_amt > 0 else "Pending"
    conn = get_sqlite_conn()
    conn.execute(
        "UPDATE shopping_planner SET actual_amt = ?, status = ? WHERE id = ?",
        (float(actual_amt), status, int(item_id)),
    )
    conn.commit()
    conn.close()
    export_full_backup_json()


def delete_shopping_item_db(item_id: int):
    conn = get_sqlite_conn()
    conn.execute("DELETE FROM shopping_planner WHERE id = ?", (int(item_id),))
    conn.commit()
    conn.close()
    export_full_backup_json()


def fetch_all_expenses_df() -> pd.DataFrame:
    conn = get_sqlite_conn()
    df = pd.read_sql_query("SELECT * FROM expenses ORDER BY id DESC", conn)
    conn.close()
    if not df.empty:
        df["parsed_date"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.date
    return df


def add_expense_to_db(logged_by, spent_by, category, item_name, description, payment_mode, upi_app, need_level, amount, is_bad_expense, upi_id, notes):
    now = datetime.now()
    conn = get_sqlite_conn()
    conn.execute(
        """
        INSERT INTO expenses (
            timestamp, date_only, month_year, logged_by, spent_by, category,
            item_name, description, payment_mode, upi_app, need_level,
            amount, is_bad_expense, upi_id, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            now.strftime("%Y-%m-%d %H:%M:%S"),
            now.strftime("%Y-%m-%d"),
            now.strftime("%Y-%m"),
            logged_by,
            spent_by,
            category,
            item_name,
            description,
            payment_mode,
            upi_app,
            need_level,
            float(amount),
            1 if is_bad_expense else 0,
            upi_id,
            notes,
        ),
    )
    conn.commit()
    conn.close()
    export_full_backup_json()


def update_expense_in_db(expense_id: int, spent_by: str, category: str, item_name: str, amount: float, is_bad: bool, notes: str):
    conn = get_sqlite_conn()
    conn.execute(
        "UPDATE expenses SET spent_by = ?, category = ?, item_name = ?, amount = ?, is_bad_expense = ?, notes = ? WHERE id = ?",
        (spent_by, category, item_name, float(amount), 1 if is_bad else 0, notes, int(expense_id)),
    )
    conn.commit()
    conn.close()
    export_full_backup_json()


def delete_expense_from_db(expense_id: int):
    conn = get_sqlite_conn()
    conn.execute("DELETE FROM expenses WHERE id = ?", (int(expense_id),))
    conn.commit()
    conn.close()
    export_full_backup_json()


def fetch_vault_df(month_year: str = None) -> pd.DataFrame:
    conn = get_sqlite_conn()
    if month_year:
        df = pd.read_sql_query("SELECT * FROM vault_deposits WHERE month_year = ? ORDER BY id DESC", conn, params=(month_year,))
    else:
        df = pd.read_sql_query("SELECT * FROM vault_deposits ORDER BY id DESC", conn)
    conn.close()
    return df


def add_vault_deposit(deposited_by: str, vault_bucket: str, amount: float, notes: str):
    now = datetime.now()
    conn = get_sqlite_conn()
    conn.execute(
        "INSERT INTO vault_deposits (timestamp, month_year, deposited_by, vault_bucket, amount, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m"), deposited_by, vault_bucket, float(amount), notes),
    )
    conn.commit()
    conn.close()
    export_full_backup_json()


def add_urge_victory_db(user_name: str, item_resisted: str, amount_saved: float, goal_linked: str):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_sqlite_conn()
    conn.execute(
        "INSERT INTO urge_victories (timestamp, user_name, item_resisted, amount_saved, goal_linked) VALUES (?, ?, ?, ?, ?)",
        (now_str, user_name, item_resisted.strip(), float(amount_saved), goal_linked),
    )
    conn.commit()
    conn.close()
    export_full_backup_json()


def fetch_urge_victories_df() -> pd.DataFrame:
    conn = get_sqlite_conn()
    df = pd.read_sql_query("SELECT * FROM urge_victories ORDER BY id DESC", conn)
    conn.close()
    return df


def get_all_users_dict() -> dict:
    conn = get_sqlite_conn()
    rows = conn.execute("SELECT username, password, role, is_admin, avatar FROM app_users ORDER BY is_admin DESC, username ASC").fetchall()
    conn.close()
    return {r[0]: {"password": str(r[1]), "role": str(r[2]), "is_admin": bool(r[3]), "avatar": str(r[4] or "👤")} for r in rows}


def upsert_user_account(username: str, password: str, role: str, is_admin: bool, avatar: str = "👤"):
    conn = get_sqlite_conn()
    conn.execute(
        "INSERT OR REPLACE INTO app_users (username, password, role, is_admin, avatar) VALUES (?, ?, ?, ?, ?)",
        (username.strip(), password.strip(), role.strip(), 1 if is_admin else 0, avatar),
    )
    conn.commit()
    conn.close()


def export_full_backup_json() -> str:
    data = {
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "master_settings": {k: v["val"] for k, v in get_master_settings_dict().items()},
        "custom_goals": fetch_goals_df().to_dict(orient="records"),
        "shopping_planner": fetch_shopping_df().to_dict(orient="records"),
        "expenses": fetch_all_expenses_df().drop(columns=["parsed_date"], errors="ignore").to_dict(orient="records"),
        "vault_deposits": fetch_vault_df().to_dict(orient="records"),
        "urge_victories": fetch_urge_victories_df().to_dict(orient="records"),
    }
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    try:
        with open(BACKUP_MIRROR_FILE, "w", encoding="utf-8") as f:
            f.write(json_str)
    except Exception:
        pass
    return json_str


def restore_from_backup_json(json_str: str) -> bool:
    try:
        payload = json.loads(json_str)
        conn = get_sqlite_conn()
        cur = conn.cursor()
        for k, v in payload.get("master_settings", {}).items():
            cur.execute("UPDATE master_settings SET setting_val = ? WHERE setting_key = ?", (float(v), k))
        for row in payload.get("custom_goals", []):
            cur.execute(
                "INSERT OR REPLACE INTO custom_goals (id, goal_title, icon, target_amt, current_amt, deadline, priority) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (row.get("id"), row.get("goal_title"), row.get("icon", "🎯"), float(row.get("target_amt", 10000)), float(row.get("current_amt", 0)), row.get("deadline", ""), row.get("priority", "High")),
            )
        for row in payload.get("shopping_planner", []):
            cur.execute(
                "INSERT OR REPLACE INTO shopping_planner (id, trip_name, trip_budget, item_name, category, expected_amt, actual_amt, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (row.get("id"), row.get("trip_name", "Shopping"), float(row.get("trip_budget", 6000)), row.get("item_name"), row.get("category"), float(row.get("expected_amt", 0)), float(row.get("actual_amt", 0)), row.get("status", "Pending"), row.get("created_at", "")),
            )
        for row in payload.get("expenses", []):
            cur.execute(
                """
                INSERT OR REPLACE INTO expenses (
                    id, timestamp, date_only, month_year, logged_by, spent_by, category,
                    item_name, description, payment_mode, upi_app, need_level,
                    amount, is_bad_expense, upi_id, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get("id"), row.get("timestamp"), row.get("date_only"), row.get("month_year"),
                    row.get("logged_by"), row.get("spent_by"), row.get("category"), row.get("item_name"),
                    row.get("description", ""), row.get("payment_mode", "UPI"), row.get("upi_app", "GPay"),
                    row.get("need_level", "Essential"), float(row.get("amount", 0)), int(row.get("is_bad_expense", 0)),
                    row.get("upi_id", ""), row.get("notes", ""),
                ),
            )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


if fetch_all_expenses_df().empty and os.path.exists(BACKUP_MIRROR_FILE):
    try:
        with open(BACKUP_MIRROR_FILE, "r", encoding="utf-8") as bf:
            restore_from_backup_json(bf.read())
    except Exception:
        pass


# ==============================================================================
# 6. IN-APP MULTI-ANGLE YOUTUBE SHORTS ENGINE (NO INSTAGRAM)
# ==============================================================================
FALLBACK_VIDEO_POOL = {
    "food": ["CO2c3s2nB50", "w7Wj2_T0b9A", "3m7B92p2R7k", "AD9h3d7X6tI"],
    "tech": ["UrsmFxEIp5k", "vmEHCJofslg", "Vl0H-qTclOg", "0aeZX1l4JT4"],
    "english": ["jul2urONzOQ", "mEsleV16qdo", "JwSS70SZdyM", "HXV3zeQKqGY"],
}


@st.cache_data(ttl=3600, show_spinner=False)
def search_youtube_video_id(query_text: str, fallback_idx: int = 0) -> str:
    try:
        q_enc = urllib.parse.quote_plus(query_text)
        url = f"https://www.youtube.com/results?search_query={q_enc}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
            },
        )
        with urllib.request.urlopen(req, timeout=4.5) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
        unique_ids = []
        for v in ids:
            if v not in unique_ids:
                unique_ids.append(v)
        if unique_ids:
            return unique_ids[min(fallback_idx, len(unique_ids) - 1)]
    except Exception:
        pass
    q_low = query_text.lower()
    if any(k in q_low for k in ["python", "excel", "sql", "code", "ai", "data", "power query"]):
        pool = FALLBACK_VIDEO_POOL["tech"]
    elif any(k in q_low for k in ["english", "interview", "speak", "office"]):
        pool = FALLBACK_VIDEO_POOL["english"]
    else:
        pool = FALLBACK_VIDEO_POOL["food"]
    return pool[fallback_idx % len(pool)]


def build_multi_angle_ai_and_shorts(topic_query: str):
    clean_t = topic_query.strip()
    q_low = clean_t.lower()
    is_tech_or_career = any(
        w in q_low for w in ["python", "excel", "power query", "sql", "english", "interview", "ai", "data", "job", "coding", "office"]
    )
    if is_tech_or_career:
        angles = [
            {
                "badge": "📘 Angle 1: कैसे सीखें (Step-by-Step विधि)",
                "title": f"{clean_t} — शून्य से स्टेप-बाय-स्टेप कैसे करें?",
                "ai_summary": f"**{clean_t}** को सीखने का सबसे तेज़ तरीका: पहले इसके 3 कोर कमांड/टेम्पलेट समझें और अपने ऑफिस के किसी 1 असली काम पर इसे लगाकर देखें।",
                "yt_query": f"{clean_t} step by step tutorial in hindi shorts",
            },
            {
                "badge": "⏱️ Angle 2: कितना समय लगेगा (Fast 5-Min Trick)",
                "title": f"{clean_t} — कम समय में मास्टर करने की शॉर्टकट ट्रिक",
                "ai_summary": f"**समय की बचत:** रोज़ सिर्फ **15 मिनट** प्रैक्टिस करने पर आप **7 दिनों** में {clean_t} से घंटों का काम मिनटों में कर लेंगे!",
                "yt_query": f"{clean_t} fast shortcut tricks hindi youtube shorts",
            },
            {
                "badge": "💰 Angle 3: खर्च बनाम सैलरी फायदा (Cost & ROI)",
                "title": f"{clean_t} — ₹0 खर्च में सीखें और करियर में कितना फायदा होगा?",
                "ai_summary": f"**लागत: ₹0 (100% Free)।** इस स्किल से Data Analytics और Operations में आपकी सैलरी वैल्यू **30% से 60% तक** बढ़ जाती है।",
                "yt_query": f"{clean_t} career salary growth tips hindi shorts",
            },
            {
                "badge": "🔥 Angle 4: प्रो टिप्स और इंटरव्यू सीक्रेट",
                "title": f"{clean_t} — इंटरव्यू और ऑफिस के लिए टॉप सीक्रेट टिप्स",
                "ai_summary": f"**प्रो सीक्रेट:** आज ही इस वीडियो को देखकर 2 प्रैक्टिकल उदाहरण खुद बोलकर या लिखकर ट्राई करें!",
                "yt_query": f"{clean_t} interview tips and mistakes hindi shorts",
            },
        ]
    else:
        angles = [
            {
                "badge": "🍲 Angle 1: कैसे बनती है (Step-by-Step Recipe)",
                "title": f"{clean_t} — घर पर एकदम स्वादिष्ट कैसे बनाएं?",
                "ai_summary": f"**{clean_t} बनाने की विधि:** घर के ताज़ा मसालों और सही तड़के से इसे बनाएं। रेस्टोरेंट से 10 गुना शुद्ध और सेहतमंद!",
                "yt_query": f"{clean_t} kaise banate hain ghar par easy recipe hindi shorts",
            },
            {
                "badge": "⏱️ Angle 2: कितनी देर में बनेगी (Time & Cooker Hack)",
                "title": f"{clean_t} — सिर्फ 15-20 मिनट में झटपट बनाने की ट्रिक",
                "ai_summary": f"**बनने का समय:** प्रेशर कुकर या स्मार्ट प्री-प्रेप ट्रिक से यह सिर्फ **15 से 20 मिनट** में गरमा-गरम तैयार हो जाती है!",
                "yt_query": f"{clean_t} jhatpat 10 minute mein kaise banaye cooker trick shorts",
            },
            {
                "badge": "💰 Angle 3: कितने की आएगी (Home Cost vs Market Price)",
                "title": f"{clean_t} — घर पर बनाने का खर्च बनाम बाहर होटल का बिल",
                "ai_summary": f"**बजट गणित:** बाहर जो **{clean_t}** ₹250–₹400 की आती है, वह घर पर सिर्फ **₹60–₹100** में पूरे परिवार के लिए बन जाती है! यानी **₹200+ की सीधी बचत (4 ईंटें 🧱)**!",
                "yt_query": f"{clean_t} street food price vs home budget recipe hindi shorts",
            },
            {
                "badge": "🌶️ Angle 4: ढाबा/होटल का सीक्रेट स्वाद (Pro Touch)",
                "title": f"{clean_t} — ढाबे वाले आखिरी में क्या सीक्रेट मिलाते हैं?",
                "ai_summary": f"**सीक्रेट टिप:** आखिरी में कसूरी मेथी और देसी घी/मक्खन का हल्का तड़का इसके स्वाद को दोगुना कर देता है।",
                "yt_query": f"{clean_t} dhaba secret tips restaurant taste hindi shorts",
            },
        ]

    for idx, ang in enumerate(angles):
        ang["video_id"] = search_youtube_video_id(ang["yt_query"], fallback_idx=idx)
    return angles


def render_in_app_youtube_short(video_id: str, title: str, badge: str, height: int = 340):
    embed_html = f"""
    <div style="background:#0f172a; border:2px solid #f43f5e; border-radius:18px; padding:10px; color:#fff; font-family:sans-serif; box-shadow:0 10px 25px rgba(0,0,0,0.6);">
        <div style="font-size:11px; font-weight:900; color:#00ff9d; text-transform:uppercase; margin-bottom:4px;">{badge}</div>
        <div style="font-size:13px; font-weight:800; color:#ffffff; margin-bottom:8px; line-height:1.3;">{title}</div>
        <div style="position:relative; width:100%; height:{height}px; border-radius:14px; overflow:hidden; border:1px solid #334155;">
            <iframe
                src="https://www.youtube.com/embed/{video_id}?rel=0&modestbranding=1&playsinline=1"
                style="width:100%; height:100%; border:0;"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowfullscreen>
            </iframe>
        </div>
    </div>
    """
    components.html(embed_html, height=height + 82)


# ==============================================================================
# 7. GOAL BRIDGE WIDGET (CONNECTS EVERY MODULE DIRECTLY TO USER'S GOALS!)
# ==============================================================================
def render_goal_bridge_widget(module_key: str, suggested_amt: float, reason_label: str):
    """Allows user to push saved money from ANY module directly into their chosen Life Goal."""
    goals_df = fetch_goals_df()
    if goals_df.empty:
        return
    st.markdown(
        f"""
        <div style="background:linear-gradient(90deg, rgba(16,185,129,0.18), rgba(244,63,94,0.18)); border:1.5px dashed #00ff9d; border-radius:14px; padding:10px 14px; margin-top:8px;">
            <span style="font-weight:900; color:#00ff9d;">🎯 Goal Bridge ({reason_label}):</span>
            <span style="font-size:0.85rem; color:#ffffff;"> अपनी इस बचत (<b>₹{suggested_amt:,.0f}</b>) को सीधे अपने किसी बड़े लक्ष्य में जोड़ें!</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    gb1, gb2, gb3 = st.columns([1.8, 1.0, 1.2])
    with gb1:
        goal_options = {int(r["id"]): f"{r['icon']} {r['goal_title']} (₹{r['current_amt']:,.0f}/₹{r['target_amt']:,.0f})" for _, r in goals_df.iterrows()}
        chosen_g_id = st.selectbox("लक्ष्य चुनें (Select Goal)", options=list(goal_options.keys()), format_func=lambda x: goal_options[x], key=f"gb_sel_{module_key}")
    with gb2:
        amt_to_push = st.number_input("बचत रकम (₹)", min_value=10.0, value=float(max(10.0, suggested_amt)), step=50.0, key=f"gb_amt_{module_key}")
    with gb3:
        st.markdown("<div style='padding-top:24px;'></div>", unsafe_allow_html=True)
        if st.button("🚀 लक्ष्य में जोड़ें (+Goal)", key=f"gb_btn_{module_key}"):
            boost_goal_saved_amount_db(chosen_g_id, amt_to_push)
            st.balloons()
            st.success(f"🎉 ₹{amt_to_push:,.0f} सीधे आपके लक्ष्य में जुड़ गए!")
            st.rerun()


# ==============================================================================
# 8. AUTHENTICATION & LOAD DYNAMIC MASTER CONSTANTS
# ==============================================================================
if len(st.query_params) > 0:
    st.query_params.clear()

if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None
if "willpower_xp" not in st.session_state:
    st.session_state.willpower_xp = 150

apply_neo_interactive_css(st.session_state.selected_theme)
USERS_DICT = get_all_users_dict()
MASTER_CFG = get_master_settings_dict()

UNIVERSAL_FAMILY_POOL = MASTER_CFG["universal_pool"]["val"]
STRICT_SAVINGS_VAULT = MASTER_CFG["savings_vault_target"]["val"]
MAX_SPENDING_BUDGET = max(1000.0, UNIVERSAL_FAMILY_POOL - STRICT_SAVINGS_VAULT)
CAP_FOOD = MASTER_CFG["cap_food"]["val"]
CAP_RENT = MASTER_CFG["cap_rent"]["val"]
DEFAULT_SHOPPING_LIMIT = MASTER_CFG["default_shopping_budget"]["val"]
BRICK_PRICE = max(10.0, MASTER_CFG["brick_price"]["val"])


def render_login_screen():
    st.markdown(
        """
        <div class="neo-card" style="text-align:center; border-left:none; border-top:4px solid #f43f5e;">
            <div style="font-size:3rem; margin-bottom:4px;">👑</div>
            <h2 style="margin:0; color:#ffffff;">Parivaar OS 6.0 • Creator & Wealth Edition</h2>
            <p style="color:#fde68a; font-size:0.9rem; margin-top:4px;">
                100x Interactive Universal Bank • Separate Expected vs Actual • Master Goal Editor • Impulse Crusher
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("strict_login_form"):
        user_options = list(USERS_DICT.keys())
        selected_user = st.selectbox(
            "👤 अपना अकाउंट चुनें",
            options=user_options,
            format_func=lambda u: f"{USERS_DICT[u]['avatar']} {u} — {USERS_DICT[u]['role']}",
        )
        pin_input = st.text_input("🔑 अपना पासवर्ड / PIN डालें", type="password", placeholder="अपना पासवर्ड लिखें...")
        if st.form_submit_button("🔓 अनलॉक करें (Launch Parivaar OS 6.0)"):
            if pin_input.strip() == USERS_DICT.get(selected_user, {}).get("password", ""):
                st.session_state.authenticated_user = selected_user
                st.rerun()
            else:
                st.error("❌ गलत पासवर्ड! कृपया सही पासवर्ड डालें।")


if not st.session_state.authenticated_user or st.session_state.authenticated_user not in USERS_DICT:
    render_login_screen()
    st.stop()


# ==============================================================================
# 9. LIVE FINANCIAL & GOAL METRICS + INSTAGRAM STORIES TOP BAR
# ==============================================================================
current_user = st.session_state.authenticated_user
current_user_info = USERS_DICT[current_user]
is_admin = bool(current_user_info["is_admin"])

today_obj = date.today()
today_str = today_obj.strftime("%Y-%m-%d")
current_month_str = datetime.now().strftime("%Y-%m")

df_all_expenses = fetch_all_expenses_df()
df_month = df_all_expenses[df_all_expenses["month_year"] == current_month_str].copy() if not df_all_expenses.empty else pd.DataFrame()
df_all_vault = fetch_vault_df()
df_month_vault = fetch_vault_df(current_month_str)
df_shopping = fetch_shopping_df()
df_goals = fetch_goals_df()
df_urges = fetch_urge_victories_df()

total_spent_month = float(df_month["amount"].sum()) if not df_month.empty else 0.0
spent_today = float(df_month[df_month["timestamp"].str.startswith(today_str, na=False)]["amount"].sum()) if not df_month.empty else 0.0
bad_spent_month = float(df_month[df_month["is_bad_expense"] == 1]["amount"].sum()) if not df_month.empty else 0.0
urge_saved_total = float(df_urges["amount_saved"].sum()) if not df_urges.empty else 0.0

days_in_month = calendar.monthrange(today_obj.year, today_obj.month)[1]
days_left = max(1, days_in_month - today_obj.day + 1)

remaining_spendable_balance = max(0.0, MAX_SPENDING_BUDGET - total_spent_month)
budget_overflow = max(0.0, total_spent_month - MAX_SPENDING_BUDGET)
effective_monthly_savings = max(0.0, STRICT_SAVINGS_VAULT - budget_overflow)
daily_safe_limit = remaining_spendable_balance / days_left
spend_utilization_pct = min(100.0, (total_spent_month / MAX_SPENDING_BUDGET) * 100.0) if MAX_SPENDING_BUDGET > 0 else 0.0

# Top Header Bar: Theme Selector + Willpower XP + Logout
hdr1, hdr2, hdr3 = st.columns([2.2, 1.1, 0.8])
with hdr1:
    chosen_theme = st.selectbox(
        "🎨 Interactive UI Theme चुनें",
        options=list(THEMES.keys()),
        index=list(THEMES.keys()).index(st.session_state.selected_theme),
    )
    if chosen_theme != st.session_state.selected_theme:
        st.session_state.selected_theme = chosen_theme
        st.rerun()
with hdr2:
    st.markdown("<div style='padding-top:18px;'></div>", unsafe_allow_html=True)
    if st.button(f"⚡ XP: {st.session_state.willpower_xp} (+10)"):
        st.session_state.willpower_xp += 10
        st.toast("🔥 +10 Willpower XP! आप अपने लक्ष्य के और करीब पहुँच रहे हैं!")
with hdr3:
    st.markdown("<div style='padding-top:18px;'></div>", unsafe_allow_html=True)
    if st.button("🔒 लॉगआउट"):
        st.session_state.authenticated_user = None
        st.rerun()

# INSTAGRAM STORIES GOAL RINGS BAR
stories_html = '<div class="insta-story-bar">'
stories_html += f"""
<div class="insta-story-item">
    <div class="insta-ring">
        <div class="insta-inner">
            <span style="font-size:1.1rem;">🏦</span>
            <span style="font-size:0.65rem; font-weight:900; color:#00ff9d;">{100 - spend_utilization_pct:.0f}%</span>
        </div>
    </div>
    <div class="insta-label">बचा बजट</div>
    <div class="insta-sub">₹{remaining_spendable_balance:,.0f}</div>
</div>
<div class="insta-story-item">
    <div class="insta-ring">
        <div class="insta-inner">
            <span style="font-size:1.1rem;">🛡️</span>
            <span style="font-size:0.65rem; font-weight:900; color:#fbbf24;">₹{urge_saved_total:,.0f}</span>
        </div>
    </div>
    <div class="insta-label">लालच जीत</div>
    <div class="insta-sub">{len(df_urges)} Urges Won</div>
</div>
"""
for _, g_row in df_goals.iterrows():
    g_pct = min(100.0, (float(g_row["current_amt"]) / max(1.0, float(g_row["target_amt"]))) * 100.0)
    short_title = str(g_row["goal_title"]).split("(")[0].strip()[:12]
    stories_html += f"""
    <div class="insta-story-item">
        <div class="insta-ring">
            <div class="insta-inner">
                <span style="font-size:1.1rem;">{g_row['icon']}</span>
                <span style="font-size:0.65rem; font-weight:900; color:#fde68a;">{g_pct:.0f}%</span>
            </div>
        </div>
        <div class="insta-label">{short_title}</div>
        <div class="insta-sub">₹{float(g_row['current_amt']):,.0f}</div>
    </div>
    """
stories_html += "</div>"
st.markdown(stories_html, unsafe_allow_html=True)

# Top 3 Animated Circular SVG Gauges (Universal Bank Overview)
g_col1, g_col2, g_col3 = st.columns(3)
with g_col1:
    st.markdown(
        render_svg_ring_gauge(
            "💳 मासिक खर्च मीटर (Spend Limit)",
            f"बचा है: ₹{remaining_spendable_balance:,.0f} (आज Safe: ₹{daily_safe_limit:,.0f})",
            spend_utilization_pct,
            f"₹{total_spent_month:,.0f} / ₹{MAX_SPENDING_BUDGET:,.0f}",
            "#f43f5e" if spend_utilization_pct > 85 else "#00ff9d",
        ),
        unsafe_allow_html=True,
    )
with g_col2:
    vault_pct = min(100.0, (effective_monthly_savings / max(1.0, STRICT_SAVINGS_VAULT)) * 100.0)
    st.markdown(
        render_svg_ring_gauge(
            "🔐 पक्की बचत तिजोरी (Vault)",
            f"{int(effective_monthly_savings // BRICK_PRICE)} पक्की ईंटें 🧱 सुरक्षित",
            vault_pct,
            f"₹{effective_monthly_savings:,.0f} / ₹{STRICT_SAVINGS_VAULT:,.0f}",
            "#fbbf24",
        ),
        unsafe_allow_html=True,
    )
with g_col3:
    sh_budget = float(df_shopping["trip_budget"].iloc[0]) if not df_shopping.empty else DEFAULT_SHOPPING_LIMIT
    sh_actual_total = float(df_shopping["actual_amt"].sum()) if not df_shopping.empty else 0.0
    sh_pct = min(100.0, (sh_actual_total / max(1.0, sh_budget)) * 100.0)
    st.markdown(
        render_svg_ring_gauge(
            "🛍️ शॉपिंग बजट Utilization",
            f"शॉपिंग में बचा: ₹{sh_budget - sh_actual_total:,.0f}",
            sh_pct,
            f"₹{sh_actual_total:,.0f} / ₹{sh_budget:,.0f}",
            "#38bdf8",
        ),
        unsafe_allow_html=True,
    )

st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)

# ==============================================================================
# 10. MAIN 7 ULTRA-INTERACTIVE TABS
# ==============================================================================
tab_shop_sep, tab_master, tab_psych, tab_pay, tab_yt_ai, tab_passbook, tab_backup = st.tabs(
    [
        "🛍️ 1. Expected vs Actual (अलग-अलग)",
        "🎛️ 2. Master Hub (सब Edit करें)",
        "🧠 3. लालच ब्रेकर & Time-Machine",
        "⚡ 4. तेज़ UPI पेमेंट",
        "🎬 5. In-App Shorts & AI",
        "📊 6. बैंक पासबुक & तिजोरी",
        "🛡️ 7. Backup & Zero-Ad App",
    ]
)

# ==============================================================================
# TAB 1: STRICTLY SEPARATED EXPECTED vs ACTUAL SHOPPING & BUDGET ENGINE
# ==============================================================================
with tab_shop_sep:
    st.markdown(
        """
        <div class="neo-card">
            <h4 style="margin:0; color:#fbbf24;">🛍️ 2-Step Smart Shopping Engine: (1) Expected अलग • (2) Actual अलग!</h4>
            <p style="margin:4px 0 0 0; font-size:0.85rem; color:#cbd5e1;">
                पहले <b>Step 1 (📋 Expected प्लानर)</b> में अपना कुल बजट (जैसे ₹6,000) और जो सामान लेना है उसकी अनुमानित कीमत लिखें।
                फिर जब सामान खरीद लें, तब <b>Step 2 (✅ Actual एंट्री & % मीटर)</b> में जाकर असली खर्च डालें!
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "active_trip_budget" not in st.session_state:
        st.session_state.active_trip_budget = float(df_shopping["trip_budget"].iloc[0]) if not df_shopping.empty else DEFAULT_SHOPPING_LIMIT
    if "active_trip_name" not in st.session_state:
        st.session_state.active_trip_name = str(df_shopping["trip_name"].iloc[0]) if not df_shopping.empty else "त्योहार / मार्केट शॉपिंग"

    # Top Master Shopping Budget Bar
    tb1, tb2, tb3 = st.columns([1.6, 1.2, 1.1])
    with tb1:
        trip_name_val = st.text_input("🛒 शॉपिंग मिशन का नाम", value=st.session_state.active_trip_name)
        st.session_state.active_trip_name = trip_name_val
    with tb2:
        trip_budget_val = st.number_input(
            "💰 कुल Expected शॉपिंग बजट (₹)",
            min_value=100.0,
            max_value=500000.0,
            value=float(st.session_state.active_trip_budget),
            step=500.0,
        )
        st.session_state.active_trip_budget = trip_budget_val
    with tb3:
        st.markdown("<div style='padding-top:24px;'></div>", unsafe_allow_html=True)
        if st.button("✨ ₹6,000 सैंपल लिस्ट लोड करें"):
            demo_items = [
                ("साड़ी (Saree)", "Shopping & Clothes (साड़ी, कपड़े और शॉपिंग)", 2000.0),
                ("फॉर्मल शर्ट और ट्राउज़र", "Shopping & Clothes (साड़ी, कपड़े और शॉपिंग)", 1500.0),
                ("जूते / बूट्स (Footwear)", "Shopping & Clothes (साड़ी, कपड़े और शॉपिंग)", 1200.0),
                ("राशन और घर का सामान", "Sabzi & Kirana (सब्ज़ी और राशन)", 1300.0),
            ]
            for d_nm, d_cat, d_exp in demo_items:
                add_expected_shopping_item_db(trip_name_val, trip_budget_val, d_nm, d_cat, d_exp)
            st.rerun()

    # TWO SEPARATE SUB-TABS FOR EXPECTED AND ACTUAL!
    sub_expected, sub_actual = st.tabs(
        [
            "📋 STEP 1: EXPECTED एंट्री (खरीदने से पहले की लिस्ट)",
            "✅ STEP 2: ACTUAL एंट्री & LIVE % UTILIZATION (खरीदने के बाद)",
        ]
    )

    df_shopping = fetch_shopping_df()
    total_exp_planned = float(df_shopping["expected_amt"].sum()) if not df_shopping.empty else 0.0
    total_act_spent = float(df_shopping["actual_amt"].sum()) if not df_shopping.empty else 0.0
    unplanned_buffer = trip_budget_val - total_exp_planned

    # --------------------------------------------------------------------------
    # ZONE 1: ONLY EXPECTED PLANNING (NO ACTUAL CONFUSION HERE)
    # --------------------------------------------------------------------------
    with sub_expected:
        st.markdown("#### 📋 Step 1: यहाँ सिर्फ अपना **Expected (अनुमानित)** सामान जोड़ें या Edit करें")
        e_m1, e_m2, e_m3 = st.columns(3)
        e_m1.metric("कुल शॉपिंग बजट", f"₹{trip_budget_val:,.0f}", "Master Trip Limit")
        e_m2.metric("Expected सामान का जोड़", f"₹{total_exp_planned:,.0f}", f"{(total_exp_planned/max(1.0, trip_budget_val))*100:.1f}% Planned")
        e_m3.metric("बचा हुआ अन-प्लान्ड बफर", f"₹{unplanned_buffer:,.0f}", "Safe Buffer" if unplanned_buffer >= 0 else "Over-Planned!")

        with st.form("only_expected_form", clear_on_submit=True):
            ex1, ex2, ex3 = st.columns([1.6, 1.4, 1.0])
            with ex1:
                exp_item_name = st.text_input("🏷️ क्या लेना है? (सामान का नाम)", placeholder="जैसे: साड़ी, कुर्ती, जूते, किचन सामान...")
            with ex2:
                exp_cat = st.selectbox("📂 श्रेणी (Category)", options=list(CATEGORY_DESCRIPTIONS.keys()))
            with ex3:
                exp_price = st.number_input("💭 Expected कीमत (₹)", min_value=10.0, max_value=200000.0, value=2000.0, step=100.0)

            if st.form_submit_button("➕ Expected लिस्ट में जोड़ें (Save Expected Item)"):
                if exp_item_name.strip():
                    add_expected_shopping_item_db(trip_name_val, trip_budget_val, exp_item_name, exp_cat, exp_price)
                    st.success(f"✅ '{exp_item_name}' (Expected: ₹{exp_price:,.0f}) जुड़ गया! अब खरीदने पर Step 2 (Actual) में जाएं।")
                    st.rerun()
                else:
                    st.warning("कृपया सामान का नाम लिखें!")

        if not df_shopping.empty:
            st.markdown("##### ✏️ आपकी Expected लिस्ट (चाहें तो किसी भी Expected आइटम को यहीं Edit या Delete करें):")
            for _, row in df_shopping.iterrows():
                rid = int(row["id"])
                ec1, ec2, ec3, ec4, ec5 = st.columns([1.5, 1.3, 1.0, 0.8, 0.7])
                with ec1:
                    ed_nm = st.text_input(f"नाम #{rid}", value=str(row["item_name"]), key=f"ed_nm_{rid}")
                with ec2:
                    cat_keys = list(CATEGORY_DESCRIPTIONS.keys())
                    c_idx = cat_keys.index(row["category"]) if row["category"] in cat_keys else 0
                    ed_cat = st.selectbox(f"श्रेणी #{rid}", options=cat_keys, index=c_idx, key=f"ed_cat_{rid}")
                with ec3:
                    ed_exp = st.number_input(f"Expected ₹ #{rid}", min_value=10.0, value=float(row["expected_amt"]), step=100.0, key=f"ed_exp_{rid}")
                with ec4:
                    st.markdown("<div style='padding-top:24px;'></div>", unsafe_allow_html=True)
                    if st.button("💾 अपडेट", key=f"btn_ed_exp_{rid}"):
                        edit_expected_shopping_item_db(rid, ed_nm, ed_cat, ed_exp)
                        st.toast(f"✅ '{ed_nm}' का Expected बजट अपडेट हो गया!")
                        st.rerun()
                with ec5:
                    st.markdown("<div style='padding-top:24px;'></div>", unsafe_allow_html=True)
                    if st.button("🗑️ हटाएं", key=f"btn_del_exp_{rid}"):
                        delete_shopping_item_db(rid)
                        st.rerun()

    # --------------------------------------------------------------------------
    # ZONE 2: ONLY ACTUAL EXECUTION, % UTILIZATION & HIGHLIGHT ENGINE
    # --------------------------------------------------------------------------
    with sub_actual:
        st.markdown("#### ✅ Step 2: खरीदने के बाद यहाँ **Actual (असली खर्च)** डालें और Live % देखें")

        if df_shopping.empty:
            st.info("💡 पहले **STEP 1: EXPECTED एंट्री** टैब में जाकर सामान जोड़ें या ऊपर **'✨ ₹6,000 सैंपल लिस्ट लोड करें'** बटन दबाएं!")
        else:
            bought_df = df_shopping[df_shopping["actual_amt"] > 0]
            exp_of_bought = float(bought_df["expected_amt"].sum()) if not bought_df.empty else 0.0
            saved_on_bought = exp_of_bought - total_act_spent
            remaining_trip_cash = trip_budget_val - total_act_spent
            overall_util_pct = (total_act_spent / max(1.0, trip_budget_val)) * 100.0
            remaining_pct = max(0.0, 100.0 - overall_util_pct)

            # Live Highlight Banner
            hl_color = "#00ff9d" if remaining_trip_cash >= 0 else "#ef4444"
            st.markdown(
                f"""
                <div class="neo-card" style="border-left:6px solid {hl_color};">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                        <div>
                            <div style="font-size:0.78rem; color:#fde68a; font-weight:800;">📊 LIVE SHOPPING UTILIZATION HIGHLIGHT</div>
                            <div style="font-size:1.2rem; font-weight:900; color:#ffffff;">
                                कुल ₹{trip_budget_val:,.0f} में से <span style="color:#f43f5e;">₹{total_act_spent:,.0f} ({overall_util_pct:.1f}%)</span> इस्तेमाल हो गया!
                            </div>
                            <div style="font-size:0.92rem; font-weight:800; color:{hl_color}; margin-top:2px;">
                                💰 अभी ₹{remaining_trip_cash:,.0f} ({remaining_pct:.1f}% बजट) आपके पास बाकी बचा है!
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:0.75rem; color:#cbd5e1;">Expected बनाम Actual बचत</div>
                            <div style="font-size:1.25rem; font-weight:900; color:{'#00ff9d' if saved_on_bought >= 0 else '#ef4444'};">
                                {f'+₹{saved_on_bought:,.0f} बचाए 🎉' if saved_on_bought >= 0 else f'-₹{abs(saved_on_bought):,.0f} ज़्यादा लगा 🚨'}
                            </div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Quick Form to Enter Actual Amount for any Expected Item
            with st.form("enter_actual_spend_form"):
                st.markdown("##### 🛍️ खरीदे गए सामान की Actual कीमत दर्ज करें:")
                item_map = {
                    int(r["id"]): f"{r['item_name']} — (Expected: ₹{float(r['expected_amt']):,.0f} | अभी Actual: ₹{float(r['actual_amt']):,.0f})"
                    for _, r in df_shopping.iterrows()
                }
                ac1, ac2, ac3 = st.columns([2.0, 1.1, 1.1])
                with ac1:
                    chosen_shop_id = st.selectbox("Expected लिस्ट में से सामान चुनें:", options=list(item_map.keys()), format_func=lambda x: item_map[x])
                with ac2:
                    actual_paid_in = st.number_input("💵 असली कीमत (Actual Paid ₹)", min_value=0.0, max_value=200000.0, value=1800.0, step=50.0)
                with ac3:
                    also_add_passbook = st.checkbox("🏦 मुख्य बैंक पासबुक में भी जोड़ें", value=True)

                if st.form_submit_button("✅ Actual खर्च लॉक करें और % कैलकुलेट करें"):
                    record_actual_shopping_spend_db(chosen_shop_id, actual_paid_in)
                    sel_row = df_shopping[df_shopping["id"] == chosen_shop_id].iloc[0]
                    if also_add_passbook and actual_paid_in > 0:
                        add_expense_to_db(
                            logged_by=current_user,
                            spent_by="Universal Family Account",
                            category=str(sel_row["category"]),
                            item_name=f"{sel_row['item_name']} (Actual Shopping)",
                            description=f"Expected ₹{float(sel_row['expected_amt']):,.0f} vs Actual ₹{actual_paid_in:,.0f}",
                            payment_mode="UPI",
                            upi_app="Google Pay (GPay)",
                            need_level="बहुत ज़रूरी (Essential)",
                            amount=actual_paid_in,
                            is_bad_expense=(actual_paid_in > float(sel_row["expected_amt"]) * 1.25),
                            upi_id="",
                            notes=f"Shopping Actual Entry ({trip_name_val})",
                        )
                    st.success("🎉 Actual खर्च अपडेट हो गया! नीचे हर आइटम का % और हाईलाइट देखें।")
                    st.rerun()

            # Item-by-Item Expected vs Actual Comparison Cards
            st.markdown("##### 📊 आइटम-वाइज Expected बनाम Actual रिज़ल्ट कार्ड्स:")
            for _, row in df_shopping.iterrows():
                r_nm = str(row["item_name"])
                r_exp = float(row["expected_amt"])
                r_act = float(row["actual_amt"])
                item_util_pct = (r_act / max(1.0, r_exp)) * 100.0
                share_of_total_budget = (r_act / max(1.0, trip_budget_val)) * 100.0
                diff = r_exp - r_act

                if r_act == 0:
                    status_pill = f'<span class="badge-wait">⏳ अभी खरीदा नहीं (Expected: ₹{r_exp:,.0f})</span>'
                    bar_pct = 0.0
                elif diff > 0:
                    status_pill = f'<span class="badge-saved">🎉 ₹{diff:,.0f} की बचत! ({item_util_pct:.0f}% of Expected | कुल बजट का {share_of_total_budget:.1f}%)</span>'
                    bar_pct = min(1.0, r_act / max(1.0, r_exp))
                elif diff == 0:
                    status_pill = f'<span class="badge-saved">✅ 100% सटीक बजट (कुल बजट का {share_of_total_budget:.1f}%)</span>'
                    bar_pct = 1.0
                else:
                    status_pill = f'<span class="badge-over">🚨 ₹{abs(diff):,.0f} ओवर-बजट! ({item_util_pct:.0f}% of Expected | कुल बजट का {share_of_total_budget:.1f}%)</span>'
                    bar_pct = 1.0

                st.markdown(
                    f"""
                    <div class="neo-card" style="padding:12px 16px; margin-bottom:8px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;">
                            <div>
                                <span style="font-size:1.04rem; font-weight:900; color:#ffffff;">🛍️ {r_nm}</span>
                                <div style="font-size:0.83rem; color:#fde68a; margin-top:2px;">
                                    📋 Expected: <b>₹{r_exp:,.0f}</b> &nbsp;|&nbsp; ✅ Actual: <b>₹{r_act:,.0f}</b>
                                </div>
                            </div>
                            <div>{status_pill}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.progress(bar_pct, text=f"{r_nm}: Expected का {item_util_pct:.1f}% इस्तेमाल हुआ")

            # Goal Bridge: Push any shopping savings directly to a Life Goal!
            if saved_on_bought > 0:
                render_goal_bridge_widget("shopping_save", saved_on_bought, "शॉपिंग में बचाया गया पैसा")


# ==============================================================================
# TAB 2: MASTER CONTROL & GOAL EDITOR HUB (EDIT EVERYTHING IN ONE PLACE!)
# ==============================================================================
with tab_master:
    st.markdown(
        """
        <div class="neo-card">
            <h4 style="margin:0; color:#00ff9d;">🎛️ Master Control Center (अपने सारे गोल्स, बजट नियम और एंट्री को यहीं से Edit करें!)</h4>
            <p style="margin:4px 0 0 0; font-size:0.85rem; color:#cbd5e1;">
                यहाँ से आप <b>सपनों के घर या किसी भी गोल का टारगेट</b>, <b>मासिक यूनिवर्सल पूल (₹38,000)</b>, <b>सेविंग टारगेट (₹15,000)</b>,
                <b>कैटेगरी लिमिट्स</b> और <b>किसी भी पुरानी एंट्री</b> को कभी भी बदल सकते हैं!
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    m_sub_goals, m_sub_rules, m_sub_entries = st.tabs(
        [
            "🎯 1. मास्टर गोल्स एडिटर (Edit/Add Goals)",
            "⚙️ 2. मास्टर बजट & कैप्स एडिटर (Edit ₹38K/₹15K Rules)",
            "✏️ 3. पासबुक एंट्री & यूज़र मास्टर एडिटर",
        ]
    )

    # 1. MASTER GOALS EDITOR
    with m_sub_goals:
        st.markdown("#### 🎯 आपके परिवार के बड़े लक्ष्य (किसी भी लक्ष्य का नाम, टारगेट या जमा रकम तुरंत Edit करें)")
        for _, g_row in df_goals.iterrows():
            gid = int(g_row["id"])
            g_pct = min(100.0, (float(g_row["current_amt"]) / max(1.0, float(g_row["target_amt"]))) * 100.0)
            rem_g = max(0.0, float(g_row["target_amt"]) - float(g_row["current_amt"]))

            with st.expander(f"{g_row['icon']} {g_row['goal_title']} — {g_pct:.1f}% पूरा (जमा: ₹{float(g_row['current_amt']):,.0f} / टारगेट: ₹{float(g_row['target_amt']):,.0f})", expanded=True):
                st.progress(g_pct / 100.0, text=f"🎯 लक्ष्य पूरा होने में ₹{rem_g:,.0f} बाकी हैं ({int(rem_g // BRICK_PRICE)} ईंटें 🧱)")
                gc1, gc2, gc3, gc4 = st.columns([1.6, 0.7, 1.1, 1.1])
                with gc1:
                    eg_title = st.text_input("लक्ष्य का नाम", value=str(g_row["goal_title"]), key=f"eg_t_{gid}")
                with gc2:
                    eg_icon = st.selectbox(
                        "आइकॉन",
                        options=["🏡", "👂", "💻", "🛡️", "🚗", "💍", "✈️", "🎓", "🎯"],
                        index=["🏡", "👂", "💻", "🛡️", "🚗", "💍", "✈️", "🎓", "🎯"].index(g_row["icon"])
                        if g_row["icon"] in ["🏡", "👂", "💻", "🛡️", "🚗", "💍", "✈️", "🎓", "🎯"]
                        else 0,
                        key=f"eg_ic_{gid}",
                    )
                with gc3:
                    eg_target = st.number_input("कुल टारगेट (₹)", min_value=500.0, value=float(g_row["target_amt"]), step=5000.0, key=f"eg_tar_{gid}")
                with gc4:
                    eg_curr = st.number_input("अब तक जमा रकम (₹)", min_value=0.0, value=float(g_row["current_amt"]), step=1000.0, key=f"eg_cur_{gid}")

                gb_1, gb_2, gb_3 = st.columns([1.2, 1.2, 0.8])
                with gb_1:
                    eg_dl = st.text_input("डेडलाइन (तारीख)", value=str(g_row.get("deadline", "2027-12-31")), key=f"eg_dl_{gid}")
                with gb_2:
                    st.markdown("<div style='padding-top:24px;'></div>", unsafe_allow_html=True)
                    if st.button("💾 यह गोल सेव/अपडेट करें", key=f"save_g_{gid}"):
                        update_custom_goal_db(gid, eg_title, eg_icon, eg_target, eg_curr, eg_dl, str(g_row.get("priority", "High")))
                        st.success(f"✅ '{eg_title}' अपडेट हो गया!")
                        st.rerun()
                with gb_3:
                    st.markdown("<div style='padding-top:24px;'></div>", unsafe_allow_html=True)
                    if st.button("🗑️ गोल हटाएं", key=f"del_g_{gid}"):
                        delete_custom_goal_db(gid)
                        st.rerun()

        with st.form("add_new_master_goal"):
            st.markdown("##### ➕ नया लक्ष्य (New Life Goal) जोड़ें")
            ng1, ng2, ng3, ng4 = st.columns([1.6, 0.8, 1.1, 1.1])
            with ng1:
                ng_title = st.text_input("नए लक्ष्य का नाम", placeholder="जैसे: उत्तराखंड यात्रा / नया लैपटॉप / सोने की अंगूठी")
            with ng2:
                ng_ic = st.selectbox("आइकॉन चुनें", ["🎯", "🏡", "💻", "💍", "✈️", "🚗", "🎓", "👂"])
            with ng3:
                ng_tar = st.number_input("टारगेट रकम (₹)", min_value=500.0, value=25000.0, step=1000.0)
            with ng4:
                ng_cur = st.number_input("शुरुआती जमा (₹)", min_value=0.0, value=0.0, step=500.0)
            if st.form_submit_button("🚀 नया लक्ष्य जोड़ें"):
                if ng_title.strip():
                    add_custom_goal_db(ng_title, ng_ic, ng_tar, ng_cur, "2027-12-31", "High Priority")
                    st.success(f"🎉 नया लक्ष्य '{ng_title}' जुड़ गया और ऊपर Instagram Story Bar में भी आ गया!")
                    st.rerun()

    # 2. MASTER BUDGET & CAPS EDITOR
    with m_sub_rules:
        st.markdown("#### ⚙️ मास्टर बजट नियम एडिटर (यहाँ से कोई भी मासिक लिमिट या कैप बदलें)")
        with st.form("master_settings_form"):
            new_settings_vals = {}
            ms_cols = st.columns(2)
            for idx, (s_key, s_info) in enumerate(MASTER_CFG.items()):
                with ms_cols[idx % 2]:
                    new_settings_vals[s_key] = st.number_input(
                        s_info["label"],
                        min_value=10.0,
                        max_value=5000000.0,
                        value=float(s_info["val"]),
                        step=100.0,
                        key=f"ms_in_{s_key}",
                    )
            if st.form_submit_button("✅ सारे मास्टर बजट नियम अपडेट करें"):
                for k, v in new_settings_vals.items():
                    update_master_setting_db(k, v)
                st.success("🎉 मास्टर बजट नियम अपडेट हो गए! पूरा ऐप अब नए नंबरों के हिसाब से चलेगा।")
                st.rerun()

    # 3. MASTER ENTRY & USER EDITOR
    with m_sub_entries:
        st.markdown("#### ✏️ किसी भी पासबुक खर्च एंट्री को Edit या Delete करें")
        if not df_all_expenses.empty:
            all_exp_ids = df_all_expenses["id"].tolist()
            sel_exp_id = st.selectbox(
                "एंट्री चुनें:",
                options=all_exp_ids,
                format_func=lambda x: f"ID #{x} — {df_all_expenses[df_all_expenses['id']==x].iloc[0]['item_name']} (₹{df_all_expenses[df_all_expenses['id']==x].iloc[0]['amount']:,.0f})",
            )
            erow = df_all_expenses[df_all_expenses["id"] == sel_exp_id].iloc[0]
            with st.form("master_edit_exp_form"):
                me1, me2, me3 = st.columns(3)
                with me1:
                    m_item = st.text_input("सामान का नाम", value=str(erow["item_name"]))
                with me2:
                    m_cat = st.selectbox(
                        "श्रेणी",
                        options=list(CATEGORY_DESCRIPTIONS.keys()),
                        index=list(CATEGORY_DESCRIPTIONS.keys()).index(erow["category"]) if erow["category"] in CATEGORY_DESCRIPTIONS else 0,
                    )
                with me3:
                    m_amt = st.number_input("सही रकम (₹)", min_value=1.0, value=float(erow["amount"]), step=10.0)
                m_bad = st.checkbox("यह फालतू खर्च (Bad Expense) है", value=bool(erow["is_bad_expense"]))
                m_notes = st.text_input("नोट", value=str(erow.get("notes", "") or ""))
                c_up, c_dl = st.columns(2)
                if c_up.form_submit_button("💾 एंट्री अपडेट करें"):
                    update_expense_in_db(sel_exp_id, str(erow["spent_by"]), m_cat, m_item, m_amt, m_bad, m_notes)
                    st.success(f"✅ एंट्री #{sel_exp_id} अपडेट हो गई!")
                    st.rerun()
            if st.button(f"🗑️ एंट्री #{sel_exp_id} को हमेशा के लिए हटाएं"):
                delete_expense_from_db(sel_exp_id)
                st.success("एंट्री हटा दी गई!")
                st.rerun()


# ==============================================================================
# TAB 3: PSYCHOLOGICAL IMPULSE URGE CRUSHER & FUTURE TIME-MACHINE
# ==============================================================================
with tab_psych:
    st.markdown(
        """
        <div class="neo-card">
            <h4 style="margin:0; color:#f43f5e;">🧠 10-Second Impulse Urge Crusher (मनोवैज्ञानिक लालच ब्रेकर) & 🧬 Future Time-Machine</h4>
            <p style="margin:4px 0 0 0; font-size:0.85rem; color:#cbd5e1;">
                जब भी बाहर का पिज़्ज़ा/मोमोज़, रिज़र्व ऑटो या गैर-ज़रूरी ऑनलाइन शॉपिंग करने का मन करे—पेमेंट करने से पहले यहाँ रकम डालकर
                उसका <b>असली मनोवैज्ञानिक सच</b> देखें और लालच को हराकर उस पैसे को सीधे अपने सपनों के गोल में भेजें!
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    p_col1, p_col2 = st.columns([1.4, 1.1])
    with p_col1:
        urge_item = st.text_input("🍔 अभी किस गैर-ज़रूरी चीज़ पर पैसे खर्च करने का मन हो रहा है?", value="बाहर का फास्ट फूड / मोमोज़ / रिज़र्व ऑटो")
    with p_col2:
        urge_amt = st.number_input("💸 उस चीज़ की कीमत (₹)", min_value=10.0, max_value=50000.0, value=200.0, step=20.0)

    # Psychological Reality Calculations
    hourly_wage = UNIVERSAL_FAMILY_POOL / (26 * 9)  # Approx ₹162/hour of hard family work
    hours_of_sweat = urge_amt / max(1.0, hourly_wage)
    bricks_destroyed = urge_amt / BRICK_PRICE
    yearly_drain_if_weekly = urge_amt * 52
    five_year_compound = yearly_drain_if_weekly * 5 * 1.35

    st.markdown(
        f"""
        <div class="neo-card" style="border-left:6px solid #fbbf24; background:rgba(30,20,10,0.88);">
            <div style="font-size:0.8rem; font-weight:900; color:#fbbf24;">⚡ मनोवैज्ञानिक एक्स-रे रिपोर्ट: "{urge_item}" (₹{urge_amt:,.0f})</div>
            <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:10px; margin-top:10px;">
                <div style="background:rgba(0,0,0,0.4); padding:10px; border-radius:12px;">
                    <div style="font-size:0.72rem; color:#cbd5e1;">😓 पसीने की कीमत</div>
                    <div style="font-size:1.1rem; font-weight:900; color:#f43f5e;">{hours_of_sweat:.1f} घंटे</div>
                    <div style="font-size:0.7rem; color:#fde68a;">की कड़ी ऑफिस मेहनत</div>
                </div>
                <div style="background:rgba(0,0,0,0.4); padding:10px; border-radius:12px;">
                    <div style="font-size:0.72rem; color:#cbd5e1;">🧱 घर का नुकसान</div>
                    <div style="font-size:1.1rem; font-weight:900; color:#fbbf24;">{bricks_destroyed:.1f} ईंटें</div>
                    <div style="font-size:0.7rem; color:#fde68a;">सपनों के घर की टूटेंगी</div>
                </div>
                <div style="background:rgba(0,0,0,0.4); padding:10px; border-radius:12px;">
                    <div style="font-size:0.72rem; color:#cbd5e1;">📈 अगर हफ्ते में 1 बार रोका</div>
                    <div style="font-size:1.1rem; font-weight:900; color:#00ff9d;">₹{yearly_drain_if_weekly:,.0f}/साल</div>
                    <div style="font-size:0.7rem; color:#fde68a;">5 साल में: ₹{five_year_compound:,.0f}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    goals_list = df_goals["goal_title"].tolist() if not df_goals.empty else ["🏡 सपनों का अपना घर"]
    target_g_for_urge = st.selectbox("🎯 अगर आप अभी यह खर्च रोकते हैं, तो यह पैसा किस लक्ष्य में जुड़ेगा?", options=goals_list)

    if st.button(f"🔥 मैंने लालच हरा दिया! ₹{urge_amt:,.0f} सीधे '{target_g_for_urge}' में जोड़ें (+50 XP)"):
        add_urge_victory_db(current_user, urge_item, urge_amt, target_g_for_urge)
        matched_g = df_goals[df_goals["goal_title"] == target_g_for_urge]
        if not matched_g.empty:
            boost_goal_saved_amount_db(int(matched_g.iloc[0]["id"]), urge_amt)
        st.session_state.willpower_xp += 50
        st.balloons()
        st.success(f"🏆 शानदार जीत {current_user}! आपने ₹{urge_amt:,.0f} बचाकर सीधे '{target_g_for_urge}' को मजबूत कर दिया!")
        st.rerun()

    if not df_urges.empty:
        st.markdown(f"##### 🛡️ अब तक लालच हराकर बचाया गया अदृश्य धन: **₹{urge_saved_total:,.0f}** ({len(df_urges)} बार जीत!)")
        st.dataframe(df_urges[["timestamp", "user_name", "item_resisted", "amount_saved", "goal_linked"]], use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("#### 🧬 Future Self Time-Machine (2026 से 2031 तक आपकी दौलत का सफर)")
    tm1, tm2 = st.columns(2)
    with tm1:
        extra_daily_save = st.slider("💰 रोज़ छोटी बचत से कितना एक्स्ट्रा बचाएंगे? (₹/दिन)", 0, 500, 100, 25)
    with tm2:
        career_hike_monthly = st.slider("🚀 Python/Power Query और English से मासिक सैलरी बढ़त (₹/महीना)", 0, 30000, 8000, 1000)

    total_monthly_power = STRICT_SAVINGS_VAULT + (extra_daily_save * 30) + (career_hike_monthly * 0.7)
    yr1 = total_monthly_power * 12 * 1.08
    yr3 = total_monthly_power * 36 * 1.22
    yr5 = total_monthly_power * 60 * 1.42

    t_c1, t_c2, t_c3 = st.columns(3)
    t_c1.metric("1 साल बाद (2027)", f"₹{yr1:,.0f}", f"{int(yr1 // BRICK_PRICE)} Bricks 🧱")
    t_c2.metric("3 साल बाद (2029)", f"₹{yr3:,.0f}", "Dream House Ready!")
    t_c3.metric("5 साल बाद (2031)", f"₹{yr5:,.0f}", "Financial Freedom 👑")


# ==============================================================================
# TAB 4: FAST DAILY EXPENSE & INSTANT UPI LAUNCHER
# ==============================================================================
with tab_pay:
    st.caption("⚡ **1-Tap तेज़ बटन:**")
    q1, q2, q3, q4 = st.columns(4)
    if q1.button("☕ ₹15 चाय"):
        st.session_state.qf_cat = "Food & Mess (खाना, चिकन/मछली और टिफिन)"
        st.session_state.qf_amt = 15.0
        st.session_state.qf_desc = "सुबह की चाय / बिस्किट (Morning Tea)"
    if q2.button("🚌 ₹30 बस/ई-रिक्शा"):
        st.session_state.qf_cat = "Metro, Bus & Auto (आना-जाना)"
        st.session_state.qf_amt = 30.0
        st.session_state.qf_desc = "शेयरिंग ई-रिक्शा / ऑटो (Necessary E-Rickshaw)"
    if q3.button("🥛 ₹66 दूध"):
        st.session_state.qf_cat = "Food & Mess (खाना, चिकन/मछली और टिफिन)"
        st.session_state.qf_amt = 66.0
        st.session_state.qf_desc = "दूध, दही, ओट्स और केले (Milk, Oats & Fruits)"
    if q4.button("🥦 ₹80 सब्ज़ी"):
        st.session_state.qf_cat = "Sabzi & Kirana (सब्ज़ी और राशन)"
        st.session_state.qf_amt = 80.0
        st.session_state.qf_desc = "रोज़ की हरी सब्ज़ी (आलू, प्याज, भिंडी, टमाटर)"

    cat_list = list(CATEGORY_DESCRIPTIONS.keys())
    default_cat = st.session_state.get("qf_cat", cat_list[1])
    cat_idx = cat_list.index(default_cat) if default_cat in cat_list else 0

    c_who, c_cat = st.columns(2)
    with c_who:
        spent_by_val = st.selectbox("🏦 खाता / सदस्य चुनें", options=["Universal Family Account"] + list(USERS_DICT.keys()))
    with c_cat:
        selected_category = st.selectbox("📂 श्रेणी (Category)", options=cat_list, index=cat_idx)

    desc_list = CATEGORY_DESCRIPTIONS.get(selected_category, ["अन्य खर्च..."])
    with st.form("fast_upi_form_v6"):
        fc1, fc2 = st.columns([1.5, 1.0])
        with fc1:
            custom_item = st.text_input("🏷️ सामान / खर्च का नाम", value=st.session_state.get("qf_desc", desc_list[0]))
        with fc2:
            amount_val = st.number_input("₹ रकम (Amount)", min_value=1.0, max_value=200000.0, value=float(st.session_state.get("qf_amt", 50.0)), step=10.0)

        selected_upi_app = st.selectbox("📲 पेमेंट मोड", ["Google Pay (GPay)", "PhonePe", "Paytm", "Cash (नकद)"])
        is_bad_chk = st.checkbox("🚨 यह गैर-ज़रूरी / फालतू खर्च है", value=("Faltu" in selected_category))

        if st.form_submit_button("🚀 पासबुक में सेव करें और UPI खोलें"):
            add_expense_to_db(
                logged_by=current_user,
                spent_by=spent_by_val,
                category=selected_category,
                item_name=custom_item.strip(),
                description=custom_item.strip(),
                payment_mode="Cash" if "Cash" in selected_upi_app else "UPI",
                upi_app=selected_upi_app,
                need_level="Essential",
                amount=amount_val,
                is_bad_expense=is_bad_chk,
                upi_id="",
                notes="",
            )
            st.success(f"✅ ₹{amount_val:,.0f} ({custom_item}) पासबुक में सेव हो गया!")
            st.rerun()

    u_c1, u_c2, u_c3 = st.columns(3)
    u_c1.markdown('<a href="intent://upi/#Intent;scheme=tez;package=com.google.android.apps.nbu.paisa.user;end" class="upi-app-btn">🟢 Open GPay</a>', unsafe_allow_html=True)
    u_c2.markdown('<a href="intent://#Intent;scheme=phonepe;package=com.phonepe.app;end" class="upi-app-btn" style="background:linear-gradient(90deg,#a855f7,#7e22ce); color:#fff !important;">🟣 Open PhonePe</a>', unsafe_allow_html=True)
    u_c3.markdown('<a href="intent://#Intent;scheme=paytmmp;package=net.one97.paytm;end" class="upi-app-btn" style="background:linear-gradient(90deg,#38bdf8,#0284c7); color:#fff !important;">🔵 Open Paytm</a>', unsafe_allow_html=True)

    if spent_today <= MASTER_CFG["daily_reward_limit"]["val"]:
        saved_today_diff = max(10.0, daily_safe_limit - spent_today)
        render_goal_bridge_widget("daily_low_spend", saved_today_diff, f"आज कम खर्च (₹{spent_today:,.0f}) से बची रकम")


# ==============================================================================
# TAB 5: IN-APP MULTI-ANGLE YOUTUBE SHORTS & AI 360 OVERVIEW
# ==============================================================================
with tab_yt_ai:
    st.markdown(
        """
        <div class="neo-card">
            <h4 style="margin:0; color:#00ff9d;">🎬 In-App Multi-Angle YouTube Shorts + 🤖 AI 360° Overview</h4>
            <p style="margin:4px 0 0 0; font-size:0.85rem; color:#cbd5e1;">
                कोई भी रेसिपी (जैसे <b>Dal Makhani</b>) या करियर टॉपिक (<b>Power Query / Python / Spoken English</b>) चुनें—
                ऊपर <b>AI के 4 अलग-अलग कार्ड्स</b> आएंगे और नीचे <b>ऐप के अंदर ही 4 अलग-अलग एंगल की YouTube Shorts</b> चलेंगी!
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "active_search_topic" not in st.session_state:
        st.session_state.active_search_topic = "Dal Makhani (दाल मखनी)"

    q_b1, q_b2, q_b3, q_b4, q_b5 = st.columns(5)
    if q_b1.button("🍲 दाल मखनी"):
        st.session_state.active_search_topic = "Dal Makhani (दाल मखनी)"
    if q_b2.button("🍗 चिकन करी"):
        st.session_state.active_search_topic = "Dhaba Style Chicken Curry"
    if q_b3.button("🍛 चना आलू"):
        st.session_state.active_search_topic = "Chana Aloo Curry High Protein"
    if q_b4.button("📊 Power Query"):
        st.session_state.active_search_topic = "Excel Power Query Combine Multiple Files"
    if q_b5.button("🗣️ English Call"):
        st.session_state.active_search_topic = "Spoken English Telecalling & Client Handling"

    s_in1, s_in2 = st.columns([2.5, 1.0])
    with s_in1:
        topic_in = st.text_input("🔍 कोई भी डिश, कोडिंग या इंग्लिश टॉपिक लिखें:", value=st.session_state.active_search_topic)
    with s_in2:
        st.markdown("<div style='padding-top:24px;'></div>", unsafe_allow_html=True)
        if st.button("🚀 4-Angle Shorts चलाएं"):
            st.session_state.active_search_topic = topic_in.strip()

    angles = build_multi_angle_ai_and_shorts(topic_in.strip() or "Dal Makhani")

    ov1, ov2 = st.columns(2)
    for idx, ang in enumerate(angles):
        with (ov1 if idx % 2 == 0 else ov2):
            st.markdown(
                f"""
                <div class="neo-card" style="padding:12px 14px;">
                    <div style="font-size:0.74rem; color:#00ff9d; font-weight:900;">{ang['badge']}</div>
                    <div style="font-size:0.95rem; font-weight:900; color:#ffffff; margin:3px 0;">{ang['title']}</div>
                    <div style="font-size:0.83rem; color:#cbd5e1;">{ang['ai_summary']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    v1, v2 = st.columns(2)
    for idx, ang in enumerate(angles):
        with (v1 if idx % 2 == 0 else v2):
            render_in_app_youtube_short(ang["video_id"], ang["title"], ang["badge"], height=330)

    render_goal_bridge_widget("home_cooking_save", 200.0, "बाहर के बजाय घर पर बनाने या नई स्किल सीखने का इनाम")


# ==============================================================================
# TAB 6: UNIVERSAL BANK PASSBOOK & ₹15,000 VAULT
# ==============================================================================
with tab_passbook:
    st.markdown("#### 🏦 यूनिवर्सल बैंक पासबुक (Spending vs Saving Analytics)")
    if not df_all_expenses.empty:
        st.dataframe(
            df_all_expenses[["id", "timestamp", "spent_by", "category", "item_name", "amount", "upi_app", "notes"]],
            use_container_width=True,
            hide_index=True,
        )
        c_pie, c_bar = st.columns(2)
        with c_pie:
            fig1 = px.pie(df_all_expenses.groupby("category", as_index=False)["amount"].sum(), names="category", values="amount", hole=0.5, template="plotly_dark", title="खर्च का बंटवारा")
            fig1.update_layout(margin=dict(t=35, b=10, l=5, r=5), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig1, use_container_width=True)
        with c_bar:
            vs_df = pd.DataFrame(
                {
                    "Type": ["मासिक खर्च (Spent)", "बचा खर्च बजट (Available)", "लॉक्ड बचत तिजोरी (Vault)"],
                    "Amount": [total_spent_month, remaining_spendable_balance, effective_monthly_savings],
                }
            )
            fig2 = px.bar(vs_df, x="Type", y="Amount", color="Type", template="plotly_dark", title="Universal Bank: खर्च बनाम बचत")
            fig2.update_layout(margin=dict(t=35, b=10, l=5, r=5), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("अभी पासबुक में कोई खर्च दर्ज नहीं है।")


# ==============================================================================
# TAB 7: ZERO-DATA-LOSS BACKUP SHIELD & ZERO-AD NATIVE APP
# ==============================================================================
with tab_backup:
    st.markdown(
        """
        <div class="neo-card">
            <h4 style="margin:0; color:#00ff9d;">🛡️ Zero-Data-Loss Backup Shield (ऐप स्लीप या रीबूट होने पर भी 100% सुरक्षित!)</h4>
            <p style="margin:4px 0 0 0; font-size:0.85rem; color:#cbd5e1;">
                आपका सारा डेटा (Goals, Expected vs Actual Shopping, Passbook, Master Rules) अपने-आप मिरर फाइल में सेव होता है।
                नीचे से कभी भी 1-Click Backup डाउनलोड या Restore करें!
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    b1, b2 = st.columns(2)
    with b1:
        full_json = export_full_backup_json()
        st.download_button(
            "📥 1-Click Master Backup डाउनलोड करें (.json)",
            data=full_json.encode("utf-8"),
            file_name=f"Parivaar_OS6_Backup_{today_str}.json",
            mime="application/json",
        )
    with b2:
        up_file = st.file_uploader("📤 Backup File से 1-Click Restore करें", type=["json"])
        if up_file is not None and st.button("🔄 अभी सारा डेटा Restore करें"):
            if restore_from_backup_json(up_file.read().decode("utf-8")):
                st.success("🎉 आपके सारे गोल्स, शॉपिंग और पासबुक रिकॉर्ड वापस आ गए!")
                st.rerun()

# Keep-Alive Heartbeat
components.html(
    "<script>setInterval(function(){console.log('Parivaar OS 6.0 Active');}, 40000);</script>",
    height=0,
)
