import os
import io
import json
import sqlite3
import hashlib
import urllib.parse
from datetime import datetime, date
import calendar

import streamlit as st
import pandas as pd
import plotly.express as px
import qrcode

# Optional SQLAlchemy for Cloud PostgreSQL (Supabase/Neon)
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
# 1. PAGE SETUP & CRASH-PROOF CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="Ajay, Meenakshi & Ajeet | Parivaar VIP",
    page_icon="🏡",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ==============================================================================
# 2. FAMILY CONSTANTS & USERS (AJAY, MEENAKSHI, AJEET)
# ==============================================================================
PRIMARY_INCOME = 23000   # Ajay's Income
SPOUSE_INCOME = 15000    # Meenakshi's Income
TOTAL_POOL = PRIMARY_INCOME + SPOUSE_INCOME  # ₹38,000 Total
STRICT_SAVINGS_TARGET = 15000                # ₹15,000 Separate Dream House + Medical Vault
MAX_SPENDING_BUDGET = TOTAL_POOL - STRICT_SAVINGS_TARGET  # ₹23,000 Max Spending

# Monthly Category Caps
CAP_FOOD = 7000
CAP_RENT = 6000
CAP_HOME_MIN = 5000
CAP_HOME_MAX = 7000
CAP_MEDICAL_EAR = 3000
PSYCHOLOGY_DAILY_REWARD_LIMIT = 200.0  # Spend under ₹200/day triggers huge dopamine reward

USERS_DB = {
    "Ajay": {
        "pin": "1234",
        "role": "Primary Earner (₹23,000/mo)",
        "avatar": "👨‍💻",
    },
    "Meenakshi": {
        "pin": "2345",
        "role": "Partner Earner (₹15,000/mo)",
        "avatar": "👩‍💼",
    },
    "Ajeet": {
        "pin": "3456",
        "role": "Brother & Family Pillar",
        "avatar": "🧑‍🎓",
    },
}

# Simple, Relatable Categories & Smart Descriptions
CATEGORY_DESCRIPTIONS = {
    "Food & Mess (खाना और टिफिन)": [
        "सुबह की चाय / बिस्किट (Morning Tea)",
        "ऑफिस लंच / टिफिन (Office Lunch)",
        "दूध, दही और ब्रेड (Milk & Curd)",
        "महीने का मेस / राशन बिल (Mess/Ration)",
        "शाम का समोसा / बाहर का नाश्ता (Avoid!)",
        "कोल्ड ड्रिंक / जंक फूड / मोमोज (Bad Expense!)",
        "अन्य खाने का खर्च (Custom Food Item)...",
    ],
    "Sabzi & Kirana (सब्ज़ी और राशन)": [
        "रोज़ की हरी सब्ज़ी (आलू, प्याज, भिंडी, टमाटर)",
        "आटा, चावल, दाल और तेल (Monthly Grocery)",
        "मसाले, नमक और रसोई का सामान",
        "रसोई गैस सिलेंडर (LPG Refill)",
        "अन्य किराना सामान (Custom Grocery)...",
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
        "मेट्रो कार्ड रिचार्ज / बस टिकट (Metro/Bus)",
        "शेयरिंग ई-रिक्शा / ऑटो (Necessary Auto)",
        "अकेले रिज़र्व ऑटो / कैब (फालतू खर्च - Avoid!)",
        "पेट्रोल / गाड़ी मेंटेनेंस",
        "अन्य ट्रैवल खर्च...",
    ],
    "Mobile & Wi-Fi (रिचार्ज और इंटरनेट)": [
        "मोबाइल रिचार्ज (Jio / Airtel)",
        "पढ़ाई के लिए Wi-Fi / ब्रॉडबैंड बिल",
        "अन्य बिल...",
    ],
    "Padhai & Tech (Python / Excel / Career)": [
        "Python / Data Engineering कोर्स या किताब",
        "फॉर्म फीस / सर्टिफिकेट",
        "कॉपी, पेन और पढ़ाई का सामान",
        "अन्य पढ़ाई खर्च...",
    ],
    "Faltu / Bad Expense (गैर-ज़रूरी खर्च)": [
        "बिना सोचे-समझे ऑटो / कैब किया (Unplanned Ride)",
        "बाहर का महंगा फास्ट फूड / पिज़्ज़ा / बर्गर",
        "ऑनलाइन फालतू शॉपिंग (Impulse Buy)",
        "अन्य गैर-ज़रूरी खर्च...",
    ],
    "Other Zaroori Kharch (अन्य ज़रूरी)": [
        "बाल कटवाना / साबुन / तेल (Daily Use)",
        "घर का छोटा-मोटा ज़रूरी सामान",
        "अन्य ज़रूरी खर्च...",
    ],
}

# ==============================================================================
# 3. 4 ULTRA-MODERN VIP THEMES + HIGH-CONTRAST TEXT FIX
# ==============================================================================
THEMES = {
    "👑 Royal Gold & Obsidian (महाराजा गोल्ड)": {
        "bg_main": "radial-gradient(circle at top, #1a1608 0%, #07090e 100%)",
        "card_bg": "#111827",
        "card_border": "#f59e0b",
        "accent": "#fbbf24",
        "accent_secondary": "#10b981",
        "text_bright": "#ffffff",
        "text_sub": "#fde68a",
        "banner_grad": "linear-gradient(135deg, #451a03 0%, #111827 65%, #064e3b 100%)",
    },
    "⚡ Cyber Emerald (पैसा और तरक्की ग्रीन)": {
        "bg_main": "radial-gradient(circle at top, #042f2e 0%, #060913 100%)",
        "card_bg": "#0f172a",
        "card_border": "#00ff9d",
        "accent": "#00ff9d",
        "accent_secondary": "#38bdf8",
        "text_bright": "#ffffff",
        "text_sub": "#a7f3d0",
        "banner_grad": "linear-gradient(135deg, #064e3b 0%, #0f172a 65%, #1e1b4b 100%)",
    },
    "🌊 Deep Ocean Sapphire (शांत और फोकस ब्लू)": {
        "bg_main": "radial-gradient(circle at top, #0c192c 0%, #050811 100%)",
        "card_bg": "#0f172a",
        "card_border": "#38bdf8",
        "accent": "#38bdf8",
        "accent_secondary": "#a855f7",
        "text_bright": "#ffffff",
        "text_sub": "#bae6fd",
        "banner_grad": "linear-gradient(135deg, #0c4a6e 0%, #0f172a 65%, #311042 100%)",
    },
    "🔥 Agni Hustle (जोश और जूनून रेड-गोल्ड)": {
        "bg_main": "radial-gradient(circle at top, #2a0a12 0%, #08070c 100%)",
        "card_bg": "#181018",
        "card_border": "#f97316",
        "accent": "#fb923c",
        "accent_secondary": "#facc15",
        "text_bright": "#ffffff",
        "text_sub": "#fed7aa",
        "banner_grad": "linear-gradient(135deg, #431407 0%, #181018 65%, #3b0764 100%)",
    },
}

if "selected_theme" not in st.session_state:
    st.session_state.selected_theme = "👑 Royal Gold & Obsidian (महाराजा गोल्ड)"


def apply_vip_theme(theme_name: str):
    t = THEMES.get(theme_name, THEMES["👑 Royal Gold & Obsidian (महाराजा गोल्ड)"])
    st.markdown(
        f"""
        <style>
        /* Force Dark High-Contrast Background & 100% Visible Text Everywhere */
        .stApp {{
            background: {t['bg_main']} !important;
            color: {t['text_bright']} !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }}
        .block-container {{
            padding-top: 1rem !important;
            padding-bottom: 4.5rem !important;
            max-width: 740px !important;
        }}

        /* Fix ALL Hidden / Low-Contrast Labels in Streamlit */
        label, .stWidgetLabel, .stMarkdown p, .stMarkdown li, .stCaption, span, h1, h2, h3, h4, h5, h6 {{
            color: {t['text_bright']} !important;
        }}
        .stCaption {{
            color: {t['text_sub']} !important;
            font-size: 0.85rem !important;
        }}

        /* Fix Input Boxes, Number Inputs & Dropdown Selectboxes so text NEVER hides */
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
        /* Dropdown menu options list */
        ul[data-baseweb="menu"],
        div[data-baseweb="popover"] div,
        li[role="option"] {{
            background-color: #0f172a !important;
            color: #ffffff !important;
            font-weight: 600 !important;
        }}
        li[role="option"]:hover {{
            background-color: {t['card_border']} !important;
            color: #000000 !important;
        }}

        /* Fix Metric Cards Visibility */
        div[data-testid="stMetric"] {{
            background-color: {t['card_bg']} !important;
            border: 1px solid {t['card_border']} !important;
            border-radius: 14px !important;
            padding: 12px 14px !important;
            box-shadow: 0 4px 14px rgba(0,0,0,0.4) !important;
        }}
        div[data-testid="stMetricLabel"] p,
        div[data-testid="stMetricLabel"] {{
            color: {t['text_sub']} !important;
            font-weight: 700 !important;
            font-size: 0.85rem !important;
        }}
        div[data-testid="stMetricValue"] div,
        div[data-testid="stMetricValue"] {{
            color: {t['accent']} !important;
            font-weight: 800 !important;
            font-size: 1.4rem !important;
        }}

        /* Fix Tabs Visibility on Mobile */
        button[data-baseweb="tab"] {{
            background-color: #1e293b !important;
            color: #cbd5e1 !important;
            border-radius: 10px 10px 0 0 !important;
            padding: 8px 12px !important;
            margin-right: 4px !important;
            font-weight: 700 !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            background-color: {t['accent']} !important;
            color: #020617 !important;
            font-weight: 800 !important;
        }}
        button[data-baseweb="tab"][aria-selected="true"] p {{
            color: #020617 !important;
            font-weight: 800 !important;
        }}

        /* Top Daily Motivation Banner */
        .motivation-banner {{
            background: {t['banner_grad']};
            border: 2px solid {t['accent']};
            border-left: 8px solid {t['accent']};
            border-radius: 16px;
            padding: 15px 18px;
            margin-bottom: 14px;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.45);
        }}
        .motivation-day-tag {{
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: {t['accent']};
            font-weight: 800;
            margin-bottom: 5px;
        }}
        .motivation-quote {{
            font-size: 1.04rem;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.5;
        }}
        .motivation-sub {{
            font-size: 0.85rem;
            color: {t['text_sub']};
            margin-top: 8px;
            font-weight: 600;
        }}

        /* Psychology Dopamine Celebration Banner (< ₹200 Daily Spend) */
        .psych-reward-banner {{
            background: linear-gradient(135deg, #065f46 0%, #047857 50%, #064e3b 100%);
            border: 2px solid #34d399;
            border-radius: 16px;
            padding: 14px 16px;
            margin-bottom: 14px;
            color: #ffffff;
            box-shadow: 0 0 22px rgba(52, 211, 153, 0.28);
        }}

        /* VIP Cards */
        .vip-card {{
            background: {t['card_bg']};
            border: 1px solid {t['card_border']};
            border-radius: 16px;
            padding: 16px;
            margin-bottom: 14px;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
        }}

        /* Flashing Red Alert Banner */
        @keyframes pulseRed {{
            0% {{ box-shadow: 0 0 0 0 rgba(255, 51, 102, 0.7); border-color: #ff3366; }}
            70% {{ box-shadow: 0 0 0 12px rgba(255, 51, 102, 0); border-color: #fda4af; }}
            100% {{ box-shadow: 0 0 0 0 rgba(255, 51, 102, 0); border-color: #ff3366; }}
        }}
        .red-alert-banner {{
            background: linear-gradient(135deg, #7f1d1d 0%, #31102f 100%);
            border: 2px solid #ff3366;
            border-radius: 14px;
            padding: 14px 16px;
            margin-bottom: 14px;
            color: #ffffff;
            font-weight: 700;
            animation: pulseRed 1.8s infinite;
        }}

        /* UPI App Launch Buttons */
        .upi-app-btn {{
            display: block;
            width: 100%;
            text-align: center;
            background: linear-gradient(90deg, #00ff9d 0%, #10b981 100%);
            color: #022c22 !important;
            font-weight: 900;
            font-size: 1.08rem;
            padding: 15px 16px;
            border-radius: 14px;
            text-decoration: none !important;
            margin: 8px 0;
            box-shadow: 0 6px 20px rgba(0, 255, 157, 0.35);
            border: 2px solid #ffffff;
        }}
        .upi-scanner-btn {{
            display: block;
            width: 100%;
            text-align: center;
            background: linear-gradient(90deg, #fbbf24 0%, #f59e0b 100%);
            color: #090d16 !important;
            font-weight: 900;
            font-size: 1.02rem;
            padding: 14px 16px;
            border-radius: 14px;
            text-decoration: none !important;
            margin: 8px 0;
            box-shadow: 0 6px 20px rgba(251, 191, 36, 0.3);
            border: 2px solid #ffffff;
        }}

        /* Touch-friendly Streamlit Buttons */
        div.stButton > button, div.stFormSubmitButton > button {{
            width: 100%;
            border-radius: 12px !important;
            min-height: 48px !important;
            font-weight: 800 !important;
            font-size: 1rem !important;
            border: 2px solid {t['accent']} !important;
            background-color: #1e293b !important;
            color: #ffffff !important;
        }}
        div.stButton > button:hover, div.stFormSubmitButton > button:hover {{
            background-color: {t['accent']} !important;
            color: #020617 !important;
        }}
        div.stButton > button:hover p, div.stFormSubmitButton > button:hover p {{
            color: #020617 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ==============================================================================
# 4. 10-YEAR PSYCHOLOGY-DRIVEN DAILY MOTIVATION ENGINE (NEVER REPEATS)
# ==============================================================================
def get_psychology_daily_motivation(current_savings: float = 0):
    """
    Uses Behavioral Psychology (Future Self Visualization, Pride of Family, Loss Aversion,
    and Small Wins) to generate unique daily guidance for 10+ years (3,650+ days).
    """
    anchor_date = date(2025, 1, 1)
    today = date.today()
    day_index = max(1, (today - anchor_date).days + 1)

    psych_triggers = [
        "🧠 मनोवैज्ञानिक सच (Future Self Power):",
        "🏡 अपने पक्के घर का सपना (Dream House Vision):",
        "👨‍👩‍👦 अजय, मीनाक्षी और अजीत की एकता:",
        "🛡️ ₹15,000 सुरक्षा कवच (No-Compromise Rule):",
        "🚀 ₹23,000 से ₹1,00,000/महीना का सफर:",
        "💎 मिडिल-क्लास की असली ताकत (Iron Discipline):",
        "🧱 एक-एक ईंट का हिसाब (Brick Psychology):",
        "👑 माता-पिता का गर्व (Family Pride):",
        "⚡ 10-सेकंड का नियम (Impulse Control):",
        "🎯 विजेता की आदत (Daily Winner Mindset):",
    ]

    deep_messages = [
        "जब भी बाहर कुछ फालतू खाने या अकेले ऑटो करने का मन करे, तो अपनी आँखें बंद करके उस दिन को देखो जब आपके अपने घर के बाहर 'रावत निवास' की नेमप्लेट लगेगी। आज का बचाया ₹100 उसी नेमप्लेट की कीमत है!",
        "अजय की मेहनत, मीनाक्षी का साथ और अजीत की समझदारी—जब परिवार के तीनों स्तंभ एक साथ ₹15,000 हर महीने अलग रखते हैं, तो दुनिया की कोई ताकत आपको आगे बढ़ने से नहीं रोक सकती।",
        "दिमाग का नियम है: जो खर्च लिख दिया जाता है, वह अपने-आप 30% कम हो जाता है। पेमेंट करने से पहले इस ऐप में एंट्री करना आपकी सबसे बड़ी जीत है!",
        "कान का पूरा इलाज (Ear Treatment) और माता-पिता की खुशी किसी भी दिखावे से बड़ी है। आज का दिन बिना एक भी फालतू खर्च (₹0 Bad Expense) के पूरा करके दिखाओ!",
        "गरीबी तब तक रहती है जब तक हम समय और पैसे को बिना हिसाब के खर्च करते हैं। रोज़ 45 मिनट Python, SQL और Excel की पढ़ाई आपको कुछ ही महीनों में बड़ी सैलरी दिलाएगी!",
        "बाहर का ₹100 का जंक फूड सिर्फ 5 मिनट जीभ को अच्छा लगता है, लेकिन घर की बनी ₹30 की तहरी या भिंडी-रोटी सेहत भी देती है और आपके घर की 2 नई ईंटें भी जोड़ती है!",
        "अमीर दिखने की कोशिश मत करो, सच में मजबूत बनो। जिस परिवार के पास अलग से हर महीने ₹15,000 की बचत जुड़ती है, उसे कभी किसी के सामने झुकना नहीं पड़ता।",
        "आज का लक्ष्य बिल्कुल साफ है: अगर आज पूरे दिन का खर्च ₹200 से कम रखा, तो आज रात आप एक विजेता की तरह सोएंगे!",
        "जब थकान लगे और पढ़ने का मन न करे, तो याद करना कि यह Python और Excel की पढ़ाई सिर्फ कोड नहीं है—यह आपके पूरे परिवार की ज़िंदगी बदलने की चाबी है।",
        "छोटी बचत से कभी शर्म मत करना। ₹20 की चाय-समोसा बचाना कंजूसी नहीं है, अपने सपनों के घर की नींव को मजबूत करना है!",
        "हर बार जब आप GPay या PhonePe खोलने से पहले यहाँ खर्च लिखते हैं, आप अपने दिमाग को ट्रेनिंग दे रहे हैं कि पैसा आपका गुलाम है, आप पैसे के गुलाम नहीं!",
        "सफलता एक झटके में नहीं मिलती, बल्कि रोज़ ₹50–₹100 फालतू खर्च से बचाने और रोज़ 1 नया Tech Skill सीखने से मिलती है।",
    ]

    action_nudges = [
        "🎯 आज का मनोवैज्ञानिक टारगेट: आज का कुल खर्च ₹200 से नीचे रखकर 'Green Champion Badge' हासिल करें!",
        "🎯 आज का टारगेट: आज बाहर का जंक फूड ₹0 रहेगा और शाम को 30 मिनट Python/Excel की क्लास पूरी होगी।",
        "🎯 आज का टारगेट: कोई भी पेमेंट बिना इस ऐप में दर्ज किए नहीं किया जाएगा।",
        "🎯 आज का टारगेट: आज आने-जाने में मेट्रो/बस या शेयरिंग का ही इस्तेमाल करें और अपने घर की 2 ईंटें बचाएं।",
    ]

    t_idx = day_index % len(psych_triggers)
    m_idx = (day_index * 5 + (day_index // len(deep_messages))) % len(deep_messages)
    a_idx = (day_index * 3) % len(action_nudges)

    return {
        "day_number": day_index,
        "date_str": today.strftime("%d %b %Y"),
        "headline": f"{psych_triggers[t_idx]} (Day #{day_index} of 3,650)",
        "quote": deep_messages[m_idx],
        "action": action_nudges[a_idx],
    }


# ==============================================================================
# 5. CRASH-PROOF DATABASE ENGINE (SQLITE WAL + AUTO-MIGRATION + CLOUD POSTGRES)
# ==============================================================================
DB_FILE = "parivaar_vip_v2.db"


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
    """Creates tables and safely migrates columns so the app never crashes."""
    engine = get_db_engine()
    if engine:
        with engine.begin() as conn:
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
                    CREATE TABLE IF NOT EXISTS career_progress (
                        skill_key TEXT PRIMARY KEY,
                        completed INTEGER DEFAULT 0,
                        updated_at TEXT
                    );
                    """
                )
            )
    else:
        conn = get_sqlite_conn()
        c = conn.cursor()
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
        # Safe column migration in case an older database file exists
        existing_cols = [row[1] for row in c.execute("PRAGMA table_info(expenses)").fetchall()]
        if "date_only" not in existing_cols:
            c.execute("ALTER TABLE expenses ADD COLUMN date_only TEXT DEFAULT '';")
        if "upi_app" not in existing_cols:
            c.execute("ALTER TABLE expenses ADD COLUMN upi_app TEXT DEFAULT 'Google Pay (GPay)';")

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


init_db()


def add_expense_to_db(
    logged_by,
    spent_by,
    category,
    item_name,
    description,
    payment_mode,
    upi_app,
    need_level,
    amount,
    is_bad_expense,
    upi_id,
    notes,
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
                    "ts": now_str,
                    "do": date_only,
                    "my": month_year,
                    "lb": logged_by,
                    "sb": spent_by,
                    "cat": category,
                    "item": item_name,
                    "desc": description,
                    "pm": payment_mode,
                    "ua": upi_app,
                    "nl": need_level,
                    "amt": float(amount),
                    "bad": bad_int,
                    "upi": upi_id,
                    "notes": notes,
                },
            )
    else:
        conn = get_sqlite_conn()
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO expenses (
                timestamp, date_only, month_year, logged_by, spent_by, category,
                item_name, description, payment_mode, upi_app, need_level,
                amount, is_bad_expense, upi_id, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now_str,
                date_only,
                month_year,
                logged_by,
                spent_by,
                category,
                item_name,
                description,
                payment_mode,
                upi_app,
                need_level,
                float(amount),
                bad_int,
                upi_id,
                notes,
            ),
        )
        conn.commit()
        conn.close()


def fetch_expenses_df(month_year: str = None) -> pd.DataFrame:
    try:
        engine = get_db_engine()
        if engine:
            with engine.connect() as conn:
                if month_year:
                    return pd.read_sql(
                        text("SELECT * FROM expenses WHERE month_year = :my ORDER BY id DESC"),
                        conn,
                        params={"my": month_year},
                    )
                return pd.read_sql(text("SELECT * FROM expenses ORDER BY id DESC"), conn)
        else:
            conn = get_sqlite_conn()
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
    except Exception:
        return pd.DataFrame()


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
        conn = get_sqlite_conn()
        conn.execute(
            """
            INSERT INTO vault_deposits (timestamp, month_year, deposited_by, vault_bucket, amount, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (now_str, month_year, deposited_by, vault_bucket, float(amount), notes),
        )
        conn.commit()
        conn.close()


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
                df = pd.read_sql_query(
                    "SELECT * FROM vault_deposits WHERE month_year = ? ORDER BY id DESC",
                    conn,
                    params=(month_year,),
                )
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


# ==============================================================================
# 6. MULTI-APP UPI ENGINE (GPAY / PHONEPE / PAYTM / BHIM) - 100% RELIABLE
# ==============================================================================
def generate_upi_links_and_qr(upi_id: str, payee_name: str, amount: float, note: str):
    """
    Generates:
    1. Direct App Launchers (Opens GPay, PhonePe, Paytm directly so user can scan any shop QR or pay a contact)
    2. Pre-filled UPI Intent URLs (when the shopkeeper's real UPI ID is known)
    3. QR Code
    """
    clean_upi = (upi_id or "").strip()
    has_real_upi = "@" in clean_upi and len(clean_upi) >= 5

    # Direct App Openers (Android Intent + URI Schemes) - Works even WITHOUT receiver UPI ID!
    direct_openers = {
        "Google Pay (GPay)": "intent://upi/#Intent;scheme=tez;package=com.google.android.apps.nbu.paisa.user;end",
        "PhonePe": "intent://#Intent;scheme=phonepe;package=com.phonepe.app;end",
        "Paytm": "intent://#Intent;scheme=paytmmp;package=net.one97.paytm;end",
        "BHIM / Any UPI App": "upi://pay",
    }

    if has_real_upi:
        params = {
            "pa": clean_upi,
            "pn": (payee_name or "Shop")[:20],
            "am": f"{float(amount):.2f}",
            "cu": "INR",
            "tn": (note or "Payment")[:35],
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
        qr_data = f"Amount: INR {float(amount):.2f} | Note: {note}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=7,
        border=2,
    )
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


# ==============================================================================
# 7. NEVER-LOGOUT AUTHENTICATION SYSTEM (QUERY PARAM + TOKEN AUTO-RESTORE)
# ==============================================================================
def make_auth_token(username: str) -> str:
    pin = USERS_DB.get(username, {}).get("pin", "")
    raw = f"parivaar_vip_{username}_{pin}_permanent"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

# Auto-restore login from URL query parameters so page refresh / sleep NEVER logs out!
if not st.session_state.authenticated_user:
    qp_user = st.query_params.get("u", "")
    qp_tok = st.query_params.get("t", "")
    if qp_user in USERS_DB and qp_tok == make_auth_token(qp_user):
        st.session_state.authenticated_user = qp_user

# Apply currently selected VIP Theme
apply_vip_theme(st.session_state.selected_theme)


def render_login_screen():
    mot = get_psychology_daily_motivation()
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
            <h2 style="margin-bottom:4px; color:#fbbf24;">🏡 अजय, मीनाक्षी और अजीत — Parivaar VIP</h2>
            <p style="font-size:0.95rem; margin-top:4px;">
                कुल आय: <b>₹38,000</b> • अलग बचत तिजोरी (Dream House + Ear Medical): <b>₹15,000</b> • अधिकतम खर्च बजट: <b>₹23,000</b>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("permanent_login_form"):
        selected_user = st.selectbox(
            "👤 अपना नाम चुनें (Select Family Member)",
            options=list(USERS_DB.keys()),
            format_func=lambda u: f"{USERS_DB[u]['avatar']} {u} — {USERS_DB[u]['role']}",
        )
        pin_input = st.text_input(
            "🔑 4-अंकों का PIN डालें (Ajay: 1234 | Meenakshi: 2345 | Ajeet: 3456)",
            type="password",
            placeholder="अपना 4-डिजिट पिन लिखें...",
        )
        remember_me = st.checkbox(
            "✅ इस फोन पर हमेशा लॉगिन रखें (Never Logout on Refresh/Sleep)",
            value=True,
        )
        login_btn = st.form_submit_button("🔓 ऐप खोलें (Unlock VIP App)")

        if login_btn:
            if pin_input.strip() == USERS_DB[selected_user]["pin"]:
                st.session_state.authenticated_user = selected_user
                if remember_me:
                    st.query_params["u"] = selected_user
                    st.query_params["t"] = make_auth_token(selected_user)
                st.rerun()
            else:
                st.error("❌ गलत PIN! सही PIN: Ajay = 1234 | Meenakshi = 2345 | Ajeet = 3456")


if not st.session_state.authenticated_user:
    render_login_screen()
    st.stop()


# ==============================================================================
# 8. LOAD LIVE METRICS & PSYCHOLOGY ENGINE FOR LOGGED-IN FAMILY MEMBER
# ==============================================================================
current_user = st.session_state.authenticated_user
today_str = date.today().strftime("%Y-%m-%d")
current_month_str = datetime.now().strftime("%Y-%m")

df_month = fetch_expenses_df(current_month_str)
df_all_vault = fetch_vault_df()
df_month_vault = fetch_vault_df(current_month_str)

# Calculate Today's & This Month's Spending
if not df_month.empty:
    total_spent_month = float(df_month["amount"].sum())
    # Filter today's spend safely
    df_today = df_month[df_month["timestamp"].str.startswith(today_str, na=False)]
    spent_today = float(df_today["amount"].sum()) if not df_today.empty else 0.0
    bad_spent_month = float(df_month[df_month["is_bad_expense"] == 1]["amount"].sum())
    food_spent_month = float(
        df_month[df_month["category"].str.startswith("Food", na=False)]["amount"].sum()
    )
    rent_spent_month = float(
        df_month[df_month["category"].str.startswith("Room Rent", na=False)]["amount"].sum()
    )
    home_transfer_month = float(
        df_month[df_month["category"].str.startswith("Home Transfer", na=False)]["amount"].sum()
    )
    ear_medical_month = float(
        df_month[df_month["category"].str.startswith("Ear Medical", na=False)]["amount"].sum()
    )
else:
    total_spent_month = 0.0
    spent_today = 0.0
    bad_spent_month = 0.0
    food_spent_month = 0.0
    rent_spent_month = 0.0
    home_transfer_month = 0.0
    ear_medical_month = 0.0

vault_saved_this_month = float(df_month_vault["amount"].sum()) if not df_month_vault.empty else 0.0
vault_saved_all_time = float(df_all_vault["amount"].sum()) if not df_all_vault.empty else 0.0

# Daily Safe Spend Calculation
today_obj = date.today()
days_in_month = calendar.monthrange(today_obj.year, today_obj.month)[1]
days_left = max(1, days_in_month - today_obj.day + 1)
remaining_monthly_budget = max(0.0, MAX_SPENDING_BUDGET - total_spent_month)
daily_safe_limit = remaining_monthly_budget / days_left

# Top Bar: Theme Switcher + Active User + Logout
bar_c1, bar_c2, bar_c3 = st.columns([2.2, 1.5, 1])
with bar_c1:
    chosen_theme = st.selectbox(
        "🎨 ऐप की थीम बदलें (Choose VIP Theme)",
        options=list(THEMES.keys()),
        index=list(THEMES.keys()).index(st.session_state.selected_theme),
    )
    if chosen_theme != st.session_state.selected_theme:
        st.session_state.selected_theme = chosen_theme
        st.rerun()
with bar_c2:
    st.markdown(
        f"<div style='padding-top:26px; font-weight:800;'>{USERS_DB[current_user]['avatar']} {current_user} (Active)</div>",
        unsafe_allow_html=True,
    )
with bar_c3:
    st.markdown("<div style='padding-top:18px;'></div>", unsafe_allow_html=True)
    if st.button("🚪 बदलें"):
        st.session_state.authenticated_user = None
        st.query_params.clear()
        st.rerun()

# 1. TOP DAILY MOTIVATION BANNER (10-YEAR ENGINE)
mot_data = get_psychology_daily_motivation(current_savings=vault_saved_all_time)
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

# 2. PSYCHOLOGY REWARD / NUDGE NOTIFICATION (< ₹200 SPENT TODAY CELEBRATION!)
if spent_today <= PSYCHOLOGY_DAILY_REWARD_LIMIT:
    extra_saved_today = max(0.0, daily_safe_limit - spent_today)
    extra_bricks = max(1, int(extra_saved_today // 50))
    st.markdown(
        f"""
        <div class="psych-reward-banner">
            🏆 <b>बहुत बढ़िया {current_user}! सुपर अनुशासन (Daily Champion Reward):</b><br>
            आज आपका कुल खर्च सिर्फ <b>₹{spent_today:,.0f}</b> है (₹200 की लिमिट से कम)!
            आपने आज अपने <b>Dream House</b> और <b>कान के इलाज</b> के लिए <b>₹{extra_saved_today:,.0f} एक्स्ट्रा बचाए हैं</b>
            (यानी आज घर की <b>+{extra_bricks} नई ईंटें 🧱</b> पक्की कर लीं)! इसे ऐसे ही बनाए रखें!
        </div>
        """,
        unsafe_allow_html=True,
    )
elif spent_today <= daily_safe_limit:
    st.markdown(
        f"""
        <div class="vip-card" style="border-left:6px solid #38bdf8;">
            ⚡ <b>आज का खर्च नियंत्रण में है:</b> आज आपने <b>₹{spent_today:,.0f}</b> खर्च किए हैं।
            आज की सुरक्षित सीमा <b>₹{daily_safe_limit:,.0f}</b> है। अब आज कोई भी गैर-ज़रूरी खर्च न करें!
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    over_today = spent_today - daily_safe_limit
    st.markdown(
        f"""
        <div class="red-alert-banner">
            🛑 <b>मनोवैज्ञानिक चेतावनी (Today's Limit Crossed!):</b>
            आज का खर्च <b>₹{spent_today:,.0f}</b> हो चुका है, जो आज की सुरक्षित सीमा (₹{daily_safe_limit:,.0f}) से <b>₹{over_today:,.0f} ज़्यादा</b> है!
            कृपया आज के लिए बटुआ और UPI लॉक कर दें ताकि ₹15,000 की बचत सुरक्षित रहे।
        </div>
        """,
        unsafe_allow_html=True,
    )

# 3. FOOD > 80% AND BAD EXPENSE FLASHING ALERTS
if food_spent_month >= 0.8 * CAP_FOOD:
    st.markdown(
        f"""
        <div class="red-alert-banner">
            🚨 <b>FOOD BUDGET 80%+ ALERT:</b> खाने का खर्च <b>₹{food_spent_month:,.0f} / ₹{CAP_FOOD:,}</b> हो गया है!
            बाहर की चाय, समोसा और स्नैक्स तुरंत बंद करें—सिर्फ घर का बना खाना खाएं!
        </div>
        """,
        unsafe_allow_html=True,
    )

if bad_spent_month > 0:
    lost_bricks = max(1, int(bad_spent_month // 50))
    st.markdown(
        f"""
        <div class="red-alert-banner">
            ⚠️ <b>फालतू खर्च अलर्ट (Bad Expenses):</b> इस महीने <b>₹{bad_spent_month:,.0f}</b> फालतू चीजों (कैब/जंक फूड) में गए हैं।
            इसका मतलब आपके सपनों के घर की <b>{lost_bricks} ईंटें (🧱)</b> कम हो गईं!
        </div>
        """,
        unsafe_allow_html=True,
    )

# ==============================================================================
# 9. MAIN MOBILE NAVIGATION TABS
# ==============================================================================
tab_pay, tab_vault, tab_ledger, tab_learn, tab_analytics = st.tabs(
    [
        "💳 पेमेंट और UPI",
        "🏡 ₹15K घर तिजोरी",
        "📋 खर्च का हिसाब",
        "🎓 पढ़ाई, खाना और सर्च",
        "🧠 रिपोर्ट और सलाह",
    ]
)

# ==============================================================================
# TAB 1: PRE-PAYMENT LOGGER + WORKING GPAY / PHONEPE / PAYTM LAUNCHER
# ==============================================================================
with tab_pay:
    st.markdown(
        """
        <div class="vip-card">
            <h4 style="margin:0; color:#00ff9d;">⚡ नियम #1: पहले यहाँ एंट्री करें, फिर GPay / PhonePe / Paytm से पेमेंट करें</h4>
            <p style="margin:5px 0 0 0; font-size:0.88rem;">
                नीचे खर्च का विवरण चुनें। जैसे ही आप सेव करेंगे, आपका पसंदीदा UPI ऐप (GPay / PhonePe / Paytm) तुरंत खुलने के लिए तैयार हो जाएगा!
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1-Tap Quick Presets for Fast Mobile Entry
    st.caption("⚡ **1-Tap तेज़ एंट्री बटन (दबाते ही अपने-आप भर जाएगा):**")
    q1, q2, q3, q4 = st.columns(4)
    if q1.button("☕ ₹15 चाय"):
        st.session_state.qf_cat = "Food & Mess (खाना और टिफिन)"
        st.session_state.qf_amt = 15.0
        st.session_state.qf_desc = "सुबह की चाय / बिस्किट (Morning Tea)"
    if q2.button("🚇 ₹40 मेट्रो"):
        st.session_state.qf_cat = "Metro, Bus & Auto (आना-जाना)"
        st.session_state.qf_amt = 40.0
        st.session_state.qf_desc = "मेट्रो कार्ड रिचार्ज / बस टिकट (Metro/Bus)"
    if q3.button("🥛 ₹66 दूध"):
        st.session_state.qf_cat = "Food & Mess (खाना और टिफिन)"
        st.session_state.qf_amt = 66.0
        st.session_state.qf_desc = "दूध, दही और ब्रेड (Milk & Curd)"
    if q4.button("🥦 ₹80 सब्ज़ी"):
        st.session_state.qf_cat = "Sabzi & Kirana (सब्ज़ी और राशन)"
        st.session_state.qf_amt = 80.0
        st.session_state.qf_desc = "रोज़ की हरी सब्ज़ी (आलू, प्याज, भिंडी, टमाटर)"

    # Dynamic Dropdowns (Outside form so Category immediately updates Description options)
    cat_list = list(CATEGORY_DESCRIPTIONS.keys())
    default_cat = st.session_state.get("qf_cat", cat_list[0])
    cat_idx = cat_list.index(default_cat) if default_cat in cat_list else 0

    c_who, c_cat = st.columns(2)
    with c_who:
        spent_by_list = ["Ajay", "Meenakshi", "Ajeet", "Joint Family (पूरा परिवार)"]
        def_who_idx = spent_by_list.index(current_user) if current_user in spent_by_list else 0
        spent_by_val = st.selectbox(
            "👤 किसने खर्च किया? (Spent By)",
            options=spent_by_list,
            index=def_who_idx,
        )
    with c_cat:
        selected_category = st.selectbox(
            "📂 खर्च की श्रेणी (Expense Category)",
            options=cat_list,
            index=cat_idx,
        )

    desc_list = CATEGORY_DESCRIPTIONS.get(selected_category, ["अन्य खर्च..."])
    default_desc = st.session_state.get("qf_desc", desc_list[0])
    desc_idx = desc_list.index(default_desc) if default_desc in desc_list else 0

    c_desc, c_app = st.columns(2)
    with c_desc:
        selected_desc = st.selectbox(
            "📝 विवरण चुनें (Description Dropdown)",
            options=desc_list,
            index=desc_idx,
        )
    with c_app:
        selected_upi_app = st.selectbox(
            "📲 पेमेंट ऐप चुनें (Choose UPI App / Cash)",
            options=[
                "Google Pay (GPay)",
                "PhonePe",
                "Paytm",
                "BHIM / Any UPI App",
                "Cash (नकद पेमेंट)",
                "Bank Transfer / Debit Card",
            ],
        )

    auto_bad = (
        "Faltu" in selected_category
        or "Bad" in selected_desc
        or "Avoid" in selected_desc
    )

    with st.form("upi_pre_pay_form", clear_on_submit=False):
        fc1, fc2 = st.columns([1.4, 1])
        with fc1:
            custom_item = st.text_input(
                "🏷️ सामान का नाम (चाहें तो बदलें)",
                value="" if "Custom" in selected_desc or "अन्य" in selected_desc else selected_desc,
                placeholder="जैसे: 1 किलो आलू + भिंडी / ऑटो किराया",
            )
        with fc2:
            amount_val = st.number_input(
                "₹ रकम (Amount in INR)",
                min_value=1.0,
                max_value=100000.0,
                value=float(st.session_state.get("qf_amt", 50.0)),
                step=10.0,
            )

        p_col1, p_col2 = st.columns(2)
        with p_col1:
            need_level_val = st.selectbox(
                "⚖️ यह खर्च कितना ज़रूरी है?",
                options=[
                    "बहुत ज़रूरी (Essential)",
                    "कान का इलाज (Ear Medical Priority)",
                    "माता-पिता / घर की जिम्मेदारी",
                    "पढ़ाई और करियर (Python/Excel)",
                    "गैर-ज़रूरी / फालतू खर्च (Bad Expense)",
                ],
                index=4 if auto_bad else (1 if "Ear" in selected_category else 0),
            )
        with p_col2:
            upi_id_input = st.text_input(
                "🆔 दुकानदार की UPI ID (पता हो तो डालें, वरना खाली छोड़ें)",
                value="",
                placeholder="उदा: 9876543210@ybl (खाली छोड़ने पर स्कैनर खुलेगा)",
            )

        is_bad_chk = st.checkbox(
            "🚨 क्या यह गैर-ज़रूरी / फालतू खर्च (Bad Expense) है? (जैसे जंक फूड, अकेले ऑटो/कैब)",
            value=auto_bad,
        )

        notes_val = st.text_input(
            "📌 कोई खास नोट (Optional)",
            placeholder="जैसे: 2 दिन की सब्ज़ी / डॉक्टर की दवाई",
        )

        # Psychology Loss-Aversion Frame inside Form
        bricks_eq = max(1, int(amount_val // 50))
        days_sabzi_eq = round(amount_val / 80, 1)
        st.info(
            f"🧠 **सोचकर खर्च करें:** `₹{amount_val:,.0f}` का मतलब आपके सपनों के घर की **{bricks_eq} ईंटें (🧱)** या **{days_sabzi_eq} दिन की घर की हरी सब्ज़ी** है।"
        )

        submit_tx = st.form_submit_button("✅ हिसाब सेव करें और पेमेंट बटन खोलें")

        if submit_tx:
            final_item_name = custom_item.strip() or selected_desc
            final_is_bad = bool(
                is_bad_chk
                or "Faltu" in selected_category
                or "गैर-ज़रूरी" in need_level_val
            )
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
                "time": datetime.now().strftime("%d %b %Y, %I:%M %p"),
            }
            st.rerun()

    # ==========================================================================
    # INSTANT UPI LAUNCHER BOX (GPAY / PHONEPE / PAYTM DIRECT & PRE-FILLED)
    # ==========================================================================
    if st.session_state.get("last_payment_receipt"):
        rec = st.session_state.last_payment_receipt
        st.markdown("---")
        st.success(
            f"✅ **हिसाब सेव हो गया!** ₹{rec['amount']:,.0f} — **{rec['item']}** (खर्च किया: `{rec['spent_by']}` | ऐप: `{rec['upi_app']}`)"
        )

        if "Cash" in rec["upi_app"] or "Bank" in rec["upi_app"]:
            st.info(f"💵 आपने **{rec['upi_app']}** चुना है। आपकी एंट्री सफलतापूर्वक रजिस्टर में जुड़ गई है!")
        else:
            upi_bundle = generate_upi_links_and_qr(
                upi_id=rec["upi_id"],
                payee_name=rec["item"],
                amount=rec["amount"],
                note=rec["item"],
            )
            chosen_app = rec["upi_app"]
            direct_app_url = upi_bundle["direct_openers"].get(chosen_app, "upi://pay")
            prefilled_url = upi_bundle["prefilled_links"].get(chosen_app, direct_app_url)

            st.markdown(
                f"""
                <div class="vip-card">
                    <h4 style="margin:0 0 8px 0; color:#fbbf24;">📲 {chosen_app} से तुरंत पेमेंट करें (Amount: ₹{rec['amount']:,.0f})</h4>
                """,
                unsafe_allow_html=True,
            )

            # If user entered a valid Receiver UPI ID, show the Pre-Filled Amount Deep Link first
            if upi_bundle["has_real_upi"]:
                st.markdown(
                    f"""
                    <a href="{prefilled_url}" class="upi-app-btn">
                        🚀 {chosen_app} में सीधे ₹{rec['amount']:,.0f} पेमेंट खोलें (UPI ID: {rec['upi_id']})
                    </a>
                    """,
                    unsafe_allow_html=True,
                )

            # ALWAYS show Direct App Openers so the user can open GPay / PhonePe / Paytm to scan any shop QR without failure!
            st.markdown(
                f"""
                <a href="{direct_app_url}" class="upi-scanner-btn">
                    📷 सीधा {chosen_app} ऐप खोलें (दुकान का QR स्कैन करने या नंबर पर भेजने के लिए)
                </a>
                """,
                unsafe_allow_html=True,
            )

            # Quick Links for all 3 apps side-by-side just in case
            b1, b2, b3 = st.columns(3)
            b1.markdown(
                f'<a href="{upi_bundle["direct_openers"]["Google Pay (GPay)"]}" class="upi-app-btn" style="font-size:0.85rem; padding:10px;">Open GPay</a>',
                unsafe_allow_html=True,
            )
            b2.markdown(
                f'<a href="{upi_bundle["direct_openers"]["PhonePe"]}" class="upi-app-btn" style="font-size:0.85rem; padding:10px; background:linear-gradient(90deg,#a855f7,#7e22ce); color:#fff !important;">Open PhonePe</a>',
                unsafe_allow_html=True,
            )
            b3.markdown(
                f'<a href="{upi_bundle["direct_openers"]["Paytm"]}" class="upi-app-btn" style="font-size:0.85rem; padding:10px; background:linear-gradient(90deg,#38bdf8,#0284c7); color:#fff !important;">Open Paytm</a>',
                unsafe_allow_html=True,
            )

            st.markdown("</div>", unsafe_allow_html=True)

            with st.expander("🏁 दूसरे फोन से स्कैन करने के लिए QR कोड देखें"):
                st.image(upi_bundle["qr_buf"], caption=f"₹{rec['amount']:,.0f} QR", width=220)


# ==============================================================================
# TAB 2: SEPARATE ₹15,000 DREAM HOUSE + EAR MEDICAL + EMERGENCY VAULT
# ==============================================================================
with tab_vault:
    st.markdown(
        """
        <div class="vip-card">
            <h3 style="margin:0; color:#fbbf24;">🏡 ₹15,000 अलग बचत तिजोरी (Dream House & Ear Medical Vault)</h3>
            <p style="margin:6px 0 0 0; font-size:0.9rem;">
                यह <b>₹15,000/महीना</b> का ट्रैकर आपके ₹23,000 के खर्च बजट से बिल्कुल अलग है।
                इसमें जुड़ा पैसा सिर्फ <b>सपनों के घर (Dream House)</b>, <b>कान के इलाज (Ear Treatment)</b> और <b>इमरजेंसी</b> के लिए है!
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    DREAM_HOUSE_GOAL = 8000
    EAR_MEDICAL_GOAL = 4000
    EMERGENCY_GOAL = 3000

    def get_bucket_sum(df_v, name_prefix):
        if df_v.empty:
            return 0.0
        return float(
            df_v[df_v["vault_bucket"].str.startswith(name_prefix, na=False)]["amount"].sum()
        )

    dh_m = get_bucket_sum(df_month_vault, "🏡")
    ear_m = get_bucket_sum(df_month_vault, "👂")
    emg_m = get_bucket_sum(df_month_vault, "🛡️")

    dh_all = get_bucket_sum(df_all_vault, "🏡")
    ear_all = get_bucket_sum(df_all_vault, "👂")
    emg_all = get_bucket_sum(df_all_vault, "🛡️")

    budget_overflow = max(0.0, total_spent_month - MAX_SPENDING_BUDGET)
    safe_15k = max(0.0, STRICT_SAVINGS_TARGET - budget_overflow)

    vc1, vc2, vc3 = st.columns(3)
    vc1.metric("इस महीने तिजोरी में जमा", f"₹{vault_saved_this_month:,.0f}", "लक्ष्य: ₹15,000")
    vc2.metric("कुल जमा पूंजी (All-Time)", f"₹{vault_saved_all_time:,.0f}", f"{int(vault_saved_all_time // 50)} ईंटें 🧱")
    vc3.metric("₹15K सुरक्षा स्थिति", f"₹{safe_15k:,.0f}", "100% सुरक्षित" if budget_overflow == 0 else f"-₹{budget_overflow:,.0f} खतरे में")

    st.markdown("#### 🎯 ₹15,000 मासिक लक्ष्य मीटर")
    st.progress(
        min(1.0, vault_saved_this_month / STRICT_SAVINGS_TARGET),
        text=f"कुल मासिक बचत जमा: ₹{vault_saved_this_month:,.0f} / ₹15,000",
    )
    st.progress(
        min(1.0, dh_m / DREAM_HOUSE_GOAL),
        text=f"🏡 Dream House (सपनों का घर): ₹{dh_m:,.0f} / ₹{DREAM_HOUSE_GOAL:,} (कुल जमा: ₹{dh_all:,.0f})",
    )
    st.progress(
        min(1.0, ear_m / EAR_MEDICAL_GOAL),
        text=f"👂 Ear Treatment (कान का इलाज): ₹{ear_m:,.0f} / ₹{EAR_MEDICAL_GOAL:,} (कुल जमा: ₹{ear_all:,.0f})",
    )
    st.progress(
        min(1.0, emg_m / EMERGENCY_GOAL),
        text=f"🛡️ Emergency Fund (आपातकालीन कवच): ₹{emg_m:,.0f} / ₹{EMERGENCY_GOAL:,} (कुल जमा: ₹{emg_all:,.0f})",
    )

    # Brick-by-Brick Visual House Progress
    bricks_count = max(1, int((vault_saved_all_time + dh_m) // 50))
    st.markdown(
        f"""
        <div class="vip-card">
            <div style="font-weight:800; color:#fbbf24; margin-bottom:6px;">
                🏗️ हमारे सपनों के घर की दीवार ({bricks_count} ईंटें जुड़ चुकी हैं @ ₹50/ईंट)
            </div>
            <div style="font-size:1.3rem; line-height:1.5; word-wrap:break-word;">
                {"🧱" * min(65, bricks_count)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### ➕ ₹15,000 तिजोरी में पैसे जमा करें")
    with st.form("vault_add_form", clear_on_submit=True):
        v_col1, v_col2, v_col3 = st.columns(3)
        with v_col1:
            dep_by = st.selectbox("किसने जमा किया?", ["Ajay", "Meenakshi", "Ajeet", "Joint Family"])
        with v_col2:
            v_bucket = st.selectbox(
                "किस फंड में जमा किया?",
                [
                    "🏡 Dream House (सपनों का घर फंड)",
                    "👂 Ear Medical (कान के इलाज का फंड)",
                    "🛡️ Emergency Shield (इमरजेंसी फंड)",
                ],
            )
        with v_col3:
            v_amt = st.number_input("जमा रकम (₹)", min_value=100.0, max_value=100000.0, value=5000.0, step=500.0)

        v_note = st.text_input("बैंक / RD / गुल्लक का नोट", placeholder="जैसे: SBI RD या अलग बैंक अकाउंट में ट्रांसफर किया")
        if st.form_submit_button("🔐 तिजोरी में लॉक करें (Save to Vault)"):
            add_vault_deposit(dep_by, v_bucket, v_amt, v_note)
            st.success(f"🎉 बहुत बढ़िया! ₹{v_amt:,.0f} सफलतापूर्वक तिजोरी में जुड़ गए!")
            st.rerun()

    if not df_all_vault.empty:
        st.markdown("#### 📜 तिजोरी में जमा पैसों का पूरा रिकॉर्ड")
        st.dataframe(
            df_all_vault[["timestamp", "deposited_by", "vault_bucket", "amount", "notes"]].rename(
                columns={
                    "timestamp": "तारीख",
                    "deposited_by": "जमाकर्ता",
                    "vault_bucket": "फंड",
                    "amount": "रकम (₹)",
                    "notes": "नोट",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


# ==============================================================================
# TAB 3: LIVE LEDGER, CATEGORY METERS & BACKUP/RESTORE (ZERO DATA LOSS)
# ==============================================================================
with tab_ledger:
    st.markdown("### 📋 महीने के खर्च का पूरा हिसाब (Live Family Ledger)")

    m_a, m_b, m_c = st.columns(3)
    m_a.metric("आज का खर्च (Today)", f"₹{spent_today:,.0f}", f"आज की लिमिट: ₹{daily_safe_limit:,.0f}")
    m_b.metric("इस महीने कुल खर्च", f"₹{total_spent_month:,.0f}", f"बचा बजट: ₹{MAX_SPENDING_BUDGET - total_spent_month:,.0f}")
    m_c.metric("फालतू खर्च (Bad)", f"₹{bad_spent_month:,.0f}", "लक्ष्य: ₹0")

    st.markdown("#### 🚦 बजट कैप मीटर (Category Caps)")
    st.progress(
        min(1.0, food_spent_month / CAP_FOOD),
        text=f"🍲 खाना और मेस (Food Cap ₹7,000): ₹{food_spent_month:,.0f} / ₹{CAP_FOOD:,} ({food_spent_month/CAP_FOOD*100:.0f}%)",
    )
    st.progress(
        min(1.0, rent_spent_month / CAP_RENT),
        text=f"🏠 कमरे का किराया (Rent Cap ₹6,000): ₹{rent_spent_month:,.0f} / ₹{CAP_RENT:,} ({rent_spent_month/CAP_RENT*100:.0f}%)",
    )
    st.progress(
        min(1.0, home_transfer_month / CAP_HOME_MAX),
        text=f"🏡 गाँव / घर ट्रांसफर (₹5k–₹7k): ₹{home_transfer_month:,.0f} / ₹{CAP_HOME_MAX:,}",
    )
    st.progress(
        min(1.0, ear_medical_month / CAP_MEDICAL_EAR),
        text=f"👂 कान का इलाज (Ear Medical): ₹{ear_medical_month:,.0f}",
    )

    st.markdown("#### 🧾 सभी पेमेंट्स की लिस्ट (`Spent By`, `Category`, `Description` और `UPI App` के साथ)")
    flt1, flt2 = st.columns(2)
    with flt1:
        f_member = st.selectbox("सदस्य के हिसाब से देखें (Spent By)", ["All (सभी)", "Ajay", "Meenakshi", "Ajeet", "Joint Family (पूरा परिवार)"])
    with flt2:
        f_cat = st.selectbox("श्रेणी के हिसाब से देखें (Category)", ["All (सभी)"] + list(CATEGORY_DESCRIPTIONS.keys()))

    df_show = df_month.copy()
    if not df_show.empty:
        if f_member != "All (सभी)":
            df_show = df_show[df_show["spent_by"] == f_member]
        if f_cat != "All (सभी)":
            df_show = df_show[df_show["category"] == f_cat]

        df_show["Status"] = df_show["is_bad_expense"].apply(lambda x: "🚨 फालतू" if x == 1 else "✅ ज़रूरी")
        cols_to_show = [
            "id",
            "timestamp",
            "spent_by",
            "category",
            "item_name",
            "description",
            "amount",
            "upi_app",
            "Status",
            "notes",
        ]
        # Ensure all columns exist
        for col in cols_to_show:
            if col not in df_show.columns:
                df_show[col] = ""

        st.dataframe(
            df_show[cols_to_show].rename(
                columns={
                    "id": "ID",
                    "timestamp": "समय",
                    "spent_by": "Spent By (किसने)",
                    "category": "Expense Category",
                    "item_name": "सामान",
                    "description": "Description",
                    "amount": "रकम (₹)",
                    "upi_app": "Payment App",
                    "notes": "नोट",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        b_dl, b_del = st.columns(2)
        with b_dl:
            csv_data = df_show.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 यह लिस्ट Excel/CSV में डाउनलोड करें",
                data=csv_data,
                file_name=f"ajay_family_ledger_{current_month_str}.csv",
                mime="text/csv",
            )
        with b_del:
            with st.expander("🗑️ गलत एंट्री डिलीट करें (Delete by ID)"):
                del_row_id = st.number_input("हटाने के लिए ID नंबर डालें", min_value=1, step=1)
                if st.button("एंट्री हटाएं (Confirm Delete)"):
                    delete_expense_from_db(int(del_row_id))
                    st.success(f"ID #{int(del_row_id)} हटा दिया गया!")
                    st.rerun()
    else:
        st.info("इस महीने अभी तक कोई खर्च दर्ज नहीं हुआ है।")


# ==============================================================================
# TAB 4: STUDY (PYTHON, EXCEL, DATA ENG), DESI KHANA SHORTS & GOOGLE/AI SEARCH
# ==============================================================================
with tab_learn:
    st.markdown(
        """
        <div class="vip-card">
            <h4 style="margin:0; color:#00ff9d;">🎓 अजय का Data Engineer मिशन • 🍲 सस्ता देसी खाना • 🔍 AI और Google सर्च</h4>
            <p style="margin:5px 0 0 0; font-size:0.88rem;">
                यहाँ कोई टाइम-पास नहीं! सिर्फ सैलरी बढ़ाने वाली पढ़ाई (Python, Excel, SQL) और ₹7,000 के फूड बजट को जीतने के लिए घर के सस्ते खाने की शॉर्ट्स।
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. GOOGLE + YOUTUBE + GEMINI AI SEARCH BAR
    st.markdown("### 🔍 स्मार्ट सर्च बार (Python, Excel, देसी रेसिपी या कुछ भी खोजें)")
    s_col1, s_col2 = st.columns([2.2, 1])
    with s_col1:
        user_q = st.text_input(
            "यहाँ अपना सवाल लिखें:",
            placeholder="जैसे: Excel में XLOOKUP कैसे लगाएं? या ₹40 में मसाला तहरी कैसे बनाएं?",
        )
    with s_col2:
        q_topic = st.selectbox(
            "विषय चुनें",
            [
                "🐍 Python & Data Eng",
                "📊 Advanced Excel",
                "🍲 सस्ता घर का खाना",
                "🌐 Google Search",
            ],
        )

    enc_query = urllib.parse.quote_plus(f"{user_q} {q_topic.split(' ', 1)[1]}" if user_q else "Python Data Engineer Full Course Hindi")
    sb1, sb2, sb3 = st.columns(3)
    ai_btn = sb1.button("🤖 AI Mentor से पूछें")
    sb2.markdown(
        f'<a href="https://www.google.com/search?q={enc_query}" target="_blank" class="upi-app-btn" style="padding:10px; font-size:0.9rem; margin:0;">🌐 Google पर खोजें</a>',
        unsafe_allow_html=True,
    )
    sb3.markdown(
        f'<a href="https://www.youtube.com/results?search_query={enc_query}" target="_blank" class="upi-scanner-btn" style="padding:10px; font-size:0.9rem; margin:0;">▶️ YouTube पर देखें</a>',
        unsafe_allow_html=True,
    )

    if ai_btn and user_q.strip():
        q_low = user_q.lower()
        if any(w in q_low for w in ["excel", "vlookup", "xlookup", "pivot"]):
            st.markdown(
                """
                <div class="vip-card">
                <h4>📊 Advanced Excel टिप:</h4>
                <ul>
                    <li><b>XLOOKUP फॉर्मूला:</b> <code>=XLOOKUP(क्या_ढूंढना_है, कहाँ_ढूंढना_है, क्या_रिजल्ट_चाहिए, "Not Found")</code></li>
                    <li><b>Power Query:</b> रोज़ की बड़ी-बड़ी Excel फाइलों को बिना कॉपी-पेस्ट किए 1 क्लिक में जोड़ने और साफ करने के लिए <b>Data Tab → Get Data</b> का इस्तेमाल करें।</li>
                </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif any(w in q_low for w in ["khana", "tehri", "bhindi", "recipe", "aloo", "dal"]):
            st.markdown(
                """
                <div class="vip-card">
                <h4>🍲 ₹40 बजट घर का स्वादिष्ट खाना:</h4>
                <ul>
                    <li><b>15-मिनट मसाला तहरी:</b> कुकर में सरसों तेल, जीरा, प्याज, आलू, सोयाबीन और हल्दी-गरम मसाला भूनें। चावल और दोगुना पानी डालकर 2 सीटी लगाएं। बाहर के ₹150 के खाने से लाख गुना बेहतर!</li>
                    <li><b>कुरकुरी भिंडी:</b> भिंडी को धोकर सुखाकर काटें। बिना ढके सरसों के तेल और जीरे-हरी मिर्च में पकाएं और अंत में नमक व अमचूर डालें।</li>
                </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="vip-card">
                <h4>🚀 Data Engineer & Career Mentor:</h4>
                आपका सवाल: <b>{user_q}</b><br>
                Data Engineer या Data Scientist बनने के लिए रोज़ 45 मिनट <b>1. Python (Pandas/Automation)</b>, <b>2. SQL (Joins & Window Functions)</b>, और <b>3. Advanced Excel + PySpark</b> प्रैक्टिस करें। ऊपर दिए गए <b>Google</b> या <b>YouTube</b> बटन पर क्लिक करके इसके लाइव ट्यूटोरियल तुरंत देखें!
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")
    v_tab1, v_tab2, v_tab3 = st.tabs(
        [
            "🖥️ Long Videos (Python, Excel, Data Eng)",
            "📱 Shorts/Reels (सस्ता देसी खाना और जोश)",
            "🗺️ Career Checklist",
        ]
    )

    with v_tab1:
        st.markdown("#### 🖥️ लंबी क्लासेज (Data Engineer / Scientist बनने के लिए)")
        course_choice = st.selectbox(
            "पढ़ाई का विषय चुनें:",
            [
                "🐍 Python Full Course (Automation, Pandas & Data Science)",
                "📊 Advanced Excel & MIS Automation (High Salary Skill)",
                "🗄️ SQL & PySpark Data Engineering Mastery",
                "📈 Streamlit, Power BI & Portfolio Projects",
            ],
        )

        VIDEOS_MAP = {
            "🐍 Python Full Course (Automation, Pandas & Data Science)": [
                ("Python Full Course in Hindi (Beginner to Pro)", "https://www.youtube.com/watch?v=UrsmFxEIp5k"),
                ("Python Pandas Data Analysis Tutorial", "https://www.youtube.com/watch?v=vmEHCJofslg"),
            ],
            "📊 Advanced Excel & MIS Automation (High Salary Skill)": [
                ("Advanced Excel Full Course (XLOOKUP, Pivot, Dashboards)", "https://www.youtube.com/watch?v=Vl0H-qTclOg"),
                ("Power Query Automation in Excel", "https://www.youtube.com/watch?v=0aeZX1l4JT4"),
            ],
            "🗄️ SQL & PySpark Data Engineering Mastery": [
                ("SQL Full Course for Data Engineers", "https://www.youtube.com/watch?v=HXV3zeQKqGY"),
                ("PySpark Big Data Engineering Course", "https://www.youtube.com/watch?v=_C8kWso4ne4"),
            ],
            "📈 Streamlit, Power BI & Portfolio Projects": [
                ("Python Streamlit Web App Tutorial", "https://www.youtube.com/watch?v=JwSS70SZdyM"),
                ("Machine Learning & Data Science Full Course", "https://www.youtube.com/watch?v=i_LwzRVP7bg"),
            ],
        }

        for title, link in VIDEOS_MAP[course_choice]:
            st.markdown(f"**▶️ {title}**")
            st.video(link)

    with v_tab2:
        st.markdown("#### 📱 शॉर्ट वीडियो / रील्स (सस्ता घर का खाना और परिवार मोटिवेशन)")
        short_type = st.radio(
            "कौन-सी शॉर्ट्स देखना चाहते हैं?",
            [
                "🍲 सस्ता और स्वादिष्ट घर का खाना (Budget Indian Cooking Shorts)",
                "🔥 मेहनत, बचत और कामयाबी मोटिवेशन (Hustle Shorts)",
            ],
        )

        if "खाना" in short_type:
            c_sh1, c_sh2 = st.columns(2)
            with c_sh1:
                st.markdown("**🍛 झटपट कुकर मसाला तहरी / पुलाव**")
                st.video("https://www.youtube.com/watch?v=w7Wj2_T0b9A")
                st.markdown(
                    '<a href="https://www.youtube.com/results?search_query=simple+desi+sabzi+dal+chawal+cooking+shorts+hindi" target="_blank" class="upi-app-btn" style="font-size:0.85rem; padding:10px;">📱 देसी दाल-सब्ज़ी कुकिंग रील्स खोलें</a>',
                    unsafe_allow_html=True,
                )
            with c_sh2:
                st.markdown("**🥗 कुरकुरी भिंडी और टिफिन सब्ज़ी**")
                st.video("https://www.youtube.com/watch?v=3m7B92p2R7k")
                st.markdown(
                    '<a href="https://www.youtube.com/results?search_query=indian+recipes+under+50+rupees+shorts+hindi" target="_blank" class="upi-scanner-btn" style="font-size:0.85rem; padding:10px;">🍲 ₹50 से कम में बनने वाले खाने की रील्स</a>',
                    unsafe_allow_html=True,
                )
        else:
            m_sh1, m_sh2 = st.columns(2)
            with m_sh1:
                st.markdown("**💪 कभी हार मत मानो (Hard Work)**")
                st.video("https://www.youtube.com/watch?v=ZXsQAXx_ao0")
                st.markdown(
                    '<a href="https://www.youtube.com/results?search_query=middle+class+family+struggle+to+success+motivation+shorts+hindi" target="_blank" class="upi-app-btn" style="font-size:0.85rem; padding:10px;">🔥 मिडिल-क्लास मोटिवेशन शॉर्ट्स</a>',
                    unsafe_allow_html=True,
                )
            with m_sh2:
                st.markdown("**🏡 अपने लक्ष्य पर फोकस रखो**")
                st.video("https://www.youtube.com/watch?v=mgmVOuLgFB0")
                st.markdown(
                    '<a href="https://www.youtube.com/results?search_query=study+after+work+job+motivation+shorts+hindi" target="_blank" class="upi-scanner-btn" style="font-size:0.85rem; padding:10px;">🚀 जॉब के साथ पढ़ाई मोटिवेशन रील्स</a>',
                    unsafe_allow_html=True,
                )

    with v_tab3:
        st.markdown("#### 🗺️ अजय का Data Engineer बनने का रोडमैप (टिक करके सेव करें)")
        SKILLS_LIST = [
            ("s1", "📊 Step 1: Advanced Excel (XLOOKUP, Pivot Table, Power Query)"),
            ("s2", "🐍 Step 2: Python Core & Automation (Scripts, Playwright, File Handling)"),
            ("s3", "🐼 Step 3: Python Pandas (CSV/Excel Data Cleaning & Analysis)"),
            ("s4", "🗄️ Step 4: SQL Mastery (Joins, Group By, Window Functions)"),
            ("s5", "📈 Step 5: Streamlit & Power BI Dashboards"),
            ("s6", "⚡ Step 6: PySpark & ETL Data Pipelines (Data Engineer Core)"),
        ]
        curr_prog = get_career_progress()
        done_cnt = 0
        for k, lbl in SKILLS_LIST:
            val = curr_prog.get(k, False)
            new_val = st.checkbox(lbl, value=val, key=f"road_{k}")
            if new_val != val:
                set_career_progress(k, new_val)
                st.rerun()
            if new_val:
                done_cnt += 1
        st.progress(done_cnt / len(SKILLS_LIST), text=f"प्रगति: {done_cnt}/{len(SKILLS_LIST)} स्टेप्स पूरे!")


# ==============================================================================
# TAB 5: MONTHLY ANALYTICS & PSYCHOLOGICAL FAMILY COUNSELOR
# ==============================================================================
with tab_analytics:
    st.markdown("### 🧠 मासिक फैमिली काउंसलर और ग्राफ (Monthly Counselor)")

    score = 100
    notes_list = []
    if total_spent_month > MAX_SPENDING_BUDGET:
        score -= 35
        notes_list.append(
            f"❌ **बजट अलर्ट:** कुल खर्च ₹{total_spent_month:,.0f} हो गया है जो ₹23,000 की सीमा से ₹{total_spent_month - MAX_SPENDING_BUDGET:,.0f} ज़्यादा है।"
        )
    else:
        notes_list.append(
            f"✅ **शानदार बजट कंट्रोल:** कुल खर्च ₹{total_spent_month:,.0f} है (₹23,000 के अंदर)। आपकी ₹15,000 की बचत पूरी तरह सुरक्षित है!"
        )

    if bad_spent_month == 0:
        notes_list.append("🏆 **Zero फालतू खर्च:** इस महीने अजय, मीनाक्षी और अजीत ने ₹1 भी फालतू बर्बाद नहीं किया!")
    else:
        score -= min(30, int(bad_spent_month // 100) * 5 + 10)
        notes_list.append(
            f"⚠️ **सुधार की ज़रूरत:** ₹{bad_spent_month:,.0f} गैर-ज़रूरी चीजों पर खर्च हुए हैं। अगले महीने इसे ₹0 करके सीधे घर की तिजोरी में डालें।"
        )

    score = max(0, score)
    st.markdown(
        f"""
        <div class="vip-card">
            <h4 style="margin:0; color:#00ff9d;">🏅 इस महीने का परिवार अनुशासन स्कोर: {score} / 100</h4>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for n in notes_list:
        st.markdown(n)

    if not df_month.empty:
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("#### 🍩 किस श्रेणी में कितना खर्च हुआ?")
            cat_df = df_month.groupby("category", as_index=False)["amount"].sum()
            fig1 = px.pie(
                cat_df,
                names="category",
                values="amount",
                hole=0.5,
                template="plotly_dark",
            )
            fig1.update_layout(
                margin=dict(t=15, b=15, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#ffffff"),
            )
            st.plotly_chart(fig1, use_container_width=True)

        with g2:
            st.markdown("#### 👨‍👩‍👦 किसने कितना खर्च किया? (`Spent By`)")
            who_df = df_month.groupby("spent_by", as_index=False)["amount"].sum()
            fig2 = px.bar(
                who_df,
                x="spent_by",
                y="amount",
                color="spent_by",
                template="plotly_dark",
            )
            fig2.update_layout(
                margin=dict(t=15, b=15, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#ffffff"),
                showlegend=False,
            )
            st.plotly_chart(fig2, use_container_width=True)
