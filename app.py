import os
import io
import random
import sqlite3
import urllib.parse
from datetime import datetime, date, timedelta
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

# ==============================================================================
# 1. PAGE SETUP & HIDE ALL GITHUB / STREAMLIT MENUS
# ==============================================================================
st.set_page_config(
    page_title="Parivaar VIP 4.0 | Ajay Super App",
    page_icon="👑",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ==============================================================================
# 2. CORE FINANCIAL CONSTANTS & DEFAULT USERS
# ==============================================================================
PRIMARY_INCOME = 23000   # Ajay's Monthly Income
SPOUSE_INCOME = 15000    # Meenakshi's Monthly Income
TOTAL_POOL = PRIMARY_INCOME + SPOUSE_INCOME  # ₹38,000 Total Pool
STRICT_SAVINGS_TARGET = 15000                # ₹15,000 Separate Dream House + Medical Vault
MAX_SPENDING_BUDGET = TOTAL_POOL - STRICT_SAVINGS_TARGET  # ₹23,000 Max Spending

CAP_FOOD = 7000
CAP_RENT = 6000
CAP_HOME_MAX = 7000
CAP_MEDICAL_EAR = 3000
PSYCHOLOGY_DAILY_REWARD_LIMIT = 200.0

DEFAULT_USERS = [
    ("Ajay", "52729211", "👑 Chief Admin & Primary Earner (₹23k)", 1, "👑"),
    ("Meenakshi", "2345", "Partner Earner (₹15k)", 0, "👩‍💼"),
    ("Ajeet", "3456", "Brother & Family Member", 0, "🧑‍🎓"),
]

CATEGORY_DESCRIPTIONS = {
    "Food & Mess (खाना, चिकन/मछली और टिफिन)": [
        "सुबह की चाय / बिस्किट (Morning Tea)",
        "ऑफिस लंच / टिफिन (Office Lunch)",
        "दूध, दही और ब्रेड (Milk & Curd)",
        "ताज़ी मछली / चिकन / अंडे (Home Non-Veg)",
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
    "Padhai, AI & English (पढ़ाई और करियर)": [
        "Python / Data Engineering / AI कोर्स या किताब",
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
    "Other Zaroori Kharch (अन्य ज़रूरी)": [
        "बाल कटवाना / साबुन / तेल (Daily Use)",
        "घर का छोटा-मोटा ज़रूरी सामान",
        "अन्य ज़रूरी खर्च...",
    ],
}

# ==============================================================================
# 3. 5 PREMIUM VIP THEMES + STRICT CSS LOCK (NO HIDDEN TEXT, NO GITHUB BUTTONS)
# ==============================================================================
THEMES = {
    "👑 Maharaja Gold & Obsidian (अजय एडमिन स्पेशल)": {
        "bg_main": "radial-gradient(circle at top, #1f1705 0%, #07090f 100%)",
        "card_bg": "#111827",
        "card_border": "#f59e0b",
        "accent": "#fbbf24",
        "text_bright": "#ffffff",
        "text_sub": "#fde68a",
        "banner_grad": "linear-gradient(135deg, #451a03 0%, #111827 65%, #064e3b 100%)",
    },
    "⚡ Emerald Wealth (पैसा और तरक्की ग्रीन)": {
        "bg_main": "radial-gradient(circle at top, #042f2e 0%, #060913 100%)",
        "card_bg": "#0f172a",
        "card_border": "#00ff9d",
        "accent": "#00ff9d",
        "text_bright": "#ffffff",
        "text_sub": "#a7f3d0",
        "banner_grad": "linear-gradient(135deg, #064e3b 0%, #0f172a 65%, #1e1b4b 100%)",
    },
    "🌊 Mindful Psychiatrist Blue (शांत और फोकस ब्लू)": {
        "bg_main": "radial-gradient(circle at top, #0c192c 0%, #050811 100%)",
        "card_bg": "#0f172a",
        "card_border": "#38bdf8",
        "accent": "#38bdf8",
        "text_bright": "#ffffff",
        "text_sub": "#bae6fd",
        "banner_grad": "linear-gradient(135deg, #0c4a6e 0%, #0f172a 65%, #311042 100%)",
    },
    "🟣 Royal Amethyst (प्रीमियम पर्पल नाइट)": {
        "bg_main": "radial-gradient(circle at top, #2e1065 0%, #070510 100%)",
        "card_bg": "#131124",
        "card_border": "#c084fc",
        "accent": "#e879f9",
        "text_bright": "#ffffff",
        "text_sub": "#f5d0fe",
        "banner_grad": "linear-gradient(135deg, #3b0764 0%, #131124 65%, #0f172a 100%)",
    },
    "🔥 Agni Hustle (जोश और अनुशासन)": {
        "bg_main": "radial-gradient(circle at top, #2a0a12 0%, #08070c 100%)",
        "card_bg": "#181018",
        "card_border": "#f97316",
        "accent": "#fb923c",
        "text_bright": "#ffffff",
        "text_sub": "#fed7aa",
        "banner_grad": "linear-gradient(135deg, #431407 0%, #181018 65%, #3b0764 100%)",
    },
}

if "selected_theme" not in st.session_state:
    st.session_state.selected_theme = "👑 Maharaja Gold & Obsidian (अजय एडमिन स्पेशल)"


def apply_vip_theme(theme_name: str):
    t = THEMES.get(theme_name, THEMES["👑 Maharaja Gold & Obsidian (अजय एडमिन स्पेशल)"])
    st.markdown(
        f"""
        <style>
        /* COMPLETELY HIDE STREAMLIT HEADER, GITHUB ICON, FORK, MANAGE APP & FOOTER */
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

        /* Global App Styling */
        .stApp {{
            background: {t['bg_main']} !important;
            color: {t['text_bright']} !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }}
        .block-container {{
            padding-top: 0.7rem !important;
            padding-bottom: 4.5rem !important;
            max-width: 760px !important;
        }}

        /* Force 100% High-Contrast Visible Text on All Labels & Elements */
        label, .stWidgetLabel, .stMarkdown p, .stMarkdown li, span, h1, h2, h3, h4, h5, h6 {{
            color: {t['text_bright']} !important;
        }}
        .stCaption {{
            color: {t['text_sub']} !important;
            font-size: 0.85rem !important;
        }}

        /* High-Contrast Dropdowns & Inputs */
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
            border: 1px solid {t['card_border']} !important;
            border-radius: 14px !important;
            padding: 12px 14px !important;
            box-shadow: 0 4px 14px rgba(0,0,0,0.45) !important;
        }}
        div[data-testid="stMetricLabel"] p,
        div[data-testid="stMetricLabel"] {{
            color: {t['text_sub']} !important;
            font-weight: 700 !important;
            font-size: 0.84rem !important;
        }}
        div[data-testid="stMetricValue"] div,
        div[data-testid="stMetricValue"] {{
            color: {t['accent']} !important;
            font-weight: 800 !important;
            font-size: 1.35rem !important;
        }}

        /* Mobile Navigation Tabs */
        button[data-baseweb="tab"] {{
            background-color: #1e293b !important;
            color: #cbd5e1 !important;
            border-radius: 10px 10px 0 0 !important;
            padding: 8px 10px !important;
            margin-right: 3px !important;
            font-weight: 700 !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            background-color: {t['accent']} !important;
            color: #020617 !important;
            font-weight: 900 !important;
        }}
        button[data-baseweb="tab"][aria-selected="true"] p {{
            color: #020617 !important;
            font-weight: 900 !important;
        }}

        /* Compact Psychiatrist Daily Motivation Banner */
        .psych-banner {{
            background: {t['banner_grad']};
            border: 1.5px solid {t['accent']};
            border-left: 7px solid {t['accent']};
            border-radius: 14px;
            padding: 10px 14px;
            margin-bottom: 10px;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.45);
        }}
        .psych-tag {{
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: {t['accent']};
            font-weight: 800;
            margin-bottom: 2px;
        }}
        .psych-quote {{
            font-size: 0.96rem;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.38;
        }}

        /* Daily < ₹200 Spend Dopamine Reward Card */
        .reward-banner {{
            background: linear-gradient(135deg, #065f46 0%, #047857 100%);
            border: 2px solid #34d399;
            border-radius: 14px;
            padding: 10px 14px;
            margin-bottom: 10px;
            color: #ffffff;
            font-size: 0.9rem;
            box-shadow: 0 0 18px rgba(52, 211, 153, 0.25);
        }}

        /* VIP Cards */
        .vip-card {{
            background: {t['card_bg']};
            border: 1px solid {t['card_border']};
            border-radius: 15px;
            padding: 14px 16px;
            margin-bottom: 12px;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.38);
        }}

        /* Admin Badge Card */
        .admin-badge-bar {{
            background: linear-gradient(90deg, #451a03 0%, #78350f 50%, #1e293b 100%);
            border: 1.5px solid #fbbf24;
            border-radius: 12px;
            padding: 8px 14px;
            margin-bottom: 10px;
            font-size: 0.85rem;
            font-weight: 700;
            color: #fde68a;
        }}

        /* Red Alert Banner */
        @keyframes pulseRed {{
            0% {{ box-shadow: 0 0 0 0 rgba(255, 51, 102, 0.65); border-color: #ff3366; }}
            70% {{ box-shadow: 0 0 0 10px rgba(255, 51, 102, 0); border-color: #fda4af; }}
            100% {{ box-shadow: 0 0 0 0 rgba(255, 51, 102, 0); border-color: #ff3366; }}
        }}
        .red-alert-banner {{
            background: linear-gradient(135deg, #7f1d1d 0%, #31102f 100%);
            border: 2px solid #ff3366;
            border-radius: 14px;
            padding: 11px 14px;
            margin-bottom: 10px;
            color: #ffffff;
            font-weight: 700;
            font-size: 0.88rem;
            animation: pulseRed 1.8s infinite;
        }}

        /* Instant UPI & Action Buttons */
        .upi-app-btn {{
            display: block;
            width: 100%;
            text-align: center;
            background: linear-gradient(90deg, #00ff9d 0%, #10b981 100%);
            color: #022c22 !important;
            font-weight: 900;
            font-size: 0.98rem;
            padding: 12px 14px;
            border-radius: 12px;
            text-decoration: none !important;
            margin: 6px 0;
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
            font-size: 0.95rem;
            padding: 11px 14px;
            border-radius: 12px;
            text-decoration: none !important;
            margin: 6px 0;
            border: 1.5px solid #ffffff;
        }}

        /* Buttons */
        div.stButton > button, div.stFormSubmitButton > button, div.stDownloadButton > button {{
            width: 100%;
            border-radius: 11px !important;
            min-height: 45px !important;
            font-weight: 800 !important;
            border: 1.5px solid {t['accent']} !important;
            background-color: #1e293b !important;
            color: #ffffff !important;
        }}
        div.stButton > button:hover, div.stFormSubmitButton > button:hover, div.stDownloadButton > button:hover {{
            background-color: {t['accent']} !important;
            color: #020617 !important;
        }}
        div.stButton > button:hover p, div.stFormSubmitButton > button:hover p, div.stDownloadButton > button:hover p {{
            color: #020617 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ==============================================================================
# 4. SHORT PSYCHIATRIST DAILY MINDSET ENGINE (1-LINE HITS FOR 10+ YEARS)
# ==============================================================================
def get_short_psychiatrist_motivation():
    anchor = date(2025, 1, 1)
    today = date.today()
    day_num = max(1, (today - anchor).days + 1)

    tags = [
        "🧠 Psychiatrist Note",
        "🌿 शांत दिमाग, पक्का घर",
        "💎 10-Second Control",
        "🏡 ₹15K Dream House Rule",
        "⚡ Winner Mindset",
        "🛡️ फेलियर से जीत",
    ]

    short_quotes = [
        "पेमेंट से पहले 1 गहरी सांस लें—आपका ₹15,000 का घर का सपना 5 मिनट के लालच से बहुत बड़ा है।",
        "इंग्लिश बोलते समय या कोडिंग में गलती होना शर्म की बात नहीं, तरक्की की पहली सीढ़ी है!",
        "ऑफिस की टेंशन को अपनी पढ़ाई से हराओ; रोज़ 45 मिनट Python/AI आपको नई ऊंचाई पर ले जाएगा।",
        "बाहर का जंक फूड 2 मिनट का नकली सुख देता है, घर का खाना और बचत जीवन भर की सुरक्षा देती है।",
        "आज बचाया गया हर ₹100 आपके अपने घर की 2 मजबूत ईंटें (🧱) हैं।",
        "तुलना दिमाग की शांति छीनती है और अनुशासन किस्मत बदलता है। आज सिर्फ अपने लक्ष्य पर टिके रहें।",
        "छोटी जीत (रोज़ ₹200 से कम खर्च + 5 नए English वाक्य) आपके दिमाग को विजेता बनाती है।",
        "अजय, मीनाक्षी और अजीत की एकता ही इस परिवार की सबसे बड़ी दौलत है।",
    ]

    micro_goals = [
        "✅ आज का नियम: खर्च ≤ ₹200 | 10 मिनट Spoken English | 30 मिनट Python/AI",
        "✅ आज का नियम: ₹0 फालतू खर्च | हर पेमेंट से पहले एंट्री | शांत दिमाग",
    ]

    return {
        "day": day_num,
        "date_str": today.strftime("%d %b %Y"),
        "tag": f"{tags[day_num % len(tags)]} • Day #{day_num}",
        "quote": short_quotes[(day_num * 3 + (day_num // len(short_quotes))) % len(short_quotes)],
        "goal": micro_goals[day_num % len(micro_goals)],
    }


# ==============================================================================
# 5. 37 LAKH+ (3,750,000+) COMBINATORIAL SMART PROMPT ENGINE
# ==============================================================================
PROMPT_DOMAINS = {
    "🗣️ Spoken English & Office Fluency": {
        "topics": [
            "Daily Office Meeting Sentences", "Boss & Client Email Writing", "Job Interview Self-Introduction",
            "Phone Call English Conversation", "Salary Hike & Promotion Discussion", "Explaining Logistics & Data Reports",
            "Overcoming Hesitation & Fear of Speaking", "Common Grammar Mistakes Fix", "Polite Disagreement in Office",
            "Small Talk with Colleagues", "Presentation Opening & Closing Lines", "Asking Clarifying Questions",
        ],
        "contexts": [
            "for a beginner who thinks in Hindi first", "for IT & Data Engineering interviews",
            "when speaking to senior management", "for daily morning standup calls",
            "when handling an angry client or delay update", "for confident body language and tone",
            "with Hindi pronunciation and meaning", "for 5-minute mirror speaking practice",
        ],
    },
    "🐍 Python, SQL, Excel & Data Engineering": {
        "topics": [
            "Python Pandas CSV/Excel Automation", "Playwright Web Scraping & Auto-Login", "SQL Window Functions (ROW_NUMBER, RANK)",
            "Advanced Excel XLOOKUP & INDEX-MATCH", "Excel Power Query 1-Click Cleaning", "PySpark Big Data ETL Pipeline",
            "Streamlit Interactive Dashboard Design", "Python Error Handling & Debugging", "Automating Daily Office MIS Reports",
            "PostgreSQL Performance Tuning", "GitHub Portfolio Project Building", "API Data Fetching with Python Requests",
        ],
        "contexts": [
            "with ready-to-run copy-paste code", "explained in simple Hinglish for beginners",
            "for cracking ₹8L–₹15L LPA Data Engineer interviews", "to save 3 hours of manual office work daily",
            "with real-world logistics & fleet dataset examples", "step-by-step from zero to production",
            "with common errors and how to fix them", "for resume and LinkedIn showcase",
        ],
    },
    "🤖 AI Learning, ChatGPT/Gemini & Tech News": {
        "topics": [
            "Latest AI Tools for Office Productivity", "Prompt Engineering Masterclass", "Building Free AI Agents with Python",
            "Generative AI & LLM Latest Breakthroughs", "Using AI to Debug Python & SQL Code", "AI Resume & Interview Preparation",
            "Free AI Tools for Spoken English Practice", "Automating Excel Formulas with AI", "Future Tech Jobs & AI Trends 2026-2030",
            "Creating YouTube Shorts & Scripts with AI", "AI Data Analysis & Chart Generation", "Gemini API Free Integration",
        ],
        "contexts": [
            "using 100% free tools without paying anything", "for working professionals studying at night",
            "with latest 2026 tech industry news", "to double coding speed and accuracy",
            "explained in simple Hindi with examples", "for career switch into Data & AI",
        ],
    },
    "🍗 Chicken, Fish, Chinese, Korean & Desi Khana": {
        "topics": [
            "मसालेदार देसी चिकन करी (Dhaba Style Chicken Curry)", "सरसों वाली मछली करी और कुरकुरी फिश फ्राई (Fish Curry & Fry)",
            "स्ट्रीट स्टाइल वेज/चिकन चाउमीन और मंचूरियन (Indo-Chinese)", "कोरियन स्पाइसी रैमेन नूडल्स और Tteokbokki (Korean Food)",
            "झटपट कुकर मसाला तहरी और कुरकुरी भिंडी (Budget Desi Food)", "चिली चिकन और स्टीम्ड मोमोज़ विद रेड चटनी",
            "हैदराबादी चिकन दम बिरयानी और अंडा करी", "कोरियन गार्लिक ब्रेड और क्रिस्पी फ्राइड चिकन",
            "₹40 बजट हाई-प्रोटीन सोयाबीन, चना और पनीर भुर्जी", "ढाबा स्टाइल दाल तड़का और जीरा राइस",
        ],
        "contexts": [
            "घर के बेसिक मसालों से कम बजट में बनाने की विधि", "15 से 20 मिनट में कुकर या कड़ाही में झटपट रेसिपी",
            "होटल और रेस्टोरेंट जैसा असली स्वाद घर पर लाने के सीक्रेट टिप्स", "संडे स्पेशल फैमिली डिनर के लिए स्टेप-बाय-स्टेप",
            "कम तेल और ज़्यादा प्रोटीन के साथ सेहतमंद तरीके से", "शुरुआती लोगों (Beginners) के लिए एकदम आसान भाषा में",
        ],
    },
    "🔥 Failure Recovery, Office Politics & Mindset": {
        "topics": [
            "अंग्रेज़ी बोलते समय अटकने या मज़ाक बनने के डर को कैसे खत्म करें",
            "कोडिंग या इंटरव्यू में बार-बार फेल होने के बाद दोगुनी ताकत से वापसी कैसे करें",
            "ऑफिस में गलती होने या बॉस की डांट के बाद दिमाग को शांत और मजबूत कैसे रखें",
            "ऑफिस पॉलिटिक्स से बचते हुए अपने काम और प्रमोशन पर फोकस कैसे करें",
            "थकान और आलस को हराकर रोज़ रात को पढ़ने की आदत कैसे डालें",
            "पैसों की तंगी में भी परिवार का हौसला और खुशी कैसे बनाए रखें",
        ],
        "contexts": [
            "सच्ची प्रेरक कहानी और साइकोलॉजिकल समाधान के साथ", "दिमाग का तनाव 5 मिनट में खत्म करने की प्रैक्टिकल ट्रिक",
            "असफलता को अपनी सबसे बड़ी ताकत बनाने के 5 नियम", "आत्मविश्वास (Self-Confidence) तुरंत वापस पाने का तरीका",
        ],
    },
    "✈️ Travel, Vlogs, Cartoons & Hindi Kahaniyaan": {
        "topics": [
            "कम बजट (Under ₹3,000) में दिल्ली के पास वीकेंड फैमिली ट्रैवल प्लान", "पहाड़ों और नदियों की खूबसूरत ट्रैवल व्लॉगिंग गाइड",
            "रोमांचक और सस्पेंस से भरी प्रेरणादायक हिंदी कहानी", "पंचतंत्र और तेनालीराम की बुद्धिमत्ता वाली कहानियाँ",
            "भारतीय क्लासिक कार्टून और एनिमेशन स्टोरीज़", "दुनिया के अजूबे और रहस्यमयी जगहों की जानकारी",
        ],
        "contexts": [
            "पूरे परिवार के मनोरंजन और ज्ञान के लिए", "मूड फ्रेश करने और नई ऊर्जा पाने के लिए",
            "रोचक तथ्यों और सटीक जानकारी के साथ", "आसान और दिलचस्प कहानी की शैली में",
        ],
    },
}

PROMPT_FORMATS = [
    "स्टेप-बाय-स्टेप आसान हिंदी गाइड",
    "प्रैक्टिकल उदाहरण और शॉर्टकट ट्रिक्स के साथ",
    "सवाल-जवाब और डेली प्रैक्टिस प्लान के रूप में",
    "एक्सपर्ट टिप्स और शुरुआती गलतियों से बचने के तरीके",
    "5 मिनट में समझ आने वाले बुलेट पॉइंट्स में",
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
# 6. DATABASE ENGINE (USERS, EXPENSES, VAULT, CAREER)
# ==============================================================================
DB_FILE = "parivaar_vip_v3.db"


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
            "UPDATE app_users SET password = ? WHERE username = 'Ajay' AND password = '1234'",
            ("52729211",),
        )

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


# ==============================================================================
# 7. FAST MULTI-APP UPI ENGINE & ZERO-AD NATIVE WEBAPP GENERATOR
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
    """
    Generates a 100% Ad-Free, Fullscreen Native-Style App file (.html) with embedded
    PWA manifest and full-screen iframe wrapper so the user gets zero ads forever.
    """
    html_code = """<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#07090f">
<title>Parivaar VIP 4.0 (Zero-Ad Native App)</title>
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
      <h2 style="color:#fbbf24; margin-bottom:8px;">👑 Parivaar VIP 4.0</h2>
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
# 8. STRICT TAB-ISOLATED LOGIN (RE-LOGIN REQUIRED ON NEW TAB / PASTE LINK)
# ==============================================================================
if len(st.query_params) > 0:
    st.query_params.clear()

if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

apply_vip_theme(st.session_state.selected_theme)
USERS_DICT = get_all_users_dict()


def render_login_screen():
    mot = get_short_psychiatrist_motivation()
    st.markdown(
        f"""
        <div class="psych-banner">
            <div class="psych-tag">{mot['tag']} • {mot['date_str']}</div>
            <div class="psych-quote">“{mot['quote']}”</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="vip-card" style="text-align:center;">
            <h2 style="margin-bottom:4px; color:#fbbf24;">👑 Parivaar VIP 4.0 Super-App</h2>
            <p style="font-size:0.88rem; margin-top:2px;">
                🔒 <b>Secure Tab Protection:</b> नए टैब या फोन में लिंक खोलने पर पासवर्ड अनिवार्य है।
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("strict_login_form"):
        user_options = list(USERS_DICT.keys())
        selected_user = st.selectbox(
            "👤 अपना अकाउंट चुनें (Select User ID)",
            options=user_options,
            format_func=lambda u: f"{USERS_DICT[u]['avatar']} {u} — {USERS_DICT[u]['role']}",
        )
        pin_input = st.text_input(
            "🔑 अपना पासवर्ड / PIN डालें",
            type="password",
            placeholder="अपना पासवर्ड लिखें...",
        )
        login_btn = st.form_submit_button("🔓 सुरक्षित लॉगिन करें (Unlock App)")

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
# 9. LOGGED-IN USER & ADMIN PROFILE STATUS
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

if not df_month.empty:
    total_spent_month = float(df_month["amount"].sum())
    df_today = df_month[df_month["timestamp"].str.startswith(today_str, na=False)]
    spent_today = float(df_today["amount"].sum()) if not df_today.empty else 0.0
    bad_spent_month = float(df_month[df_month["is_bad_expense"] == 1]["amount"].sum())
    food_spent_month = float(df_month[df_month["category"].str.startswith("Food", na=False)]["amount"].sum())
    rent_spent_month = float(df_month[df_month["category"].str.startswith("Room Rent", na=False)]["amount"].sum())
    home_transfer_month = float(df_month[df_month["category"].str.startswith("Home Transfer", na=False)]["amount"].sum())
    ear_medical_month = float(df_month[df_month["category"].str.startswith("Ear Medical", na=False)]["amount"].sum())
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

days_in_month = calendar.monthrange(today_obj.year, today_obj.month)[1]
days_left = max(1, days_in_month - today_obj.day + 1)
remaining_monthly_budget = max(0.0, MAX_SPENDING_BUDGET - total_spent_month)
daily_safe_limit = remaining_monthly_budget / days_left

# Top Bar: Theme + Profile + Quick Download + Logout
top_c1, top_c2, top_c3 = st.columns([2.2, 1.5, 0.9])
with top_c1:
    chosen_theme = st.selectbox(
        "🎨 VIP थीम चुनें (Theme)",
        options=list(THEMES.keys()),
        index=list(THEMES.keys()).index(st.session_state.selected_theme),
    )
    if chosen_theme != st.session_state.selected_theme:
        st.session_state.selected_theme = chosen_theme
        st.rerun()
with top_c2:
    role_badge = "👑 SUPER ADMIN" if is_admin else "👤 MEMBER"
    st.markdown(
        f"<div style='padding-top:26px; font-weight:900; font-size:0.9rem;'>{current_user_info['avatar']} {current_user} <span style='color:#fbbf24;'>({role_badge})</span></div>",
        unsafe_allow_html=True,
    )
with top_c3:
    st.markdown("<div style='padding-top:18px;'></div>", unsafe_allow_html=True)
    if st.button("🔒 लॉगआउट"):
        st.session_state.authenticated_user = None
        st.rerun()

if is_admin:
    st.markdown(
        """
        <div class="admin-badge-bar">
            👑 <b>Ajay Singh Rawat — Master Admin Mode:</b> गलत एंट्री Edit/Delete करने, नए यूज़र बनाने और पासवर्ड बदलने का 100% कंट्रोल सक्रिय है।
        </div>
        """,
        unsafe_allow_html=True,
    )

# Short Psychiatrist Daily Motivation Banner
mot = get_short_psychiatrist_motivation()
st.markdown(
    f"""
    <div class="psych-banner">
        <div class="psych-tag">{mot['tag']} • {mot['date_str']}</div>
        <div class="psych-quote">“{mot['quote']}”</div>
        <div style="font-size:0.78rem; color:#fde68a; margin-top:4px; font-weight:700;">{mot['goal']}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Daily < ₹200 Spend Dopamine Notification
if spent_today <= PSYCHOLOGY_DAILY_REWARD_LIMIT:
    extra_saved = max(0.0, daily_safe_limit - spent_today)
    bricks_won = max(1, int(extra_saved // 50))
    st.markdown(
        f"""
        <div class="reward-banner">
            🏆 <b>बहुत बढ़िया {current_user}!</b> आज खर्च सिर्फ <b>₹{spent_today:,.0f}</b> (₹200 से कम) है!
            आपने आज <b>₹{extra_saved:,.0f} एक्स्ट्रा बचाकर</b> अपने घर की <b>+{bricks_won} नई ईंटें (🧱)</b> पक्की कर लीं!
        </div>
        """,
        unsafe_allow_html=True,
    )

# ==============================================================================
# 10. MAIN 7 SUPER-TABS
# ==============================================================================
tab_pay, tab_vault, tab_ledger, tab_prompts, tab_media, tab_comeback, tab_admin = st.tabs(
    [
        "⚡ तेज़ UPI",
        "🏡 ₹15K तिजोरी",
        "📊 हिसाब & AI",
        "🚀 37 लाख+ Prompts",
        "🍗 फूड, ट्रैवल & कार्टून",
        "🔥 जीत की कहानियाँ & Games",
        "👑 Admin & Free App",
    ]
)

# ==============================================================================
# TAB 1: ULTRA-FAST PRE-PAYMENT & INSTANT UPI LAUNCHER
# ==============================================================================
with tab_pay:
    st.caption("⚡ **1-Tap तेज़ बटन (दबाते ही रकम और कारण अपने-आप भर जाएगा):**")
    q1, q2, q3, q4 = st.columns(4)
    if q1.button("☕ ₹15 चाय"):
        st.session_state.qf_cat = "Food & Mess (खाना, चिकन/मछली और टिफिन)"
        st.session_state.qf_amt = 15.0
        st.session_state.qf_desc = "सुबह की चाय / बिस्किट (Morning Tea)"
    if q2.button("🚇 ₹40 मेट्रो"):
        st.session_state.qf_cat = "Metro, Bus & Auto (आना-जाना)"
        st.session_state.qf_amt = 40.0
        st.session_state.qf_desc = "मेट्रो कार्ड रिचार्ज / बस टिकट (Metro/Bus)"
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
        spent_by_options = list(USERS_DICT.keys()) + ["Joint Family (पूरा परिवार)"]
        def_who_idx = spent_by_options.index(current_user) if current_user in spent_by_options else 0
        spent_by_val = st.selectbox("👤 किसने खर्च किया? (Spent By)", options=spent_by_options, index=def_who_idx)
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
                placeholder="जैसे: आलू-भिंडी / चिकन / ऑटो किराया",
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
                placeholder="खाली छोड़ने पर सीधा स्कैनर खुलेगा",
            )

        is_bad_chk = st.checkbox("🚨 यह गैर-ज़रूरी / फालतू खर्च (Bad Expense) है", value=auto_bad)
        notes_val = st.text_input("📌 नोट (Optional)", placeholder="कोई खास बात...")

        bricks_eq = max(1, int(amount_val // 50))
        st.caption(f"🧱 **मनोवैज्ञानिक सच:** `₹{amount_val:,.0f}` = आपके सपनों के घर की **{bricks_eq} ईंटें**।")

        submit_tx = st.form_submit_button("🚀 सेव करें और तुरंत GPay / PhonePe खोलें")

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
        st.success(f"✅ **सेव हो गया!** ₹{rec['amount']:,.0f} — **{rec['item']}** (`{rec['spent_by']}`)")

    st.markdown("#### ⚡ 1-Tap फास्ट UPI पेमेंट और स्कैनर")
    if upi_bundle["has_real_upi"]:
        pref_url = upi_bundle["prefilled_links"].get(active_app, "upi://pay")
        st.markdown(
            f'<a href="{pref_url}" class="upi-app-btn">🚀 {active_app} में सीधे ₹{active_amt:,.0f} पेमेंट खोलें</a>',
            unsafe_allow_html=True,
        )

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
# TAB 2: SEPARATE ₹15,000 DREAM HOUSE + EAR MEDICAL VAULT
# ==============================================================================
with tab_vault:
    st.markdown(
        """
        <div class="vip-card">
            <h4 style="margin:0; color:#fbbf24;">🏡 ₹15,000 अलग बचत तिजोरी (Dream House & Ear Medical Vault)</h4>
            <p style="margin:4px 0 0 0; font-size:0.86rem;">
                यह ₹15,000/महीना का फंड आपके ₹23,000 खर्च बजट से बिल्कुल अलग और सुरक्षित है।
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

    budget_overflow = max(0.0, total_spent_month - MAX_SPENDING_BUDGET)
    safe_15k = max(0.0, STRICT_SAVINGS_TARGET - budget_overflow)

    v1, v2, v3 = st.columns(3)
    v1.metric("इस महीने जमा", f"₹{vault_saved_this_month:,.0f}", "Target: ₹15,000")
    v2.metric("कुल तिजोरी फंड", f"₹{vault_saved_all_time:,.0f}", f"{int(vault_saved_all_time // 50)} ईंटें 🧱")
    v3.metric("₹15K सुरक्षा", f"₹{safe_15k:,.0f}", "100% Safe" if budget_overflow == 0 else f"-₹{budget_overflow:,.0f}")

    st.progress(min(1.0, vault_saved_this_month / STRICT_SAVINGS_TARGET), text=f"मासिक ₹15K लक्ष्य: ₹{vault_saved_this_month:,.0f} / ₹15,000")
    st.progress(min(1.0, dh_m / DREAM_HOUSE_GOAL), text=f"🏡 Dream House: ₹{dh_m:,.0f} / ₹{DREAM_HOUSE_GOAL:,} (कुल: ₹{dh_all:,.0f})")
    st.progress(min(1.0, ear_m / EAR_MEDICAL_GOAL), text=f"👂 Ear Treatment: ₹{ear_m:,.0f} / ₹{EAR_MEDICAL_GOAL:,} (कुल: ₹{ear_all:,.0f})")
    st.progress(min(1.0, emg_m / EMERGENCY_GOAL), text=f"🛡️ Emergency Fund: ₹{emg_m:,.0f} / ₹{EMERGENCY_GOAL:,} (कुल: ₹{emg_all:,.0f})")

    bricks_count = max(1, int((vault_saved_all_time + dh_m) // 50))
    st.markdown(
        f"""
        <div class="vip-card">
            <div style="font-weight:800; color:#fbbf24; margin-bottom:4px;">
                🏗️ सपनों के घर की दीवार ({bricks_count} ईंटें जुड़ चुकी हैं @ ₹50/ईंट)
            </div>
            <div style="font-size:1.25rem; line-height:1.45; word-wrap:break-word;">
                {"🧱" * min(60, bricks_count)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("vault_deposit_form", clear_on_submit=True):
        vc1, vc2, vc3 = st.columns(3)
        with vc1:
            dep_by = st.selectbox("किसने जमा किया?", list(USERS_DICT.keys()) + ["Joint Family"])
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
        v_note = st.text_input("नोट / बैंक रेफरेंस", placeholder="जैसे: SBI RD या अलग अकाउंट में जमा")
        if st.form_submit_button("🔐 तिजोरी में जमा करें"):
            add_vault_deposit(dep_by, v_bucket, v_amt, v_note)
            st.success(f"🎉 ₹{v_amt:,.0f} तिजोरी में लॉक हो गए!")
            st.rerun()

    if not df_all_vault.empty:
        st.dataframe(df_all_vault[["id", "timestamp", "deposited_by", "vault_bucket", "amount", "notes"]], use_container_width=True, hide_index=True)
        if is_admin:
            with st.expander("👑 Admin (Ajay Only): तिजोरी की गलत एंट्री डिलीट करें"):
                del_v_id = st.number_input("हटाने के लिए Vault ID डालें", min_value=1, step=1, key="del_v_id")
                if st.button("🗑️ Vault Entry हटाएं"):
                    delete_vault_deposit_from_db(int(del_v_id))
                    st.success(f"Vault ID #{int(del_v_id)} हटा दिया गया!")
                    st.rerun()


# ==============================================================================
# TAB 3: LIVE LEDGER, PERIOD SELECTOR, AI REVIEWER & AJAY ADMIN EDIT/DELETE
# ==============================================================================
with tab_ledger:
    st.markdown("### 📊 कस्टम पीरियड खर्च, रजिस्टर और 🤖 AI सलाहकार")

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
    m3.metric("इस महीने बचा बजट", f"₹{MAX_SPENDING_BUDGET - total_spent_month:,.0f}", f"आज Safe: ₹{daily_safe_limit:,.0f}")

    st.progress(min(1.0, food_spent_month / CAP_FOOD), text=f"🍲 इस महीने Food Cap: ₹{food_spent_month:,.0f} / ₹{CAP_FOOD:,}")
    st.progress(min(1.0, rent_spent_month / CAP_RENT), text=f"🏠 इस महीने Rent Cap: ₹{rent_spent_month:,.0f} / ₹{CAP_RENT:,}")

    # AI Financial Reviewer
    with st.expander("🤖 AI Financial Reviewer (अपने खर्च पर AI से सवाल पूछें)", expanded=False):
        ai_q = st.text_input(
            "💬 अपना सवाल लिखें:",
            value="इस पीरियड में मेरा सबसे ज़्यादा पैसा कहाँ जा रहा है और मैं ₹15,000 की बचत कैसे पक्की करूं?",
        )
        if st.button("🧠 AI रिव्यू रिपोर्ट देखें"):
            if df_period.empty:
                st.info("चुने गए पीरियड में कोई खर्च दर्ज नहीं है।")
            else:
                top_cat = df_period.groupby("category")["amount"].sum().sort_values(ascending=False)
                top_who = df_period.groupby("spent_by")["amount"].sum().sort_values(ascending=False)
                st.markdown(
                    f"""
                    <div class="vip-card">
                        <h4 style="color:#00ff9d; margin:0 0 6px 0;">🧠 AI Financial Review ({period_choice})</h4>
                        <ul>
                            <li><b>सबसे बड़ा खर्च:</b> <b>{top_cat.index[0]}</b> में कुल <b>₹{top_cat.iloc[0]:,.0f}</b> खर्च हुए हैं।</li>
                            <li><b>किसने सबसे ज़्यादा खर्च किया:</b> <b>{top_who.index[0]}</b> (₹{top_who.iloc[0]:,.0f})।</li>
                            <li><b>फालतू खर्च:</b> ₹{p_bad:,.0f} गैर-ज़रूरी चीजों में गए (= <b>{int(p_bad // 50)} घर की ईंटें 🧱</b>)।</li>
                            <li><b>सलाह:</b> अगले 7 दिन रोज़ का खर्च <b>₹{daily_safe_limit:,.0f}</b> से नीचे रखें।</li>
                        </ul>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

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
            fig_c = px.pie(df_period.groupby("category", as_index=False)["amount"].sum(), names="category", values="amount", hole=0.48, template="plotly_dark")
            fig_c.update_layout(margin=dict(t=10, b=10, l=5, r=5), paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#fff"))
            st.plotly_chart(fig_c, use_container_width=True)
        with ch2:
            fig_m = px.bar(df_period.groupby("spent_by", as_index=False)["amount"].sum(), x="spent_by", y="amount", color="spent_by", template="plotly_dark")
            fig_m.update_layout(margin=dict(t=10, b=10, l=5, r=5), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#fff"), showlegend=False)
            st.plotly_chart(fig_m, use_container_width=True)

        # ADMIN ONLY: Edit or Delete Wrong Entries (Strictly locked to Ajay)
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
                        new_sb = st.selectbox("Spent By", options=list(USERS_DICT.keys()) + ["Joint Family (पूरा परिवार)"])
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
        else:
            st.caption("🔒 नोट: गलत एंट्री को एडिट या डिलीट करने का अधिकार सिर्फ **Admin (Ajay)** के पास है।")


# ==============================================================================
# TAB 4: 37 LAKH+ SMART PROMPT ENGINE + SPOKEN ENGLISH + AI & TECH CLASSES
# ==============================================================================
with tab_prompts:
    st.markdown(
        """
        <div class="vip-card">
            <h4 style="margin:0; color:#00ff9d;">🚀 37,50,000+ (37 लाख+) Smart Prompt Generator & Career Lab</h4>
            <p style="margin:4px 0 0 0; font-size:0.86rem;">
                यहाँ लाखों अलग-अलग प्रॉम्प्ट्स का खजाना है! हर क्लिक पर नए प्रॉम्प्ट्स बनाएं या कस्टम प्रॉम्प्ट बिल्डर से अपना खुद का प्रॉम्प्ट तैयार करें।
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "mega_prompt_seed" not in st.session_state:
        st.session_state.mega_prompt_seed = (date.today() - date(2025, 1, 1)).days * 13

    p_col1, p_col2 = st.columns([2.3, 1.1])
    with p_col1:
        chosen_domain = st.selectbox(
            "📂 1. प्रॉम्प्ट की श्रेणी चुनें (Choose Prompt Category):",
            options=list(PROMPT_DOMAINS.keys()),
        )
    with p_col2:
        st.markdown("<div style='padding-top:24px;'></div>", unsafe_allow_html=True)
        if st.button("🎲 8 नए प्रॉम्प्ट्स लाएं"):
            st.session_state.mega_prompt_seed += random.randint(3, 999)
            st.rerun()

    generated_prompts = generate_batch_of_smart_prompts(chosen_domain, st.session_state.mega_prompt_seed, count=8)
    selected_mega_prompt = st.selectbox(
        "✨ 2. आज के ताज़ा स्मार्ट प्रॉम्प्ट्स में से चुनें (हर क्लिक पर नया):",
        options=generated_prompts,
    )

    with st.expander("🛠️ Custom Lakh-Prompt Mixer (अपनी मर्जी से Topic + Context + Style मिलाकर नया प्रॉम्प्ट बनाएं)"):
        dom_obj = PROMPT_DOMAINS[chosen_domain]
        mix_t = st.selectbox("Topic चुनें:", dom_obj["topics"])
        mix_c = st.selectbox("Context / स्थिति चुनें:", dom_obj["contexts"])
        mix_f = st.selectbox("उत्तर की स्टाइल चुनें:", PROMPT_FORMATS)
        if st.button("⚡ यह कस्टम प्रॉम्प्ट ऊपर बॉक्स में लगाएं"):
            selected_mega_prompt = f"{mix_t} — {mix_c} ({mix_f})"

    final_search_prompt = st.text_input("🔍 फाइनल सर्च / AI प्रॉम्प्ट (चाहें तो एडिट करें):", value=selected_mega_prompt)
    enc_p = urllib.parse.quote_plus(final_search_prompt)

    b_p1, b_p2, b_p3, b_p4 = st.columns(4)
    in_app_ai = b_p1.button("🤖 यहीं जवाब देखें")
    b_p2.markdown(
        f'<a href="https://www.google.com/search?q={enc_p}" target="_blank" class="upi-app-btn" style="padding:10px; font-size:0.83rem; margin:0;">🌐 Google Search</a>',
        unsafe_allow_html=True,
    )
    b_p3.markdown(
        f'<a href="https://www.youtube.com/results?search_query={enc_p}" target="_blank" class="upi-scanner-btn" style="padding:10px; font-size:0.83rem; margin:0;">▶️ YouTube पर देखें</a>',
        unsafe_allow_html=True,
    )
    b_p4.markdown(
        f'<a href="https://news.google.com/search?q={enc_p}" target="_blank" class="upi-app-btn" style="padding:10px; font-size:0.83rem; margin:0; background:linear-gradient(90deg,#38bdf8,#0284c7); color:#fff !important;">📰 Latest News</a>',
        unsafe_allow_html=True,
    )

    if in_app_ai:
        st.markdown(
            f"""
            <div class="vip-card">
                <h4 style="color:#fbbf24; margin-top:0;">🤖 AI Mentor Instant Guide:</h4>
                <p><b>चुना गया प्रॉम्प्ट:</b> <i>{final_search_prompt}</i></p>
                <ul>
                    <li><b>Step 1 (Action):</b> इसके मुख्य बिंदु को आज 15 मिनट बोलकर या लिखकर प्रैक्टिस करें।</li>
                    <li><b>Step 2 (Deep Dive):</b> ऊपर दिए गए <b>Google Search</b> या <b>YouTube पर देखें</b> बटन को दबाकर इसके लाइव उदाहरण और वीडियो तुरंत खोलें।</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    sub_eng, sub_ai, sub_road = st.tabs(
        ["🗣️ आज की Spoken English प्रैक्टिस", "🤖 AI, Python & Excel Long Videos", "🗺️ Career Checklist"]
    )

    with sub_eng:
        st.markdown(
            """
            <div class="vip-card">
                <h4 style="color:#00ff9d; margin-top:0;">🗣️ आज के 6 ऑफिस और इंटरव्यू इंग्लिश वाक्य (जोर से बोलकर अभ्यास करें):</h4>
                <ol>
                    <li><b>"I have cross-checked the report and updated the tracker."</b> (मैंने रिपोर्ट चेक करके ट्रैकर अपडेट कर दिया है।)</li>
                    <li><b>"Could you please give me 10 minutes to automate this sheet?"</b> (क्या आप मुझे इस शीट को ऑटोमेट करने के लिए 10 मिनट दे सकते हैं?)</li>
                    <li><b>"Don't worry about the mistake, I am fixing it right away."</b> (गलती की चिंता मत कीजिए, मैं इसे अभी ठीक कर रहा हूँ।)</li>
                    <li><b>"The vehicle was delayed due to heavy congestion on NH-48."</b> (NH-48 पर भारी जाम के कारण गाड़ी लेट हुई।)</li>
                    <li><b>"I am learning Python, SQL, and Generative AI every evening."</b> (मैं हर शाम Python, SQL और AI सीख रहा हूँ।)</li>
                    <li><b>"Every failure teaches me how to speak and code better."</b> (हर असफलता मुझे और बेहतर बोलना और कोडिंग करना सिखाती है।)</li>
                </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.video("https://www.youtube.com/watch?v=jul2urONzOQ")

    with sub_ai:
        tech_track = st.selectbox(
            "कोर्स चुनें:",
            [
                "🤖 Generative AI, Prompt Engineering & Latest AI Tools",
                "🐍 Python Full Course (Automation, Playwright, Pandas)",
                "📊 Advanced Excel & Power Query MIS Mastery",
                "🗄️ SQL & PySpark Data Engineering Course",
            ],
        )
        TECH_VIDEOS = {
            "🤖 Generative AI, Prompt Engineering & Latest AI Tools": [
                ("Generative AI Full Course for Beginners", "https://www.youtube.com/watch?v=mEsleV16qdo"),
                ("Build AI Web Apps with Python & Streamlit", "https://www.youtube.com/watch?v=JwSS70SZdyM"),
            ],
            "🐍 Python Full Course (Automation, Playwright, Pandas)": [
                ("Python Complete Tutorial in Hindi", "https://www.youtube.com/watch?v=UrsmFxEIp5k"),
                ("Python Pandas Data Analysis Tutorial", "https://www.youtube.com/watch?v=vmEHCJofslg"),
            ],
            "📊 Advanced Excel & Power Query MIS Mastery": [
                ("Advanced Excel Full Course (XLOOKUP, Pivot, Dashboards)", "https://www.youtube.com/watch?v=Vl0H-qTclOg"),
                ("Power Query Automation in Excel", "https://www.youtube.com/watch?v=0aeZX1l4JT4"),
            ],
            "🗄️ SQL & PySpark Data Engineering Course": [
                ("SQL Full Course for Data Engineers", "https://www.youtube.com/watch?v=HXV3zeQKqGY"),
                ("PySpark Big Data Engineering Course", "https://www.youtube.com/watch?v=_C8kWso4ne4"),
            ],
        }
        for t_title, t_url in TECH_VIDEOS[tech_track]:
            st.markdown(f"**▶️ {t_title}**")
            st.video(t_url)

    with sub_road:
        SKILLS = [
            ("sk_eng", "🗣️ Daily Spoken English & Interview Confidence"),
            ("sk_ai", "🤖 Generative AI & Prompt Engineering"),
            ("sk_exl", "📊 Advanced Excel (XLOOKUP, Pivot, Power Query)"),
            ("sk_py", "🐍 Python Core, Playwright & Pandas Automation"),
            ("sk_sql", "🗄️ SQL & Database Mastery"),
            ("sk_de", "⚡ PySpark, Streamlit & Data Engineering Portfolio"),
        ]
        prog = get_career_progress()
        done_c = 0
        for k, lbl in SKILLS:
            cur_v = prog.get(k, False)
            nv = st.checkbox(lbl, value=cur_v, key=f"sk_{k}")
            if nv != cur_v:
                set_career_progress(k, nv)
                st.rerun()
            if nv:
                done_c += 1
        st.progress(done_c / len(SKILLS), text=f"प्रगति: {done_c}/{len(SKILLS)} स्किल्स पूरी!")


# ==============================================================================
# TAB 5: CHICKEN/FISH, CHINESE/KOREAN FOOD, TRAVEL, GIRLS/LIFESTYLE, CARTOONS & NEWS
# ==============================================================================
with tab_media:
    st.markdown(
        """
        <div class="vip-card">
            <h4 style="margin:0; color:#fbbf24;">🍗 फूड & मुकबांग • 🍜 चाइनीज़/कोरियन • ✈️ ट्रैवल & Vlogs • 🎬 कार्टून, कहानियाँ & न्यूज़</h4>
            <p style="margin:4px 0 0 0; font-size:0.86rem;">
                पढ़ाई और काम के बाद मूड फ्रेश करने और घर पर ही होटल जैसा चिकन, मछली, चाइनीज़ और कोरियन खाना बनाने का पूरा हब!
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    m_sub1, m_sub2, m_sub3, m_sub4 = st.tabs(
        [
            "🍗 चिकन, मछली & देसी खाना",
            "🍜 चाइनीज़, कोरियन & Mukbang",
            "✈️ ट्रैवल, Lifestyle & Vlogs",
            "🎬 कार्टून, कहानियाँ & News",
        ]
    )

    # 1. CHICKEN, FISH & DESI FOOD
    with m_sub1:
        st.markdown("#### 🍗 देसी चिकन करी, मछली फ्राई/करी और बजट घर का खाना")
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            st.markdown("**🍗 ढाबा स्टाइल मसालेदार चिकन करी (घर पर सस्ते में)**")
            st.video("https://www.youtube.com/watch?v=CO2c3s2nB50")
            st.markdown(
                '<a href="https://www.youtube.com/results?search_query=desi+chicken+curry+recipe+home+style+shorts+hindi" target="_blank" class="upi-app-btn" style="font-size:0.84rem; padding:10px;">🍗 चिकन करी और बिरयानी Shorts खोलें</a>',
                unsafe_allow_html=True,
            )
        with f_col2:
            st.markdown("**🐟 सरसों वाली मछली करी और कुरकुरी फिश फ्राई**")
            st.video("https://www.youtube.com/watch?v=K9q6b3K35jU")
            st.markdown(
                '<a href="https://www.youtube.com/results?search_query=masala+fish+fry+and+fish+curry+desi+style+shorts+hindi" target="_blank" class="upi-scanner-btn" style="font-size:0.84rem; padding:10px;">🐟 मछली फ्राई और फिश करी Reels खोलें</a>',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        d_col1, d_col2 = st.columns(2)
        with d_col1:
            st.markdown("**🍛 ₹40 कुकर मसाला तहरी (15 मिनट में)**")
            st.video("https://www.youtube.com/watch?v=w7Wj2_T0b9A")
        with d_col2:
            st.markdown("**🥗 कुरकुरी तली हुई भिंडी (टिफिन स्पेशल)**")
            st.video("https://www.youtube.com/watch?v=3m7B92p2R7k")

    # 2. CHINESE, KOREAN FOOD & MUKBANG REELS
    with m_sub2:
        st.markdown("#### 🍜 देसी चाइनीज़, कोरियन स्ट्रीट फूड और खाना खाने वाली (Mukbang) रील्स")
        ck_c1, ck_c2 = st.columns(2)
        with ck_c1:
            st.markdown("**🍜 स्ट्रीट स्टाइल चाउमीन, मंचूरियन और मोमोज़**")
            st.video("https://www.youtube.com/watch?v=AD9h3d7X6tI")
            st.markdown(
                '<a href="https://www.youtube.com/results?search_query=desi+street+style+chowmein+manchurian+chilli+chicken+shorts" target="_blank" class="upi-app-btn" style="font-size:0.84rem; padding:10px;">🥟 चाइनीज़ चाउमीन & मोमोज़ Shorts</a>',
                unsafe_allow_html=True,
            )
        with ck_c2:
            st.markdown("**🌶️ स्पाइसी कोरियन रैमेन (Ramen), Tteokbokki & Mukbang**")
            st.video("https://www.youtube.com/watch?v=s8B4nL5k2vM")
            st.markdown(
                '<a href="https://www.youtube.com/results?search_query=korean+spicy+ramen+street+food+eating+mukbang+shorts" target="_blank" class="upi-scanner-btn" style="font-size:0.84rem; padding:10px;">🍜 Korean Food & Eating Reels खोलें</a>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '<a href="https://www.youtube.com/results?search_query=indian+spicy+chicken+fish+thali+eating+show+mukbang+shorts" target="_blank" class="upi-app-btn" style="font-size:0.9rem; padding:12px;">🍽️ स्वादिष्ट खाना खाने वाली (Desi Thali & Chicken/Fish Mukbang) Reels देखें</a>',
            unsafe_allow_html=True,
        )

    # 3. TRAVEL, GIRLS / LIFESTYLE / DANCE / FASHION VLOGS
    with m_sub3:
        st.markdown("#### ✈️ ट्रैवल व्लॉग्स, लाइफस्टाइल, डांस और ट्रेंडिंग गर्ल्स/फैशन रील्स")
        tr_c1, tr_c2 = st.columns(2)
        with tr_c1:
            st.markdown("**🏔️ खूबसूरत पहाड़, ट्रेन यात्रा और बजट ट्रैवल व्लॉग्स**")
            st.video("https://www.youtube.com/watch?v=K4TOrB7at0Y")
            st.markdown(
                '<a href="https://www.youtube.com/results?search_query=indian+budget+mountain+train+travel+vlog+shorts+hindi" target="_blank" class="upi-app-btn" style="font-size:0.84rem; padding:10px;">✈️ खूबसूरत Travel Shorts खोलें</a>',
                unsafe_allow_html=True,
            )
        with tr_c2:
            st.markdown("**💃 ट्रेंडिंग गर्ल्स व्लॉग्स, लाइफस्टाइल, डांस और रिएक्शन रील्स**")
            st.markdown(
                """
                <div class="vip-card">
                    <p style="font-size:0.86rem; margin-bottom:8px;">मूड फ्रेश करने के लिए ट्रेंडिंग लाइफस्टाइल, कॉलेज/ट्रैवल गर्ल्स व्लॉग्स, डांस और फन रील्स की सीधी फीड:</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(
                '<a href="https://www.youtube.com/results?search_query=indian+girls+lifestyle+travel+mini+vlog+dance+trending+shorts" target="_blank" class="upi-scanner-btn" style="font-size:0.86rem; padding:11px;">✨ Trending Girls Lifestyle & Mini-Vlog Reels</a>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<a href="https://www.youtube.com/results?search_query=korean+and+indian+cute+aesthetic+travel+food+vlog+shorts" target="_blank" class="upi-app-btn" style="font-size:0.86rem; padding:11px;">🌸 Korean & Desi Aesthetic Vlog Shorts</a>',
                unsafe_allow_html=True,
            )

    # 4. INDIAN CARTOONS, HINDI KAHANIYAAN & LIVE NEWS
    with m_sub4:
        st.markdown("#### 🎬 इंडियन कार्टून, मजेदार हिंदी कहानियाँ और ताज़ा खबरें (Live News)")
        cn_c1, cn_c2, cn_c3 = st.columns(3)
        with cn_c1:
            st.markdown(
                '<a href="https://www.youtube.com/results?search_query=indian+cartoon+moral+stories+chacha+chaudhary+tenali+rama+hindi" target="_blank" class="upi-app-btn" style="font-size:0.84rem; padding:11px;">🎬 इंडियन कार्टून & एनिमेशन</a>',
                unsafe_allow_html=True,
            )
        with cn_c2:
            st.markdown(
                '<a href="https://www.youtube.com/results?search_query=interesting+hindi+kahaniya+suspense+moral+story" target="_blank" class="upi-scanner-btn" style="font-size:0.84rem; padding:11px;">📖 रोचक हिंदी कहानियाँ</a>',
                unsafe_allow_html=True,
            )
        with cn_c3:
            st.markdown(
                '<a href="https://www.youtube.com/results?search_query=live+hindi+news+india+today+aaj+tak+ndtv+india" target="_blank" class="upi-app-btn" style="font-size:0.84rem; padding:11px; background:linear-gradient(90deg,#ef4444,#dc2626); color:#fff !important;">📺 Live Hindi News</a>',
                unsafe_allow_html=True,
            )

        with st.expander("📖 यहीं पढ़ें: 2-मिनट की रोचक और बुद्धिमानी भरी हिंदी कहानी", expanded=True):
            st.markdown(
                """
                **👑 कहानी: पत्थर की कीमत (अपनी असली ताकत पहचानो)**
                एक बार एक गरीब युवक एक संत के पास गया और बोला—*"गुरुजी, मैं बहुत मेहनत करता हूँ, फिर भी लोग मेरी कदर नहीं करते और कई बार काम में फेल हो जाता हूँ।"*
                संत ने उसे एक चमकदार पत्थर दिया और कहा—*"इसे पहले सब्ज़ी मंडी ले जाओ, फिर सुनार के पास, और अंत में हीरे के जौहरी के पास। बस कीमत पूछना, बेचना मत!"*
                - सब्ज़ी वाले ने कहा: *"इसे दे दो और 2 किलो आलू ले लो।"*
                - सुनार ने कहा: *"मैं इसके ₹5,000 दे सकता हूँ।"*
                - हीरे के जौहरी ने जब उसे देखा तो हाथ जोड़कर बोला: *"यह अनमोल हीरा है, मेरी पूरी दुकान बेचकर भी इसकी कीमत नहीं चुकाई जा सकती!"*

                **💡 सीख:** अगर ऑफिस में या शुरुआती करियर में कोई आपकी कीमत न समझे, तो निराश मत होइए। अपनी स्किल्स (**Python, Excel, Spoken English, AI**) को तराशते रहिए—सही जगह (Data Engineering) पहुँचते ही आपकी कीमत कई गुना बढ़ जाएगी!
                """
            )


# ==============================================================================
# TAB 6: FAILURE RECOVERY HUB (ENGLISH, CODING, OFFICE) & PLAYABLE MIND GAMES
# ==============================================================================
with tab_comeback:
    st.markdown(
        """
        <div class="vip-card">
            <h4 style="margin:0; color:#00ff9d;">🔥 फेलियर से जीत (Failure Recovery Hub) & 🧠 दिमागी खेल (Mind Games)</h4>
            <p style="margin:4px 0 0 0; font-size:0.86rem;">
                अंग्रेज़ी बोलने, सॉफ्टवेयर सीखने या ऑफिस के काम में जब भी कोई गलती या असफलता मिले—यहाँ से तुरंत अपना हौसला और रास्ता वापस पाएं!
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    fb_tab, game_tab = st.tabs(["🔥 हार से जीत की सच्ची कहानियाँ और समाधान", "🎮 दिमागी खेल (Play Mind Games)"])

    with fb_tab:
        failure_type = st.selectbox(
            "🛡️ अभी आपको किस क्षेत्र में कठिनाई या असफलता महसूस हो रही है?",
            [
                "🗣️ 1. Spoken English में अटकना, झिझक या किसी का हंसना",
                "💻 2. Software / Python / Excel सीखने में एरर आना या समझ न आना",
                "🏢 3. Office Work में गलती होना, बॉस का दबाव या प्रमोशन रुकना",
                "💸 4. अचानक बड़ा खर्च आ जाना या बजट बिगड़ जाना",
            ],
        )

        if "Spoken English" in failure_type:
            st.markdown(
                """
                <div class="vip-card">
                    <h4 style="color:#fbbf24; margin-top:0;">🗣️ जब अंग्रेज़ी बोलते समय जुबान अटक जाए या लोग हंसें — तब क्या करें?</h4>
                    <p><b>📖 सच्ची प्रेरक कहानी:</b> भारत के सबसे बड़े कीपैड और सॉफ्टवेयर लीडर्स में से कई ने 12वीं तक हिंदी माध्यम से पढ़ाई की। अपने पहले इंटरव्यू में जब वे टूटी-फूटी इंग्लिश बोले, तो इंटरव्यूअर मुस्कुरा दिया। उन्होंने हार मानने के बजाय एक नियम बनाया: <b>"मैं रोज़ रात को 10 मिनट अपने आज के काम के बारे में सिर्फ 5 लाइन इंग्लिश में बोलूंगा।"</b> 6 महीने के अंदर वही इंसान पूरी टीम को लीड करने लगा!</p>
                    <hr style="border-color:#334155;">
                    <b>🛠️ तुरंत काम करने का 3-स्टेप फॉर्मूला:</b>
                    <ol>
                        <li><b>अंग्रेज़ी एक भाषा है, बुद्धिमत्ता का पैमाना नहीं:</b> अगर कोई आपकी ग्रामर पर हंसे, तो समझ जाइए कि आपको 2 भाषाएं (हिंदी + इंग्लिश) आती हैं।</li>
                        <li><b>Template Formula अपनाएं:</b> पूरे वाक्य बनाने के बजाय 3 फिक्स ऑफिस टेम्पलेट रट लें:
                            <ul>
                                <li><i>"I am looking into this issue and will update you in 15 minutes."</i></li>
                                <li><i>"As per the latest data, here is the current status..."</i></li>
                                <li><i>"Could you please clarify this point once more?"</i></li>
                            </ul>
                        </li>
                        <li><b>2-Minute Voice Note Trick:</b> WhatsApp पर खुद के नंबर पर रोज़ 1 मिनट का इंग्लिश वॉइस नोट भेजें और सुनें। 21 दिन में झिझक 100% खत्म हो जाएगी!</li>
                    </ol>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif "Software" in failure_type:
            st.markdown(
                """
                <div class="vip-card">
                    <h4 style="color:#00ff9d; margin-top:0;">💻 जब Python / SQL कोड समझ न आए या बार-बार Error आए — तब क्या करें?</h4>
                    <p><b>📖 सच्ची कहानी:</b> लॉजिस्टिक्स ऑपरेशन में काम करने वाले एक सामान्य कर्मचारी ने जब पहली बार Python और Playwright सीखा, तो पहले 15 दिन तक उसका एक भी कोड बिना Error के नहीं चला। कई बार लगा कि "कोडिंग मेरे बस की नहीं है"। लेकिन उसने फैसला किया कि वह पूरा कोर्स रटने के बजाय <b>"अपने ऑफिस की सिर्फ 1 एक्सेल फाइल को Python से ऑटोमेट करेगा।"</b> जैसे ही पहली स्क्रिप्ट चली, उसका आत्मविश्वास आसमान छू गया!</p>
                    <hr style="border-color:#334155;">
                    <b>🛠️ कोडिंग फेलियर से निकलने का पक्का तरीका:</b>
                    <ol>
                        <li><b>Error का मतलब फेलियर नहीं है:</b> दुनिया के सबसे बड़े सीनियर इंजीनियर का कोड भी पहली बार में नहीं चलता। लाल रंग का Error आपको यह बताता है कि किस लाइन को सुधारना है।</li>
                        <li><b>Copy-Modify-Run नियम:</b> कोई भी कोड शून्य से रटकर मत लिखिए। पहले चलता हुआ कोड कॉपी करें, उसमें सिर्फ 1 बदलाव करें और चलाकर देखें।</li>
                        <li><b>20-मिनट रूल:</b> अगर 20 मिनट तक कोई बग सॉल्व न हो, तो पानी पिएं, उस Error को AI या Google में पेस्ट करें—2 सेकंड में हल मिल जाएगा!</li>
                    </ol>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif "Office Work" in failure_type:
            st.markdown(
                """
                <div class="vip-card">
                    <h4 style="color:#38bdf8; margin-top:0;">🏢 जब ऑफिस में गलती हो जाए, बॉस डांटे या काम का बोझ ज़्यादा हो — तब क्या करें?</h4>
                    <p><b>📖 मनोवैज्ञानिक सत्य:</b> ऑफिस में गलती सिर्फ उसी से होती है जो सच में काम करता है। अगर कभी रिपोर्ट में या डेटा में कोई चूक हो जाए, तो घबराकर सफाई देने के बजाय शांत दिमाग से समाधान पेश करने वाला इंसान ही सबसे ज़्यादा भरोसेमंद माना जाता है।</p>
                    <hr style="border-color:#334155;">
                    <b>🛠️ ऑफिस संकट से तुरंत बाहर निकलने के 3 नियम:</b>
                    <ol>
                        <li><b>Own + Fix + Prevent:</b> सिर्फ एक लाइन बोलें—<i>"There was a data mismatch in the previous file. I have corrected it now and added a formula check so it won't happen again."</i> (इससे बॉस का गुस्सा तुरंत शांत हो जाता है।)</li>
                        <li><b>ऑफिस की बात ऑफिस के गेट पर छोड़ें:</b> शाम को घर आते समय याद रखें कि आपकी असली पहचान आपका परिवार और आपकी नई स्किल्स हैं।</li>
                        <li><b>Silent Upgrade:</b> जब ऑफिस में लोग पॉलिटिक्स करें, तब आप चुपचाप अपना Python, SQL और Excel इतना मजबूत कर लें कि अगले 6 महीने में आपके पास उससे दोगुनी सैलरी का ऑफर हो!</li>
                    </ol>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="vip-card">
                    <h4 style="color:#f97316; margin-top:0;">💸 जब अचानक कोई बड़ा खर्च आ जाए और बजट गड़बड़ा जाए — तब क्या करें?</h4>
                    <ol>
                        <li><b>खुद को दोष मत दें:</b> परिवार और सेहत (जैसे कान का इलाज या माता-पिता की ज़रूरत) के लिए ही पैसा कमाया जाता है।</li>
                        <li><b>अगले 10 दिन 'Zero-Wastage Mode' चलाएं:</b> अगर किसी दिन ₹1,000 एक्स्ट्रा खर्च हो गया, तो अगले 10 दिनों तक बाहर की चाय, नाश्ता और ऑटो बंद करके ₹100/दिन बचाएं—बजट अपने-आप बराबर हो जाएगा!</li>
                    </ol>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ==========================================================================
    # PLAYABLE MIND GAMES (MENTAL MATH, BRAIN RIDDLES, ENGLISH WORD CHALLENGE)
    # ==========================================================================
    with game_tab:
        st.markdown("#### 🎮 दिमागी कसरत और माइंड गेम्स (Brain Sharpness Games)")
        if "mind_game_score" not in st.session_state:
            st.session_state.mind_game_score = 0

        st.metric("🏆 आपका कुल दिमागी स्कोर (Brain Score)", f"{st.session_state.mind_game_score} Points")

        g_sub1, g_sub2, g_sub3 = st.tabs(
            ["🔢 1. तेज़ हिसाब चैलेंज", "🕵️ 2. दिमागी पहेलियाँ (Riddles)", "🔤 3. English & Tech Quiz"]
        )

        # GAME 1: FAST MENTAL MATH & SAVINGS GAME
        with g_sub1:
            st.markdown("##### 🔢 गेम 1: फटाफट हिसाब लगाओ (Mental Math Sharpener)")
            if "math_q" not in st.session_state:
                a = random.randint(12, 49)
                b = random.randint(11, 39)
                op = random.choice(["+", "-", "*"])
                if op == "+":
                    ans = a + b
                elif op == "-":
                    ans = a - b
                else:
                    a, b = random.randint(6, 19), random.randint(4, 12)
                    ans = a * b
                st.session_state.math_q = f"{a} {op} {b}"
                st.session_state.math_ans = ans

            st.markdown(
                f"<div class='vip-card' style='text-align:center;'><h3>सवाल: <code>{st.session_state.math_q} = ?</code></h3></div>",
                unsafe_allow_html=True,
            )
            user_math = st.number_input("अपना जवाब लिखें:", value=0, step=1, key="math_in")
            mc1, mc2 = st.columns(2)
            if mc1.button("✅ जवाब चेक करें", key="chk_math"):
                if int(user_math) == int(st.session_state.math_ans):
                    st.session_state.mind_game_score += 10
                    st.balloons()
                    st.success("🎉 बिल्कुल सही जवाब! +10 Points मिले!")
                    del st.session_state.math_q
                else:
                    st.error(f"❌ थोड़ा चूक गए! सही जवाब {st.session_state.math_ans} था। फिर से कोशिश करें!")
            if mc2.button("🔄 नया सवाल लाएं", key="new_math"):
                if "math_q" in st.session_state:
                    del st.session_state.math_q
                st.rerun()

        # GAME 2: HINDI BRAIN RIDDLES & LOGIC PUZZLES
        with g_sub2:
            st.markdown("##### 🕵️ गेम 2: बुद्धिमान पहेलियाँ (Logic & IQ Riddles)")
            RIDDLES = [
                {
                    "q": "वह क्या है जो आपके पास जितना ज़्यादा होता है, आपको उतना ही कम दिखाई देता है?",
                    "options": ["पैसा", "अंधेरा (Darkness)", "पानी", "सपना"],
                    "ans": "अंधेरा (Darkness)",
                },
                {
                    "q": "अगर आप एक रेस में दौड़ रहे हैं और आपने दूसरे (2nd) नंबर वाले धावक को पीछे छोड़ दिया, तो अब आप किस नंबर पर हैं?",
                    "options": ["पहले (1st) नंबर पर", "दूसरे (2nd) नंबर पर", "तीसरे (3rd) नंबर पर", "चौथे नंबर पर"],
                    "ans": "दूसरे (2nd) नंबर पर",
                },
                {
                    "q": "ऐसी कौन सी चीज़ है जिसे तोड़ने पर कोई आवाज़ नहीं आती, लेकिन इंसान बहुत मजबूत बन जाता है?",
                    "options": ["कांच", "आलस और रिकॉर्ड (Laziness / Record)", "लकड़ी", "पत्थर"],
                    "ans": "आलस और रिकॉर्ड (Laziness / Record)",
                },
                {
                    "q": "एक आदमी बारिश में बिना छाते और बिना टोपी के बाहर निकला, फिर भी उसके सिर का एक भी बाल गीला नहीं हुआ। कैसे?",
                    "options": ["बारिश नकली थी", "वह गंजा था (He was bald)", "वह तेज़ भागा", "हवा चल रही थी"],
                    "ans": "वह गंजा था (He was bald)",
                },
                {
                    "q": "यदि ₹38,000 में से ₹15,000 हर महीने बचाए जाएं, तो 1 साल (12 महीने) में बिना ब्याज के कुल कितनी रकम जमा होगी?",
                    "options": ["₹1,50,000", "₹1,80,000", "₹2,00,000", "₹1,65,000"],
                    "ans": "₹1,80,000",
                },
            ]
            if "riddle_idx" not in st.session_state:
                st.session_state.riddle_idx = 0

            curr_r = RIDDLES[st.session_state.riddle_idx % len(RIDDLES)]
            st.markdown(f"<div class='vip-card'><b>पहेली:</b> {curr_r['q']}</div>", unsafe_allow_html=True)
            r_choice = st.radio("सही उत्तर चुनें:", curr_r["options"], key=f"rad_r_{st.session_state.riddle_idx}")
            rc1, rc2 = st.columns(2)
            if rc1.button("✅ पहेली का उत्तर जांचें"):
                if r_choice == curr_r["ans"]:
                    st.session_state.mind_game_score += 15
                    st.success(f"🏆 शाबाश! '{curr_r['ans']}' बिल्कुल सही है! (+15 Points)")
                else:
                    st.warning("🤔 फिर से सोचिए! एक और कोशिश करें।")
            if rc2.button("➡️ अगली पहेली"):
                st.session_state.riddle_idx += 1
                st.rerun()

        # GAME 3: SPOKEN ENGLISH & TECH QUIZ
        with g_sub3:
            st.markdown("##### 🔤 गेम 3: ऑफिस इंग्लिश और टेक क्विज़")
            QUIZ_LIST = [
                {
                    "q": "ऑफिस में 'मैं यह काम आज शाम तक पूरा कर दूंगा' को प्रोफेशनल इंग्लिश में कैसे बोलेंगे?",
                    "options": [
                        "I will complete this task by EOD today.",
                        "I am doing work night today.",
                        "Work finish evening today.",
                    ],
                    "ans": "I will complete this task by EOD today.",
                },
                {
                    "q": "Python में किसी Excel या CSV फाइल को पढ़ने के लिए Pandas का कौन-सा कमांड इस्तेमाल होता है?",
                    "options": ["pd.read_csv() / pd.read_excel()", "pd.open_file()", "python.load_sheet()"],
                    "ans": "pd.read_csv() / pd.read_excel()",
                },
                {
                    "q": "Excel में पुरानी VLOOKUP की जगह नया और सबसे तेज़ फॉर्मूला कौन-सा है?",
                    "options": ["XLOOKUP", "ZLOOKUP", "FASTLOOKUP"],
                    "ans": "XLOOKUP",
                },
            ]
            if "quiz_idx" not in st.session_state:
                st.session_state.quiz_idx = 0

            curr_q = QUIZ_LIST[st.session_state.quiz_idx % len(QUIZ_LIST)]
            st.markdown(f"<div class='vip-card'><b>सवाल:</b> {curr_q['q']}</div>", unsafe_allow_html=True)
            q_ans = st.radio("उत्तर चुनें:", curr_q["options"], key=f"q_rad_{st.session_state.quiz_idx}")
            qc_a, qc_b = st.columns(2)
            if qc_a.button("✅ क्विज़ चेक करें"):
                if q_ans == curr_q["ans"]:
                    st.session_state.mind_game_score += 20
                    st.success("🎉 एकदम परफेक्ट! +20 Points!")
                else:
                    st.error(f"सही उत्तर है: {curr_q['ans']}")
            if qc_b.button("➡️ अगला सवाल"):
                st.session_state.quiz_idx += 1
                st.rerun()


# ==============================================================================
# TAB 7: 100% AD-FREE APP DOWNLOAD + AJAY SUPER-ADMIN PANEL
# ==============================================================================
with tab_admin:
    st.markdown(
        """
        <div class="vip-card">
            <h4 style="margin:0; color:#00ff9d;">📲 100% Free & Zero-Ads Mobile App Download (बिना किसी विज्ञापन के)</h4>
            <p style="margin:6px 0 0 0; font-size:0.88rem;">
                किसी भी थर्ड-पार्टी विज्ञापन वाली वेबसाइट की ज़रूरत नहीं! नीचे दिए गए बटन से <b>100% Ad-Free Native App File</b> सीधे अपने फोन में डाउनलोड करें,
                या Chrome के 3 बिंदुओं (⋮) पर टैप करके <b>Install App</b> दबाएं।
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    clean_app_bytes = generate_zero_ad_fullscreen_app_file()
    st.download_button(
        label="📲 Download 100% Ad-Free Parivaar VIP App (Zero Ads Forever)",
        data=clean_app_bytes,
        file_name="Parivaar_VIP_4_AdFree_App.html",
        mime="text/html",
    )

    with st.expander("🛠️ अगर अलग Android .APK फाइल बिना किसी विज्ञापन (0% Ads) के मुफ्त में बनानी हो:"):
        st.markdown(
            """
            1. अपने ब्राउज़र में Microsoft की आधिकारिक फ्री वेबसाइट **[pwabuilder.com](https://www.pwabuilder.com/)** खोलें।
            2. वहां अपने इस Streamlit ऐप का लिंक पेस्ट करें और **Start** दबाएं।
            3. **Package for stores** $\rightarrow$ **Android** $\rightarrow$ **Download Package** पर टैप करें।
            4. आपको **बिना एक भी विज्ञापन (100% Ad-Free)** वाली असली `.apk` फाइल बिल्कुल मुफ्त में मिल जाएगी!
            """
        )

    st.markdown("---")
    if is_admin:
        st.markdown("### 👑 अजय सुपर एडमिन पैनल (User ID & Password Control)")
        st.info("यहाँ सिर्फ **Ajay (Admin - Password: `52729211`)** ही किसी का पासवर्ड बदल सकता है या नया यूज़र अकाउंट बना सकता है।")

        users_table_rows = []
        for u_name, u_data in USERS_DICT.items():
            users_table_rows.append(
                {
                    "Avatar": u_data["avatar"],
                    "User ID (नाम)": u_name,
                    "Current Password / PIN": u_data["password"],
                    "Role": u_data["role"],
                    "Admin Access": "👑 YES (Admin)" if u_data["is_admin"] else "👤 Member Only",
                }
            )
        st.dataframe(pd.DataFrame(users_table_rows), use_container_width=True, hide_index=True)

        adm_u1, adm_u2 = st.columns(2)
        with adm_u1:
            st.markdown("#### 🔑 पासवर्ड बदलें या नया यूज़र बनाएं")
            with st.form("admin_upsert_user_form"):
                u_name_in = st.text_input("👤 User ID (नया या पुराना नाम लिखें)", placeholder="जैसे: Ajay, Meenakshi, Ajeet, Jyoti...")
                u_pass_in = st.text_input("🔑 नया पासवर्ड / PIN", placeholder="नया पासवर्ड डालें...")
                u_role_in = st.text_input("🏷️ परिवार में भूमिका (Role)", value="Family Member")
                u_av_in = st.selectbox("😀 आइकॉन चुनें", ["👑", "👨‍💻", "👩‍💼", "🧑‍🎓", "👴", "👵", "👦", "👧"])
                u_adm_in = st.checkbox("👑 क्या इन्हें भी Admin पावर देनी है?", value=False)

                if st.form_submit_button("✅ यूज़र / पासवर्ड सेव करें"):
                    if u_name_in.strip() and u_pass_in.strip():
                        final_adm = True if u_name_in.strip().lower() == "ajay" else u_adm_in
                        upsert_user_account(u_name_in, u_pass_in, u_role_in, final_adm, u_av_in)
                        st.success(f"✅ '{u_name_in}' का अकाउंट और पासवर्ड अपडेट हो गया!")
                        st.rerun()
                    else:
                        st.error("कृपया नाम और पासवर्ड दोनों भरें!")

        with adm_u2:
            st.markdown("#### 🗑️ किसी यूज़र की एक्सेस हटाएं")
            non_ajay_users = [u for u in USERS_DICT.keys() if u.lower() != "ajay"]
            if non_ajay_users:
                del_u_target = st.selectbox("हटाने के लिए यूज़र चुनें", options=non_ajay_users)
                if st.button("🚫 इस यूज़र का अकाउंट हटाएं"):
                    delete_user_account(del_u_target)
                    st.success(f"'{del_u_target}' का अकाउंट हटा दिया गया!")
                    st.rerun()
            else:
                st.caption("हटाने के लिए कोई अतिरिक्त यूज़र नहीं है। (Ajay Admin को हटाया नहीं जा सकता)")
    else:
        st.warning("🔒 **Admin Access Restricted:** यूज़र पासवर्ड बदलने, नया अकाउंट बनाने या गलत डेटा डिलीट करने का अधिकार सिर्फ **Chief Admin (Ajay)** के पास है।")
