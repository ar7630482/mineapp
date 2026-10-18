import os
import io
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
    page_title="Parivaar VIP | Ajay Admin Edition",
    page_icon="👑",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ==============================================================================
# 2. CORE FINANCIAL CONSTANTS
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
            padding-top: 0.8rem !important;
            padding-bottom: 4.5rem !important;
            max-width: 750px !important;
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
            font-size: 1.38rem !important;
        }}

        /* Mobile Navigation Tabs */
        button[data-baseweb="tab"] {{
            background-color: #1e293b !important;
            color: #cbd5e1 !important;
            border-radius: 10px 10px 0 0 !important;
            padding: 8px 11px !important;
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
            padding: 11px 15px;
            margin-bottom: 12px;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.45);
        }}
        .psych-tag {{
            font-size: 0.74rem;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: {t['accent']};
            font-weight: 800;
            margin-bottom: 3px;
        }}
        .psych-quote {{
            font-size: 0.98rem;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.4;
        }}

        /* Daily < ₹200 Spend Dopamine Reward Card */
        .reward-banner {{
            background: linear-gradient(135deg, #065f46 0%, #047857 100%);
            border: 2px solid #34d399;
            border-radius: 14px;
            padding: 11px 15px;
            margin-bottom: 12px;
            color: #ffffff;
            font-size: 0.92rem;
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
            font-size: 0.86rem;
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
            padding: 12px 15px;
            margin-bottom: 12px;
            color: #ffffff;
            font-weight: 700;
            font-size: 0.9rem;
            animation: pulseRed 1.8s infinite;
        }}

        /* Instant UPI Buttons */
        .upi-app-btn {{
            display: block;
            width: 100%;
            text-align: center;
            background: linear-gradient(90deg, #00ff9d 0%, #10b981 100%);
            color: #022c22 !important;
            font-weight: 900;
            font-size: 1.02rem;
            padding: 13px 14px;
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
            font-size: 0.98rem;
            padding: 12px 14px;
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
# 4. SHORT, PUNCHY PSYCHIATRIST-STYLE DAILY MINDSET ENGINE (10+ YEARS)
# ==============================================================================
def get_short_psychiatrist_motivation():
    """
    Generates crisp, 1-to-2 line clinical & behavioral psychiatrist insights
    that calm anxiety, build self-control, and never repeat for 10+ years.
    """
    anchor = date(2025, 1, 1)
    today = date.today()
    day_num = max(1, (today - anchor).days + 1)

    tags = [
        "🧠 Psychiatrist Mindset Note",
        "🌿 शांत दिमाग, मज़बूत भविष्य",
        "💎 10-Second Impulse Therapy",
        "🏡 Subconscious Wealth Habits",
        "⚡ Dopamine Reset Rule",
        "🛡️ Emotional & Financial Peace",
    ]

    short_quotes = [
        "जल्दबाज़ी का खर्च थकान और तनाव की निशानी है। पेमेंट से पहले 1 गहरी सांस लें—आपका ₹15,000 का घर का सपना किसी भी 5 मिनट के लालच से बड़ा है।",
        "असली आत्मविश्वास महंगे कपड़ों से नहीं, बैंक में रखे ₹15,000 के सुरक्षित फंड और रोज़ 1 घंटा नई स्किल (Python/English) सीखने से आता है।",
        "जब आप ₹50 फालतू खर्च करने से रुकते हैं, तो आपका दिमाग कमज़ोर नहीं बल्कि और शक्तिशाली बनता है। आज सिर्फ ज़रूरत पर खर्च करें।",
        "तुलना (Comparison) दिमाग की शांति छीन लेती है, और अनुशासन (Discipline) किस्मत बदल देता है। आज अपने बजट और अपनी पढ़ाई पर टिके रहें।",
        "बाहर का जंक फूड सिर्फ 2 मिनट का नकली डोपामाइन देता है; घर का सादा खाना और बचत पूरे परिवार को असली सुरक्षा देती है।",
        "एक सफल इंसान अपने मूड के हिसाब से नहीं, अपने लक्ष्य (Dream House + Career) के हिसाब से पैसे और समय खर्च करता है।",
        "छोटी-छोटी जीत (रोज़ ₹200 से कम खर्च और 30 मिनट पढ़ाई) आपके दिमाग को अमीर और शांत बनने की ट्रेनिंग देती हैं।",
        "पैसा बचाना कंजूसी नहीं, अपने परिवार के सम्मान और कान के सही इलाज के प्रति आपका प्यार है।",
        "जब मन भटके, तो खुद से एक सवाल पूछें: 'क्या यह खर्च मुझे मेरे सपनों के घर के करीब ले जा रहा है या दूर?'",
        "शांत दिमाग ही सबसे तेज़ तरक्की करता है। आज का हिसाब साफ रखें और आज 5 नए English वाक्य व 1 नया AI/Python कॉन्सेप्ट ज़रूर सीखें।",
    ]

    micro_goals = [
        "✅ आज का माइंडसेट: खर्च ≤ ₹200 | 15 मिनट Spoken English | 30 मिनट Python/AI",
        "✅ आज का माइंडसेट: ₹0 जंक फूड | हर पेमेंट से पहले एंट्री | शांत और फोकस दिमाग",
        "✅ आज का माइंडसेट: घर का टिफिन | मेट्रो/बस की बचत | 1 नया AI/Excel टूल सीखना",
    ]

    return {
        "day": day_num,
        "date_str": today.strftime("%d %b %Y"),
        "tag": f"{tags[day_num % len(tags)]} • Day #{day_num}",
        "quote": short_quotes[(day_num * 3 + (day_num // len(short_quotes))) % len(short_quotes)],
        "goal": micro_goals[day_num % len(micro_goals)],
    }


# ==============================================================================
# 5. 5-YEAR (1,825+ DAYS) DAILY ROTATING SMART PROMPTS GENERATOR
# ==============================================================================
def get_5_year_daily_prompts(seed_offset: int = 0) -> dict:
    """
    Generates fresh, daily rotating search & practice prompts across Spoken English,
    AI Learning & News, Python/Data Engineering, Advanced Excel, and Budget Cooking for 5+ years.
    """
    day_seed = (date.today() - date(2025, 1, 1)).days + seed_offset

    english_situations = [
        "ऑफिस मीटिंग में अपनी बात आत्मविश्वास से इंग्लिश में कैसे बोलें (10 Daily Sentences)",
        "Data Engineer / Analyst जॉब इंटरव्यू में 'Tell me about yourself' का बेस्ट इंग्लिश जवाब",
        "ऑफिस में बॉस या क्लाइंट को प्रोफेशनल ईमेल और मैसेज लिखने की इंग्लिश प्रैक्टिस",
        "रोज़मर्रा की बातचीत में इस्तेमाल होने वाले 20 स्मार्ट इंग्लिश मुहावरे और वाक्य (Hindi to English)",
        "बिना अटके फोन कॉल पर इंग्लिश में बात करने की 10 मिनट की प्रैक्टिस",
        "Past, Present और Future Tense की गलतियां सुधारने की आसान बोलचाल प्रैक्टिस",
        "सैलरी बढ़ाने (Salary Negotiation) और प्रमोशन की बात इंग्लिश में कैसे करें",
        "Logistics और Operations रिपोर्ट को इंग्लिश में समझाने के 15 प्रोफेशनल वाक्य",
    ]

    ai_learning_and_news = [
        "Latest AI News & Trends This Week: नई AI टेक्नोलॉजी और टूल्स जो जॉब आसान बनाएं",
        "Prompt Engineering Mastery: ChatGPT और Gemini से Python कोड और Excel फॉर्मूला कैसे लिखवाएं",
        "AI Agents और Automation क्या हैं? फ्री AI टूल्स से रोज़ का ऑफिस काम ऑटोमेट कैसे करें",
        "Data Engineers और Analysts के लिए टॉप 5 AI Tools जो सैलरी दोगुनी कर सकते हैं",
        "Generative AI और LLM (Large Language Models) आसान हिंदी में समझें",
        "Python और Free Gemini API को जोड़कर अपना खुद का AI प्रोजेक्ट कैसे बनाएं",
        "AI की मदद से अपना Resume, LinkedIn प्रोफाइल और Interview तैयारी कैसे करें",
        "दुनिया में चल रहे नए AI मॉडल्स और टेक न्यूज़ (Latest AI Breakthroughs in Hindi)",
    ]

    python_data_eng = [
        "Python Pandas से बड़ी CSV और Excel फाइलों को 10 सेकंड में साफ (Clean) कैसे करें",
        "SQL Window Functions (ROW_NUMBER, RANK, LEAD, LAG) इंटरव्यू के असली सवालों के साथ",
        "Python Playwright और BeautifulSoup से वेब स्क्रैपिंग और ऑटोमेशन कैसे बनाएं",
        "Apache Spark (PySpark) क्या है? Data Engineer बनने के लिए पहला ETL पाइपलाइन प्रोजेक्ट",
        "Python से ऑटोमैटिक WhatsApp / Email रिपोर्ट भेजने की स्क्रिप्ट कैसे लिखें",
        "PostgreSQL और SQLite डेटाबेस को Python Streamlit डैशबोर्ड से कैसे जोड़ें",
    ]

    excel_advanced = [
        "Advanced Excel: XLOOKUP और INDEX-MATCH से हजारों रो का डेटा 5 सेकंड में कैसे मिलाएं",
        "Excel Power Query से रोज़ की गंदी रिपोर्ट को 1 क्लिक में ऑटोमैटिक साफ कैसे करें",
        "Excel Pivot Table, Slicers और Conditional Formatting से सुंदर MIS डैशबोर्ड कैसे बनाएं",
        "Excel में SUMIFS, COUNTIFS और IFERROR फॉर्मूले का असली ऑफिस डेटा पर इस्तेमाल",
    ]

    desi_khana = [
        "₹40 में 15 मिनट के अंदर कुकर में स्वादिष्ट यूपी-स्टाइल मसाला तहरी बनाने की विधि",
        "टिफिन के लिए बिना चिपचिपी कुरकुरी भिंडी और दाल फ्राई बनाने का देसी तरीका",
        "₹30 में हाई-प्रोटीन बेसन चीला और सोयाबीन-आलू की सब्ज़ी बनाने की तेज़ रेसिपी",
        "कम तेल और घर के मसालों में ढाबा जैसी आलू-गोभी या चना दाल तड़का कैसे बनाएं",
    ]

    return {
        "🗣️ Spoken English (अंग्रेज़ी बोलना सीखें - आज की प्रैक्टिस)": [
            english_situations[(day_seed + i) % len(english_situations)] for i in range(4)
        ],
        "🤖 AI Learning & Latest AI News (AI सीखें और ताज़ा खबरें)": [
            ai_learning_and_news[(day_seed + i) % len(ai_learning_and_news)] for i in range(4)
        ],
        "🐍 Python, SQL & Data Engineering (कोडिंग और ऑटोमेशन)": [
            python_data_eng[(day_seed + i) % len(python_data_eng)] for i in range(4)
        ],
        "📊 Advanced Excel & MIS Tricks (ऑफिस एक्सेल मास्टरी)": [
            excel_advanced[(day_seed + i) % len(excel_advanced)] for i in range(3)
        ],
        "🍲 Sasta Ghar Ka Khana (₹40–₹50 देसी कुकिंग)": [
            desi_khana[(day_seed + i) % len(desi_khana)] for i in range(3)
        ],
    }


# ==============================================================================
# 6. CRASH-PROOF DATABASE ENGINE (USERS, EXPENSES, VAULT, CAREER)
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
            # Ensure Ajay always has Admin rights
            conn.execute(
                text("UPDATE app_users SET is_admin = 1 WHERE username = 'Ajay'")
            )
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
                """
                INSERT OR IGNORE INTO app_users (username, password, role, is_admin, avatar)
                VALUES (?, ?, ?, ?, ?)
                """,
                (u, p, r, adm, av),
            )
        # Ensure Ajay is always Super Admin and upgrade default 1234 PIN to 52729211 if unchanged
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


# ==============================================================================
# 7. USER MANAGEMENT & CRUD FUNCTIONS (ADMIN PROTECTED)
# ==============================================================================
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
            """
            INSERT OR REPLACE INTO app_users (username, password, role, is_admin, avatar)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username.strip(), password.strip(), role.strip(), adm_int, avatar),
        )
        conn.commit()
        conn.close()


def delete_user_account(username: str):
    if username.lower() == "ajay":
        return False  # Super Admin Ajay can never be deleted
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
        conn.execute(
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
                {
                    "sb": spent_by,
                    "cat": category,
                    "item": item_name,
                    "amt": float(amount),
                    "bad": bad_int,
                    "notes": notes,
                    "id": int(expense_id),
                },
            )
    else:
        conn = get_sqlite_conn()
        conn.execute(
            """
            UPDATE expenses
            SET spent_by = ?, category = ?, item_name = ?, amount = ?, is_bad_expense = ?, notes = ?
            WHERE id = ?
            """,
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
# 8. ULTRA-FAST MULTI-APP UPI ENGINE (GPAY / PHONEPE / PAYTM / BHIM)
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


def generate_downloadable_mobile_app_html() -> bytes:
    """Creates a standalone mobile WebApp launcher file that users can download right to their phone."""
    html_content = """<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#07090f">
<title>Parivaar VIP App Launcher</title>
<style>
  body {
    margin: 0; padding: 24px; background: radial-gradient(circle at top, #1f1705 0%, #07090f 100%);
    color: #fff; font-family: sans-serif; text-align: center;
  }
  .card {
    background: #111827; border: 2px solid #fbbf24; border-radius: 18px;
    padding: 24px; max-width: 420px; margin: 40px auto; box-shadow: 0 10px 30px rgba(0,0,0,0.6);
  }
  .btn {
    display: block; background: linear-gradient(90deg, #00ff9d, #10b981); color: #022c22;
    font-weight: 900; padding: 16px; border-radius: 12px; text-decoration: none;
    font-size: 18px; margin-top: 18px;
  }
  input {
    width: 90%; padding: 12px; border-radius: 8px; border: 1px solid #fbbf24;
    background: #1e293b; color: #fff; font-size: 15px; margin-top: 10px;
  }
</style>
</head>
<body>
  <div class="card">
    <h1>👑 Parivaar VIP</h1>
    <p>Ajay, Meenakshi & Ajeet — Family Finance & Dream House App</p>
    <p style="font-size:13px; color:#fde68a;">नीचे अपने Streamlit ऐप का लिंक एक बार सेव करें और सीधे फुल-स्क्रीन ऐप खोलें:</p>
    <input type="text" id="appUrl" placeholder="https://your-app.streamlit.app" />
    <a href="#" class="btn" onclick="launchApp()">🚀 Open Full-Screen VIP App</a>
  </div>
  <script>
    const saved = localStorage.getItem('parivaar_vip_url');
    if (saved) { document.getElementById('appUrl').value = saved; }
    function launchApp() {
      const u = document.getElementById('appUrl').value.trim();
      if (u) {
        localStorage.setItem('parivaar_vip_url', u);
        window.location.href = u;
      } else {
        alert('कृपया अपने Streamlit ऐप का लिंक डालें!');
      }
    }
  </script>
</body>
</html>"""
    return html_content.encode("utf-8")


# ==============================================================================
# 9. STRICT TAB-ISOLATED LOGIN (RE-LOGIN REQUIRED ON NEW TAB / PASTE LINK)
# ==============================================================================
# Clear any URL query params so copying the URL to a new tab NEVER bypasses login!
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
            <h2 style="margin-bottom:4px; color:#fbbf24;">👑 Parivaar Wealth VIP 3.0</h2>
            <p style="font-size:0.9rem; margin-top:2px;">
                🔒 <b>Secure Tab Session:</b> नए टैब या फोन में लिंक खोलने पर सुरक्षा के लिए पासवर्ड ज़रूरी है।
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
            placeholder="अपना सुरक्षित पासवर्ड लिखें...",
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
# 10. LOGGED-IN USER & ADMIN PROFILE STATUS
# ==============================================================================
current_user = st.session_state.authenticated_user
current_user_info = USERS_DICT[current_user]
is_admin = bool(current_user_info["is_admin"])  # True ONLY for Ajay (or Admin accounts)

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

# Calculate Live Spending Metrics
if not df_month.empty:
    total_spent_month = float(df_month["amount"].sum())
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

days_in_month = calendar.monthrange(today_obj.year, today_obj.month)[1]
days_left = max(1, days_in_month - today_obj.day + 1)
remaining_monthly_budget = max(0.0, MAX_SPENDING_BUDGET - total_spent_month)
daily_safe_limit = remaining_monthly_budget / days_left

# Top Control Bar: Theme Switcher + Profile Status + Logout
top_c1, top_c2, top_c3 = st.columns([2.2, 1.5, 0.9])
with top_c1:
    chosen_theme = st.selectbox(
        "🎨 प्रीमियम थीम चुनें (Theme)",
        options=list(THEMES.keys()),
        index=list(THEMES.keys()).index(st.session_state.selected_theme),
    )
    if chosen_theme != st.session_state.selected_theme:
        st.session_state.selected_theme = chosen_theme
        st.rerun()
with top_c2:
    role_badge = "👑 SUPER ADMIN" if is_admin else "👤 MEMBER"
    st.markdown(
        f"<div style='padding-top:26px; font-weight:900; font-size:0.92rem;'>{current_user_info['avatar']} {current_user} <span style='color:#fbbf24;'>({role_badge})</span></div>",
        unsafe_allow_html=True,
    )
with top_c3:
    st.markdown("<div style='padding-top:18px;'></div>", unsafe_allow_html=True)
    if st.button("🔒 लॉगआउट"):
        st.session_state.authenticated_user = None
        st.rerun()

# Special Executive Profile Bar for Ajay (Super Admin)
if is_admin:
    st.markdown(
        f"""
        <div class="admin-badge-bar">
            👑 <b>अजय सिंह रावत — चीफ एडमिन कमांड सेंटर:</b> आपके पास गलत एंट्री सुधारने/डिलीट करने, नए यूज़र बनाने और पासवर्ड बदलने का 100% कंट्रोल है।
        </div>
        """,
        unsafe_allow_html=True,
    )

# 1. SHORT PSYCHIATRIST-STYLE DAILY MOTIVATION BANNER
mot = get_short_psychiatrist_motivation()
st.markdown(
    f"""
    <div class="psych-banner">
        <div class="psych-tag">{mot['tag']} • {mot['date_str']}</div>
        <div class="psych-quote">“{mot['quote']}”</div>
        <div style="font-size:0.8rem; color:#fde68a; margin-top:5px; font-weight:700;">{mot['goal']}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# 2. DAILY < ₹200 SPEND DOPAMINE NOTIFICATION
if spent_today <= PSYCHOLOGY_DAILY_REWARD_LIMIT:
    extra_saved = max(0.0, daily_safe_limit - spent_today)
    bricks_won = max(1, int(extra_saved // 50))
    st.markdown(
        f"""
        <div class="reward-banner">
            🏆 <b>शानदार {current_user}!</b> आज खर्च सिर्फ <b>₹{spent_today:,.0f}</b> (₹200 से कम) है!
            आपने आज <b>₹{extra_saved:,.0f} एक्स्ट्रा बचाकर</b> अपने घर की <b>+{bricks_won} नई ईंटें (🧱)</b> पक्की कर लीं!
        </div>
        """,
        unsafe_allow_html=True,
    )
elif spent_today > daily_safe_limit:
    st.markdown(
        f"""
        <div class="red-alert-banner">
            🛑 <b>आज की लिमिट पार:</b> आज ₹{spent_today:,.0f} खर्च हो चुके हैं (आज की सुरक्षित सीमा: ₹{daily_safe_limit:,.0f})। अब आज पेमेंट रोकें!
        </div>
        """,
        unsafe_allow_html=True,
    )

if food_spent_month >= 0.8 * CAP_FOOD:
    st.markdown(
        f"""
        <div class="red-alert-banner">
            🚨 <b>Food Cap 80%+ Alert:</b> खाने का खर्च ₹{food_spent_month:,.0f} / ₹{CAP_FOOD:,} पहुंच गया है! बाहर का नाश्ता बंद करें।
        </div>
        """,
        unsafe_allow_html=True,
    )

# ==============================================================================
# 11. MAIN TABS (INCLUDING ADMIN & APP DOWNLOAD TAB)
# ==============================================================================
tab_pay, tab_vault, tab_ledger, tab_learn, tab_reports, tab_admin = st.tabs(
    [
        "⚡ तेज़ पेमेंट",
        "🏡 ₹15K तिजोरी",
        "📋 खर्च हिसाब",
        "🎓 English, AI & पढ़ाई",
        "📊 पीरियड रिपोर्ट & AI",
        "👑 Admin & App" if is_admin else "📲 Download App",
    ]
)

# ==============================================================================
# TAB 1: ULTRA-FAST PRE-PAYMENT & INSTANT UPI LAUNCHER
# ==============================================================================
with tab_pay:
    st.caption("⚡ **1-Tap तेज़ बटन (दबाते ही रकम और कारण अपने-आप भर जाएगा):**")
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

    cat_list = list(CATEGORY_DESCRIPTIONS.keys())
    default_cat = st.session_state.get("qf_cat", cat_list[0])
    cat_idx = cat_list.index(default_cat) if default_cat in cat_list else 0

    c_who, c_cat = st.columns(2)
    with c_who:
        spent_by_options = list(USERS_DICT.keys()) + ["Joint Family (पूरा परिवार)"]
        def_who_idx = spent_by_options.index(current_user) if current_user in spent_by_options else 0
        spent_by_val = st.selectbox(
            "👤 किसने खर्च किया? (Spent By)",
            options=spent_by_options,
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
            "📝 विवरण चुनें (Description)",
            options=desc_list,
            index=desc_idx,
        )
    with c_app:
        selected_upi_app = st.selectbox(
            "📲 पेमेंट ऐप चुनें (UPI App / Cash)",
            options=[
                "Google Pay (GPay)",
                "PhonePe",
                "Paytm",
                "BHIM / Any UPI App",
                "Cash (नकद पेमेंट)",
                "Bank Transfer / Card",
            ],
        )

    auto_bad = "Faltu" in selected_category or "Bad" in selected_desc or "Avoid" in selected_desc

    with st.form("fast_upi_form", clear_on_submit=False):
        fc1, fc2 = st.columns([1.4, 1])
        with fc1:
            custom_item = st.text_input(
                "🏷️ सामान का नाम (चाहें तो लिखें)",
                value="" if "Custom" in selected_desc or "अन्य" in selected_desc else selected_desc,
                placeholder="जैसे: आलू-भिंडी / ऑटो किराया",
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

        is_bad_chk = st.checkbox(
            "🚨 यह गैर-ज़रूरी / फालतू खर्च (Bad Expense) है",
            value=auto_bad,
        )
        notes_val = st.text_input("📌 नोट (Optional)", placeholder="कोई खास बात...")

        bricks_eq = max(1, int(amount_val // 50))
        st.caption(f"🧱 **मनोवैज्ञानिक सच:** `₹{amount_val:,.0f}` = आपके सपनों के घर की **{bricks_eq} ईंटें**।")

        submit_tx = st.form_submit_button("🚀 सेव करें और तुरंत GPay / PhonePe खोलें")

        if submit_tx:
            final_item_name = custom_item.strip() or selected_desc
            final_is_bad = bool(
                is_bad_chk or "Faltu" in selected_category or "गैर-ज़रूरी" in need_level_val
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
            }
            st.rerun()

    # Instant 1-Tap UPI App Opener right below form (Always available + Receipt aware)
    rec = st.session_state.get("last_payment_receipt")
    active_amt = rec["amount"] if rec else 50.0
    active_item = rec["item"] if rec else "Expense"
    active_upi = rec["upi_id"] if rec else ""
    active_app = rec["upi_app"] if rec else selected_upi_app

    upi_bundle = generate_upi_links_and_qr(active_upi, active_item, active_amt, active_item)

    if rec:
        st.success(f"✅ **सेव हो गया!** ₹{rec['amount']:,.0f} — **{rec['item']}** (`{rec['spent_by']}`)")

    st.markdown("#### ⚡ 1-Tap फास्ट UPI पेमेंट और स्कैनर (बिना किसी रुकावट के)")
    if upi_bundle["has_real_upi"]:
        pref_url = upi_bundle["prefilled_links"].get(active_app, "upi://pay")
        st.markdown(
            f'<a href="{pref_url}" class="upi-app-btn">🚀 {active_app} में सीधे ₹{active_amt:,.0f} पेमेंट खोलें</a>',
            unsafe_allow_html=True,
        )

    u_c1, u_c2, u_c3 = st.columns(3)
    u_c1.markdown(
        f'<a href="{upi_bundle["direct_openers"]["Google Pay (GPay)"]}" class="upi-app-btn" style="font-size:0.88rem; padding:11px;">🟢 Open GPay</a>',
        unsafe_allow_html=True,
    )
    u_c2.markdown(
        f'<a href="{upi_bundle["direct_openers"]["PhonePe"]}" class="upi-app-btn" style="font-size:0.88rem; padding:11px; background:linear-gradient(90deg,#a855f7,#7e22ce); color:#fff !important;">🟣 Open PhonePe</a>',
        unsafe_allow_html=True,
    )
    u_c3.markdown(
        f'<a href="{upi_bundle["direct_openers"]["Paytm"]}" class="upi-app-btn" style="font-size:0.88rem; padding:11px; background:linear-gradient(90deg,#38bdf8,#0284c7); color:#fff !important;">🔵 Open Paytm</a>',
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
        st.markdown("#### 📜 तिजोरी जमा रिकॉर्ड")
        st.dataframe(df_all_vault[["id", "timestamp", "deposited_by", "vault_bucket", "amount", "notes"]], use_container_width=True, hide_index=True)

        # ADMIN ONLY: Delete wrong vault entry
        if is_admin:
            with st.expander("👑 Admin (Ajay Only): तिजोरी की गलत एंट्री डिलीट करें"):
                del_v_id = st.number_input("हटाने के लिए Vault ID डालें", min_value=1, step=1, key="del_v_id")
                if st.button("🗑️ Vault Entry हटाएं"):
                    delete_vault_deposit_from_db(int(del_v_id))
                    st.success(f"Vault ID #{int(del_v_id)} हटा दिया गया!")
                    st.rerun()


# ==============================================================================
# TAB 3: LIVE LEDGER + ADMIN-ONLY EDIT / DELETE PROTECTION
# ==============================================================================
with tab_ledger:
    st.markdown("### 📋 खर्च का पूरा रजिस्टर (Live Expense Ledger)")

    m1, m2, m3 = st.columns(3)
    m1.metric("आज का खर्च", f"₹{spent_today:,.0f}", f"Safe Limit: ₹{daily_safe_limit:,.0f}")
    m2.metric("इस महीने खर्च", f"₹{total_spent_month:,.0f}", f"बचा: ₹{MAX_SPENDING_BUDGET - total_spent_month:,.0f}")
    m3.metric("फालतू खर्च (Bad)", f"₹{bad_spent_month:,.0f}", "Target: ₹0")

    st.progress(min(1.0, food_spent_month / CAP_FOOD), text=f"🍲 Food Cap: ₹{food_spent_month:,.0f} / ₹{CAP_FOOD:,}")
    st.progress(min(1.0, rent_spent_month / CAP_RENT), text=f"🏠 Rent Cap: ₹{rent_spent_month:,.0f} / ₹{CAP_RENT:,}")
    st.progress(min(1.0, home_transfer_month / CAP_HOME_MAX), text=f"🏡 Home Transfer: ₹{home_transfer_month:,.0f} / ₹{CAP_HOME_MAX:,}")

    if not df_month.empty:
        df_show = df_month.copy()
        df_show["Status"] = df_show["is_bad_expense"].apply(lambda x: "🚨 फालतू" if x == 1 else "✅ ज़रूरी")
        cols = ["id", "timestamp", "spent_by", "category", "item_name", "amount", "upi_app", "Status", "notes"]
        for c in cols:
            if c not in df_show.columns:
                df_show[c] = ""

        st.dataframe(
            df_show[cols].rename(
                columns={
                    "id": "ID",
                    "timestamp": "समय",
                    "spent_by": "Spent By",
                    "category": "Category",
                    "item_name": "सामान",
                    "amount": "रकम (₹)",
                    "upi_app": "App",
                    "notes": "नोट",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

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
                        new_sb = st.selectbox(
                            "Spent By",
                            options=list(USERS_DICT.keys()) + ["Joint Family (पूरा परिवार)"],
                            index=0,
                        )
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
    else:
        st.info("इस महीने अभी तक कोई एंट्री नहीं है।")


# ==============================================================================
# TAB 4: 5-YEAR DAILY PROMPTS + SPOKEN ENGLISH + AI LEARNING & NEWS + TECH + KHANA
# ==============================================================================
with tab_learn:
    st.markdown(
        """
        <div class="vip-card">
            <h4 style="margin:0; color:#00ff9d;">🎓 5-Year Daily Smart Prompts: English • AI News • Python/Excel • Desi Khana</h4>
            <p style="margin:4px 0 0 0; font-size:0.86rem;">
                हर रोज़ नए प्रॉम्प्ट्स! आपको बार-बार एक ही चीज़ टाइप करने की ज़रूरत नहीं—नीचे से आज का नया प्रॉम्प्ट चुनें और 1 क्लिक में सीखें।
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "prompt_shuffle_seed" not in st.session_state:
        st.session_state.prompt_shuffle_seed = 0

    daily_prompts_map = get_5_year_daily_prompts(st.session_state.prompt_shuffle_seed)

    pr_c1, pr_c2 = st.columns([2.5, 1])
    with pr_c1:
        selected_prompt_cat = st.selectbox(
            "📚 आज आप किस विषय का नया प्रॉम्प्ट खोज़ना चाहते हैं?",
            options=list(daily_prompts_map.keys()),
        )
    with pr_c2:
        st.markdown("<div style='padding-top:24px;'></div>", unsafe_allow_html=True)
        if st.button("🎲 नए प्रॉम्प्ट्स लाएं"):
            st.session_state.prompt_shuffle_seed += 7
            st.rerun()

    prompt_list_for_cat = daily_prompts_map[selected_prompt_cat]
    chosen_ready_prompt = st.selectbox(
        "✨ आज का रेडीमेड स्मार्ट प्रॉम्प्ट चुनें (5-Year Daily Rotation):",
        options=prompt_list_for_cat,
    )

    custom_search_text = st.text_input(
        "🔍 या इसमें अपना खुद का सवाल जोड़ें / बदलें:",
        value=chosen_ready_prompt,
    )

    enc_q = urllib.parse.quote_plus(custom_search_text)
    s_b1, s_b2, s_b3, s_b4 = st.columns(4)
    ai_coach_btn = s_b1.button("🤖 यहीं जवाब देखें")
    s_b2.markdown(
        f'<a href="https://www.google.com/search?q={enc_q}" target="_blank" class="upi-app-btn" style="padding:10px; font-size:0.84rem; margin:0;">🌐 Google Search</a>',
        unsafe_allow_html=True,
    )
    s_b3.markdown(
        f'<a href="https://news.google.com/search?q={enc_q}" target="_blank" class="upi-scanner-btn" style="padding:10px; font-size:0.84rem; margin:0;">📰 Latest News</a>',
        unsafe_allow_html=True,
    )
    s_b4.markdown(
        f'<a href="https://www.youtube.com/results?search_query={enc_q}" target="_blank" class="upi-app-btn" style="padding:10px; font-size:0.84rem; margin:0; background:linear-gradient(90deg,#ef4444,#dc2626); color:#fff !important;">▶️ YouTube Video</a>',
        unsafe_allow_html=True,
    )

    if ai_coach_btn:
        st.markdown(
            f"""
            <div class="vip-card">
                <h4 style="color:#fbbf24; margin-top:0;">🤖 Instant Practice & Guide: {custom_search_text}</h4>
                <ul>
                    <li><b>🗣️ अगर यह English Practice है:</b> आज आईने के सामने खड़े होकर या परिवार के साथ कम से कम 5 मिनट इस विषय पर बोलकर अभ्यास करें: <i>"I am currently working on automating logistics reports using Python and Excel to improve team efficiency."</i></li>
                    <li><b>🤖 अगर यह AI / Data Engineering है:</b> आज इसका 1 छोटा प्रैक्टिकल कोड अपनी मशीन पर चलाएं और ऊपर दिए गए <b>Google Search</b> या <b>YouTube Video</b> बटन पर टैप करके लाइव ट्यूटोरियल देखें।</li>
                    <li><b>🍲 अगर यह देसी कुकिंग है:</b> घर के मसालों और ताज़ी सब्ज़ी से इसे कम बजट में बनाएं और बाहर के जंक फूड के ₹150 बचाएं!</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    learn_t1, learn_t2, learn_t3, learn_t4 = st.tabs(
        [
            "🗣️ Spoken English",
            "🤖 AI & Tech Long Videos",
            "🍲 देसी खाना & जोश Shorts",
            "🗺️ Career Checklist",
        ]
    )

    with learn_t1:
        st.markdown("#### 🗣️ अंग्रेज़ी बोलना सीखें — आज की प्रैक्टिस (Daily Spoken English)")
        st.markdown(
            """
            <div class="vip-card">
                <b>🎯 आज के 5 ऑफिस और इंटरव्यू इंग्लिश वाक्य (बोलकर प्रैक्टिस करें):</b>
                <ol>
                    <li><b>"Let me check the data and get back to you shortly."</b> (मैं डेटा चेक करके आपको थोड़ी देर में बताता हूँ।)</li>
                    <li><b>"I have automated this daily report using Python and Advanced Excel."</b> (मैंने इस रोज़ की रिपोर्ट को Python और Excel से ऑटोमेट कर दिया है।)</li>
                    <li><b>"Could you please share the updated file by EOD?"</b> (क्या आप आज शाम तक अपडेटेड फाइल भेज सकते हैं?)</li>
                    <li><b>"We noticed a delay due to traffic congestion on the highway."</b> (हाईवे पर जाम के कारण हमें देरी देखने को मिली।)</li>
                    <li><b>"I am upskilling myself in SQL, PySpark, and Generative AI."</b> (मैं खुद को SQL, PySpark और AI में अपग्रेड कर रहा हूँ।)</li>
                </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.video("https://www.youtube.com/watch?v=jul2urONzOQ")
        st.markdown(
            '<a href="https://www.youtube.com/results?search_query=daily+english+speaking+practice+sentences+for+office+hindi" target="_blank" class="upi-app-btn" style="padding:10px; font-size:0.88rem;">🗣️ और Spoken English प्रैक्टिस वीडियो खोलें</a>',
            unsafe_allow_html=True,
        )

    with learn_t2:
        st.markdown("#### 🤖 AI Learning, Python, Excel & Data Engineering (Long Classes)")
        tech_choice = st.selectbox(
            "कोर्स चुनें:",
            [
                "🤖 Generative AI, Prompt Engineering & AI Tools (Full Course)",
                "🐍 Python Full Mastery (Automation, Pandas & Data Science)",
                "📊 Advanced Excel & Power Query MIS Automation",
                "🗄️ SQL & PySpark Data Engineering Pipeline",
            ],
        )
        TECH_VIDS = {
            "🤖 Generative AI, Prompt Engineering & AI Tools (Full Course)": [
                ("Generative AI & ChatGPT/Gemini Mastery for Beginners", "https://www.youtube.com/watch?v=mEsleV16qdo"),
                ("Build AI Apps with Python & Free LLM APIs", "https://www.youtube.com/watch?v=JwSS70SZdyM"),
            ],
            "🐍 Python Full Mastery (Automation, Pandas & Data Science)": [
                ("Python Complete Course in Hindi", "https://www.youtube.com/watch?v=UrsmFxEIp5k"),
                ("Python Pandas Full Data Analysis Tutorial", "https://www.youtube.com/watch?v=vmEHCJofslg"),
            ],
            "📊 Advanced Excel & Power Query MIS Automation": [
                ("Advanced Excel Full Course (XLOOKUP, Pivot, Dashboards)", "https://www.youtube.com/watch?v=Vl0H-qTclOg"),
                ("Power Query Automation in Excel", "https://www.youtube.com/watch?v=0aeZX1l4JT4"),
            ],
            "🗄️ SQL & PySpark Data Engineering Pipeline": [
                ("SQL Full Course for Data Engineers", "https://www.youtube.com/watch?v=HXV3zeQKqGY"),
                ("PySpark Big Data Engineering Course", "https://www.youtube.com/watch?v=_C8kWso4ne4"),
            ],
        }
        for v_title, v_url in TECH_VIDS[tech_choice]:
            st.markdown(f"**▶️ {v_title}**")
            st.video(v_url)

    with learn_t3:
        st.markdown("#### 📱 शॉर्ट वीडियो: सस्ता घर का खाना (₹40–₹50) और मोटिवेशन")
        c_s1, c_s2 = st.columns(2)
        with c_s1:
            st.markdown("**🍛 झटपट कुकर मसाला तहरी / पुलाव**")
            st.video("https://www.youtube.com/watch?v=w7Wj2_T0b9A")
            st.markdown(
                '<a href="https://www.youtube.com/results?search_query=budget+indian+home+cooking+sabzi+dal+shorts+hindi" target="_blank" class="upi-app-btn" style="font-size:0.84rem; padding:10px;">🍲 देसी कुकिंग शॉर्ट्स खोलें</a>',
                unsafe_allow_html=True,
            )
        with c_s2:
            st.markdown("**🥗 कुरकुरी भिंडी और जोश शॉर्ट्स**")
            st.video("https://www.youtube.com/watch?v=3m7B92p2R7k")
            st.markdown(
                '<a href="https://www.youtube.com/results?search_query=middle+class+hard+work+study+motivation+shorts+hindi" target="_blank" class="upi-scanner-btn" style="font-size:0.84rem; padding:10px;">🔥 फैमिली मोटिवेशन शॉर्ट्स</a>',
                unsafe_allow_html=True,
            )

    with learn_t4:
        st.markdown("#### 🗺️ अजय का Career & Skill रोडमैप")
        SKILLS = [
            ("sk_eng", "🗣️ Daily Spoken English & Interview Communication"),
            ("sk_ai", "🤖 Generative AI, Prompt Engineering & AI Automation"),
            ("sk_exl", "📊 Advanced Excel (XLOOKUP, Pivot, Power Query)"),
            ("sk_py", "🐍 Python Core, Playwright & Pandas Data Analysis"),
            ("sk_sql", "🗄️ SQL & PostgreSQL Database Mastery"),
            ("sk_de", "⚡ PySpark, Streamlit & Data Engineering Projects"),
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
# TAB 5: PERIOD SELECTOR REPORTS & INTERACTIVE AI FINANCIAL REVIEWER
# ==============================================================================
with tab_reports:
    st.markdown("### 📊 कस्टम पीरियड रिपोर्ट और 🤖 AI खर्च सलाहकार")

    period_choice = st.selectbox(
        "📅 किस समय का खर्च और विश्लेषण देखना चाहते हैं? (Select Time Period)",
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
            cutoff = today_obj - timedelta(days=7)
            df_period = df_period[df_period["parsed_date"] >= cutoff]
        elif period_choice == "इस महीने (This Month)":
            df_period = df_period[df_period["month_year"] == current_month_str]
        elif period_choice == "पिछले 30 दिन (Last 30 Days)":
            cutoff = today_obj - timedelta(days=30)
            df_period = df_period[df_period["parsed_date"] >= cutoff]
        elif period_choice == "कस्टम तारीख चुनें (Custom Date Range)":
            d_c1, d_c2 = st.columns(2)
            with d_c1:
                start_d = st.date_input("शुरुआती तारीख (Start Date)", value=today_obj - timedelta(days=15))
            with d_c2:
                end_d = st.date_input("आखिरी तारीख (End Date)", value=today_obj)
            df_period = df_period[(df_period["parsed_date"] >= start_d) & (df_period["parsed_date"] <= end_d)]

    p_total = float(df_period["amount"].sum()) if not df_period.empty else 0.0
    p_bad = float(df_period[df_period["is_bad_expense"] == 1]["amount"].sum()) if not df_period.empty else 0.0
    p_count = len(df_period)

    r1, r2, r3 = st.columns(3)
    r1.metric("चुने गए पीरियड का खर्च", f"₹{p_total:,.0f}", f"{p_count} ट्रांजेक्शन")
    r2.metric("इसमें फालतू खर्च (Bad)", f"₹{p_bad:,.0f}", f"{(p_bad/p_total*100 if p_total else 0):.0f}% of total")
    r3.metric("ज़रूरी खर्च (Essential)", f"₹{(p_total - p_bad):,.0f}", "सही उपयोग")

    # INTERACTIVE AI FINANCIAL REVIEWER
    st.markdown("#### 🤖 AI Financial Reviewer (अपने खर्च के बारे में कुछ भी पूछें)")
    ai_q_preset = st.selectbox(
        "⚡ त्वरित सवाल चुनें या नीचे अपना सवाल लिखें:",
        options=[
            "इस पीरियड में मेरा सबसे ज़्यादा पैसा कहाँ जा रहा है और मैं कैसे बचाऊं?",
            "क्या हमारा ₹15,000 का Dream House और Ear Medical टारगेट सुरक्षित है?",
            "किस सदस्य (Spent By) ने कितना खर्च किया है और फालतू खर्च कैसे रोकें?",
            "₹7,000 के Food Budget के अंदर रहने के लिए मुझे इस हफ्ते क्या करना चाहिए?",
        ],
    )
    custom_ai_q = st.text_input("💬 या अपना सवाल यहाँ लिखें:", value=ai_q_preset)

    if st.button("🧠 AI से अपने डेटा का पूरा रिव्यू लें"):
        if df_period.empty:
            st.warning("चुने गए पीरियड में अभी कोई खर्च डेटा नहीं है।")
        else:
            top_cat_row = df_period.groupby("category")["amount"].sum().sort_values(ascending=False)
            top_cat_name = top_cat_row.index[0]
            top_cat_val = top_cat_row.iloc[0]

            top_mem_row = df_period.groupby("spent_by")["amount"].sum().sort_values(ascending=False)
            top_mem_name = top_mem_row.index[0]
            top_mem_val = top_mem_row.iloc[0]

            bricks_wasted = int(p_bad // 50)
            st.markdown(
                f"""
                <div class="vip-card">
                    <h4 style="color:#00ff9d; margin-top:0;">🧠 AI Psychiatrist & Financial Review ({period_choice})</h4>
                    <p><b>आपका सवाल:</b> <i>"{custom_ai_q}"</i></p>
                    <ul>
                        <li><b>1. सबसे बड़ा खर्च (Top Category):</b> इस पीरियड में सबसे ज़्यादा पैसा <b>{top_cat_name}</b> में गया है (<b>₹{top_cat_val:,.0f}</b>)।</li>
                        <li><b>2. सदस्य विश्लेषण (Spent By):</b> सबसे अधिक ट्रांजेक्शन <b>{top_mem_name}</b> द्वारा (<b>₹{top_mem_val:,.0f}</b>) किए गए हैं।</li>
                        <li><b>3. फालतू खर्च की जांच:</b> इस दौरान <b>₹{p_bad:,.0f}</b> गैर-ज़रूरी चीजों पर खर्च हुए। अगर इसे रोका जाता, तो आपके सपनों के घर में <b>+{bricks_wasted} नई ईंटें (🧱)</b> और जुड़तीं!</li>
                        <li><b>4. आज का एक्शन प्लान:</b> अगले 7 दिनों तक रोज़ का खर्च <b>₹{daily_safe_limit:,.0f}/दिन</b> के अंदर रखें और बाहर के स्नैक्स/ऑटो पर ₹0 खर्च करें।</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if not df_period.empty:
        ch1, ch2 = st.columns(2)
        with ch1:
            st.markdown("##### 🍩 श्रेणी के अनुसार खर्च")
            cat_df = df_period.groupby("category", as_index=False)["amount"].sum()
            fig_c = px.pie(cat_df, names="category", values="amount", hole=0.48, template="plotly_dark")
            fig_c.update_layout(margin=dict(t=15, b=15, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#fff"))
            st.plotly_chart(fig_c, use_container_width=True)

        with ch2:
            st.markdown("##### 👨‍👩‍👦 सदस्य के अनुसार खर्च (`Spent By`)")
            mem_df = df_period.groupby("spent_by", as_index=False)["amount"].sum()
            fig_m = px.bar(mem_df, x="spent_by", y="amount", color="spent_by", template="plotly_dark")
            fig_m.update_layout(margin=dict(t=15, b=15, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#fff"), showlegend=False)
            st.plotly_chart(fig_m, use_container_width=True)


# ==============================================================================
# TAB 6: AJAY SUPER-ADMIN USER/PASSWORD PANEL + DOWNLOAD APP TO PHONE
# ==============================================================================
with tab_admin:
    # 1. DOWNLOAD APP TO PHONE SECTION (AVAILABLE TO ALL FAMILY MEMBERS)
    st.markdown(
        """
        <div class="vip-card">
            <h4 style="margin:0; color:#00ff9d;">📲 फोन में यह ऐप डाउनलोड और इंस्टॉल करें (Download Mobile App)</h4>
            <p style="margin:5px 0 0 0; font-size:0.88rem;">
                नीचे दिए गए बटन से अपने फोन में <b>Parivaar VIP App Launcher</b> डाउनलोड करें, या Chrome के मेनू (⋮) से <b>Install App / Add to Home Screen</b> दबाएं।
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    app_launcher_bytes = generate_downloadable_mobile_app_html()
    st.download_button(
        label="📲 Download Parivaar VIP Mobile App Launcher (.html)",
        data=app_launcher_bytes,
        file_name="Parivaar_VIP_App.html",
        mime="text/html",
    )

    # 2. STRICT ADMIN-ONLY USER & PASSWORD MANAGEMENT PANEL (ONLY FOR AJAY)
    st.markdown("---")
    if is_admin:
        st.markdown("### 👑 अजय सुपर एडमिन पैनल (User ID & Password Control)")
        st.info("यहाँ सिर्फ **Ajay (Admin)** ही किसी का पासवर्ड बदल सकता है या नया यूज़र अकाउंट बना सकता है।")

        # Show current users table (including passwords for Admin Ajay)
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
                        # Keep Ajay always Admin even if unchecked accidentally
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
