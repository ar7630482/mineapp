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
# 1. PAGE SETUP & HIDE ALL GITHUB / STREAMLIT MENUS
# ==============================================================================
st.set_page_config(
    page_title="Parivaar VIP 5.0 | Universal Super-App",
    page_icon="👑",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ==============================================================================
# 2. UNIVERSAL FAMILY BANK CONSTANTS (SINGLE UNIFIED ACCOUNT)
# ==============================================================================
UNIVERSAL_FAMILY_POOL = 38000      # ₹38,000 Single Universal Parivaar Bank Pool (No Split!)
STRICT_SAVINGS_VAULT = 15000       # ₹15,000 Locked Dream House + Medical Vault
MAX_SPENDING_BUDGET = UNIVERSAL_FAMILY_POOL - STRICT_SAVINGS_VAULT  # ₹23,000 Spendable Limit

CAP_FOOD = 7000
CAP_RENT = 6000
CAP_HOME_MAX = 7000
CAP_MEDICAL_EAR = 3000
PSYCHOLOGY_DAILY_REWARD_LIMIT = 200.0

DEFAULT_USERS = [
    ("Ajay", "52729211", "👑 Chief Admin • Universal Parivaar Account", 1, "👑"),
    ("Meenakshi", "2345", "👩‍💼 Partner • Universal Parivaar Account", 0, "👩‍💼"),
    ("Ajeet", "3456", "🧑‍🎓 Family Member • Universal Parivaar Account", 0, "🧑‍🎓"),
]

CATEGORY_DESCRIPTIONS = {
    "Food & Mess (खाना, चिकन/मछली और टिफिन)": [
        "सुबह की चाय / बिस्किट (Morning Tea)",
        "ऑफिस लंच / टिफिन (Office Lunch)",
        "दूध, दही और ब्रेड (Milk & Curd)",
        "ताज़ी मछली / चिकन / अंडे (Home Non-Veg)",
        "दाल मखनी / पनीर / संडे स्पेशल डिनर",
        "महीने का मेस / राशन बिल (Mess/Ration)",
        "शाम का समोसा / बाहर का नाश्ता (Avoid!)",
        "बाहर का चाउमीन / मोमोज / जंक फूड (Bad Expense!)",
        "अन्य खाने का खर्च (Custom Food Item)...",
    ],
    "Sabzi & Kirana (सब्ज़ी और राशन)": [
        "रोज़ की हरी सब्ज़ी (आलू, प्याज, भिंडी, टमाटर)",
        "आटा, चावल, दाल और तेल (Monthly Grocery)",
        "मसाले, नमक और रसोई का सामान",
        "रसोई गैस सिलेंडर (LPG Refill)",
        "अन्य किराना सामान (Custom Grocery)...",
    ],
    "Shopping & Clothes (साड़ी, कपड़े और शॉपिंग)": [
        "साड़ी / सूट / कुर्ती शॉपिंग (Saree & Ethnic)",
        "फॉर्मल शर्ट / ट्राउज़र / ऑफिस वियर",
        "जूते / सैंडल / बूट्स (Footwear)",
        "स्किनकेयर / सनस्क्रीन / डेली केयर",
        "त्योहार या परिवार की शॉपिंग",
        "अन्य शॉपिंग खर्च...",
    ],
    "Room Rent (कमरे का किराया)": [
        "महीने का रूम रेंट (Monthly Room Rent)",
        "बिजली और पानी का बिल (Electricity/Water)",
        "कमरे की मरम्मत / मेंटेनेंस",
        "अन्य किराया खर्च...",
    ],
    "Home Transfer (गाँव / माता-पिता)": [
        "माता-पिता के लिए महीने का खर्च (Parents Support)",
        "गाँव में दवाई / इलाज के लिए पैसे",
        "त्योहार / घर की ज़रूरत के लिए ट्रांसफर",
        "अन्य घर ट्रांसफर...",
    ],
    "Ear Medical (कान का इलाज - Priority)": [
        "कान के डॉक्टर की फीस (Ear Specialist Fee)",
        "कान की दवाई और ड्रॉप्स (Ear Medicine)",
        "कान की जांच / टेस्ट (Ear Checkup/Test)",
        "अन्य कान के इलाज का खर्च...",
    ],
    "Other Medical (अन्य दवाई / सेहत)": [
        "बुखार / सर्दी / ज़रूरी दवाई",
        "परिवार का ब्लड टेस्ट / चेकअप",
        "अन्य मेडिकल खर्च...",
    ],
    "Metro, Bus & Auto (आना-जाना)": [
        "DTC बस टिकट / मेट्रो रिचार्ज (Bus/Metro)",
        "शेयरिंग ई-रिक्शा / ऑटो (Necessary E-Rickshaw)",
        "अकेले रिज़र्व ऑटो / कैब (फालतू खर्च - Avoid!)",
        "पेट्रोल / गाड़ी मेंटेनेंस",
        "अन्य ट्रैवल खर्च...",
    ],
    "Mobile & Wi-Fi (रिचार्ज और इंटरनेट)": [
        "मोबाइल रिचार्ज (Jio / Airtel)",
        "पढ़ाई के लिए Wi-Fi / ब्रॉडबैंड बिल",
        "अन्य बिल...",
    ],
    "Padhai, AI & English (पढ़ाई और करियर)": [
        "Python / Power Query / Data Analysis कोर्स या किताब",
        "Spoken English प्रैक्टिस / नोटबुक",
        "फॉर्म फीस / सर्टिफिकेट",
        "अन्य पढ़ाई खर्च...",
    ],
    "Faltu / Bad Expense (गैर-ज़रूरी खर्च)": [
        "बिना सोचे-समझे ऑटो / कैब किया (Unplanned Ride)",
        "बाहर का महंगा फास्ट फूड / पिज़्ज़ा / बर्गर",
        "ऑनलाइन फालतू शॉपिंग (Impulse Buy)",
        "अन्य गैर-ज़रूरी खर्च...",
    ],
}

# ==============================================================================
# 3. 5 PREMIUM VIP THEMES + ANIMATED POSTER & BANK CARD CSS
# ==============================================================================
THEMES = {
    "👑 Maharaja Gold & Obsidian (अजय रॉयल स्पेशल)": {
        "bg_main": "radial-gradient(circle at top, #231904 0%, #07090f 100%)",
        "card_bg": "#111827",
        "card_border": "#fbbf24",
        "accent": "#fbbf24",
        "accent_sec": "#00ff9d",
        "text_bright": "#ffffff",
        "text_sub": "#fde68a",
        "banner_grad": "linear-gradient(135deg, #451a03 0%, #111827 55%, #064e3b 100%)",
    },
    "⚡ Emerald Cyber Bank (मॉडर्न नियो-बैंक ग्रीन)": {
        "bg_main": "radial-gradient(circle at top, #042f2e 0%, #060913 100%)",
        "card_bg": "#0f172a",
        "card_border": "#00ff9d",
        "accent": "#00ff9d",
        "accent_sec": "#fbbf24",
        "text_bright": "#ffffff",
        "text_sub": "#a7f3d0",
        "banner_grad": "linear-gradient(135deg, #064e3b 0%, #0f172a 55%, #1e1b4b 100%)",
    },
    "🌊 Mindful Sapphire Blue (शांत और फोकस ब्लू)": {
        "bg_main": "radial-gradient(circle at top, #0c192c 0%, #050811 100%)",
        "card_bg": "#0f172a",
        "card_border": "#38bdf8",
        "accent": "#38bdf8",
        "accent_sec": "#f472b6",
        "text_bright": "#ffffff",
        "text_sub": "#bae6fd",
        "banner_grad": "linear-gradient(135deg, #0c4a6e 0%, #0f172a 55%, #311042 100%)",
    },
    "🟣 Royal Amethyst (प्रीमियम पर्पल नाइट)": {
        "bg_main": "radial-gradient(circle at top, #2e1065 0%, #070510 100%)",
        "card_bg": "#131124",
        "card_border": "#c084fc",
        "accent": "#e879f9",
        "accent_sec": "#38bdf8",
        "text_bright": "#ffffff",
        "text_sub": "#f5d0fe",
        "banner_grad": "linear-gradient(135deg, #3b0764 0%, #131124 55%, #0f172a 100%)",
    },
    "🔥 Agni Hustle (जोश और अनुशासन)": {
        "bg_main": "radial-gradient(circle at top, #2a0a12 0%, #08070c 100%)",
        "card_bg": "#181018",
        "card_border": "#f97316",
        "accent": "#fb923c",
        "accent_sec": "#fbbf24",
        "text_bright": "#ffffff",
        "text_sub": "#fed7aa",
        "banner_grad": "linear-gradient(135deg, #431407 0%, #181018 55%, #3b0764 100%)",
    },
}

if "selected_theme" not in st.session_state:
    st.session_state.selected_theme = "👑 Maharaja Gold & Obsidian (अजय रॉयल स्पेशल)"


def apply_vip_theme(theme_name: str):
    t = THEMES.get(theme_name, THEMES["👑 Maharaja Gold & Obsidian (अजय रॉयल स्पेशल)"])
    st.markdown(
        f"""
        <style>
        /* HIDE STREAMLIT HEADER, GITHUB ICON, FORK, MANAGE APP & FOOTER */
        #MainMenu {{visibility: hidden !important; display: none !important;}}
        header {{visibility: hidden !important; height: 0px !important; display: none !important;}}
        footer {{visibility: hidden !important; display: none !important;}}
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        [data-testid="manage-app-button"],
        .stAppDeployButton,
        .stDeployButton,
        .viewerBadge_container__1QSob,
        .styles_viewerBadge__1yB5_ {{
            display: none !important;
            visibility: hidden !important;
        }}

        .stApp {{
            background: {t['bg_main']} !important;
            color: {t['text_bright']} !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }}
        .block-container {{
            padding-top: 0.6rem !important;
            padding-bottom: 4.5rem !important;
            max-width: 820px !important;
        }}

        label, .stWidgetLabel, .stMarkdown p, .stMarkdown li, span, h1, h2, h3, h4, h5, h6 {{
            color: {t['text_bright']} !important;
        }}
        .stCaption {{
            color: {t['text_sub']} !important;
            font-size: 0.85rem !important;
        }}

        /* Inputs & Selects */
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        div[data-baseweb="base-input"],
        input, textarea {{
            background-color: #1e293b !important;
            color: #ffffff !important;
            border-color: {t['card_border']} !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
        }}
        div[data-baseweb="select"] span,
        div[data-baseweb="select"] div {{
            color: #ffffff !important;
        }}
        ul[data-baseweb="menu"],
        div[data-baseweb="popover"] div,
        li[role="option"] {{
            background-color: #0f172a !important;
            color: #ffffff !important;
            font-weight: 600 !important;
        }}
        li[role="option"]:hover {{
            background-color: {t['accent']} !important;
            color: #000000 !important;
        }}

        /* Metric Boxes */
        div[data-testid="stMetric"] {{
            background-color: {t['card_bg']} !important;
            border: 1.5px solid {t['card_border']} !important;
            border-radius: 14px !important;
            padding: 12px 14px !important;
            box-shadow: 0 6px 16px rgba(0,0,0,0.5) !important;
        }}
        div[data-testid="stMetricLabel"] p,
        div[data-testid="stMetricLabel"] {{
            color: {t['text_sub']} !important;
            font-weight: 700 !important;
            font-size: 0.83rem !important;
        }}
        div[data-testid="stMetricValue"] div,
        div[data-testid="stMetricValue"] {{
            color: {t['accent']} !important;
            font-weight: 900 !important;
            font-size: 1.32rem !important;
        }}

        /* Tabs */
        button[data-baseweb="tab"] {{
            background-color: #1e293b !important;
            color: #cbd5e1 !important;
            border-radius: 11px 11px 0 0 !important;
            padding: 8px 11px !important;
            margin-right: 3px !important;
            font-weight: 700 !important;
            border: 1px solid rgba(255,255,255,0.14) !important;
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            background: linear-gradient(90deg, {t['accent']}, {t['accent_sec']}) !important;
            color: #020617 !important;
            font-weight: 900 !important;
        }}
        button[data-baseweb="tab"][aria-selected="true"] p {{
            color: #020617 !important;
            font-weight: 900 !important;
        }}

        /* Animated Royal Hero Poster */
        @keyframes glowPulse {{
            0% {{ box-shadow: 0 0 12px rgba(251, 191, 36, 0.35); }}
            50% {{ box-shadow: 0 0 26px rgba(0, 255, 157, 0.55); }}
            100% {{ box-shadow: 0 0 12px rgba(251, 191, 36, 0.35); }}
        }}
        @keyframes floatCrown {{
            0%, 100% {{ transform: translateY(0px) rotate(0deg); }}
            50% {{ transform: translateY(-5px) rotate(3deg); }}
        }}
        .hero-poster {{
            background: {t['banner_grad']};
            border: 2px solid {t['accent']};
            border-radius: 18px;
            padding: 14px 18px;
            margin-bottom: 12px;
            animation: glowPulse 4s infinite ease-in-out;
            position: relative;
            overflow: hidden;
        }}
        .logo-badge {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 54px;
            height: 54px;
            border-radius: 16px;
            background: linear-gradient(135deg, #fbbf24 0%, #d97706 100%);
            color: #020617;
            font-size: 1.9rem;
            font-weight: 900;
            box-shadow: 0 6px 18px rgba(251, 191, 36, 0.5);
            animation: floatCrown 3s infinite ease-in-out;
            margin-right: 14px;
            flex-shrink: 0;
        }}

        /* Formatted Motivation Poster Card */
        .motivation-poster {{
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 60%, #064e3b 100%);
            border: 1.5px solid {t['accent_sec']};
            border-left: 8px solid {t['accent']};
            border-radius: 16px;
            padding: 14px 16px;
            margin-bottom: 12px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }}

        /* 3D Virtual Universal Bank Card */
        .universal-bank-card {{
            background: linear-gradient(135deg, #090d16 0%, #1e293b 50%, #3b2304 100%);
            border: 2px solid #fbbf24;
            border-radius: 20px;
            padding: 18px 20px;
            margin-bottom: 14px;
            box-shadow: 0 12px 30px rgba(0,0,0,0.65);
            position: relative;
        }}
        .bank-chip {{
            width: 44px;
            height: 32px;
            border-radius: 7px;
            background: linear-gradient(135deg, #fde68a 0%, #d97706 100%);
            border: 1px solid #ffffff;
            display: inline-block;
        }}

        /* VIP Cards */
        .vip-card {{
            background: {t['card_bg']};
            border: 1px solid {t['card_border']};
            border-radius: 15px;
            padding: 14px 16px;
            margin-bottom: 12px;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.4);
        }}

        /* Shopping Status Pills */
        .pill-saved {{
            background: rgba(16, 185, 129, 0.2);
            border: 1.5px solid #10b981;
            color: #6ee7b7 !important;
            padding: 4px 10px;
            border-radius: 999px;
            font-weight: 800;
            font-size: 0.8rem;
        }}
        .pill-over {{
            background: rgba(239, 68, 68, 0.25);
            border: 1.5px solid #ef4444;
            color: #fca5a5 !important;
            padding: 4px 10px;
            border-radius: 999px;
            font-weight: 800;
            font-size: 0.8rem;
        }}
        .pill-pending {{
            background: rgba(251, 191, 36, 0.18);
            border: 1.5px solid #fbbf24;
            color: #fde68a !important;
            padding: 4px 10px;
            border-radius: 999px;
            font-weight: 800;
            font-size: 0.8rem;
        }}

        /* UPI & Action Buttons */
        .upi-app-btn {{
            display: block;
            width: 100%;
            text-align: center;
            background: linear-gradient(90deg, #00ff9d 0%, #10b981 100%);
            color: #022c22 !important;
            font-weight: 900;
            font-size: 0.96rem;
            padding: 11px 14px;
            border-radius: 12px;
            text-decoration: none !important;
            margin: 5px 0;
            box-shadow: 0 5px 16px rgba(0, 255, 157, 0.35);
            border: 1.5px solid #ffffff;
        }}
        .upi-scanner-btn {{
            display: block;
            width: 100%;
            text-align: center;
            background: linear-gradient(90deg, #fbbf24 0%, #f59e0b 100%);
            color: #090d16 !important;
            font-weight: 900;
            font-size: 0.94rem;
            padding: 11px 14px;
            border-radius: 12px;
            text-decoration: none !important;
            margin: 5px 0;
            border: 1.5px solid #ffffff;
        }}

        div.stButton > button, div.stFormSubmitButton > button, div.stDownloadButton > button {{
            width: 100%;
            border-radius: 11px !important;
            min-height: 44px !important;
            font-weight: 800 !important;
            border: 1.5px solid {t['accent']} !important;
            background-color: #1e293b !important;
            color: #ffffff !important;
            transition: all 0.2s ease-in-out !important;
        }}
        div.stButton > button:hover, div.stFormSubmitButton > button:hover, div.stDownloadButton > button:hover {{
            background-color: {t['accent']} !important;
            color: #020617 !important;
            transform: translateY(-1px);
        }}
        div.stButton > button:hover p, div.stFormSubmitButton > button:hover p, div.stDownloadButton > button:hover p {{
            color: #020617 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ==============================================================================
# 4. RICH FORMATTED PSYCHIATRIST MOTIVATION & POSTER ENGINE
# ==============================================================================
POSTER_SLIDES = [
    {
        "badge": "👑 PARIVAAR UNIVERSAL BANK 5.0",
        "title": "एक परिवार • एक तिजोरी • एक बड़ा सपना!",
        "sub": "₹38,000 Universal Pool में से ₹15,000 सीधा सपनों के घर और सेहत के लिए लॉक, और ₹23,000 में स्मार्ट गृहस्थी!",
        "quote_hi": "“जब पति-पत्नी का लक्ष्य एक होता है, तो हर बचाया हुआ रुपया दोगुनी ताकत से काम करता है।”",
        "psych_tip": "🧠 Psychiatrist Insight: पेमेंट करने से पहले सिर्फ 5 सेकंड रुककर 'Expected vs Actual' देखने से फालतू खर्च 68% तक तुरंत घट जाता है।",
        "challenge": "🎯 आज का मिशन: खर्च ≤ ₹200 रखें + 15 मिनट Spoken English और Python/Power Query प्रैक्टिस करें!",
    },
    {
        "badge": "🚀 CAREER & FLUENCY BOOSTER",
        "title": "गलती से डरना छोड़ो — रफ़्तार पकड़ो!",
        "sub": "Spoken English और Data Analytics/Python में रोज़ 1% सुधार आपको 1 साल में 100% आगे ले जाएगा।",
        "quote_hi": "“अंग्रेज़ी बोलते समय अटकना कमजोरी नहीं है, यह सबूत है कि आप अपनी मातृभाषा के साथ एक नई स्किल सीख रहे हैं!”",
        "psych_tip": "🧠 Brain Rewiring: जब भी कोडिंग या बातचीत में गलती हो, तो दिमाग से कहें—'यह मेरी ट्रेनिंग का हिस्सा है।' इससे डर तुरंत खत्म हो जाता है।",
        "challenge": "🎯 आज का मिशन: शीशे के सामने 5 इंग्लिश वाक्य बोलें और 1 नया ऑटोमेशन/फॉर्मूला सीखें!",
    },
    {
        "badge": "🏡 DREAM HOUSE BRICK BUILDER",
        "title": "बाहर का ₹100 का जंक फूड = घर की 2 पक्की ईंटें (🧱)",
        "sub": "हर बार जब आप बाहर के मोमोज/चाउमीन या रिज़र्व ऑटो को मना करते हैं, आपके अपने घर की दीवार और ऊँची होती है।",
        "quote_hi": "“आज का थोड़ा सा संयम, कल पूरे परिवार को किराए के घर से अपने खुद के मकान की चाबी दिलाएगा।”",
        "psych_tip": "🧠 Dopamine Shift: खर्च करने के बजाय 'बचत का प्रतिशत (%)' देखने से दिमाग को असली विजेता वाला डोपामाइन मिलता है।",
        "challenge": "🎯 आज का मिशन: शॉपिंग या बाज़ार जाते समय 'Shopping Planner' में पहले Expected बजट दर्ज करें!",
    },
]


def get_daily_poster_and_motivation(slide_offset: int = 0):
    anchor = date(2025, 1, 1)
    today = date.today()
    day_num = max(1, (today - anchor).days + 1)
    idx = (day_num + slide_offset) % len(POSTER_SLIDES)
    slide = POSTER_SLIDES[idx]
    return {
        "day": day_num,
        "date_str": today.strftime("%d %b %Y"),
        **slide,
    }


# ==============================================================================
# 5. PERSISTENT DATABASE + AUTO JSON MIRROR SHIELD (NEVER LOSE RECORDS ON SLEEP)
# ==============================================================================
DB_FILE = "parivaar_vip_v5.db"
BACKUP_MIRROR_FILE = "parivaar_auto_mirror_v5.json"


def get_db_engine():
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


def get_sqlite_conn():
    conn = sqlite3.connect(DB_FILE, timeout=30.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db():
    engine = get_db_engine()
    if engine:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS app_users (
                        username TEXT PRIMARY KEY,
                        password TEXT NOT NULL,
                        role TEXT NOT NULL,
                        is_admin INTEGER DEFAULT 0,
                        avatar TEXT DEFAULT '👤'
                    );
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS expenses (
                        id SERIAL PRIMARY KEY,
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
                    CREATE TABLE IF NOT EXISTS shopping_planner (
                        id SERIAL PRIMARY KEY,
                        trip_name TEXT NOT NULL,
                        trip_budget REAL NOT NULL,
                        item_name TEXT NOT NULL,
                        category TEXT NOT NULL,
                        expected_amt REAL NOT NULL,
                        actual_amt REAL DEFAULT 0,
                        status TEXT DEFAULT 'Pending',
                        created_at TEXT NOT NULL
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
            for u, p, r, adm, av in DEFAULT_USERS:
                conn.execute(
                    text(
                        """
                        INSERT INTO app_users (username, password, role, is_admin, avatar)
                        VALUES (:u, :p, :r, :adm, :av)
                        ON CONFLICT (username) DO NOTHING
                        """
                    ),
                    {"u": u, "p": p, "r": r, "adm": adm, "av": av},
                )
            conn.execute(text("UPDATE app_users SET is_admin = 1 WHERE username = 'Ajay'"))
    else:
        conn = get_sqlite_conn()
        c = conn.cursor()
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


init_db()


def export_full_backup_json() -> str:
    """Exports all tables into a single JSON string for instant backup & auto-mirroring."""
    data = {
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "expenses": fetch_all_expenses_df().drop(columns=["parsed_date"], errors="ignore").to_dict(orient="records"),
        "vault_deposits": fetch_vault_df().to_dict(orient="records"),
        "shopping_planner": fetch_shopping_df().to_dict(orient="records"),
        "career_progress": get_career_progress(),
    }
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    try:
        with open(BACKUP_MIRROR_FILE, "w", encoding="utf-8") as f:
            f.write(json_str)
    except Exception:
        pass
    return json_str


def restore_from_backup_json(json_str: str) -> bool:
    """Restores expenses, vault deposits, and shopping items from a JSON backup."""
    try:
        payload = json.loads(json_str)
        conn = get_sqlite_conn()
        cur = conn.cursor()

        for row in payload.get("expenses", []):
            cur.execute(
                """
                INSERT OR IGNORE INTO expenses (
                    id, timestamp, date_only, month_year, logged_by, spent_by, category,
                    item_name, description, payment_mode, upi_app, need_level,
                    amount, is_bad_expense, upi_id, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get("id"),
                    row.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    row.get("date_only", date.today().strftime("%Y-%m-%d")),
                    row.get("month_year", datetime.now().strftime("%Y-%m")),
                    row.get("logged_by", "Ajay"),
                    row.get("spent_by", "Ajay"),
                    row.get("category", "Food & Mess (खाना, चिकन/मछली और टिफिन)"),
                    row.get("item_name", "Item"),
                    row.get("description", ""),
                    row.get("payment_mode", "UPI"),
                    row.get("upi_app", "Google Pay (GPay)"),
                    row.get("need_level", "बहुत ज़रूरी (Essential)"),
                    float(row.get("amount", 0.0)),
                    int(row.get("is_bad_expense", 0)),
                    row.get("upi_id", ""),
                    row.get("notes", ""),
                ),
            )

        for row in payload.get("vault_deposits", []):
            cur.execute(
                """
                INSERT OR IGNORE INTO vault_deposits (
                    id, timestamp, month_year, deposited_by, vault_bucket, amount, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get("id"),
                    row.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    row.get("month_year", datetime.now().strftime("%Y-%m")),
                    row.get("deposited_by", "Ajay"),
                    row.get("vault_bucket", "🏡 Dream House (सपनों का घर फंड)"),
                    float(row.get("amount", 0.0)),
                    row.get("notes", ""),
                ),
            )

        for row in payload.get("shopping_planner", []):
            cur.execute(
                """
                INSERT OR IGNORE INTO shopping_planner (
                    id, trip_name, trip_budget, item_name, category, expected_amt, actual_amt, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get("id"),
                    row.get("trip_name", "Market Shopping"),
                    float(row.get("trip_budget", 6000.0)),
                    row.get("item_name", "Item"),
                    row.get("category", "Shopping & Clothes (साड़ी, कपड़े और शॉपिंग)"),
                    float(row.get("expected_amt", 0.0)),
                    float(row.get("actual_amt", 0.0)),
                    row.get("status", "Pending"),
                    row.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                ),
            )

        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def get_all_users_dict() -> dict:
    users = {}
    try:
        engine = get_db_engine()
        if engine:
            with engine.connect() as conn:
                rows = conn.execute(
                    text("SELECT username, password, role, is_admin, avatar FROM app_users ORDER BY is_admin DESC, username ASC")
                ).fetchall()
        else:
            conn = get_sqlite_conn()
            rows = conn.execute(
                "SELECT username, password, role, is_admin, avatar FROM app_users ORDER BY is_admin DESC, username ASC"
            ).fetchall()
            conn.close()

        for r in rows:
            users[r[0]] = {
                "password": str(r[1]),
                "role": str(r[2]),
                "is_admin": bool(r[3]),
                "avatar": str(r[4] or "👤"),
            }
    except Exception:
        for u, p, r, adm, av in DEFAULT_USERS:
            users[u] = {"password": p, "role": r, "is_admin": bool(adm), "avatar": av}
    return users


def upsert_user_account(username: str, password: str, role: str, is_admin: bool, avatar: str = "👤"):
    adm_int = 1 if is_admin else 0
    engine = get_db_engine()
    if engine:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO app_users (username, password, role, is_admin, avatar)
                    VALUES (:u, :p, :r, :a, :av)
                    ON CONFLICT (username) DO UPDATE SET
                        password = :p, role = :r, is_admin = :a, avatar = :av
                    """
                ),
                {"u": username.strip(), "p": password.strip(), "r": role.strip(), "a": adm_int, "av": avatar},
            )
    else:
        conn = get_sqlite_conn()
        conn.execute(
            "INSERT OR REPLACE INTO app_users (username, password, role, is_admin, avatar) VALUES (?, ?, ?, ?, ?)",
            (username.strip(), password.strip(), role.strip(), adm_int, avatar),
        )
        conn.commit()
        conn.close()


def delete_user_account(username: str):
    if username.lower() == "ajay":
        return False
    engine = get_db_engine()
    if engine:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM app_users WHERE username = :u"), {"u": username})
    else:
        conn = get_sqlite_conn()
        conn.execute("DELETE FROM app_users WHERE username = ?", (username,))
        conn.commit()
        conn.close()
    return True


def add_expense_to_db(
    logged_by, spent_by, category, item_name, description, payment_mode, upi_app, need_level, amount, is_bad_expense, upi_id, notes
):
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    date_only = now.strftime("%Y-%m-%d")
    month_year = now.strftime("%Y-%m")
    bad_int = 1 if is_bad_expense else 0

    engine = get_db_engine()
    if engine:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO expenses (
                        timestamp, date_only, month_year, logged_by, spent_by, category,
                        item_name, description, payment_mode, upi_app, need_level,
                        amount, is_bad_expense, upi_id, notes
                    ) VALUES (
                        :ts, :do, :my, :lb, :sb, :cat, :item, :desc, :pm, :ua, :nl, :amt, :bad, :upi, :notes
                    )
                    """
                ),
                {
                    "ts": now_str, "do": date_only, "my": month_year, "lb": logged_by, "sb": spent_by,
                    "cat": category, "item": item_name, "desc": description, "pm": payment_mode,
                    "ua": upi_app, "nl": need_level, "amt": float(amount), "bad": bad_int, "upi": upi_id, "notes": notes,
                },
            )
    else:
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
                now_str, date_only, month_year, logged_by, spent_by, category, item_name,
                description, payment_mode, upi_app, need_level, float(amount), bad_int, upi_id, notes,
            ),
        )
        conn.commit()
        conn.close()
    export_full_backup_json()


def update_expense_in_db(expense_id: int, spent_by: str, category: str, item_name: str, amount: float, is_bad: bool, notes: str):
    bad_int = 1 if is_bad else 0
    engine = get_db_engine()
    if engine:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE expenses
                    SET spent_by = :sb, category = :cat, item_name = :item,
                        amount = :amt, is_bad_expense = :bad, notes = :notes
                    WHERE id = :id
                    """
                ),
                {"sb": spent_by, "cat": category, "item": item_name, "amt": float(amount), "bad": bad_int, "notes": notes, "id": int(expense_id)},
            )
    else:
        conn = get_sqlite_conn()
        conn.execute(
            "UPDATE expenses SET spent_by = ?, category = ?, item_name = ?, amount = ?, is_bad_expense = ?, notes = ? WHERE id = ?",
            (spent_by, category, item_name, float(amount), bad_int, notes, int(expense_id)),
        )
        conn.commit()
        conn.close()
    export_full_backup_json()


def delete_expense_from_db(expense_id: int):
    engine = get_db_engine()
    if engine:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM expenses WHERE id = :id"), {"id": int(expense_id)})
    else:
        conn = get_sqlite_conn()
        conn.execute("DELETE FROM expenses WHERE id = ?", (int(expense_id),))
        conn.commit()
        conn.close()
    export_full_backup_json()


def fetch_all_expenses_df() -> pd.DataFrame:
    try:
        engine = get_db_engine()
        if engine:
            with engine.connect() as conn:
                df = pd.read_sql(text("SELECT * FROM expenses ORDER BY id DESC"), conn)
        else:
            conn = get_sqlite_conn()
            df = pd.read_sql_query("SELECT * FROM expenses ORDER BY id DESC", conn)
            conn.close()
        if not df.empty:
            df["parsed_date"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.date
        return df
    except Exception:
        return pd.DataFrame()


# ==============================================================================
# 6. SHOPPING PLANNER DB FUNCTIONS (EXPECTED VS ACTUAL TRACKER)
# ==============================================================================
def add_shopping_item_db(trip_name: str, trip_budget: float, item_name: str, category: str, expected_amt: float, actual_amt: float = 0.0):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "Completed" if actual_amt > 0 else "Pending"
    engine = get_db_engine()
    if engine:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO shopping_planner (trip_name, trip_budget, item_name, category, expected_amt, actual_amt, status, created_at)
                    VALUES (:tn, :tb, :inm, :cat, :exp, :act, :st, :ca)
                    """
                ),
                {
                    "tn": trip_name, "tb": float(trip_budget), "inm": item_name, "cat": category,
                    "exp": float(expected_amt), "act": float(actual_amt), "st": status, "ca": now_str,
                },
            )
    else:
        conn = get_sqlite_conn()
        conn.execute(
            """
            INSERT INTO shopping_planner (trip_name, trip_budget, item_name, category, expected_amt, actual_amt, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (trip_name, float(trip_budget), item_name, category, float(expected_amt), float(actual_amt), status, now_str),
        )
        conn.commit()
        conn.close()
    export_full_backup_json()


def update_shopping_actual_db(item_id: int, actual_amt: float, expected_amt: float = None):
    status = "Completed" if actual_amt > 0 else "Pending"
    engine = get_db_engine()
    if engine:
        with engine.begin() as conn:
            if expected_amt is not None:
                conn.execute(
                    text("UPDATE shopping_planner SET actual_amt = :act, expected_amt = :exp, status = :st WHERE id = :id"),
                    {"act": float(actual_amt), "exp": float(expected_amt), "st": status, "id": int(item_id)},
                )
            else:
                conn.execute(
                    text("UPDATE shopping_planner SET actual_amt = :act, status = :st WHERE id = :id"),
                    {"act": float(actual_amt), "st": status, "id": int(item_id)},
                )
    else:
        conn = get_sqlite_conn()
        if expected_amt is not None:
            conn.execute(
                "UPDATE shopping_planner SET actual_amt = ?, expected_amt = ?, status = ? WHERE id = ?",
                (float(actual_amt), float(expected_amt), status, int(item_id)),
            )
        else:
            conn.execute(
                "UPDATE shopping_planner SET actual_amt = ?, status = ? WHERE id = ?",
                (float(actual_amt), status, int(item_id)),
            )
        conn.commit()
        conn.close()
    export_full_backup_json()


def delete_shopping_item_db(item_id: int):
    engine = get_db_engine()
    if engine:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM shopping_planner WHERE id = :id"), {"id": int(item_id)})
    else:
        conn = get_sqlite_conn()
        conn.execute("DELETE FROM shopping_planner WHERE id = ?", (int(item_id),))
        conn.commit()
        conn.close()
    export_full_backup_json()


def fetch_shopping_df() -> pd.DataFrame:
    try:
        engine = get_db_engine()
        if engine:
            with engine.connect() as conn:
                return pd.read_sql(text("SELECT * FROM shopping_planner ORDER BY id DESC"), conn)
        else:
            conn = get_sqlite_conn()
            df = pd.read_sql_query("SELECT * FROM shopping_planner ORDER BY id DESC", conn)
            conn.close()
            return df
    except Exception:
        return pd.DataFrame()


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
                {"ts": now_str, "my": month_year, "db": deposited_by, "vb": vault_bucket, "amt": float(amount), "notes": notes},
            )
    else:
        conn = get_sqlite_conn()
        conn.execute(
            "INSERT INTO vault_deposits (timestamp, month_year, deposited_by, vault_bucket, amount, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (now_str, month_year, deposited_by, vault_bucket, float(amount), notes),
        )
        conn.commit()
        conn.close()
    export_full_backup_json()


def delete_vault_deposit_from_db(vault_id: int):
    engine = get_db_engine()
    if engine:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM vault_deposits WHERE id = :id"), {"id": int(vault_id)})
    else:
        conn = get_sqlite_conn()
        conn.execute("DELETE FROM vault_deposits WHERE id = ?", (int(vault_id),))
        conn.commit()
        conn.close()
    export_full_backup_json()


def fetch_vault_df(month_year: str = None) -> pd.DataFrame:
    try:
        engine = get_db_engine()
        if engine:
            with engine.connect() as conn:
                if month_year:
                    return pd.read_sql(
                        text("SELECT * FROM vault_deposits WHERE month_year = :my ORDER BY id DESC"),
                        conn,
                        params={"my": month_year},
                    )
                return pd.read_sql(text("SELECT * FROM vault_deposits ORDER BY id DESC"), conn)
        else:
            conn = get_sqlite_conn()
            if month_year:
                df = pd.read_sql_query("SELECT * FROM vault_deposits WHERE month_year = ? ORDER BY id DESC", conn, params=(month_year,))
            else:
                df = pd.read_sql_query("SELECT * FROM vault_deposits ORDER BY id DESC", conn)
            conn.close()
            return df
    except Exception:
        return pd.DataFrame()


def get_career_progress() -> dict:
    progress = {}
    try:
        engine = get_db_engine()
        if engine:
            with engine.connect() as conn:
                rows = conn.execute(text("SELECT skill_key, completed FROM career_progress")).fetchall()
                for r in rows:
                    progress[r[0]] = bool(r[1])
        else:
            conn = get_sqlite_conn()
            rows = conn.execute("SELECT skill_key, completed FROM career_progress").fetchall()
            for r in rows:
                progress[r[0]] = bool(r[1])
            conn.close()
    except Exception:
        pass
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
        conn = get_sqlite_conn()
        conn.execute(
            "INSERT OR REPLACE INTO career_progress (skill_key, completed, updated_at) VALUES (?, ?, ?)",
            (skill_key, val, now_str),
        )
        conn.commit()
        conn.close()


# Auto-recover from local mirror if DB was wiped on sleep
if fetch_all_expenses_df().empty and os.path.exists(BACKUP_MIRROR_FILE):
    try:
        with open(BACKUP_MIRROR_FILE, "r", encoding="utf-8") as bf:
            restore_from_backup_json(bf.read())
    except Exception:
        pass


# ==============================================================================
# 7. IN-APP MULTI-ANGLE YOUTUBE SHORTS ENGINE + AI 360 OVERVIEW (NO INSTAGRAM!)
# ==============================================================================
FALLBACK_VIDEO_POOL = {
    "food": ["CO2c3s2nB50", "w7Wj2_T0b9A", "3m7B92p2R7k", "AD9h3d7X6tI"],
    "tech": ["UrsmFxEIp5k", "vmEHCJofslg", "Vl0H-qTclOg", "0aeZX1l4JT4"],
    "english": ["jul2urONzOQ", "mEsleV16qdo", "JwSS70SZdyM", "HXV3zeQKqGY"],
    "default": ["CO2c3s2nB50", "w7Wj2_T0b9A", "UrsmFxEIp5k", "jul2urONzOQ"],
}


@st.cache_data(ttl=3600, show_spinner=False)
def search_youtube_video_id(query_text: str, fallback_idx: int = 0) -> str:
    """Fetches a real playable YouTube video/short ID for any query so it plays INSIDE the app."""
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
    if any(k in q_low for k in ["python", "excel", "sql", "code", "ai", "data"]):
        pool = FALLBACK_VIDEO_POOL["tech"]
    elif any(k in q_low for k in ["english", "interview", "speak", "office"]):
        pool = FALLBACK_VIDEO_POOL["english"]
    else:
        pool = FALLBACK_VIDEO_POOL["food"]
    return pool[fallback_idx % len(pool)]


def build_multi_angle_ai_and_shorts(topic_query: str):
    """
    Given ANY search topic (e.g. 'Dal Makhani', 'Chicken Curry', 'Python Power Query', 'Saree Shopping'),
    returns 4 distinct angles:
      1. कैसे बनती है / कैसे सीखें (Full Step-by-Step Method)
      2. कितनी देर में बनेगी / फास्ट ट्रिक (Time & Speed Hack)
      3. कितने की आएगी / बजट और बचत (Cost & Budget Breakdown)
      4. प्रो सीक्रेट / असली स्वाद या करियर फायदा (Pro Tips & Mistakes to Avoid)
    """
    clean_t = topic_query.strip()
    q_low = clean_t.lower()

    is_tech_or_career = any(
        w in q_low
        for w in ["python", "excel", "power query", "sql", "english", "interview", "ai", "data", "job", "coding", "office"]
    )

    if is_tech_or_career:
        angles = [
            {
                "badge": "📘 Angle 1: कैसे सीखें (Step-by-Step विधि)",
                "title": f"{clean_t} — शून्य से स्टेप-बाय-स्टेप कैसे करें?",
                "ai_summary": f"**{clean_t}** को सीखने का सबसे आसान तरीका: पहले इसके 3 मुख्य बेसिक कमांड/वाक्य समझें, फिर अपने ऑफिस के किसी 1 असली काम पर इसे लगाकर देखें। रटने के बजाय प्रैक्टिकल करने से यह 3 गुना तेज़ याद रहता है।",
                "yt_query": f"{clean_t} step by step tutorial in hindi shorts",
            },
            {
                "badge": "⏱️ Angle 2: कितना समय लगेगा (Quick 5-Min Trick)",
                "title": f"{clean_t} — कम समय में तेज़ी से मास्टर करने की शॉर्टकट ट्रिक",
                "ai_summary": f"**समय की बचत:** रोज़ सिर्फ **15 से 20 मिनट** प्रैक्टिस करने पर आप **7 से 10 दिनों** में {clean_t} का इस्तेमाल ऑफिस में धड़ल्ले से कर सकते हैं। घंटों का मैनुअल काम सिर्फ 2 मिनट में होगा!",
                "yt_query": f"{clean_t} fast shortcut tricks hindi youtube shorts",
            },
            {
                "badge": "💰 Angle 3: खर्च बनाम सैलरी फायदा (Cost & ROI)",
                "title": f"{clean_t} — ₹0 खर्च में सीखें और सैलरी कितनी बढ़ेगी?",
                "ai_summary": f"**लागत: ₹0 (100% Free)।** महंगे पेड कोर्स की ज़रूरत नहीं! इस एक स्किल को अपने रिज्यूमे और काम में जोड़ने से डेटा एनालिटिक्स/ऑपरेशंस में आपकी वैल्यू **30% से 60% तक** बढ़ जाती है।",
                "yt_query": f"{clean_t} career salary growth tips hindi shorts",
            },
            {
                "badge": "🔥 Angle 4: प्रो टिप्स और आम गलतियाँ (Pro Secrets)",
                "title": f"{clean_t} — इंटरव्यू और ऑफिस के लिए टॉप सीक्रेट टिप्स",
                "ai_summary": f"**प्रो सीक्रेट:** 90% लोग सिर्फ वीडियो देखते हैं, खुद टाइप या बोलकर प्रैक्टिस नहीं करते। आज नीचे दिया गया चौथा वीडियो देखकर तुरंत 2 उदाहरण खुद ट्राई करें!",
                "yt_query": f"{clean_t} interview tips and mistakes hindi shorts",
            },
        ]
    else:
        angles = [
            {
                "badge": "🍲 Angle 1: कैसे बनती है (Step-by-Step Recipe)",
                "title": f"{clean_t} — घर पर एकदम स्वादिष्ट कैसे बनाएं?",
                "ai_summary": f"**{clean_t} बनाने की विधि:** घर के बेसिक मसालों (अदरक-लहसुन पेस्ट, ताज़ा टमाटर-प्याज और धीमी आंच पर भुना मसाला) से इसे बनाएं। सही तड़का लगाने से घर पर ही रेस्टोरेंट से 10 गुना शुद्ध और ताज़ा स्वाद मिलता है।",
                "yt_query": f"{clean_t} kaise banate hain ghar par easy recipe hindi shorts",
            },
            {
                "badge": "⏱️ Angle 2: कितनी देर में बनेगी (Time & Pressure Cooker Hack)",
                "title": f"{clean_t} — कम समय (15-20 मिनट) में झटपट बनाने की ट्रिक",
                "ai_summary": f"**बनने का समय:** कुकर या वन-पॉट ट्रिक से यह सिर्फ **15 से 25 मिनट** में तैयार हो जाती है! अगर पहले से तैयारी (चॉपिंग/भिगोना) कर लें, तो ऑफिस से आने के बाद भी फटाफट बन जाएगी।",
                "yt_query": f"{clean_t} jhatpat 10 minute mein kaise banaye cooker trick shorts",
            },
            {
                "badge": "💰 Angle 3: कितने की आएगी (Home Cost vs Market Price)",
                "title": f"{clean_t} — घर पर बनाने में कितने रुपये लगेंगे बनाम होटल का बिल?",
                "ai_summary": f"**बजट गणित:** बाहर होटल/रेस्टोरेंट में जो **{clean_t}** ₹250 से ₹450 की मिलती है, वही घर पर पूरे परिवार के लिए सिर्फ **₹60 से ₹110 की लागत** में भरपूर और सेहतमंद बन जाती है! यानी सीधे **₹200+ की बचत (4 नई ईंटें 🧱)**!",
                "yt_query": f"{clean_t} street food price vs home budget recipe hindi shorts",
            },
            {
                "badge": "🌶️ Angle 4: ढाबा/होटल का सीक्रेट स्वाद (Pro Secret Touch)",
                "title": f"{clean_t} — होटल और ढाबे वाले आखिरी में क्या सीक्रेट मिलाते हैं?",
                "ai_summary": f"**सीक्रेट टिप:** गैस बंद करने से 2 मिनट पहले कसूरी मेथी को हथेली से रगड़कर डालना और थोड़ा सा देसी घी/मक्खन का तड़का लगाना इसके स्वाद को दोगुना कर देता है।",
                "yt_query": f"{clean_t} dhaba secret tips restaurant taste hindi shorts",
            },
        ]

    for idx, ang in enumerate(angles):
        ang["video_id"] = search_youtube_video_id(ang["yt_query"], fallback_idx=idx)
    return angles


def render_in_app_youtube_short(video_id: str, title: str, badge: str, height: int = 390):
    """Renders an embedded YouTube player directly inside the Streamlit app (Supports Shorts & Videos)."""
    embed_html = f"""
    <div style="background:#0f172a; border:2px solid #fbbf24; border-radius:16px; padding:10px; color:#fff; font-family:sans-serif; box-shadow:0 8px 20px rgba(0,0,0,0.5);">
        <div style="font-size:11px; font-weight:800; color:#00ff9d; text-transform:uppercase; margin-bottom:4px;">{badge}</div>
        <div style="font-size:13px; font-weight:700; color:#ffffff; margin-bottom:8px; line-height:1.3;">{title}</div>
        <div style="position:relative; width:100%; height:{height}px; border-radius:12px; overflow:hidden; border:1px solid #334155;">
            <iframe
                src="https://www.youtube.com/embed/{video_id}?rel=0&modestbranding=1&playsinline=1"
                style="width:100%; height:100%; border:0;"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowfullscreen>
            </iframe>
        </div>
    </div>
    """
    components.html(embed_html, height=height + 85)


# ==============================================================================
# 8. 37 LAKH+ SMART PROMPT ENGINE
# ==============================================================================
PROMPT_DOMAINS = {
    "🍲 देसी खाना, दाल मखनी, चिकन, मछली & चाइनीज़/कोरियन": {
        "topics": [
            "Dal Makhani (दाल मखनी — ढाबा स्टाइल)", "Masala Chicken Curry (मसालेदार देसी चिकन करी)",
            "Mustard Fish Curry & Crispy Fish Fry (मछली करी और फ्राई)", "Chana Aloo Curry & High-Protein Sattu Drink",
            "Egg Curry & Paneer Bhurji (अंडा करी और पनीर भुर्जी)", "Potato-Besan Cutlets & Crispy Bhindi Fry",
            "Garhwali Chua & Pahadi Recipes (गढ़वाली चूआ और पहाड़ी डिश)", "Street Style Veg/Chicken Chowmein & Momos",
            "Korean Spicy Ramen & Tteokbokki (कोरियन नूडल्स)", "15-Minute Cooker Masala Tehri & Daliya Khichdi",
        ],
        "contexts": [
            "कैसे बनती है, कितनी देर में बनेगी और कितने की आएगी", "घर के बेसिक मसालों से ₹80 के बजट में होटल जैसा स्वाद",
            "ऑफिस टिफिन और संडे स्पेशल फैमिली डिनर के लिए", "हाई-प्रोटीन और कम तेल में सेहतमंद तरीके से",
        ],
    },
    "🗣️ Spoken English, Telecalling & Office Fluency": {
        "topics": [
            "Client Telecalling & Customer Handling in English", "Daily Office Meeting & Reporting Sentences",
            "Self-Introduction for Customer Service & Data Jobs", "Handling Angry Clients Politely on Phone",
            "Boss & Senior Management Email Writing", "Overcoming Hesitation While Speaking English",
        ],
        "contexts": [
            "with Hindi meaning and mirror practice sentences", "for confident telecalling and executive interviews",
            "when you think in Hindi first and want instant fluency", "with 5 ready-to-use professional templates",
        ],
    },
    "🐍 Python, Excel Power Query & Data Analytics": {
        "topics": [
            "Excel Power Query — Combining Multiple Files in 1 Click", "Advanced Excel XLOOKUP, Pivot Tables & MIS Dashboards",
            "Python Pandas — Automating Daily Logistics & Fleet Reports", "Playwright Web Automation & Data Scraping",
            "SQL Queries for Data Analyst Interviews", "Building Interactive Apps with Python & Streamlit",
        ],
        "contexts": [
            "step-by-step in simple Hinglish with practical examples", "to save 2 hours of manual office work every day",
            "for cracking Data Analyst & MIS Executive jobs", "with copy-paste formulas and zero-error tips",
        ],
    },
    "🛍️ Smart Shopping, Saree/Formal Styling & Budget Hacks": {
        "topics": [
            "Saree, Anarkali & Kurti Budget Shopping Guide in Delhi", "Formal Office Wear (Emerald/Navy Shirts & Trousers) Styling",
            "Daily Skincare Routine (Sunscreen PA+++ & Aloe Vera) on Budget", "Monthly Grocery & Sabzi Mandi ₹2,000 Saving Hacks",
        ],
        "contexts": [
            "कम बजट में प्रीमियम और रॉयल लुक पाने के टिप्स", "Expected vs Actual बजट में 25% पैसा बचाने की ट्रिक",
        ],
    },
}

PROMPT_FORMATS = [
    "कैसे करें + कितना समय + कितना खर्च (360° गाइड)",
    "स्टेप-बाय-स्टेप प्रैक्टिकल ट्रिक्स के साथ",
    "5 मिनट में समझ आने वाले उदाहरणों के साथ",
]


def generate_batch_of_smart_prompts(domain_key: str, seed_val: int, count: int = 8) -> list:
    dom = PROMPT_DOMAINS[domain_key]
    topics = dom["topics"]
    contexts = dom["contexts"]
    results = []
    for i in range(count):
        t = topics[(seed_val + i * 3) % len(topics)]
        c = contexts[(seed_val + i * 5) % len(contexts)]
        f = PROMPT_FORMATS[(seed_val + i * 7) % len(PROMPT_FORMATS)]
        results.append(f"{t} — {c} ({f})")
    return results


# ==============================================================================
# 9. FAST UPI QR & ZERO-AD NATIVE WEBAPP GENERATOR
# ==============================================================================
def generate_upi_links_and_qr(upi_id: str, payee_name: str, amount: float, note: str):
    clean_upi = (upi_id or "").strip()
    has_real_upi = "@" in clean_upi and len(clean_upi) >= 5

    direct_openers = {
        "Google Pay (GPay)": "intent://upi/#Intent;scheme=tez;package=com.google.android.apps.nbu.paisa.user;end",
        "PhonePe": "intent://#Intent;scheme=phonepe;package=com.phonepe.app;end",
        "Paytm": "intent://#Intent;scheme=paytmmp;package=net.one97.paytm;end",
        "BHIM / Any UPI App": "upi://pay",
    }

    if has_real_upi:
        params = {
            "pa": clean_upi,
            "pn": (payee_name or "Merchant")[:20],
            "am": f"{float(amount):.2f}",
            "cu": "INR",
            "tn": (note or "Expense")[:35],
        }
        qs = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        prefilled_links = {
            "Google Pay (GPay)": f"tez://upi/pay?{qs}",
            "PhonePe": f"phonepe://pay?{qs}",
            "Paytm": f"paytmmp://pay?{qs}",
            "BHIM / Any UPI App": f"upi://pay?{qs}",
        }
        qr_data = f"upi://pay?{qs}"
    else:
        prefilled_links = direct_openers
        qr_data = f"INR {float(amount):.2f} - {note}"

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=7, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#022c22", back_color="#00ff9d")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return {
        "has_real_upi": has_real_upi,
        "direct_openers": direct_openers,
        "prefilled_links": prefilled_links,
        "qr_buf": buf,
    }


def generate_zero_ad_fullscreen_app_file() -> bytes:
    html_code = """<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#07090f">
<title>Parivaar VIP 5.0 (Zero-Ad Universal App)</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body, html { width: 100%; height: 100%; background: #07090f; color: #fff; font-family: sans-serif; overflow: hidden; }
  #setupBox {
    display: flex; flex-direction: column; justify-content: center; align-items: center;
    height: 100vh; padding: 20px; text-align: center;
    background: radial-gradient(circle at top, #1f1705 0%, #07090f 100%);
  }
  .card {
    background: #111827; border: 2px solid #fbbf24; border-radius: 18px;
    padding: 24px; max-width: 400px; width: 100%; box-shadow: 0 12px 32px rgba(0,0,0,0.7);
  }
  input {
    width: 100%; padding: 14px; border-radius: 10px; border: 1.5px solid #fbbf24;
    background: #1e293b; color: #fff; font-size: 15px; margin: 14px 0; font-weight: bold;
  }
  button {
    width: 100%; padding: 15px; border-radius: 12px; border: none;
    background: linear-gradient(90deg, #00ff9d, #10b981); color: #022c22;
    font-size: 17px; font-weight: 900; cursor: pointer;
  }
  #appFrame { width: 100vw; height: 100vh; border: none; display: none; }
</style>
</head>
<body>
  <div id="setupBox">
    <div class="card">
      <h2 style="color:#fbbf24; margin-bottom:8px;">👑 Parivaar VIP 5.0</h2>
      <p style="font-size:13px; color:#fde68a; margin-bottom:10px;">
        100% Free & Zero-Ads Native App Launcher.<br>नीचे अपने Streamlit ऐप का लिंक सिर्फ 1 बार पेस्ट करें:
      </p>
      <input type="url" id="urlInput" placeholder="https://your-app-name.streamlit.app" />
      <button onclick="saveAndLaunch()">🚀 Launch Ad-Free Fullscreen App</button>
    </div>
  </div>
  <iframe id="appFrame" allow="clipboard-read; clipboard-write; fullscreen"></iframe>
  <script>
    const currentOrigin = window.location.origin;
    const savedUrl = localStorage.getItem('parivaar_vip_clean_url');
    if (savedUrl && savedUrl.startsWith('http')) {
      launchIframe(savedUrl);
    } else if (currentOrigin.includes('streamlit.app')) {
      launchIframe(currentOrigin);
    }
    function saveAndLaunch() {
      let val = document.getElementById('urlInput').value.trim();
      if (!val.startsWith('http')) { val = 'https://' + val; }
      localStorage.setItem('parivaar_vip_clean_url', val);
      launchIframe(val);
    }
    function launchIframe(u) {
      document.getElementById('setupBox').style.display = 'none';
      const fr = document.getElementById('appFrame');
      fr.style.display = 'block';
      fr.src = u;
    }
  </script>
</body>
</html>"""
    return html_code.encode("utf-8")


# ==============================================================================
# 10. LOGIN SCREEN WITH ROYAL ANIMATED LOGO & POSTER
# ==============================================================================
if len(st.query_params) > 0:
    st.query_params.clear()

if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None
if "poster_slide_idx" not in st.session_state:
    st.session_state.poster_slide_idx = 0
if "willpower_xp" not in st.session_state:
    st.session_state.willpower_xp = 120

apply_vip_theme(st.session_state.selected_theme)
USERS_DICT = get_all_users_dict()


def render_hero_poster_and_motivation():
    poster = get_daily_poster_and_motivation(st.session_state.poster_slide_idx)
    st.markdown(
        f"""
        <div class="hero-poster">
            <div style="display:flex; align-items:center;">
                <div class="logo-badge">👑</div>
                <div>
                    <div style="font-size:0.72rem; font-weight:900; color:#00ff9d; letter-spacing:1px;">
                        {poster['badge']} • DAY #{poster['day']} ({poster['date_str']})
                    </div>
                    <div style="font-size:1.22rem; font-weight:900; color:#ffffff; margin-top:2px;">
                        {poster['title']}
                    </div>
                    <div style="font-size:0.84rem; color:#fde68a; margin-top:2px;">
                        {poster['sub']}
                    </div>
                </div>
            </div>
        </div>
        <div class="motivation-poster">
            <div style="font-size:0.75rem; font-weight:900; color:#fbbf24; text-transform:uppercase; letter-spacing:0.8px;">
                ✨ आज का पावर मोटिवेशन पोस्टर (Daily Mindset Poster)
            </div>
            <div style="font-size:1.02rem; font-weight:800; color:#ffffff; margin:6px 0; line-height:1.4;">
                {poster['quote_hi']}
            </div>
            <div style="font-size:0.84rem; color:#a7f3d0; background:rgba(0,0,0,0.35); padding:7px 10px; border-radius:10px; margin-top:4px;">
                {poster['psych_tip']}
            </div>
            <div style="font-size:0.82rem; color:#fde68a; font-weight:800; margin-top:6px;">
                {poster['challenge']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_login_screen():
    render_hero_poster_and_motivation()

    with st.form("strict_login_form"):
        st.markdown("#### 🔐 Parivaar Universal Bank & Super-App लॉगिन")
        user_options = list(USERS_DICT.keys())
        selected_user = st.selectbox(
            "👤 अपना नाम चुनें (Universal Family Account)",
            options=user_options,
            format_func=lambda u: f"{USERS_DICT[u]['avatar']} {u} — {USERS_DICT[u]['role']}",
        )
        pin_input = st.text_input(
            "🔑 अपना पासवर्ड / PIN डालें",
            type="password",
            placeholder="अपना पासवर्ड लिखें...",
        )
        login_btn = st.form_submit_button("🔓 सुपर-ऐप अनलॉक करें (Unlock Universal Account)")

        if login_btn:
            expected_pw = USERS_DICT.get(selected_user, {}).get("password", "")
            if pin_input.strip() == expected_pw:
                st.session_state.authenticated_user = selected_user
                st.rerun()
            else:
                st.error("❌ गलत पासवर्ड! कृपया सही पासवर्ड डालें।")


if not st.session_state.authenticated_user or st.session_state.authenticated_user not in USERS_DICT:
    render_login_screen()
    st.stop()


# ==============================================================================
# 11. UNIVERSAL PARIVAAR BANK CALCULATIONS (NO SPLIT - 100% UNIFIED)
# ==============================================================================
current_user = st.session_state.authenticated_user
current_user_info = USERS_DICT[current_user]
is_admin = bool(current_user_info["is_admin"])

today_obj = date.today()
today_str = today_obj.strftime("%Y-%m-%d")
current_month_str = datetime.now().strftime("%Y-%m")

df_all_expenses = fetch_all_expenses_df()
df_month = (
    df_all_expenses[df_all_expenses["month_year"] == current_month_str].copy()
    if not df_all_expenses.empty
    else pd.DataFrame()
)
df_all_vault = fetch_vault_df()
df_month_vault = fetch_vault_df(current_month_str)
df_shopping = fetch_shopping_df()

if not df_month.empty:
    total_spent_month = float(df_month["amount"].sum())
    df_today = df_month[df_month["timestamp"].str.startswith(today_str, na=False)]
    spent_today = float(df_today["amount"].sum()) if not df_today.empty else 0.0
    bad_spent_month = float(df_month[df_month["is_bad_expense"] == 1]["amount"].sum())
    food_spent_month = float(df_month[df_month["category"].str.startswith("Food", na=False)]["amount"].sum())
    rent_spent_month = float(df_month[df_month["category"].str.startswith("Room Rent", na=False)]["amount"].sum())
else:
    total_spent_month = 0.0
    spent_today = 0.0
    bad_spent_month = 0.0
    food_spent_month = 0.0
    rent_spent_month = 0.0

vault_saved_this_month = float(df_month_vault["amount"].sum()) if not df_month_vault.empty else 0.0
vault_saved_all_time = float(df_all_vault["amount"].sum()) if not df_all_vault.empty else 0.0

days_in_month = calendar.monthrange(today_obj.year, today_obj.month)[1]
days_left = max(1, days_in_month - today_obj.day + 1)

# Universal Bank Math
remaining_spendable_balance = max(0.0, MAX_SPENDING_BUDGET - total_spent_month)
budget_overflow = max(0.0, total_spent_month - MAX_SPENDING_BUDGET)
effective_monthly_savings = max(0.0, STRICT_SAVINGS_VAULT - budget_overflow)
live_total_bank_balance = remaining_spendable_balance + effective_monthly_savings
daily_safe_limit = remaining_spendable_balance / days_left

spend_utilization_pct = min(100.0, (total_spent_month / MAX_SPENDING_BUDGET) * 100.0) if MAX_SPENDING_BUDGET > 0 else 0.0
saving_health_pct = (effective_monthly_savings / STRICT_SAVINGS_VAULT) * 100.0 if STRICT_SAVINGS_VAULT > 0 else 100.0

# Top Bar Controls
top_c1, top_c2, top_c3, top_c4 = st.columns([2.0, 1.2, 1.0, 0.8])
with top_c1:
    chosen_theme = st.selectbox(
        "🎨 VIP थीम (Theme)",
        options=list(THEMES.keys()),
        index=list(THEMES.keys()).index(st.session_state.selected_theme),
    )
    if chosen_theme != st.session_state.selected_theme:
        st.session_state.selected_theme = chosen_theme
        st.rerun()
with top_c2:
    st.markdown("<div style='padding-top:18px;'></div>", unsafe_allow_html=True)
    if st.button("🖼️ अगला पोस्टर"):
        st.session_state.poster_slide_idx += 1
        st.rerun()
with top_c3:
    st.markdown("<div style='padding-top:18px;'></div>", unsafe_allow_html=True)
    if st.button(f"💪 संकल्प (+XP: {st.session_state.willpower_xp})"):
        st.session_state.willpower_xp += 10
        st.balloons()
with top_c4:
    st.markdown("<div style='padding-top:18px;'></div>", unsafe_allow_html=True)
    if st.button("🔒 लॉगआउट"):
        st.session_state.authenticated_user = None
        st.rerun()

# Render Animated Logo, Moving Poster & Motivation Card
render_hero_poster_and_motivation()

# ==============================================================================
# 12. UNIVERSAL PARIVAAR 3D BANK CARD & LIVE SPENDING vs SAVING METER
# ==============================================================================
st.markdown(
    f"""
    <div class="universal-bank-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <div>
                <div style="font-size:0.72rem; color:#fde68a; font-weight:800; letter-spacing:1.2px;">
                    🏦 PARIVAAR UNIVERSAL WEALTH BANK (एक ही संयुक्त खाता)
                </div>
                <div style="font-size:1.15rem; font-weight:900; color:#ffffff;">
                    {current_user_info['avatar']} AJAY & MEENAKSHI UNIVERSAL ACCOUNT
                </div>
            </div>
            <div class="bank-chip"></div>
        </div>
        <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:8px; background:rgba(0,0,0,0.42); padding:10px 12px; border-radius:12px; border:1px solid rgba(255,255,255,0.12);">
            <div>
                <div style="font-size:0.7rem; color:#cbd5e1;">कुल मासिक पूल</div>
                <div style="font-size:1.05rem; font-weight:900; color:#fbbf24;">₹{UNIVERSAL_FAMILY_POOL:,.0f}</div>
            </div>
            <div>
                <div style="font-size:0.7rem; color:#cbd5e1;">अभी खर्च के लिए बचा</div>
                <div style="font-size:1.05rem; font-weight:900; color:#00ff9d;">₹{remaining_spendable_balance:,.0f}</div>
            </div>
            <div>
                <div style="font-size:0.7rem; color:#cbd5e1;">इस महीने कुल खर्च</div>
                <div style="font-size:1.05rem; font-weight:900; color:#f87171;">₹{total_spent_month:,.0f} ({spend_utilization_pct:.0f}%)</div>
            </div>
            <div>
                <div style="font-size:0.7rem; color:#cbd5e1;">सुरक्षित बचत (Vault)</div>
                <div style="font-size:1.05rem; font-weight:900; color:#38bdf8;">₹{effective_monthly_savings:,.0f} ({saving_health_pct:.0f}%)</div>
            </div>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:0.78rem; color:#fde68a; margin-top:8px; font-weight:700;">
            <span>💳 A/C: 5000-PARIVAAR-2026</span>
            <span>🛡️ आज की सुरक्षित खर्च सीमा: ₹{daily_safe_limit:,.0f}/दिन</span>
            <span>🧱 कुल तिजोरी ईंटें: {int((vault_saved_all_time + effective_monthly_savings) // 50)} Bricks</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# 13. MAIN 7 INTERACTIVE SUPER-TABS
# ==============================================================================
tab_shop, tab_pay, tab_yt_ai, tab_vault, tab_ledger, tab_comeback, tab_admin = st.tabs(
    [
        "🛍️ शॉपिंग प्लानर (Expected vs Actual)",
        "⚡ तेज़ UPI & खर्च",
        "🎬 In-App Shorts & AI Search",
        "🏦 बैंक पासबुक & ₹15K तिजोरी",
        "📊 हिसाब & AI ऑडिट",
        "🔥 जीत की कहानियाँ & Games",
        "👑 Admin & Backup Shield",
    ]
)

# ==============================================================================
# TAB 1: SMART SHOPPING PLANNER (EXPECTED VS ACTUAL BUDGET TRACKER)
# ==============================================================================
with tab_shop:
    st.markdown(
        """
        <div class="vip-card">
            <h4 style="margin:0; color:#00ff9d;">🛍️ स्मार्ट शॉपिंग & बाज़ार प्लानर (Expected vs Actual Live Tracker)</h4>
            <p style="margin:4px 0 0 0; font-size:0.86rem;">
                शॉपिंग जाने से पहले अपना <b>कुल बजट (जैसे ₹6,000)</b> और सामान की <b>Expected कीमत (जैसे साड़ी ₹2,000)</b> डालें।
                खरीदते समय जैसे ही <b>Actual (असली कीमत)</b> डालेंगे, आपको तुरंत <b>% Utilization, बचत/ज़्यादा खर्च का हाईलाइट और बचा हुआ बजट</b> दिखेगा!
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "active_trip_budget" not in st.session_state:
        st.session_state.active_trip_budget = (
            float(df_shopping["trip_budget"].iloc[0]) if not df_shopping.empty else 6000.0
        )
    if "active_trip_name" not in st.session_state:
        st.session_state.active_trip_name = (
            str(df_shopping["trip_name"].iloc[0]) if not df_shopping.empty else "त्योहार / बाज़ार शॉपिंग लिस्ट"
        )

    sc1, sc2, sc3 = st.columns([1.6, 1.1, 1.1])
    with sc1:
        trip_name_in = st.text_input("🛒 शॉपिंग लिस्ट का नाम", value=st.session_state.active_trip_name)
        st.session_state.active_trip_name = trip_name_in
    with sc2:
        trip_budget_in = st.number_input(
            "💰 कुल शॉपिंग बजट (Expected Limit ₹)",
            min_value=100.0,
            max_value=200000.0,
            value=float(st.session_state.active_trip_budget),
            step=500.0,
        )
        st.session_state.active_trip_budget = trip_budget_in
    with sc3:
        st.markdown("<div style='padding-top:24px;'></div>", unsafe_allow_html=True)
        if st.button("✨ सैंपल शॉपिंग लिस्ट लोड करें (₹6000)"):
            sample_items = [
                ("साड़ी (Saree - Festival/Party)", "Shopping & Clothes (साड़ी, कपड़े और शॉपिंग)", 2000.0, 1750.0),
                ("फॉर्मल शर्ट और ट्राउज़र", "Shopping & Clothes (साड़ी, कपड़े और शॉपिंग)", 1500.0, 0.0),
                ("जूते / फॉर्मल बूट्स", "Shopping & Clothes (साड़ी, कपड़े और शॉपिंग)", 1200.0, 0.0),
                ("किराना और घर का सामान", "Sabzi & Kirana (सब्ज़ी और राशन)", 1300.0, 0.0),
            ]
            for s_name, s_cat, s_exp, s_act in sample_items:
                add_shopping_item_db(trip_name_in, trip_budget_in, s_name, s_cat, s_exp, s_act)
            st.rerun()

    # Add New Expected Item Form
    with st.form("add_shopping_item_form", clear_on_submit=True):
        st.markdown("##### ➕ नई Expected शॉपिंग आइटम जोड़ें")
        sh_c1, sh_c2, sh_c3, sh_c4 = st.columns([1.6, 1.3, 1.0, 1.0])
        with sh_c1:
            sh_item = st.text_input("सामान का नाम (जैसे: साड़ी, कुर्ती, राशन, जूते)", placeholder="जैसे: साड़ी (Saree)")
        with sh_c2:
            sh_cat = st.selectbox("श्रेणी (Category)", options=list(CATEGORY_DESCRIPTIONS.keys()), index=2)
        with sh_c3:
            sh_exp = st.number_input("Expected कीमत (₹)", min_value=10.0, max_value=100000.0, value=2000.0, step=100.0)
        with sh_c4:
            sh_act = st.number_input("Actual खर्च (₹ - अभी या बाद में)", min_value=0.0, max_value=100000.0, value=0.0, step=50.0)

        if st.form_submit_button("🛒 शॉपिंग लिस्ट में जोड़ें"):
            if sh_item.strip():
                add_shopping_item_db(trip_name_in, trip_budget_in, sh_item.strip(), sh_cat, sh_exp, sh_act)
                st.success(f"✅ '{sh_item}' (Expected: ₹{sh_exp:,.0f}) शॉपिंग प्लानर में जुड़ गया!")
                st.rerun()
            else:
                st.warning("कृपया सामान का नाम लिखें!")

    df_shopping = fetch_shopping_df()
    if not df_shopping.empty:
        total_expected_items = float(df_shopping["expected_amt"].sum())
        total_actual_spent = float(df_shopping["actual_amt"].sum())
        completed_df = df_shopping[df_shopping["actual_amt"] > 0]
        expected_of_completed = float(completed_df["expected_amt"].sum()) if not completed_df.empty else 0.0

        remaining_from_trip_budget = trip_budget_in - total_actual_spent
        trip_utilized_pct = (total_actual_spent / trip_budget_in) * 100.0 if trip_budget_in > 0 else 0.0
        net_variance_on_bought = expected_of_completed - total_actual_spent

        # Live Summary Cards with Percentage & Highlight
        sm1, sm2, sm3, sm4 = st.columns(4)
        sm1.metric("कुल शॉपिंग बजट", f"₹{trip_budget_in:,.0f}", f"Planned: ₹{total_expected_items:,.0f}")
        sm2.metric("Actual खर्च हुआ", f"₹{total_actual_spent:,.0f}", f"{trip_utilized_pct:.1f}% Utilized")
        sm3.metric(
            "अब कितना बजट बचा है?",
            f"₹{remaining_from_trip_budget:,.0f}",
            f"{max(0.0, 100.0 - trip_utilized_pct):.1f}% Left",
        )
        sm4.metric(
            "खरीदे गए सामान पर बचत",
            f"₹{net_variance_on_bought:+,.0f}",
            "Bachat 🎉" if net_variance_on_bought >= 0 else "Over Budget 🚨",
        )

        # Visual Progress Bar for Overall Shopping Utilization
        bar_val = min(1.0, max(0.0, total_actual_spent / trip_budget_in)) if trip_budget_in > 0 else 0.0
        st.progress(
            bar_val,
            text=f"📊 कुल शॉपिंग बजट Utilization: ₹{total_actual_spent:,.0f} / ₹{trip_budget_in:,.0f} ({trip_utilized_pct:.1f}% इस्तेमाल हो गया • ₹{remaining_from_trip_budget:,.0f} बाकी है)",
        )

        st.markdown("#### 📋 आपकी शॉपिंग लिस्ट (यहीं से Actual कीमत अपडेट करें और % देखें):")
        for _, row in df_shopping.iterrows():
            r_id = int(row["id"])
            r_name = str(row["item_name"])
            r_cat = str(row["category"])
            r_exp = float(row["expected_amt"])
            r_act = float(row["actual_amt"])

            item_pct_of_exp = (r_act / r_exp * 100.0) if r_exp > 0 else 0.0
            item_pct_of_trip = (r_act / trip_budget_in * 100.0) if trip_budget_in > 0 else 0.0
            diff = r_exp - r_act

            if r_act == 0:
                badge_html = f'<span class="pill-pending">⏳ लेना बाकी है (Expected: ₹{r_exp:,.0f})</span>'
            elif diff > 0:
                badge_html = f'<span class="pill-saved">🎉 ₹{diff:,.0f} बचाए! ({item_pct_of_exp:.0f}% of Expected | कुल बजट का {item_pct_of_trip:.1f}%)</span>'
            elif diff == 0:
                badge_html = f'<span class="pill-saved">✅ फिक्स बजट में मिला (100% Utilized | कुल बजट का {item_pct_of_trip:.1f}%)</span>'
            else:
                badge_html = f'<span class="pill-over">🚨 ₹{abs(diff):,.0f} ज़्यादा लगा! ({item_pct_of_exp:.0f}% of Expected | कुल बजट का {item_pct_of_trip:.1f}%)</span>'

            st.markdown(
                f"""
                <div class="vip-card" style="padding:10px 14px; margin-bottom:8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;">
                        <div>
                            <span style="font-size:1.02rem; font-weight:900; color:#fbbf24;">🛍️ {r_name}</span>
                            <span style="font-size:0.78rem; color:#cbd5e1;"> ({r_cat.split('(')[0]})</span>
                        </div>
                        <div>{badge_html}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            ic1, ic2, ic3, ic4 = st.columns([1.2, 1.2, 1.3, 0.8])
            with ic1:
                new_exp_v = st.number_input(
                    f"Expected (₹) #{r_id}",
                    min_value=10.0,
                    value=r_exp,
                    step=100.0,
                    key=f"sh_exp_{r_id}",
                )
            with ic2:
                new_act_v = st.number_input(
                    f"Actual खर्च (₹) #{r_id}",
                    min_value=0.0,
                    value=r_act,
                    step=50.0,
                    key=f"sh_act_{r_id}",
                )
            with ic3:
                st.markdown("<div style='padding-top:24px;'></div>", unsafe_allow_html=True)
                if st.button("💾 Actual सेव + बैंक खाते में जोड़ें", key=f"sh_save_{r_id}"):
                    update_shopping_actual_db(r_id, new_act_v, new_exp_v)
                    if new_act_v > 0:
                        add_expense_to_db(
                            logged_by=current_user,
                            spent_by="Universal Family Account",
                            category=r_cat,
                            item_name=f"{r_name} (Shopping)",
                            description=f"Expected ₹{new_exp_v:,.0f} vs Actual ₹{new_act_v:,.0f}",
                            payment_mode="UPI",
                            upi_app="Google Pay (GPay)",
                            need_level="बहुत ज़रूरी (Essential)",
                            amount=new_act_v,
                            is_bad_expense=(new_act_v > new_exp_v * 1.25),
                            upi_id="",
                            notes=f"Shopping Planner: Expected ₹{new_exp_v:,.0f}, Actual ₹{new_act_v:,.0f}",
                        )
                    st.success(f"✅ '{r_name}' अपडेट हो गया और मुख्य पासबुक में भी जुड़ गया!")
                    st.rerun()
            with ic4:
                st.markdown("<div style='padding-top:24px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️ हटाएं", key=f"sh_del_{r_id}"):
                    delete_shopping_item_db(r_id)
                    st.rerun()
    else:
        st.info("💡 अभी आपकी शॉपिंग लिस्ट खाली है। ऊपर **'✨ सैंपल शॉपिंग लिस्ट लोड करें (₹6000)'** दबाएं या नया आइटम जोड़ें!")


# ==============================================================================
# TAB 2: ULTRA-FAST DAILY EXPENSE & INSTANT UPI LAUNCHER
# ==============================================================================
with tab_pay:
    st.caption("⚡ **1-Tap तेज़ बटन (दबाते ही रकम और कारण अपने-आप भर जाएगा):**")
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
        st.session_state.qf_desc = "दूध, दही और ब्रेड (Milk & Curd)"
    if q4.button("🥦 ₹80 सब्ज़ी"):
        st.session_state.qf_cat = "Sabzi & Kirana (सब्ज़ी और राशन)"
        st.session_state.qf_amt = 80.0
        st.session_state.qf_desc = "रोज़ की हरी सब्ज़ी (आलू, प्याज, भिंडी, टमाटर)"

    cat_list = list(CATEGORY_DESCRIPTIONS.keys())
    default_cat = st.session_state.get("qf_cat", cat_list[0])
    cat_idx = cat_list.index(default_cat) if default_cat in cat_list else 0

    c_who, c_cat = st.columns(2)
    with c_who:
        spent_by_options = ["Universal Family Account (संयुक्त परिवार खाता)"] + list(USERS_DICT.keys())
        spent_by_val = st.selectbox("🏦 किस खाते/सदस्य द्वारा खर्च हुआ?", options=spent_by_options, index=0)
    with c_cat:
        selected_category = st.selectbox("📂 खर्च की श्रेणी (Expense Category)", options=cat_list, index=cat_idx)

    desc_list = CATEGORY_DESCRIPTIONS.get(selected_category, ["अन्य खर्च..."])
    default_desc = st.session_state.get("qf_desc", desc_list[0])
    desc_idx = desc_list.index(default_desc) if default_desc in desc_list else 0

    c_desc, c_app = st.columns(2)
    with c_desc:
        selected_desc = st.selectbox("📝 विवरण चुनें (Description)", options=desc_list, index=desc_idx)
    with c_app:
        selected_upi_app = st.selectbox(
            "📲 पेमेंट ऐप चुनें (UPI App / Cash)",
            options=["Google Pay (GPay)", "PhonePe", "Paytm", "BHIM / Any UPI App", "Cash (नकद पेमेंट)", "Bank Transfer / Card"],
        )

    auto_bad = "Faltu" in selected_category or "Bad" in selected_desc or "Avoid" in selected_desc

    with st.form("fast_upi_form", clear_on_submit=False):
        fc1, fc2 = st.columns([1.4, 1])
        with fc1:
            custom_item = st.text_input(
                "🏷️ सामान का नाम (चाहें तो लिखें)",
                value="" if "Custom" in selected_desc or "अन्य" in selected_desc else selected_desc,
                placeholder="जैसे: दाल मखनी सामान / साड़ी / सब्ज़ी",
            )
        with fc2:
            amount_val = st.number_input(
                "₹ रकम (Amount)",
                min_value=1.0,
                max_value=100000.0,
                value=float(st.session_state.get("qf_amt", 50.0)),
                step=10.0,
            )

        p1, p2 = st.columns(2)
        with p1:
            need_level_val = st.selectbox(
                "⚖️ प्राथमिकता (Priority)",
                options=[
                    "बहुत ज़रूरी (Essential)",
                    "कान का इलाज (Ear Medical Priority)",
                    "माता-पिता / घर की जिम्मेदारी",
                    "पढ़ाई और करियर (AI/Python/English)",
                    "गैर-ज़रूरी / फालतू खर्च (Bad Expense)",
                ],
                index=4 if auto_bad else (1 if "Ear" in selected_category else 0),
            )
        with p2:
            upi_id_input = st.text_input(
                "🆔 दुकानदार की UPI ID (ऑप्शनल)",
                value="",
                placeholder="खाली छोड़ने पर सीधा ऐप खुलेगा",
            )

        is_bad_chk = st.checkbox("🚨 यह गैर-ज़रूरी / फालतू खर्च (Bad Expense) है", value=auto_bad)
        notes_val = st.text_input("📌 नोट (Optional)", placeholder="कोई खास बात...")

        bricks_eq = max(1, int(amount_val // 50))
        pct_of_monthly = (amount_val / MAX_SPENDING_BUDGET) * 100.0
        st.caption(
            f"🧱 **लाइव बैंक असर:** `₹{amount_val:,.0f}` आपके मासिक खर्च बजट का **{pct_of_monthly:.1f}%** है (= सपनों के घर की **{bricks_eq} ईंटें**)."
        )

        submit_tx = st.form_submit_button("🚀 पासबुक में सेव करें और तुरंत GPay / PhonePe खोलें")

        if submit_tx:
            final_item_name = custom_item.strip() or selected_desc
            final_is_bad = bool(is_bad_chk or "Faltu" in selected_category or "गैर-ज़रूरी" in need_level_val)
            mode_label = "Cash" if "Cash" in selected_upi_app else ("Bank/Card" if "Bank" in selected_upi_app else "UPI")

            add_expense_to_db(
                logged_by=current_user,
                spent_by=spent_by_val,
                category=selected_category,
                item_name=final_item_name,
                description=selected_desc,
                payment_mode=mode_label,
                upi_app=selected_upi_app,
                need_level=need_level_val,
                amount=amount_val,
                is_bad_expense=final_is_bad,
                upi_id=upi_id_input.strip(),
                notes=notes_val.strip(),
            )

            st.session_state.last_payment_receipt = {
                "item": final_item_name,
                "category": selected_category,
                "spent_by": spent_by_val,
                "upi_app": selected_upi_app,
                "amount": amount_val,
                "upi_id": upi_id_input.strip(),
                "is_bad": final_is_bad,
            }
            st.rerun()

    rec = st.session_state.get("last_payment_receipt")
    active_amt = rec["amount"] if rec else 50.0
    active_item = rec["item"] if rec else "Expense"
    active_upi = rec["upi_id"] if rec else ""
    active_app = rec["upi_app"] if rec else selected_upi_app

    upi_bundle = generate_upi_links_and_qr(active_upi, active_item, active_amt, active_item)

    if rec:
        st.success(f"✅ **यूनिवर्सल बैंक पासबुक में सेव हो गया!** ₹{rec['amount']:,.0f} — **{rec['item']}**")

    u_c1, u_c2, u_c3 = st.columns(3)
    u_c1.markdown(
        f'<a href="{upi_bundle["direct_openers"]["Google Pay (GPay)"]}" class="upi-app-btn" style="font-size:0.86rem; padding:11px;">🟢 Open GPay</a>',
        unsafe_allow_html=True,
    )
    u_c2.markdown(
        f'<a href="{upi_bundle["direct_openers"]["PhonePe"]}" class="upi-app-btn" style="font-size:0.86rem; padding:11px; background:linear-gradient(90deg,#a855f7,#7e22ce); color:#fff !important;">🟣 Open PhonePe</a>',
        unsafe_allow_html=True,
    )
    u_c3.markdown(
        f'<a href="{upi_bundle["direct_openers"]["Paytm"]}" class="upi-app-btn" style="font-size:0.86rem; padding:11px; background:linear-gradient(90deg,#38bdf8,#0284c7); color:#fff !important;">🔵 Open Paytm</a>',
        unsafe_allow_html=True,
    )


# ==============================================================================
# TAB 3: IN-APP YOUTUBE SHORTS (4 ANGLES) + AI 360 OVERVIEW + 37L PROMPTS
# ==============================================================================
with tab_yt_ai:
    st.markdown(
        """
        <div class="vip-card">
            <h4 style="margin:0; color:#fbbf24;">🎬 In-App Multi-Angle YouTube Shorts & 🤖 AI 360° Overview (No Instagram!)</h4>
            <p style="margin:4px 0 0 0; font-size:0.86rem;">
                अब कोई भी डिश (जैसे <b>Dal Makhani</b>), कोडिंग (<b>Python / Power Query</b>) या <b>Spoken English</b> टॉपिक चुनें या लिखें।
                सबसे ऊपर <b>AI Overview</b> आएगा और ठीक नीचे <b>इसी ऐप के अंदर 4 अलग-अलग तरह की YouTube Shorts</b> चलेंगी:
                <b>(1) कैसे बनती है</b> • <b>(2) कितनी देर में बनेगी</b> • <b>(3) कितने की आएगी</b> • <b>(4) सीक्रेट प्रो टिप्स!</b>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "active_search_topic" not in st.session_state:
        st.session_state.active_search_topic = "Dal Makhani (दाल मखनी)"
    if "mega_prompt_seed" not in st.session_state:
        st.session_state.mega_prompt_seed = (date.today() - date(2025, 1, 1)).days * 13

    st.caption("⚡ **1-Click में देखें (दबाते ही 4 अलग-अलग एंगल की YouTube Shorts और AI Overview यहीं खुलेंगे):**")
    qc1, qc2, qc3, qc4, qc5 = st.columns(5)
    if qc1.button("🍲 दाल मखनी"):
        st.session_state.active_search_topic = "Dal Makhani (दाल मखनी)"
    if qc2.button("🍗 चिकन करी"):
        st.session_state.active_search_topic = "Dhaba Style Chicken Curry"
    if qc3.button("🐟 फिश फ्राई"):
        st.session_state.active_search_topic = "Masala Fish Fry & Fish Curry"
    if qc4.button("📊 Power Query"):
        st.session_state.active_search_topic = "Excel Power Query Combine Files"
    if qc5.button("🗣️ English Call"):
        st.session_state.active_search_topic = "Spoken English Telecalling & Interview"

    with st.expander("🚀 37 लाख+ Smart Prompt Generator से टॉपिक चुनें", expanded=False):
        p_col1, p_col2 = st.columns([2.3, 1.1])
        with p_col1:
            chosen_domain = st.selectbox("📂 श्रेणी चुनें:", options=list(PROMPT_DOMAINS.keys()))
        with p_col2:
            st.markdown("<div style='padding-top:24px;'></div>", unsafe_allow_html=True)
            if st.button("🎲 8 नए प्रॉम्प्ट्स"):
                st.session_state.mega_prompt_seed += random.randint(3, 999)
                st.rerun()
        generated_prompts = generate_batch_of_smart_prompts(chosen_domain, st.session_state.mega_prompt_seed, count=8)
        picked_p = st.selectbox("✨ स्मार्ट प्रॉम्प्ट चुनें:", options=generated_prompts)
        if st.button("🎬 इस प्रॉम्प्ट पर 4 अलग-अलग Shorts और AI Overview चलाएं"):
            st.session_state.active_search_topic = picked_p.split("—")[0].strip()
            st.rerun()

    # Main Search Box
    s_col1, s_col2 = st.columns([2.6, 1.0])
    with s_col1:
        user_query = st.text_input(
            "🔍 कुछ भी सर्च करें (जैसे: Dal Makhani, Chana Aloo, Saree Draping, Python Pandas, English Fluency):",
            value=st.session_state.active_search_topic,
        )
    with s_col2:
        st.markdown("<div style='padding-top:24px;'></div>", unsafe_allow_html=True)
        if st.button("🚀 4-Angle Shorts चलाएं"):
            st.session_state.active_search_topic = user_query.strip()

    active_q = user_query.strip() or "Dal Makhani"
    angles_data = build_multi_angle_ai_and_shorts(active_q)

    # 1. TOP AI 360° OVERVIEW BAR WITH INTERACTIVE FILTER BUTTONS
    st.markdown(f"### 🤖 AI 360° Overview: `{active_q}`")
    ai_b1, ai_b2, ai_b3, ai_b4 = st.columns(4)
    if "selected_ai_angle" not in st.session_state:
        st.session_state.selected_ai_angle = "ALL"

    if ai_b1.button("🍲 1. कैसे बनती/सीखते हैं"):
        st.session_state.selected_ai_angle = 0
    if ai_b2.button("⏱️ 2. कितना समय लगेगा"):
        st.session_state.selected_ai_angle = 1
    if ai_b3.button("💰 3. कितने की आएगी"):
        st.session_state.selected_ai_angle = 2
    if ai_b4.button("🔥 4. सभी 4 एंगल दिखाएं"):
        st.session_state.selected_ai_angle = "ALL"

    # Render AI Overview Cards
    ov_c1, ov_c2 = st.columns(2)
    for idx, ang in enumerate(angles_data):
        if st.session_state.selected_ai_angle != "ALL" and st.session_state.selected_ai_angle != idx:
            continue
        target_col = ov_c1 if idx % 2 == 0 else ov_c2
        with target_col:
            st.markdown(
                f"""
                <div class="vip-card" style="border-left:6px solid #00ff9d;">
                    <div style="font-size:0.74rem; color:#fbbf24; font-weight:900;">{ang['badge']}</div>
                    <div style="font-size:0.95rem; font-weight:800; color:#ffffff; margin:3px 0;">{ang['title']}</div>
                    <div style="font-size:0.84rem; color:#e2e8f0; line-height:1.4;">{ang['ai_summary']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # 2. IN-APP EMBEDDED YOUTUBE SHORTS (4 DIFFERENT ANGLES SIDE BY SIDE)
    st.markdown(f"### ▶️ In-App YouTube Shorts & Videos (`{active_q}` के 4 अलग-अलग पहलू — सीधे ऐप के अंदर)")
    v_col1, v_col2 = st.columns(2)
    for idx, ang in enumerate(angles_data):
        if st.session_state.selected_ai_angle != "ALL" and st.session_state.selected_ai_angle != idx:
            continue
        with (v_col1 if idx % 2 == 0 else v_col2):
            render_in_app_youtube_short(
                video_id=ang["video_id"],
                title=ang["title"],
                badge=ang["badge"],
                height=340,
            )


# ==============================================================================
# TAB 4: UNIVERSAL BANK PASSBOOK & ₹15,000 DREAM HOUSE + EAR MEDICAL VAULT
# ==============================================================================
with tab_vault:
    st.markdown(
        """
        <div class="vip-card">
            <h4 style="margin:0; color:#fbbf24;">🏦 यूनिवर्सल बैंक पासबुक & ₹15,000 अलग बचत तिजोरी (Dream House & Ear Medical Vault)</h4>
            <p style="margin:4px 0 0 0; font-size:0.86rem;">
                यहाँ आपका <b>₹38,000 Universal Account</b> का पूरा बैंक बैलेंस, खर्च बनाम बचत अनुपात और ₹15,000 की तिजोरी सुरक्षित रहती है।
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    DREAM_HOUSE_GOAL = 8000
    EAR_MEDICAL_GOAL = 4000
    EMERGENCY_GOAL = 3000

    def get_bucket_sum(df_v, prefix):
        if df_v.empty:
            return 0.0
        return float(df_v[df_v["vault_bucket"].str.startswith(prefix, na=False)]["amount"].sum())

    dh_m = get_bucket_sum(df_month_vault, "🏡")
    ear_m = get_bucket_sum(df_month_vault, "👂")
    emg_m = get_bucket_sum(df_month_vault, "🛡️")

    dh_all = get_bucket_sum(df_all_vault, "🏡")
    ear_all = get_bucket_sum(df_all_vault, "👂")
    emg_all = get_bucket_sum(df_all_vault, "🛡️")

    v1, v2, v3, v4 = st.columns(4)
    v1.metric("कुल बैंक बैलेंस बचा", f"₹{live_total_bank_balance:,.0f}", "Out of ₹38,000")
    v2.metric("खर्च बजट बचा है", f"₹{remaining_spendable_balance:,.0f}", f"{100 - spend_utilization_pct:.0f}% Left of ₹23K")
    v3.metric("इस महीने तिजोरी जमा", f"₹{vault_saved_this_month:,.0f}", "Target: ₹15,000")
    v4.metric("कुल तिजोरी फंड", f"₹{vault_saved_all_time:,.0f}", f"{int(vault_saved_all_time // 50)} ईंटें 🧱")

    st.progress(
        min(1.0, total_spent_month / MAX_SPENDING_BUDGET),
        text=f"💳 मासिक खर्च मीटर (Spending Limit): ₹{total_spent_month:,.0f} / ₹{MAX_SPENDING_BUDGET:,} ({spend_utilization_pct:.1f}% खर्च हुआ)",
    )
    st.progress(
        min(1.0, vault_saved_this_month / STRICT_SAVINGS_VAULT),
        text=f"🔐 मासिक ₹15K बचत लक्ष्य: ₹{vault_saved_this_month:,.0f} / ₹15,000 ({(vault_saved_this_month/STRICT_SAVINGS_VAULT)*100:.1f}% जमा)",
    )
    st.progress(min(1.0, dh_m / DREAM_HOUSE_GOAL), text=f"🏡 Dream House: ₹{dh_m:,.0f} / ₹{DREAM_HOUSE_GOAL:,} (कुल: ₹{dh_all:,.0f})")
    st.progress(min(1.0, ear_m / EAR_MEDICAL_GOAL), text=f"👂 Ear Treatment: ₹{ear_m:,.0f} / ₹{EAR_MEDICAL_GOAL:,} (कुल: ₹{ear_all:,.0f})")
    st.progress(min(1.0, emg_m / EMERGENCY_GOAL), text=f"🛡️ Emergency Fund: ₹{emg_m:,.0f} / ₹{EMERGENCY_GOAL:,} (कुल: ₹{emg_all:,.0f})")

    with st.form("vault_deposit_form", clear_on_submit=True):
        vc1, vc2, vc3 = st.columns(3)
        with vc1:
            dep_by = st.selectbox("किसने जमा किया?", ["Universal Family Account"] + list(USERS_DICT.keys()))
        with vc2:
            v_bucket = st.selectbox(
                "फंड चुनें",
                [
                    "🏡 Dream House (सपनों का घर फंड)",
                    "👂 Ear Medical (कान के इलाज का फंड)",
                    "🛡️ Emergency Shield (इमरजेंसी फंड)",
                ],
            )
        with vc3:
            v_amt = st.number_input("रकम (₹)", min_value=100.0, max_value=100000.0, value=5000.0, step=500.0)
        v_note = st.text_input("नोट / बैंक रेफरेंस", placeholder="जैसे: SBI RD या अलग सेविंग्स अकाउंट में जमा")
        if st.form_submit_button("🔐 तिजोरी में लॉक करें"):
            add_vault_deposit(dep_by, v_bucket, v_amt, v_note)
            st.success(f"🎉 ₹{v_amt:,.0f} तिजोरी में सुरक्षित लॉक हो गए!")
            st.rerun()

    if not df_all_vault.empty:
        st.dataframe(df_all_vault[["id", "timestamp", "deposited_by", "vault_bucket", "amount", "notes"]], use_container_width=True, hide_index=True)


# ==============================================================================
# TAB 5: LIVE LEDGER, PERIOD SELECTOR, AI REVIEWER & ADMIN EDIT/DELETE
# ==============================================================================
with tab_ledger:
    st.markdown("### 📊 यूनिवर्सल पासबुक रजिस्टर और 🤖 AI खर्च बनाम बचत ऑडिटर")

    period_choice = st.selectbox(
        "📅 किस समय का हिसाब देखना चाहते हैं? (Select Time Period)",
        options=[
            "इस महीने (This Month)",
            "आज का खर्च (Today)",
            "पिछले 7 दिन (Last 7 Days)",
            "पिछले 30 दिन (Last 30 Days)",
            "पूरा रिकॉर्ड (All Time)",
            "कस्टम तारीख चुनें (Custom Date Range)",
        ],
    )

    df_period = df_all_expenses.copy()
    if not df_period.empty:
        if period_choice == "आज का खर्च (Today)":
            df_period = df_period[df_period["parsed_date"] == today_obj]
        elif period_choice == "पिछले 7 दिन (Last 7 Days)":
            df_period = df_period[df_period["parsed_date"] >= (today_obj - timedelta(days=7))]
        elif period_choice == "इस महीने (This Month)":
            df_period = df_period[df_period["month_year"] == current_month_str]
        elif period_choice == "पिछले 30 दिन (Last 30 Days)":
            df_period = df_period[df_period["parsed_date"] >= (today_obj - timedelta(days=30))]
        elif period_choice == "कस्टम तारीख चुनें (Custom Date Range)":
            d_c1, d_c2 = st.columns(2)
            with d_c1:
                start_d = st.date_input("शुरुआती तारीख (Start Date)", value=today_obj - timedelta(days=15))
            with d_c2:
                end_d = st.date_input("आखिरी तारीख (End Date)", value=today_obj)
            df_period = df_period[(df_period["parsed_date"] >= start_d) & (df_period["parsed_date"] <= end_d)]

    p_total = float(df_period["amount"].sum()) if not df_period.empty else 0.0
    p_bad = float(df_period[df_period["is_bad_expense"] == 1]["amount"].sum()) if not df_period.empty else 0.0

    m1, m2, m3 = st.columns(3)
    m1.metric("चुने गए पीरियड का खर्च", f"₹{p_total:,.0f}", f"{len(df_period)} Entries")
    m2.metric("फालतू खर्च (Bad)", f"₹{p_bad:,.0f}", "Target: ₹0")
    m3.metric("उपलब्ध खर्च बैलेंस", f"₹{remaining_spendable_balance:,.0f}", f"आज Safe: ₹{daily_safe_limit:,.0f}")

    if not df_period.empty:
        df_show = df_period.copy()
        df_show["Status"] = df_show["is_bad_expense"].apply(lambda x: "🚨 फालतू" if x == 1 else "✅ ज़रूरी")
        cols = ["id", "timestamp", "spent_by", "category", "item_name", "amount", "upi_app", "Status", "notes"]
        for c in cols:
            if c not in df_show.columns:
                df_show[c] = ""
        st.dataframe(df_show[cols], use_container_width=True, hide_index=True)

        ch1, ch2 = st.columns(2)
        with ch1:
            fig_c = px.pie(
                df_period.groupby("category", as_index=False)["amount"].sum(),
                names="category",
                values="amount",
                hole=0.48,
                template="plotly_dark",
                title="श्रेणी के अनुसार खर्च (%)",
            )
            fig_c.update_layout(margin=dict(t=35, b=10, l=5, r=5), paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#fff"))
            st.plotly_chart(fig_c, use_container_width=True)
        with ch2:
            bank_vs_df = pd.DataFrame(
                {
                    "हिस्सा": ["खर्च हो चुका (Spent)", "खर्च के लिए बचा (Available)", "लॉक्ड बचत (Vault ₹15K)"],
                    "रकम": [total_spent_month, remaining_spendable_balance, effective_monthly_savings],
                }
            )
            fig_b = px.bar(
                bank_vs_df,
                x="हिस्सा",
                y="रकम",
                color="हिस्सा",
                template="plotly_dark",
                title="₹38,000 Universal Bank: खर्च बनाम बचत",
            )
            fig_b.update_layout(margin=dict(t=35, b=10, l=5, r=5), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#fff"), showlegend=False)
            st.plotly_chart(fig_b, use_container_width=True)

        if is_admin:
            st.markdown("---")
            st.markdown("#### 👑 अजय एडमिन कंट्रोल: गलत एंट्री सुधारें (Edit) या हटाएं (Delete)")
            adm_c1, adm_c2 = st.columns(2)
            with adm_c1:
                with st.expander("✏️ किसी एंट्री को सुधारें (Edit Entry by ID)"):
                    all_ids = df_all_expenses["id"].tolist()
                    edit_id = st.selectbox("सुधारने के लिए ID चुनें", options=all_ids)
                    row_data = df_all_expenses[df_all_expenses["id"] == edit_id].iloc[0]

                    with st.form("admin_edit_expense_form"):
                        new_sb = st.selectbox("Spent By", options=["Universal Family Account"] + list(USERS_DICT.keys()))
                        new_cat = st.selectbox(
                            "Category",
                            options=list(CATEGORY_DESCRIPTIONS.keys()),
                            index=list(CATEGORY_DESCRIPTIONS.keys()).index(row_data["category"])
                            if row_data["category"] in CATEGORY_DESCRIPTIONS
                            else 0,
                        )
                        new_item = st.text_input("सामान का नाम", value=str(row_data["item_name"]))
                        new_amt = st.number_input("सही रकम (₹)", min_value=1.0, value=float(row_data["amount"]), step=10.0)
                        new_bad = st.checkbox("फालतू खर्च (Bad Expense)", value=bool(row_data["is_bad_expense"]))
                        new_notes = st.text_input("नोट", value=str(row_data.get("notes", "") or ""))

                        if st.form_submit_button("✅ बदलाव सेव करें (Update Entry)"):
                            update_expense_in_db(edit_id, new_sb, new_cat, new_item, new_amt, new_bad, new_notes)
                            st.success(f"ID #{edit_id} सफलतापूर्वक अपडेट हो गया!")
                            st.rerun()

            with adm_c2:
                with st.expander("🗑️ गलत एंट्री को तुरंत डिलीट करें (Delete by ID)"):
                    del_id = st.selectbox("डिलीट करने के लिए ID चुनें", options=df_all_expenses["id"].tolist(), key="del_exp_select")
                    if st.button("🚨 यह एंट्री हमेशा के लिए हटाएं (Confirm Delete)"):
                        delete_expense_from_db(int(del_id))
                        st.success(f"एंट्री ID #{int(del_id)} को हटा दिया गया है!")
                        st.rerun()


# ==============================================================================
# TAB 6: FAILURE RECOVERY HUB & PLAYABLE MIND GAMES
# ==============================================================================
with tab_comeback:
    fb_tab, game_tab = st.tabs(["🔥 हार से जीत की सच्ची कहानियाँ और समाधान", "🎮 दिमागी खेल (Play Mind Games)"])

    with fb_tab:
        failure_type = st.selectbox(
            "🛡️ अभी आपको किस क्षेत्र में कठिनाई या असफलता महसूस हो रही है?",
            [
                "🗣️ 1. Spoken English में अटकना, झिझक या किसी का हंसना",
                "💻 2. Software / Python / Power Query सीखने में एरर आना",
                "🏢 3. Office Work में गलती होना या काम का दबाव",
                "💸 4. अचानक बड़ा खर्च आ जाना या बजट बिगड़ जाना",
            ],
        )
        if "Spoken English" in failure_type:
            st.markdown(
                """
                <div class="vip-card">
                    <h4 style="color:#fbbf24; margin-top:0;">🗣️ जब अंग्रेज़ी बोलते समय जुबान अटक जाए — तब क्या करें?</h4>
                    <p><b>सच्चाई:</b> अगर आप हिंदी और गढ़वाली जानते हुए इंग्लिश सीख रहे हैं, तो आपका दिमाग 2-3 भाषाओं को प्रोसेस कर रहा है। अटकना कमजोरी नहीं, प्रैक्टिस की निशानी है!</p>
                    <ul>
                        <li><b>Mirror Rule:</b> रोज़ सुबह 5 मिनट शीशे के सामने खड़े होकर अपने ऑफिस की 5 लाइनें बोलें।</li>
                        <li><b>3 Ready Sentences:</b> <i>"Let me check the latest status and revert in 10 minutes."</i>, <i>"I have combined the files using Power Query."</i>, <i>"Thank you for your patience, sir."</i></li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="vip-card">
                    <h4 style="color:#00ff9d; margin-top:0;">🚀 हर रुकावट से दोगुनी ताकत से वापसी का नियम:</h4>
                    <p>चाहे कोडिंग का Error हो, ऑफिस का दबाव हो या अचानक आया खर्च—1 गहरी सांस लें, समस्या को कागज़ पर 2 हिस्सों में बांटें और आज सिर्फ पहले छोटे कदम पर एक्शन लें।</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with game_tab:
        if "mind_game_score" not in st.session_state:
            st.session_state.mind_game_score = 0
        st.metric("🏆 आपका कुल दिमागी स्कोर (Brain Score)", f"{st.session_state.mind_game_score} Points")

        if "math_q" not in st.session_state:
            a, b = random.randint(15, 65), random.randint(12, 45)
            st.session_state.math_q = f"{a} + {b}"
            st.session_state.math_ans = a + b

        st.markdown(f"<div class='vip-card'><b>तेज़ हिसाब सवाल:</b> <code>{st.session_state.math_q} = ?</code></div>", unsafe_allow_html=True)
        ans_in = st.number_input("उत्तर लिखें:", value=0, step=1)
        if st.button("✅ उत्तर चेक करें"):
            if int(ans_in) == int(st.session_state.math_ans):
                st.session_state.mind_game_score += 10
                st.balloons()
                st.success("🎉 बिल्कुल सही! +10 Points!")
                del st.session_state.math_q
            else:
                st.error(f"सही जवाब {st.session_state.math_ans} था!")


# ==============================================================================
# TAB 7: ANTI-DELETE BACKUP SHIELD + ZERO-AD APP + AJAY ADMIN PANEL
# ==============================================================================
with tab_admin:
    st.markdown(
        """
        <div class="vip-card">
            <h4 style="margin:0; color:#00ff9d;">🛡️ Zero-Data-Loss Backup Shield (ऐप रीबूट या स्लीप होने पर भी रिकॉर्ड कभी नहीं मिटेगा!)</h4>
            <p style="margin:4px 0 0 0; font-size:0.86rem;">
                1. ऐप हर एंट्री के साथ अपने-आप <code>parivaar_auto_mirror_v5.json</code> में ऑटो-बैकअप बनाता है।<br>
                2. नीचे दिए गए बटन से आप कभी भी 1-Click में अपना <b>Master Backup File (.json)</b> फोन में डाउनलोड कर सकते हैं और कभी भी ऐप रीसेट होने पर 1 सेकंड में <b>Restore</b> कर सकते हैं!
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    bk_c1, bk_c2 = st.columns(2)
    with bk_c1:
        live_json_backup = export_full_backup_json()
        st.download_button(
            label="📥 1-Click Master Backup डाउनलोड करें (.json)",
            data=live_json_backup.encode("utf-8"),
            file_name=f"Parivaar_Bank_Backup_{today_str}.json",
            mime="application/json",
        )
    with bk_c2:
        uploaded_bk = st.file_uploader("📤 पुरानी Backup File यहाँ डालकर 1-Click Restore करें", type=["json"])
        if uploaded_bk is not None:
            if st.button("🔄 सारा रिकॉर्ड अभी Restore करें"):
                ok = restore_from_backup_json(uploaded_bk.read().decode("utf-8"))
                if ok:
                    st.success("🎉 आपके सारे खर्च, तिजोरी और शॉपिंग रिकॉर्ड 100% वापस आ गए!")
                    st.rerun()
                else:
                    st.error("❌ फाइल पढ़ने में त्रुटि आई।")

    st.markdown("---")
    clean_app_bytes = generate_zero_ad_fullscreen_app_file()
    st.download_button(
        label="📲 Download 100% Ad-Free Parivaar VIP 5.0 Mobile App (Zero Ads Forever)",
        data=clean_app_bytes,
        file_name="Parivaar_VIP_5_Universal_App.html",
        mime="text/html",
    )

    if is_admin:
        st.markdown("---")
        st.markdown("### 👑 अजय सुपर एडमिन पैनल (User ID & Password Control)")
        users_table_rows = [
            {
                "Avatar": u_data["avatar"],
                "User ID": u_name,
                "Password": u_data["password"],
                "Role": u_data["role"],
                "Admin": "👑 YES" if u_data["is_admin"] else "👤 Member",
            }
            for u_name, u_data in USERS_DICT.items()
        ]
        st.dataframe(pd.DataFrame(users_table_rows), use_container_width=True, hide_index=True)

        with st.form("admin_upsert_user_form"):
            u_name_in = st.text_input("👤 User ID", placeholder="जैसे: Ajay, Meenakshi, Ajeet...")
            u_pass_in = st.text_input("🔑 नया पासवर्ड / PIN")
            u_role_in = st.text_input("🏷️ भूमिका (Role)", value="Universal Parivaar Member")
            u_av_in = st.selectbox("😀 आइकॉन", ["👑", "👩‍💼", "👨‍💻", "🧑‍🎓", "👴", "👵"])
            u_adm_in = st.checkbox("👑 Admin पावर दें?", value=False)
            if st.form_submit_button("✅ यूज़र / पासवर्ड सेव करें"):
                if u_name_in.strip() and u_pass_in.strip():
                    final_adm = True if u_name_in.strip().lower() == "ajay" else u_adm_in
                    upsert_user_account(u_name_in, u_pass_in, u_role_in, final_adm, u_av_in)
                    st.success(f"✅ '{u_name_in}' का अकाउंट अपडेट हो गया!")
                    st.rerun()

# Keep-Awake Subtle Heartbeat so browser tab keeps session active
components.html(
    """
    <script>
    setInterval(function() {
        const dt = new Date();
        console.log("Parivaar VIP 5.0 Keep-Alive Heartbeat: " + dt.toISOString());
    }, 45000);
    </script>
    """,
    height=0,
)
