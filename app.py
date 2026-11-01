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
    page_title="Parivaar OS 6.0 | Ultimate Interactive Super-App",
    page_icon="👑",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ==============================================================================
# 2. DEFAULT MASTER SETTINGS, GOALS & USERS (100% EDITABLE IN MASTER HUB)
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
    ("Ajay", "52729211", "👑 Chief Admin • Universal Parivaar Account", 1, "👑"),
    ("Meenakshi", "2345", "👩‍💼 Partner • Universal Parivaar Account", 0, "👩‍💼"),
    ("Ajeet", "3456", "🧑‍🎓 Family Member • Universal Parivaar Account", 0, "🧑‍🎓"),
]

CATEGORY_DESCRIPTIONS = {
    "Shopping & Clothes (साड़ी, कपड़े और शॉपिंग)": [
        "साड़ी / सूट / कुर्ती शॉपिंग (Saree & Ethnic)",
        "फॉर्मल शर्ट / ट्राउज़र / ऑफिस वियर",
        "जूते / सैंडल / फॉर्मल बूट्स (Footwear)",
        "स्किनकेयर / सनस्क्रीन / डेली केयर",
        "त्योहार या परिवार की शॉपिंग",
        "अन्य शॉपिंग सामान (Custom Shopping)...",
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
        "अन्य खाने का खर्च (Custom Food Item)...",
    ],
    "Sabzi & Kirana (सब्ज़ी और राशन)": [
        "रोज़ की हरी सब्ज़ी (आलू, प्याज, भिंडी, टमाटर)",
        "आटा, चावल, दाल, सत्तू और चना (Monthly Grocery)",
        "मसाले, तेल और रसोई का सामान",
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
# 3. 5 ULTRA-INTERACTIVE INSTAGRAM / YOUTUBE / CRED NEO-GLASS THEMES
# ==============================================================================
THEMES = {
    "🔥 Insta-Reels Neon Glass (Instagram & YouTube Dark Mode)": {
        "bg_main": "radial-gradient(circle at 15% 10%, #240a30 0%, #090a10 55%, #040407 100%)",
        "card_bg": "rgba(18, 21, 33, 0.90)",
        "card_border": "#ec4899",
        "accent": "#f43f5e",
        "accent_sec": "#fbbf24",
        "story_grad": "linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%)",
        "banner_grad": "linear-gradient(135deg, #3b0764 0%, #111827 55%, #831843 100%)",
    },
    "💎 CRED Royal Obsidian Gold (प्रीमियम नियो-बैंक लक्ज़री)": {
        "bg_main": "radial-gradient(circle at 20% 0%, #291d06 0%, #0b0e17 60%, #04060a 100%)",
        "card_bg": "rgba(17, 24, 39, 0.92)",
        "card_border": "#fbbf24",
        "accent": "#fbbf24",
        "accent_sec": "#00ff9d",
        "story_grad": "linear-gradient(135deg, #fbbf24 0%, #f59e0b 50%, #10b981 100%)",
        "banner_grad": "linear-gradient(135deg, #451a03 0%, #111827 55%, #064e3b 100%)",
    },
    "⚡ Cyber Emerald Matrix (पैसा और ग्रोथ फोकस)": {
        "bg_main": "radial-gradient(circle at 50% 0%, #042f2e 0%, #070b14 65%, #030509 100%)",
        "card_bg": "rgba(15, 23, 42, 0.92)",
        "card_border": "#00ff9d",
        "accent": "#00ff9d",
        "accent_sec": "#38bdf8",
        "story_grad": "linear-gradient(135deg, #00ff9d 0%, #06b6d4 50%, #3b82f6 100%)",
        "banner_grad": "linear-gradient(135deg, #064e3b 0%, #0f172a 55%, #1e1b4b 100%)",
    },
    "🌌 Cosmic Creator Studio (डीप फोकस और कोडिंग नाइट)": {
        "bg_main": "radial-gradient(circle at 80% 10%, #1e1b4b 0%, #090d16 60%, #030408 100%)",
        "card_bg": "rgba(19, 17, 38, 0.92)",
        "card_border": "#818cf8",
        "accent": "#a855f7",
        "accent_sec": "#38bdf8",
        "story_grad": "linear-gradient(135deg, #a855f7 0%, #6366f1 50%, #38bdf8 100%)",
        "banner_grad": "linear-gradient(135deg, #311042 0%, #0f172a 55%, #0c4a6e 100%)",
    },
    "🔥 Agni Hustle (जोश और अनुशासन)": {
        "bg_main": "radial-gradient(circle at top, #2a0a12 0%, #08070c 100%)",
        "card_bg": "rgba(24, 16, 24, 0.92)",
        "card_border": "#f97316",
        "accent": "#fb923c",
        "accent_sec": "#fbbf24",
        "story_grad": "linear-gradient(135deg, #f97316 0%, #ef4444 50%, #eab308 100%)",
        "banner_grad": "linear-gradient(135deg, #431407 0%, #181018 55%, #3b0764 100%)",
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
            max-width: 860px !important;
        }}

        label, .stWidgetLabel, .stMarkdown p, .stMarkdown li, span, h1, h2, h3, h4, h5, h6 {{
            color: #ffffff !important;
        }}

        /* High-Contrast Inputs & Dropdowns */
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        div[data-baseweb="base-input"],
        input, textarea {{
            background-color: #161b26 !important;
            color: #ffffff !important;
            border: 1.5px solid rgba(255,255,255,0.22) !important;
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
            border: 1px solid rgba(255,255,255,0.16) !important;
            border-top: 3.5px solid {t['accent']} !important;
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

        /* Pill Navigation Tabs (Instagram / YouTube Chip Bar Style) */
        button[data-baseweb="tab"] {{
            background-color: rgba(30, 41, 59, 0.78) !important;
            color: #cbd5e1 !important;
            border-radius: 999px !important;
            padding: 7px 14px !important;
            margin-right: 5px !important;
            margin-bottom: 5px !important;
            font-weight: 700 !important;
            font-size: 0.83rem !important;
            border: 1px solid rgba(255,255,255,0.14) !important;
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

        /* Animated Royal Hero Poster */
        @keyframes glowPulse {{
            0% {{ box-shadow: 0 0 12px rgba(251, 191, 36, 0.35); }}
            50% {{ box-shadow: 0 0 26px rgba(244, 63, 94, 0.55); }}
            100% {{ box-shadow: 0 0 12px rgba(251, 191, 36, 0.35); }}
        }}
        @keyframes floatCrown {{
            0%, 100% {{ transform: translateY(0px) rotate(0deg); }}
            50% {{ transform: translateY(-5px) rotate(4deg); }}
        }}
        .hero-poster {{
            background: {t['banner_grad']};
            border: 2px solid {t['accent_sec']};
            border-radius: 18px;
            padding: 14px 18px;
            margin-bottom: 10px;
            animation: glowPulse 4s infinite ease-in-out;
        }}
        .logo-badge {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 54px;
            height: 54px;
            border-radius: 16px;
            background: {t['story_grad']};
            color: #ffffff;
            font-size: 1.9rem;
            font-weight: 900;
            box-shadow: 0 6px 18px rgba(244, 63, 94, 0.5);
            animation: floatCrown 3s infinite ease-in-out;
            margin-right: 14px;
            flex-shrink: 0;
            border: 1.5px solid #ffffff;
        }}
        .motivation-poster {{
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 60%, #064e3b 100%);
            border: 1.5px solid {t['accent_sec']};
            border-left: 8px solid {t['accent']};
            border-radius: 16px;
            padding: 12px 16px;
            margin-bottom: 10px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }}

        /* Instagram Stories Goal Bar */
        .insta-story-bar {{
            display: flex;
            gap: 12px;
            overflow-x: auto;
            padding: 8px 4px 10px 4px;
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

        /* 3D Virtual Universal Bank Card */
        .universal-bank-card {{
            background: linear-gradient(135deg, #090d16 0%, #1e293b 50%, #3b0764 100%);
            border: 2px solid {t['accent_sec']};
            border-radius: 20px;
            padding: 16px 20px;
            margin-bottom: 12px;
            box-shadow: 0 12px 30px rgba(0,0,0,0.65);
        }}
        .bank-chip {{
            width: 44px;
            height: 32px;
            border-radius: 7px;
            background: linear-gradient(135deg, #fde68a 0%, #d97706 100%);
            border: 1px solid #ffffff;
            display: inline-block;
        }}

        /* Glass Cards */
        .neo-card {{
            background: {t['card_bg']};
            backdrop-filter: blur(18px);
            border: 1px solid rgba(255,255,255,0.15);
            border-left: 5px solid {t['accent']};
            border-radius: 18px;
            padding: 15px 18px;
            margin-bottom: 12px;
            box-shadow: 0 10px 28px rgba(0,0,0,0.45);
        }}

        /* Expected vs Actual Highlight Badges */
        .badge-saved {{
            background: linear-gradient(90deg, rgba(16,185,129,0.25), rgba(5,150,105,0.45));
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
        .upi-scanner-btn {{
            display: block; width: 100%; text-align: center;
            background: linear-gradient(90deg, #fbbf24 0%, #f59e0b 100%);
            color: #090d16 !important; font-weight: 900; font-size: 0.94rem;
            padding: 11px 14px; border-radius: 12px; text-decoration: none !important;
            margin: 5px 0; border: 1.5px solid #ffffff;
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
    <div style="background:rgba(15,23,42,0.90); border:1.5px solid {color_hex}; border-radius:18px; padding:12px; text-align:center; box-shadow:0 8px 20px rgba(0,0,0,0.45);">
        <div style="font-size:0.78rem; font-weight:800; color:#cbd5e1; margin-bottom:6px;">{title}</div>
        <svg viewBox="0 0 36 36" style="width:86px; height:86px; display:block; margin:0 auto;">
            <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none" stroke="#1e293b" stroke-width="3.5"/>
            <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none" stroke="{color_hex}" stroke-width="3.5"
                  stroke-dasharray="{dash_array}" stroke-linecap="round"/>
            <text x="18" y="19.5" fill="#ffffff" font-size="7.2" font-weight="900" text-anchor="middle">{pct:.0f}%</text>
            <text x="18" y="25.5" fill="#fde68a" font-size="3.5" font-weight="700" text-anchor="middle">STATUS</text>
        </svg>
        <div style="font-size:0.98rem; font-weight:900; color:{color_hex}; margin-top:6px;">{amount_str}</div>
        <div style="font-size:0.72rem; color:#fde68a; font-weight:700;">{subtitle}</div>
    </div>
    """


# ==============================================================================
# 4. POSTER SLIDES & PSYCHIATRIST MOTIVATION ENGINE
# ==============================================================================
POSTER_SLIDES = [
    {
        "badge": "👑 PARIVAAR OS 6.0 • UNIVERSAL BANK",
        "title": "एक परिवार • एक तिजोरी • एक बड़ा सपना!",
        "sub": "₹38,000 Universal Pool में से ₹15,000 सीधा सपनों के घर और सेहत के लिए लॉक, और ₹23,000 में स्मार्ट गृहस्थी!",
        "quote_hi": "“जब पति-पत्नी का लक्ष्य एक होता है, तो हर बचाया हुआ रुपया दोगुनी ताकत से काम करता है।”",
        "psych_tip": "🧠 Psychiatrist Insight: बाज़ार जाने से पहले 'Expected' और खरीदने के बाद 'Actual' देखने से फालतू खर्च 68% तक तुरंत घट जाता है।",
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
        "challenge": "🎯 आज का मिशन: शॉपिंग या बाज़ार जाते समय 'Expected vs Actual' में पहले अपना बजट दर्ज करें!",
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


def render_hero_poster_and_motivation():
    poster = get_daily_poster_and_motivation(st.session_state.get("poster_slide_idx", 0))
    st.markdown(
        f"""
        <div class="hero-poster">
            <div style="display:flex; align-items:center;">
                <div class="logo-badge">👑</div>
                <div>
                    <div style="font-size:0.72rem; font-weight:900; color:#00ff9d; letter-spacing:1px;">
                        {poster['badge']} • DAY #{poster['day']} ({poster['date_str']})
                    </div>
                    <div style="font-size:1.18rem; font-weight:900; color:#ffffff; margin-top:2px;">
                        {poster['title']}
                    </div>
                    <div style="font-size:0.83rem; color:#fde68a; margin-top:2px;">
                        {poster['sub']}
                    </div>
                </div>
            </div>
        </div>
        <div class="motivation-poster">
            <div style="font-size:0.74rem; font-weight:900; color:#fbbf24; text-transform:uppercase; letter-spacing:0.8px;">
                ✨ आज का पावर मोटिवेशन पोस्टर (Daily Mindset Poster)
            </div>
            <div style="font-size:1.0rem; font-weight:800; color:#ffffff; margin:5px 0; line-height:1.4;">
                {poster['quote_hi']}
            </div>
            <div style="font-size:0.83rem; color:#a7f3d0; background:rgba(0,0,0,0.38); padding:7px 10px; border-radius:10px; margin-top:4px;">
                {poster['psych_tip']}
            </div>
            <div style="font-size:0.81rem; color:#fde68a; font-weight:800; margin-top:6px;">
                {poster['challenge']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==============================================================================
# 5. PERSISTENT DATABASE + CLOUD POSTGRES + AUTO JSON MIRROR SHIELD
# ==============================================================================
DB_FILE = "parivaar_vip_v6.db"
BACKUP_MIRROR_FILE = "parivaar_auto_mirror_v6.json"


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

    # 7. Psychological Urge Victories Table
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

    # 8. Career Progress Table
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
# 6. ALL CRUD & MIRROR BACKUP FUNCTIONS
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


def delete_vault_deposit_from_db(vault_id: int):
    conn = get_sqlite_conn()
    conn.execute("DELETE FROM vault_deposits WHERE id = ?", (int(vault_id),))
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


def get_career_progress() -> dict:
    conn = get_sqlite_conn()
    rows = conn.execute("SELECT skill_key, completed FROM career_progress").fetchall()
    conn.close()
    return {r[0]: bool(r[1]) for r in rows}


def set_career_progress(skill_key: str, completed: bool):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_sqlite_conn()
    conn.execute(
        "INSERT OR REPLACE INTO career_progress (skill_key, completed, updated_at) VALUES (?, ?, ?)",
        (skill_key, 1 if completed else 0, now_str),
    )
    conn.commit()
    conn.close()
    export_full_backup_json()


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


def delete_user_account(username: str):
    if username.lower() == "ajay":
        return False
    conn = get_sqlite_conn()
    conn.execute("DELETE FROM app_users WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return True


def export_full_backup_json() -> str:
    data = {
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "master_settings": {k: v["val"] for k, v in get_master_settings_dict().items()},
        "custom_goals": fetch_goals_df().to_dict(orient="records"),
        "shopping_planner": fetch_shopping_df().to_dict(orient="records"),
        "expenses": fetch_all_expenses_df().drop(columns=["parsed_date"], errors="ignore").to_dict(orient="records"),
        "vault_deposits": fetch_vault_df().to_dict(orient="records"),
        "urge_victories": fetch_urge_victories_df().to_dict(orient="records"),
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
        for row in payload.get("vault_deposits", []):
            cur.execute(
                "INSERT OR REPLACE INTO vault_deposits (id, timestamp, month_year, deposited_by, vault_bucket, amount, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (row.get("id"), row.get("timestamp"), row.get("month_year"), row.get("deposited_by", "Ajay"), row.get("vault_bucket", "🏡 Dream House"), float(row.get("amount", 0)), row.get("notes", "")),
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
# 7. 37 LAKH+ SMART PROMPT ENGINE + IN-APP MULTI-ANGLE YOUTUBE SHORTS
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
# 8. UPI QR GENERATOR, GOAL BRIDGE & ZERO-AD NATIVE WEBAPP GENERATOR
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

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=6, border=2)
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


def render_goal_bridge_widget(module_key: str, suggested_amt: float, reason_label: str):
    """Connects saved money from ANY module directly into the user's chosen Life Goal."""
    goals_df = fetch_goals_df()
    if goals_df.empty:
        return
    st.markdown(
        f"""
        <div style="background:linear-gradient(90deg, rgba(16,185,129,0.20), rgba(244,63,94,0.20)); border:1.5px dashed #00ff9d; border-radius:14px; padding:10px 14px; margin-top:10px;">
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


def generate_zero_ad_fullscreen_app_file() -> bytes:
    html_code = """<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#07090f">
<title>Parivaar OS 6.0 (Zero-Ad Native App)</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body, html { width: 100%; height: 100%; background: #07090f; color: #fff; font-family: sans-serif; overflow: hidden; }
  #setupBox {
    display: flex; flex-direction: column; justify-content: center; align-items: center;
    height: 100vh; padding: 20px; text-align: center;
    background: radial-gradient(circle at top, #240a30 0%, #07090f 100%);
  }
  .card {
    background: #111827; border: 2px solid #f43f5e; border-radius: 18px;
    padding: 24px; max-width: 400px; width: 100%; box-shadow: 0 12px 32px rgba(0,0,0,0.7);
  }
  input {
    width: 100%; padding: 14px; border-radius: 10px; border: 1.5px solid #fbbf24;
    background: #1e293b; color: #fff; font-size: 15px; margin: 14px 0; font-weight: bold;
  }
  button {
    width: 100%; padding: 15px; border-radius: 12px; border: none;
    background: linear-gradient(90deg, #f43f5e, #fbbf24); color: #ffffff;
    font-size: 17px; font-weight: 900; cursor: pointer;
  }
  #appFrame { width: 100vw; height: 100vh; border: none; display: none; }
</style>
</head>
<body>
  <div id="setupBox">
    <div class="card">
      <h2 style="color:#fbbf24; margin-bottom:8px;">👑 Parivaar OS 6.0</h2>
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
# 9. LOGIN SCREEN & DYNAMIC MASTER CONSTANTS INITIALIZATION
# ==============================================================================
if len(st.query_params) > 0:
    st.query_params.clear()

if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None
if "poster_slide_idx" not in st.session_state:
    st.session_state.poster_slide_idx = 0
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
DAILY_REWARD_LIMIT = MASTER_CFG["daily_reward_limit"]["val"]
BRICK_PRICE = max(10.0, MASTER_CFG["brick_price"]["val"])


def render_login_screen():
    render_hero_poster_and_motivation()
    with st.form("strict_login_form"):
        st.markdown("#### 🔐 Parivaar OS 6.0 • Universal Bank & Super-App लॉगिन")
        user_options = list(USERS_DICT.keys())
        selected_user = st.selectbox(
            "👤 अपना अकाउंट चुनें (Universal Family Account)",
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
# 10. LIVE METRICS, POSTER, INSTAGRAM STORIES BAR & 3D UNIVERSAL BANK CARD
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
urge_saved_total = float(df_urges["amount_saved"].sum()) if not df_urges.empty else 0.0

days_in_month = calendar.monthrange(today_obj.year, today_obj.month)[1]
days_left = max(1, days_in_month - today_obj.day + 1)

remaining_spendable_balance = max(0.0, MAX_SPENDING_BUDGET - total_spent_month)
budget_overflow = max(0.0, total_spent_month - MAX_SPENDING_BUDGET)
effective_monthly_savings = max(0.0, STRICT_SAVINGS_VAULT - budget_overflow)
live_total_bank_balance = remaining_spendable_balance + effective_monthly_savings
daily_safe_limit = remaining_spendable_balance / days_left
spend_utilization_pct = min(100.0, (total_spent_month / MAX_SPENDING_BUDGET) * 100.0) if MAX_SPENDING_BUDGET > 0 else 0.0
saving_health_pct = (effective_monthly_savings / STRICT_SAVINGS_VAULT) * 100.0 if STRICT_SAVINGS_VAULT > 0 else 100.0

# Top Bar: Theme + Next Poster + Willpower XP + Logout
top_c1, top_c2, top_c3, top_c4 = st.columns([2.0, 1.1, 1.1, 0.8])
with top_c1:
    chosen_theme = st.selectbox(
        "🎨 Interactive UI Theme",
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
    if st.button(f"⚡ XP: {st.session_state.willpower_xp} (+10)"):
        st.session_state.willpower_xp += 10
        st.balloons()
with top_c4:
    st.markdown("<div style='padding-top:18px;'></div>", unsafe_allow_html=True)
    if st.button("🔒 लॉगआउट"):
        st.session_state.authenticated_user = None
        st.rerun()

# Render Animated Logo, Moving Poster & Psychiatrist Motivation Card
render_hero_poster_and_motivation()

# Render Instagram Stories Goal Rings Bar
stories_html = '<div class="insta-story-bar">'
stories_html += f"""
<div class="insta-story-item">
    <div class="insta-ring">
        <div class="insta-inner">
            <span style="font-size:1.1rem;">🏦</span>
            <span style="font-size:0.65rem; font-weight:900; color:#00ff9d;">{100 - spend_utilization_pct:.0f}%</span>
        </div>
    </div>
    <div class="insta-label">बचा खर्च बजट</div>
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
    <div class="insta-sub">{len(df_urges)} Won</div>
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

# 3D Universal Family Bank Card
st.markdown(
    f"""
    <div class="universal-bank-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <div>
                <div style="font-size:0.72rem; color:#fde68a; font-weight:800; letter-spacing:1.2px;">
                    🏦 PARIVAAR UNIVERSAL WEALTH BANK (एक ही संयुक्त परिवार खाता)
                </div>
                <div style="font-size:1.12rem; font-weight:900; color:#ffffff;">
                    {current_user_info['avatar']} AJAY & MEENAKSHI UNIVERSAL ACCOUNT
                </div>
            </div>
            <div class="bank-chip"></div>
        </div>
        <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:8px; background:rgba(0,0,0,0.45); padding:10px 12px; border-radius:12px; border:1px solid rgba(255,255,255,0.14);">
            <div>
                <div style="font-size:0.7rem; color:#cbd5e1;">कुल मासिक पूल</div>
                <div style="font-size:1.02rem; font-weight:900; color:#fbbf24;">₹{UNIVERSAL_FAMILY_POOL:,.0f}</div>
            </div>
            <div>
                <div style="font-size:0.7rem; color:#cbd5e1;">खर्च के लिए बचा</div>
                <div style="font-size:1.02rem; font-weight:900; color:#00ff9d;">₹{remaining_spendable_balance:,.0f}</div>
            </div>
            <div>
                <div style="font-size:0.7rem; color:#cbd5e1;">इस महीने खर्च</div>
                <div style="font-size:1.02rem; font-weight:900; color:#f43f5e;">₹{total_spent_month:,.0f} ({spend_utilization_pct:.0f}%)</div>
            </div>
            <div>
                <div style="font-size:0.7rem; color:#cbd5e1;">सुरक्षित बचत (Vault)</div>
                <div style="font-size:1.02rem; font-weight:900; color:#38bdf8;">₹{effective_monthly_savings:,.0f} ({saving_health_pct:.0f}%)</div>
            </div>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:0.76rem; color:#fde68a; margin-top:8px; font-weight:700;">
            <span>💳 A/C: 6000-PARIVAAR-UNIFIED</span>
            <span>🛡️ आज की सुरक्षित सीमा: ₹{daily_safe_limit:,.0f}/दिन</span>
            <span>🧱 कुल घर ईंटें: {int((vault_saved_all_time + effective_monthly_savings) // BRICK_PRICE)} Bricks</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# 3 Animated Circular SVG Ring Gauges
rg1, rg2, rg3 = st.columns(3)
with rg1:
    st.markdown(
        render_svg_ring_gauge(
            "💳 मासिक खर्च मीटर (Spend)",
            f"बचा है: ₹{remaining_spendable_balance:,.0f}",
            spend_utilization_pct,
            f"₹{total_spent_month:,.0f} / ₹{MAX_SPENDING_BUDGET:,.0f}",
            "#f43f5e" if spend_utilization_pct > 85 else "#00ff9d",
        ),
        unsafe_allow_html=True,
    )
with rg2:
    st.markdown(
        render_svg_ring_gauge(
            "🔐 पक्की बचत तिजोरी (Vault)",
            f"{int(effective_monthly_savings // BRICK_PRICE)} ईंटें 🧱 सुरक्षित",
            saving_health_pct,
            f"₹{effective_monthly_savings:,.0f} / ₹{STRICT_SAVINGS_VAULT:,.0f}",
            "#fbbf24",
        ),
        unsafe_allow_html=True,
    )
with rg3:
    sh_budget_live = float(df_shopping["trip_budget"].iloc[0]) if not df_shopping.empty else DEFAULT_SHOPPING_LIMIT
    sh_actual_live = float(df_shopping["actual_amt"].sum()) if not df_shopping.empty else 0.0
    sh_pct_live = min(100.0, (sh_actual_live / max(1.0, sh_budget_live)) * 100.0)
    st.markdown(
        render_svg_ring_gauge(
            "🛍️ शॉपिंग बजट Utilization",
            f"बाकी बचा: ₹{sh_budget_live - sh_actual_live:,.0f}",
            sh_pct_live,
            f"₹{sh_actual_live:,.0f} / ₹{sh_budget_live:,.0f}",
            "#38bdf8",
        ),
        unsafe_allow_html=True,
    )

st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

# ==============================================================================
# 11. ALL 8 COMPLETE SUPER-TABS (NOTHING REMOVED!)
# ==============================================================================
tab_shop_sep, tab_master, tab_pay, tab_yt_ai, tab_psych, tab_vault_ledger, tab_comeback, tab_admin = st.tabs(
    [
        "🛍️ 1. Expected vs Actual (अलग-अलग)",
        "🎛️ 2. Master Hub (सब Edit करें)",
        "⚡ 3. तेज़ UPI & QR",
        "🎬 4. In-App Shorts & 37L Prompts",
        "🧠 5. लालच ब्रेकर & Time-Machine",
        "🏦 6. पासबुक, तिजोरी & AI",
        "🔥 7. जीत की कहानियाँ & Games",
        "👑 8. Admin, Backup & App",
    ]
)

# ==============================================================================
# TAB 1: STRICTLY SEPARATED EXPECTED vs ACTUAL SHOPPING & BUDGET ENGINE
# ==============================================================================
with tab_shop_sep:
    st.markdown(
        """
        <div class="neo-card">
            <h4 style="margin:0; color:#fbbf24;">🛍️ 2-Step Smart Shopping Engine: (1) Expected अलग • (2) Actual बिल्कुल अलग!</h4>
            <p style="margin:4px 0 0 0; font-size:0.85rem; color:#cbd5e1;">
                बाज़ार जाने से पहले <b>📋 STEP 1: EXPECTED एंट्री</b> में कुल बजट (जैसे ₹6,000) और सामान की अनुमानित कीमत डालें (जैसे साड़ी ₹2,000)।
                सामान खरीदने के बाद <b>✅ STEP 2: ACTUAL एंट्री & % मीटर</b> टैब में जाकर असली खर्च डालें—आपको तुरंत <b>% Utilization, बचत हाईलाइट और बचा हुआ बजट</b> दिखेगा!
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "active_trip_budget" not in st.session_state:
        st.session_state.active_trip_budget = float(df_shopping["trip_budget"].iloc[0]) if not df_shopping.empty else DEFAULT_SHOPPING_LIMIT
    if "active_trip_name" not in st.session_state:
        st.session_state.active_trip_name = str(df_shopping["trip_name"].iloc[0]) if not df_shopping.empty else "त्योहार / मार्केट शॉपिंग मिशन"

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

    # ZONE 1: ONLY EXPECTED PLANNING
    with sub_expected:
        st.markdown("#### 📋 Step 1: यहाँ सिर्फ अपना **Expected (अनुमानित)** सामान जोड़ें या Edit करें")
        e_m1, e_m2, e_m3 = st.columns(3)
        e_m1.metric("कुल शॉपिंग बजट", f"₹{trip_budget_val:,.0f}", "Master Trip Limit")
        e_m2.metric("Expected सामान का जोड़", f"₹{total_exp_planned:,.0f}", f"{(total_exp_planned/max(1.0, trip_budget_val))*100:.1f}% Planned")
        e_m3.metric("अन-प्लान्ड सेफ बफर", f"₹{unplanned_buffer:,.0f}", "Safe Buffer" if unplanned_buffer >= 0 else "Over-Planned!")

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
            st.markdown("##### ✏️ आपकी Expected लिस्ट (किसी भी आइटम का नाम या Expected कीमत यहीं से Edit/Delete करें):")
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
                    if st.button("💾 सेव", key=f"btn_ed_exp_{rid}"):
                        edit_expected_shopping_item_db(rid, ed_nm, ed_cat, ed_exp)
                        st.rerun()
                with ec5:
                    st.markdown("<div style='padding-top:24px;'></div>", unsafe_allow_html=True)
                    if st.button("🗑️ हटाएं", key=f"btn_del_exp_{rid}"):
                        delete_shopping_item_db(rid)
                        st.rerun()

    # ZONE 2: ONLY ACTUAL EXECUTION, % UTILIZATION & HIGHLIGHT ENGINE
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

            hl_color = "#00ff9d" if remaining_trip_cash >= 0 else "#ef4444"
            st.markdown(
                f"""
                <div class="neo-card" style="border-left:6px solid {hl_color};">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                        <div>
                            <div style="font-size:0.78rem; color:#fde68a; font-weight:800;">📊 LIVE SHOPPING UTILIZATION HIGHLIGHT</div>
                            <div style="font-size:1.18rem; font-weight:900; color:#ffffff;">
                                कुल ₹{trip_budget_val:,.0f} में से <span style="color:#f43f5e;">₹{total_act_spent:,.0f} ({overall_util_pct:.1f}%)</span> इस्तेमाल हो गया!
                            </div>
                            <div style="font-size:0.92rem; font-weight:800; color:{hl_color}; margin-top:2px;">
                                💰 अभी ₹{remaining_trip_cash:,.0f} ({remaining_pct:.1f}% बजट) आपके पास बाकी बचा है!
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:0.75rem; color:#cbd5e1;">Expected बनाम Actual बचत</div>
                            <div style="font-size:1.22rem; font-weight:900; color:{'#00ff9d' if saved_on_bought >= 0 else '#ef4444'};">
                                {f'+₹{saved_on_bought:,.0f} बचाए 🎉' if saved_on_bought >= 0 else f'-₹{abs(saved_on_bought):,.0f} ज़्यादा लगा 🚨'}
                            </div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

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
            "✏️ 3. पासबुक एंट्री मास्टर एडिटर",
        ]
    )

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
                    icons_list = ["🏡", "👂", "💻", "🛡️", "🚗", "💍", "✈️", "🎓", "🎯"]
                    eg_icon = st.selectbox(
                        "आइकॉन",
                        options=icons_list,
                        index=icons_list.index(g_row["icon"]) if g_row["icon"] in icons_list else 0,
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
                if st.form_submit_button("💾 एंट्री अपडेट करें"):
                    update_expense_in_db(sel_exp_id, str(erow["spent_by"]), m_cat, m_item, m_amt, m_bad, m_notes)
                    st.success(f"✅ एंट्री #{sel_exp_id} अपडेट हो गई!")
                    st.rerun()
            if st.button(f"🗑️ एंट्री #{sel_exp_id} को हमेशा के लिए हटाएं"):
                delete_expense_from_db(sel_exp_id)
                st.success("एंट्री हटा दी गई!")
                st.rerun()
        else:
            st.info("अभी पासबुक में कोई खर्च दर्ज नहीं है।")


# ==============================================================================
# TAB 3: ULTRA-FAST DAILY EXPENSE, QR CODE & INSTANT UPI LAUNCHER
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
                "🆔 दुकानदार की UPI ID (ऑप्शनल - QR के लिए)",
                value="",
                placeholder="खाली छोड़ने पर सीधा ऐप खुलेगा",
            )

        is_bad_chk = st.checkbox("🚨 यह गैर-ज़रूरी / फालतू खर्च (Bad Expense) है", value=auto_bad)
        notes_val = st.text_input("📌 नोट (Optional)", placeholder="कोई खास बात...")

        bricks_eq = max(1, int(amount_val // BRICK_PRICE))
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
        f'<a href="{upi_bundle["direct_openers"]["Google Pay (GPay)"]}" class="upi-app-btn">🟢 Open GPay</a>',
        unsafe_allow_html=True,
    )
    u_c2.markdown(
        f'<a href="{upi_bundle["direct_openers"]["PhonePe"]}" class="upi-app-btn" style="background:linear-gradient(90deg,#a855f7,#7e22ce); color:#fff !important;">🟣 Open PhonePe</a>',
        unsafe_allow_html=True,
    )
    u_c3.markdown(
        f'<a href="{upi_bundle["direct_openers"]["Paytm"]}" class="upi-app-btn" style="background:linear-gradient(90deg,#38bdf8,#0284c7); color:#fff !important;">🔵 Open Paytm</a>',
        unsafe_allow_html=True,
    )

    with st.expander("📷 UPI QR Code दिखाएं (दूसरे फोन से स्कैन करने के लिए)"):
        st.image(upi_bundle["qr_buf"], caption=f"₹{active_amt:,.0f} — {active_item}", width=200)

    if spent_today <= DAILY_REWARD_LIMIT:
        saved_today_diff = max(10.0, daily_safe_limit - spent_today)
        render_goal_bridge_widget("daily_low_spend", saved_today_diff, f"आज कम खर्च (₹{spent_today:,.0f}) से बची रकम")


# ==============================================================================
# TAB 4: IN-APP YOUTUBE SHORTS (4 ANGLES) + AI 360 OVERVIEW + 37L PROMPTS + CAREER
# ==============================================================================
with tab_yt_ai:
    st.markdown(
        """
        <div class="neo-card">
            <h4 style="margin:0; color:#fbbf24;">🎬 In-App Multi-Angle YouTube Shorts + 🤖 AI 360° Overview + 37L Prompts</h4>
            <p style="margin:4px 0 0 0; font-size:0.86rem; color:#cbd5e1;">
                कोई भी डिश (जैसे <b>Dal Makhani</b>), कोडिंग (<b>Python / Power Query</b>) या <b>Spoken English</b> टॉपिक चुनें या लिखें।
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

    ov_c1, ov_c2 = st.columns(2)
    for idx, ang in enumerate(angles_data):
        if st.session_state.selected_ai_angle != "ALL" and st.session_state.selected_ai_angle != idx:
            continue
        target_col = ov_c1 if idx % 2 == 0 else ov_c2
        with target_col:
            st.markdown(
                f"""
                <div class="neo-card" style="border-left:6px solid #00ff9d;">
                    <div style="font-size:0.74rem; color:#fbbf24; font-weight:900;">{ang['badge']}</div>
                    <div style="font-size:0.95rem; font-weight:800; color:#ffffff; margin:3px 0;">{ang['title']}</div>
                    <div style="font-size:0.84rem; color:#e2e8f0; line-height:1.4;">{ang['ai_summary']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

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

    with st.expander("🗺️ Career & Spoken English Mastery Checklist (अपनी प्रगति ट्रैक करें)"):
        SKILLS = [
            ("sk_eng", "🗣️ Daily Spoken English & Telecalling Confidence"),
            ("sk_pq", "📊 Excel Power Query (Combine Multiple Files) & XLOOKUP"),
            ("sk_py", "🐍 Python Core, Playwright & Pandas Automation"),
            ("sk_sql", "🗄️ SQL & Database Queries for Data Analysis"),
            ("sk_ai", "🤖 Generative AI & Prompt Engineering"),
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

    render_goal_bridge_widget("home_cooking_save", 200.0, "बाहर के बजाय घर पर बनाने या नई स्किल सीखने का इनाम")


# ==============================================================================
# TAB 5: PSYCHOLOGICAL IMPULSE URGE CRUSHER & FUTURE TIME-MACHINE
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

    hourly_wage = UNIVERSAL_FAMILY_POOL / (26 * 9)
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
# TAB 6: UNIVERSAL BANK PASSBOOK, ₹15K VAULT BRICK WALL & AI AUDITOR
# ==============================================================================
with tab_vault_ledger:
    st.markdown("#### 🏦 यूनिवर्सल बैंक पासबुक, ₹15,000 तिजोरी & 🤖 AI ऑडिटर")

    bricks_count = max(1, int((vault_saved_all_time + effective_monthly_savings) // BRICK_PRICE))
    st.markdown(
        f"""
        <div class="neo-card">
            <div style="font-weight:900; color:#fbbf24; margin-bottom:4px;">
                🏗️ सपनों के घर की दीवार ({bricks_count} पक्की ईंटें जुड़ चुकी हैं @ ₹{BRICK_PRICE:.0f}/ईंट)
            </div>
            <div style="font-size:1.25rem; line-height:1.45; word-wrap:break-word;">
                {"🧱" * min(70, bricks_count)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("🔐 ₹15,000 तिजोरी में नया फंड जमा करें (Deposit to Vault)", expanded=False):
        with st.form("vault_deposit_form_v6", clear_on_submit=True):
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

    st.progress(min(1.0, food_spent_month / max(1.0, CAP_FOOD)), text=f"🍲 इस महीने Food Cap: ₹{food_spent_month:,.0f} / ₹{CAP_FOOD:,.0f}")
    st.progress(min(1.0, rent_spent_month / max(1.0, CAP_RENT)), text=f"🏠 इस महीने Rent Cap: ₹{rent_spent_month:,.0f} / ₹{CAP_RENT:,.0f}")

    if not df_period.empty:
        top_cat = df_period.groupby("category")["amount"].sum().sort_values(ascending=False)
        st.markdown(
            f"""
            <div class="neo-card" style="border-left:5px solid #00ff9d;">
                <h4 style="color:#00ff9d; margin:0 0 6px 0;">🤖 AI Financial Auditor ({period_choice})</h4>
                <ul style="margin:0;">
                    <li><b>सबसे बड़ा खर्च:</b> <b>{top_cat.index[0]}</b> में कुल <b>₹{top_cat.iloc[0]:,.0f}</b> खर्च हुए हैं।</li>
                    <li><b>फालतू खर्च:</b> ₹{p_bad:,.0f} गैर-ज़रूरी चीजों में गए (= <b>{int(p_bad // BRICK_PRICE)} घर की ईंटें 🧱</b>)।</li>
                    <li><b>सलाह:</b> अगले 7 दिन रोज़ का खर्च <b>₹{daily_safe_limit:,.0f}</b> से नीचे रखें ताकि ₹15,000 की तिजोरी 100% सुरक्षित रहे।</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

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
                title="Universal Bank: खर्च बनाम बचत",
            )
            fig_b.update_layout(margin=dict(t=35, b=10, l=5, r=5), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#fff"), showlegend=False)
            st.plotly_chart(fig_b, use_container_width=True)


# ==============================================================================
# TAB 7: COMPLETE FAILURE RECOVERY HUB & ALL 3 PLAYABLE MIND GAMES
# ==============================================================================
with tab_comeback:
    fb_tab, game_tab = st.tabs(["🔥 हार से जीत की सच्ची कहानियाँ और समाधान", "🎮 दिमागी खेल (3 Playable Mind Games)"])

    with fb_tab:
        failure_type = st.selectbox(
            "🛡️ अभी आपको किस क्षेत्र में कठिनाई या असफलता महसूस हो रही है?",
            [
                "🗣️ 1. Spoken English में अटकना, झिझक या किसी का हंसना",
                "💻 2. Software / Python / Power Query सीखने में एरर आना",
                "🏢 3. Office Work में गलती होना, बॉस का दबाव या प्रमोशन रुकना",
                "💸 4. अचानक बड़ा खर्च आ जाना या बजट बिगड़ जाना",
            ],
        )

        if "Spoken English" in failure_type:
            st.markdown(
                """
                <div class="neo-card">
                    <h4 style="color:#fbbf24; margin-top:0;">🗣️ जब अंग्रेज़ी बोलते समय जुबान अटक जाए या लोग हंसें — तब क्या करें?</h4>
                    <p><b>📖 सच्चाई:</b> अगर आप हिंदी और गढ़वाली जानते हुए इंग्लिश सीख रहे हैं, तो आपका दिमाग 3 भाषाओं को प्रोसेस कर रहा है। अटकना कमजोरी नहीं, तरक्की की निशानी है!</p>
                    <ol>
                        <li><b>Mirror Rule:</b> रोज़ सुबह 5 मिनट शीशे के सामने खड़े होकर अपने ऑफिस या क्लाइंट कॉल की 5 लाइनें बोलें।</li>
                        <li><b>3 फिक्स ऑफिस टेम्पलेट रट लें:</b>
                            <ul>
                                <li><i>"I am looking into this issue and will update you in 15 minutes."</i></li>
                                <li><i>"I have combined all the files using Power Query and updated the report."</i></li>
                                <li><i>"Could you please clarify this point once more?"</i></li>
                            </ul>
                        </li>
                    </ol>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif "Software" in failure_type:
            st.markdown(
                """
                <div class="neo-card">
                    <h4 style="color:#00ff9d; margin-top:0;">💻 जब Python / Power Query समझ न आए या बार-बार Error आए — तब क्या करें?</h4>
                    <ol>
                        <li><b>Error का मतलब फेलियर नहीं है:</b> दुनिया के सबसे बड़े इंजीनियर का कोड भी पहली बार में नहीं चलता। लाल रंग का Error आपको यह सिखाता है कि किस लाइन को सुधारना है।</li>
                        <li><b>Copy-Modify-Run नियम:</b> कोई भी कोड रटकर मत लिखिए। पहले चलता हुआ कोड चलाएं और उसमें सिर्फ 1 छोटा बदलाव करके देखें।</li>
                    </ol>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif "Office Work" in failure_type:
            st.markdown(
                """
                <div class="neo-card">
                    <h4 style="color:#38bdf8; margin-top:0;">🏢 जब ऑफिस में गलती हो जाए या काम का दबाव ज़्यादा हो — तब क्या करें?</h4>
                    <ol>
                        <li><b>Own + Fix + Prevent:</b> सिर्फ एक शांत लाइन बोलें—<i>"There was a data mismatch in the previous file. I have fixed it now and added a check so it won't happen again."</i></li>
                        <li><b>Silent Upgrade:</b> जब लोग ऑफिस पॉलिटिक्स करें, तब आप चुपचाप अपना Power Query, Python और Spoken English इतना मजबूत कर लें कि आपकी वैल्यू दोगुनी हो जाए!</li>
                    </ol>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="neo-card">
                    <h4 style="color:#f97316; margin-top:0;">💸 जब अचानक कोई बड़ा खर्च आ जाए और बजट गड़बड़ा जाए — तब क्या करें?</h4>
                    <p>परिवार और सेहत (जैसे कान का इलाज या माता-पिता की ज़रूरत) के लिए ही पैसा कमाया जाता है। अगले 10 दिन बाहर का नाश्ता और रिज़र्व ऑटो बंद करके ₹100/दिन बचाएं—बजट अपने-आप बराबर हो जाएगा!</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with game_tab:
        if "mind_game_score" not in st.session_state:
            st.session_state.mind_game_score = 0

        st.metric("🏆 आपका कुल दिमागी स्कोर (Brain Score)", f"{st.session_state.mind_game_score} Points")

        g_sub1, g_sub2, g_sub3 = st.tabs(
            ["🔢 1. तेज़ हिसाब चैलेंज", "🕵️ 2. दिमागी पहेलियाँ (Riddles)", "🔤 3. English & Tech Quiz"]
        )

        with g_sub1:
            if "math_q" not in st.session_state:
                a, b = random.randint(14, 59), random.randint(11, 39)
                op = random.choice(["+", "-", "*"])
                if op == "+":
                    ans = a + b
                elif op == "-":
                    ans = a - b
                else:
                    a, b = random.randint(6, 18), random.randint(4, 12)
                    ans = a * b
                st.session_state.math_q = f"{a} {op} {b}"
                st.session_state.math_ans = ans

            st.markdown(f"<div class='neo-card' style='text-align:center;'><h3>सवाल: <code>{st.session_state.math_q} = ?</code></h3></div>", unsafe_allow_html=True)
            user_math = st.number_input("अपना जवाब लिखें:", value=0, step=1, key="math_in")
            mc1, mc2 = st.columns(2)
            if mc1.button("✅ जवाब चेक करें", key="chk_math"):
                if int(user_math) == int(st.session_state.math_ans):
                    st.session_state.mind_game_score += 10
                    st.session_state.willpower_xp += 10
                    st.balloons()
                    st.success("🎉 बिल्कुल सही जवाब! +10 Points मिले!")
                    del st.session_state.math_q
                else:
                    st.error(f"❌ सही जवाब {st.session_state.math_ans} था।")
            if mc2.button("🔄 नया सवाल लाएं", key="new_math"):
                if "math_q" in st.session_state:
                    del st.session_state.math_q
                st.rerun()

        with g_sub2:
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
                    "q": "यदि ₹38,000 में से ₹15,000 हर महीने बचाए जाएं, तो 1 साल (12 महीने) में बिना ब्याज के कुल कितनी रकम जमा होगी?",
                    "options": ["₹1,50,000", "₹1,80,000", "₹2,00,000", "₹1,65,000"],
                    "ans": "₹1,80,000",
                },
            ]
            if "riddle_idx" not in st.session_state:
                st.session_state.riddle_idx = 0
            curr_r = RIDDLES[st.session_state.riddle_idx % len(RIDDLES)]
            st.markdown(f"<div class='neo-card'><b>पहेली:</b> {curr_r['q']}</div>", unsafe_allow_html=True)
            r_choice = st.radio("सही उत्तर चुनें:", curr_r["options"], key=f"rad_r_{st.session_state.riddle_idx}")
            rc1, rc2 = st.columns(2)
            if rc1.button("✅ पहेली का उत्तर जांचें"):
                if r_choice == curr_r["ans"]:
                    st.session_state.mind_game_score += 15
                    st.success(f"🏆 शाबाश! '{curr_r['ans']}' बिल्कुल सही है! (+15 Points)")
                else:
                    st.warning("🤔 एक और कोशिश करें!")
            if rc2.button("➡️ अगली पहेली"):
                st.session_state.riddle_idx += 1
                st.rerun()

        with g_sub3:
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
                    "q": "Excel में कई सारी फाइलों को 1 क्लिक में जोड़ने (Combine) के लिए कौन-सा टूल सबसे बेस्ट है?",
                    "options": ["Power Query", "MS Paint", "Notepad"],
                    "ans": "Power Query",
                },
                {
                    "q": "Python में किसी Excel या CSV फाइल को पढ़ने के लिए Pandas का कौन-सा कमांड इस्तेमाल होता है?",
                    "options": ["pd.read_csv() / pd.read_excel()", "pd.open_file()", "python.load_sheet()"],
                    "ans": "pd.read_csv() / pd.read_excel()",
                },
            ]
            if "quiz_idx" not in st.session_state:
                st.session_state.quiz_idx = 0
            curr_q = QUIZ_LIST[st.session_state.quiz_idx % len(QUIZ_LIST)]
            st.markdown(f"<div class='neo-card'><b>सवाल:</b> {curr_q['q']}</div>", unsafe_allow_html=True)
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
# TAB 8: ANTI-SLEEP BACKUP SHIELD + ZERO-AD APP + AJAY SUPER-ADMIN PANEL
# ==============================================================================
with tab_admin:
    st.markdown(
        """
        <div class="neo-card">
            <h4 style="margin:0; color:#00ff9d;">🛡️ Zero-Data-Loss Backup Shield (ऐप स्लीप या रीबूट होने पर भी रिकॉर्ड कभी नहीं मिटेगा!)</h4>
            <p style="margin:4px 0 0 0; font-size:0.85rem; color:#cbd5e1;">
                आपका सारा डेटा (Goals, Expected vs Actual Shopping, Passbook, Master Rules) हर एंट्री पर अपने-आप <code>parivaar_auto_mirror_v6.json</code> में सेव होता है।
                नीचे से कभी भी 1-Click में अपना <b>Master Backup (.json)</b> डाउनलोड या Restore करें!
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
            file_name=f"Parivaar_OS6_Backup_{today_str}.json",
            mime="application/json",
        )
    with bk_c2:
        uploaded_bk = st.file_uploader("📤 पुरानी Backup File यहाँ डालकर 1-Click Restore करें", type=["json"])
        if uploaded_bk is not None:
            if st.button("🔄 सारा रिकॉर्ड अभी Restore करें"):
                ok = restore_from_backup_json(uploaded_bk.read().decode("utf-8"))
                if ok:
                    st.success("🎉 आपके सारे गोल्स, शॉपिंग, तिजोरी और पासबुक रिकॉर्ड 100% वापस आ गए!")
                    st.rerun()
                else:
                    st.error("❌ फाइल पढ़ने में त्रुटि आई।")

    st.markdown("---")
    clean_app_bytes = generate_zero_ad_fullscreen_app_file()
    st.download_button(
        label="📲 Download 100% Ad-Free Parivaar OS 6.0 Mobile App (Zero Ads Forever)",
        data=clean_app_bytes,
        file_name="Parivaar_OS_6_AdFree_App.html",
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

        adm_u1, adm_u2 = st.columns(2)
        with adm_u1:
            with st.form("admin_upsert_user_form"):
                u_name_in = st.text_input("👤 User ID (नया या पुराना नाम)", placeholder="जैसे: Ajay, Meenakshi, Ajeet...")
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
        with adm_u2:
            non_ajay_users = [u for u in USERS_DICT.keys() if u.lower() != "ajay"]
            if non_ajay_users:
                del_u_target = st.selectbox("हटाने के लिए यूज़र चुनें", options=non_ajay_users)
                if st.button("🚫 इस यूज़र का अकाउंट हटाएं"):
                    delete_user_account(del_u_target)
                    st.success(f"'{del_u_target}' का अकाउंट हटा दिया गया!")
                    st.rerun()

# Subtle Keep-Alive Heartbeat so browser tab keeps session active
components.html(
    """
    <script>
    setInterval(function() {
        console.log("Parivaar OS 6.0 Keep-Alive Heartbeat: " + new Date().toISOString());
    }, 40000);
    </script>
    """,
    height=0,
)
