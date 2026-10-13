# -*- coding: utf-8 -*-
"""
پرورشیار - نسخه نهایی کامل
- کارت لاگین شیشه‌ای بنفش
- پس‌زمینه گرادیانت متحرک + حباب‌های شناور
- نشان‌ها (به جای بج)
- اعداد فارسی + تاریخ شمسی
- PDF راست‌چین درست
- مخصوص مدارس شهرستان آغاجاری
"""

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, timedelta
import hashlib
from io import BytesIO
import os

# PDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm

# فارسی‌سازی PDF
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_RTL = True
except ImportError:
    HAS_RTL = False

# تاریخ شمسی
try:
    import jdatetime
    HAS_JALALI = True
except ImportError:
    HAS_JALALI = False

DB = "parvareshyar.db"
FONT_REG = "Vazirmatn-Regular.ttf"
FONT_BOLD = "Vazirmatn-Bold.ttf"


# ============ توابع کمکی ============
def to_fa_num(text):
    if text is None:
        return ""
    trans = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return str(text).translate(trans)


def to_jalali(dt_str):
    if not dt_str:
        return ""
    dt_str = str(dt_str)[:10]
    if not HAS_JALALI:
        return dt_str
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d")
        jd = jdatetime.date.fromgregorian(date=dt)
        return jd.strftime("%Y/%m/%d")
    except Exception:
        return dt_str


def current_jyear():
    if HAS_JALALI:
        return jdatetime.date.today().year
    return 1405


def fa(text):
    if text is None:
        return ""
    text = str(text)
    if not text:
        return ""
    text = to_fa_num(text)
    if not HAS_RTL:
        return text
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text


def fa_num(text):
    return to_fa_num(text)


# ============ استایل ============
def inject_css():
    st.markdown("""
    <style>
        @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css');
        html, body, [class*="css"] { font-family: Vazirmatn, Tahoma, sans-serif; direction: rtl; }

        .stApp {
            background: linear-gradient(-45deg, #667eea, #764ba2, #6C5CE7, #a29bfe, #fd79a8);
            background-size: 400% 400%;
            animation: gradientShift 15s ease infinite;
        }

        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        .bubble {
            position: fixed;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.1);
            animation: float 20s infinite ease-in-out;
            pointer-events: none;
            z-index: 0;
        }
        .bubble:nth-child(1) { width: 80px; height: 80px; top: 10%; right: 10%; animation-delay: 0s; }
        .bubble:nth-child(2) { width: 120px; height: 120px; top: 60%; right: 20%; animation-delay: 2s; }
        .bubble:nth-child(3) { width: 60px; height: 60px; top: 30%; left: 15%; animation-delay: 4s; }
        .bubble:nth-child(4) { width: 100px; height: 100px; bottom: 15%; left: 10%; animation-delay: 6s; }
        .bubble:nth-child(5) { width: 70px; height: 70px; top: 80%; right: 5%; animation-delay: 8s; }

        @keyframes float {
            0%, 100% { transform: translateY(0px) rotate(0deg); }
            50% { transform: translateY(-30px) rotate(180deg); }
        }

        .main-title {
            font-size: 52px;
            font-weight: 900;
            color: #ffffff !important;
            text-align: center;
            margin-bottom: 8px;
            text-shadow:
                0 0 20px rgba(255, 255, 255, 0.5),
                0 0 40px rgba(162, 155, 254, 0.5),
                0 4px 20px rgba(0, 0, 0, 0.2);
            letter-spacing: -1px;
            animation: glow 2s ease-in-out infinite alternate;
        }

        @keyframes glow {
            from { text-shadow: 0 0 20px rgba(255,255,255,0.5), 0 4px 20px rgba(0,0,0,0.2); }
            to { text-shadow: 0 0 30px rgba(255,255,255,0.8), 0 0 60px rgba(162,155,254,0.8), 0 4px 20px rgba(0,0,0,0.2); }
        }

        .main-sub {
            text-align: center;
            color: rgba(255, 255, 255, 0.95) !important;
            font-size: 17px;
            margin-bottom: 30px;
            font-weight: 500;
        }

        .main-title-dark {
            font-size: 34px;
            font-weight: 800;
            background: linear-gradient(135deg, #6C5CE7, #A29BFE);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            margin-bottom: 4px;
        }

        div[data-testid="stMetricValue"] {
            color: #6C5CE7;
            font-weight: 800;
            font-size: 28px;
        }

        .stButton > button {
            background: linear-gradient(135deg, #6C5CE7, #A29BFE);
            color: white !important;
            border: none !important;
            border-radius: 14px !important;
            padding: 14px 28px !important;
            font-weight: 800 !important;
            font-family: Vazirmatn !important;
            font-size: 16px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 6px 20px rgba(108, 92, 231, 0.4);
            position: relative;
            overflow: hidden;
        }
        .stButton > button:hover {
            transform: translateY(-3px) scale(1.02);
            box-shadow: 0 10px 30px rgba(108, 92, 231, 0.6);
        }
        .stButton > button:active {
            transform: translateY(-1px) scale(0.98);
        }

        .login-card {
            background: linear-gradient(145deg, rgba(162, 155, 254, 0.15) 0%, rgba(108, 92, 231, 0.25) 100%);
            border-radius: 28px;
            padding: 40px 36px;
            box-shadow:
                0 20px 60px rgba(0, 0, 0, 0.35),
                0 0 0 1px rgba(255, 255, 255, 0.3) inset,
                0 0 60px rgba(162, 155, 254, 0.3);
            max-width: 500px;
            margin: 0 auto;
            backdrop-filter: blur(30px);
            -webkit-backdrop-filter: blur(30px);
            border: 2px solid rgba(255, 255, 255, 0.35);
            animation: cardEntry 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
        }

        @keyframes cardEntry {
            0% { transform: translateY(30px) scale(0.9); opacity: 0; }
            100% { transform: translateY(0) scale(1); opacity: 1; }
        }

        .login-icon {
            text-align: center;
            font-size: 80px;
            margin-bottom: 12px;
            animation: bounceIn 0.9s cubic-bezier(0.34, 1.56, 0.64, 1);
            filter: drop-shadow(0 8px 20px rgba(255, 255, 255, 0.5));
        }

        @keyframes bounceIn {
            0%   { transform: scale(0.3) rotate(-15deg); opacity: 0; }
            50%  { transform: scale(1.1) rotate(5deg); }
            70%  { transform: scale(0.95) rotate(-3deg); }
            100% { transform: scale(1) rotate(0deg); opacity: 1; }
        }

        .login-title {
            text-align: center;
            font-size: 28px;
            font-weight: 800;
            color: #ffffff;
            text-shadow: 0 2px 12px rgba(108, 92, 231, 0.5);
            margin-bottom: 6px;
        }

        .login-subtitle {
            text-align: center;
            font-size: 14px;
            color: rgba(255, 255, 255, 0.85);
            margin-bottom: 26px;
            font-weight: 500;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background: rgba(255, 255, 255, 0.15);
            border-radius: 16px;
            padding: 8px;
            justify-content: center;
            backdrop-filter: blur(10px);
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 12px;
            padding: 12px 24px;
            font-weight: 700;
            color: rgba(255, 255, 255, 0.85);
            font-family: Vazirmatn;
            font-size: 15px;
            transition: all 0.2s;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background: rgba(255, 255, 255, 0.15);
            color: #ffffff;
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #ffffff, #e8e4ff) !important;
            color: #6C5CE7 !important;
            box-shadow: 0 4px 16px rgba(255, 255, 255, 0.4);
        }

        .stTextInput > div > div > input {
            border-radius: 14px !important;
            padding: 14px 18px !important;
            border: 2px solid rgba(255, 255, 255, 0.3) !important;
            font-family: Vazirmatn !important;
            font-size: 15px !important;
            background: rgba(255, 255, 255, 0.9) !important;
            color: #2d3436 !important;
            transition: all 0.3s;
        }
        .stTextInput > div > div > input:focus {
            border-color: #ffffff !important;
            background: #ffffff !important;
            box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.25) !important;
            transform: translateY(-2px);
        }
        .stTextInput > div > div > input::placeholder {
            color: #95a5a6;
        }

        .stTextInput > label, .stTextInput label p {
            color: #ffffff !important;
            font-weight: 600 !important;
            text-shadow: 0 1px 6px rgba(0, 0, 0, 0.3);
        }

        .preview-card {
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(10px);
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-radius: 18px;
            padding: 20px 16px;
            text-align: center;
            color: white;
            transition: all 0.3s;
            cursor: pointer;
        }
        .preview-card:hover {
            transform: translateY(-5px);
            background: rgba(255, 255, 255, 0.25);
            border-color: rgba(255, 255, 255, 0.6);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }
        .preview-card .emoji {
            font-size: 36px;
            display: block;
            margin-bottom: 8px;
            filter: drop-shadow(0 4px 8px rgba(0,0,0,0.2));
        }
        .preview-card .label {
            font-size: 13px;
            font-weight: 700;
            color: rgba(255,255,255,0.95);
        }

        .parent-link {
            text-align: center;
            margin-top: 20px;
        }
        .parent-link p {
            color: rgba(255, 255, 255, 0.9);
            font-size: 14px;
            font-weight: 500;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #F8F9FD, #EEF1FF);
        }

        .podium-item {
            text-align: center;
            padding: 20px 12px;
            border-radius: 14px;
            background: #fff;
            border: 2px solid #EEF1FF;
            box-shadow: 0 4px 16px rgba(108, 92, 231, 0.08);
        }
        .podium-item.first {
            padding: 32px 12px;
            background: linear-gradient(135deg, #FFF9E6, #FFEAA7);
            border-color: #FDCB6E;
        }
        .podium-item .medal { font-size: 40px; }
        .podium-item .name { font-weight: 700; margin: 8px 0 4px; }
        .podium-item .score { font-size: 13px; color: #636e72; }

        .badge-card {
            text-align: center;
            padding: 16px;
            background: linear-gradient(135deg, #fff, #F8F9FD);
            border: 2px solid #EEF1FF;
            border-radius: 14px;
        }
        .badge-card .emoji { font-size: 32px; }
        .badge-card .name { font-weight: 700; font-size: 13px; margin-top: 6px; }
        .badge-card .cond { font-size: 11px; color: #B2BEC3; }
    </style>

    <div class="bubble"></div>
    <div class="bubble"></div>
    <div class="bubble"></div>
    <div class="bubble"></div>
    <div class="bubble"></div>
    """, unsafe_allow_html=True)


# ============ دیتابیس ============
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        national_id TEXT UNIQUE, full_name TEXT, grade TEXT,
        school TEXT, password TEXT, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT UNIQUE, category TEXT, points INTEGER, icon TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER, activity_id INTEGER, points INTEGER,
        note TEXT, registered_by TEXT, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS challenges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, description TEXT, points INTEGER,
        start_date TEXT, end_date TEXT, active INTEGER DEFAULT 1)""")
    defaults = [
        ("شرکت در نماز جماعت", "عبادی", 2, "🕌"),
        ("شرکت در اردو", "اردویی", 20, "🚌"),
        ("مسابقه قرآن - شرکت", "قرآنی", 5, "📖"),
        ("مسابقه قرآن - رتبه برتر", "قرآنی", 25, "🏆"),
        ("جشنواره هنری", "هنری", 10, "🎨"),
        ("شورای دانش‌آموزی", "اجتماعی", 15, "🗳️"),
        ("کانون یاریگران", "پیشگیری", 10, "🤝"),
        ("کمک به همکلاسی", "اخلاقی", 5, "💝"),
    ]
    for t, cat, p, icon in defaults:
        try:
            c.execute("INSERT INTO activities (title,category,points,icon) VALUES (?,?,?,?)",
                      (t, cat, p, icon))
        except Exception:
            pass
    conn.commit()
    conn.close()


def q(sql, params=()):
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def exec_sql(sql, params=()):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(sql, params)
    conn.commit()
    conn.close()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


# ============ سطح و نشان ============
LEVELS = [(0, "تازه‌کار", "🌱"), (50, "فعال", "⭐"), (150, "کوشا", "🌟"),
          (300, "سرآمد", "💫"), (500, "ستاره پرورشی", "✨"), (1000, "الگو", "👑")]


def get_level(pts):
    cur, nxt = LEVELS[0], None
    for i, (p, n, ic) in enumerate(LEVELS):
        if pts >= p:
            cur = (p, n, ic)
            nxt = LEVELS[i + 1] if i + 1 < len(LEVELS) else None
    return cur, nxt


def total_points(sid):
    r = q("SELECT COALESCE(SUM(points),0) as t FROM scores WHERE student_id=?", (sid,))
    return int(r["t"][0])


def get_badges(sid):
    rows = q("""SELECT a.title, a.category, s.points FROM scores s
                JOIN activities a ON a.id=s.activity_id WHERE s.student_id=?""", (sid,))
    data = [(r["title"], r["category"], r["points"]) for _, r in rows.iterrows()]
    badges = []
    if sum(r[2] for r in data if "نماز" in r[0]) >= 50:
        badges.append(("نمازیار", "🕌"))
    if sum(1 for r in data if r[1] == "قرآنی") >= 3:
        badges.append(("قاری کوچک", "📖"))
    if sum(1 for r in data if r[1] == "هنری") >= 3:
        badges.append(("هنرمند", "🎨"))
    if sum(1 for r in data if r[1] == "اخلاقی") >= 5:
        badges.append(("یاریگر", "🤝"))
    if sum(r[2] for r in data) >= 500:
        badges.append(("پرورشی طلایی", "🏆"))
    return badges


def get_rank(sid):
    df = q("SELECT student_id, SUM(points) as total FROM scores GROUP BY student_id ORDER BY total DESC")
    for i, row in df.iterrows():
        if int(row["student_id"]) == sid:
            return i + 1
    return "-"


# ============ PDF ============
def register_fonts():
    try:
        if os.path.exists(FONT_REG) and os.path.exists(FONT_BOLD):
            pdfmetrics.registerFont(TTFont("Vazir", FONT_REG))
            pdfmetrics.registerFont(TTFont("VazirBold", FONT_BOLD))
            return True
    except Exception as e:
        print(f"Font error: {e}")
    return False


def make_report_pdf(sid):
    student = q("SELECT * FROM students WHERE id=?", (sid,)).iloc[0]
    pts = total_points(sid)
    (lp, ln, li), nxt = get_level(pts)
    rank = get_rank(sid)
    badges = get_badges(sid)

    acts = q("""SELECT a.title, a.category, s.points, s.created_at
                FROM scores s JOIN activities a ON a.id=s.activity_id
                WHERE s.student_id=? ORDER BY s.id DESC""", (sid,))

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    has_font = register_fonts()
    f = "Vazir" if has_font else "Helvetica"
    fb = "VazirBold" if has_font else "Helvetica-Bold"

    MARGIN = 18 * mm
    RIGHT_X = w - MARGIN
    LEFT_X = MARGIN
    CENTER_X = w / 2

    c.setFillColorRGB(0.42, 0.36, 0.91)
    c.rect(0, h - 35 * mm, w, 35 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont(fb, 20)
    c.drawCentredString(CENTER_X, h - 18 * mm, fa("کارنامه پرورشی"))
    c.setFont(f, 11)
    c.drawCentredString(CENTER_X, h - 26 * mm,
                        fa("سامانه پرورشیار - آموزش و پرورش شهرستان آغاجاری"))

    c.setFillColorRGB(0.18, 0.20, 0.21)
    y = h - 50 * mm
    c.setFont(fb, 12)
    c.drawRightString(RIGHT_X, y, fa(f"نام: {student['full_name']}"))
    c.drawString(LEFT_X, y, fa(f"کد ملی: {student['national_id']}"))
    y -= 8 * mm
    c.drawRightString(RIGHT_X, y, fa(f"پایه: {student['grade']}"))
    c.drawString(LEFT_X, y, fa(f"مدرسه: {student['school']}"))

    y -= 15 * mm
    c.setFillColorRGB(0.95, 0.95, 1)
    c.rect(MARGIN, y - 20 * mm, w - 2 * MARGIN, 22 * mm, fill=1, stroke=0)

    c.setFillColorRGB(0.42, 0.36, 0.91)
    c.setFont(fb, 16)
    c.drawCentredString(RIGHT_X - 22 * mm, y - 8 * mm, fa_num(str(pts)))
    c.drawCentredString(CENTER_X, y - 8 * mm, fa(f"{li} {ln}"))
    c.drawCentredString(LEFT_X + 22 * mm, y - 8 * mm, fa_num(f"#{rank}"))

    c.setFont(f, 9)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawCentredString(RIGHT_X - 22 * mm, y - 15 * mm, fa("امتیاز کل"))
    c.drawCentredString(CENTER_X, y - 15 * mm, fa("سطح"))
    c.drawCentredString(LEFT_X + 22 * mm, y - 15 * mm, fa("رتبه مدرسه"))

    y -= 32 * mm
    c.setFillColorRGB(0.18, 0.20, 0.21)
    c.setFont(fb, 13)
    c.drawRightString(RIGHT_X, y, fa("نشان‌های کسب‌شده:"))
    y -= 8 * mm
    if badges:
        c.setFont(f, 11)
        line = "   ".join([fa(f"{ic} {n}") for n, ic in badges])
        c.drawRightString(RIGHT_X, y, line)
    else:
        c.setFont(f, 10)
        c.drawRightString(RIGHT_X, y, fa("هنوز نشانی کسب نشده است."))

    y -= 18 * mm
    c.setFont(fb, 13)
    c.drawRightString(RIGHT_X, y, fa("فعالیت‌های ثبت‌شده:"))
    y -= 8 * mm

    c.setFillColorRGB(0.42, 0.36, 0.91)
    c.rect(MARGIN, y - 6 * mm, w - 2 * MARGIN, 7 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont(fb, 10)
    c.drawRightString(RIGHT_X - 4 * mm, y - 4 * mm, fa("فعالیت"))
    c.drawCentredString(CENTER_X, y - 4 * mm, fa("تاریخ"))
    c.drawCentredString(LEFT_X + 20 * mm, y - 4 * mm, fa("امتیاز"))

    y -= 10 * mm
    c.setFillColorRGB(0.15, 0.15, 0.15)
    c.setFont(f, 10)

    for i, (_, r) in enumerate(acts.head(30).iterrows()):
        if y < 30 * mm:
            c.showPage()
            y = h - 25 * mm
            c.setFont(f, 10)
        if i % 2 == 0:
            c.setFillColorRGB(0.97, 0.97, 1)
            c.rect(MARGIN, y - 3 * mm, w - 2 * MARGIN, 6 * mm, fill=1, stroke=0)
            c.setFillColorRGB(0.15, 0.15, 0.15)

        title = fa(str(r["title"])[:35])
        c.drawRightString(RIGHT_X - 4 * mm, y, title)
        jalali_date = to_jalali(r["created_at"])
        c.drawCentredString(CENTER_X, y, fa_num(jalali_date))
        c.drawCentredString(LEFT_X + 20 * mm, y, fa_num(f"+{r['points']}"))
        y -= 7 * mm

    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.setFont(f, 8)
    today_j = to_jalali(str(date.today()))
    c.drawCentredString(CENTER_X, 12 * mm,
                        fa(f"این کارنامه به صورت الکترونیکی تولید شده است — تاریخ: {today_j}"))

    c.save()
    buf.seek(0)
    return buf.getvalue()


# ============ صفحه ورود ============
def page_login():
    st.markdown("""
    <div style='height: 30px;'></div>
    <div class="main-title">🌟 پرورشیار</div>
    <div class="main-sub">🏆 با هر فعالیت، یک پله بالاتر برو!</div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    with col2:
        st.markdown("""
        <div class="preview-card">
            <span class="emoji">🎯</span>
            <div class="label">امتیاز بگیر</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="preview-card">
            <span class="emoji">🎖️</span>
            <div class="label">نشان بگیر</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown("""
        <div class="preview-card">
            <span class="emoji">🥇</span>
            <div class="label">رتبه ۱ بشو</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)

    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        st.markdown("""
        <div class="login-card">
            <div class="login-icon">🎓</div>
            <div class="login-title">خوش آمدی!</div>
            <div class="login-subtitle">آماده‌ای امتیاز جمع کنی؟</div>
        """, unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["👨‍🎓 دانش‌آموز", "🛠️ مربی"])

        with tab1:
            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
            nid = st.text_input("🔢 کد ملی", key="s_nid", placeholder="مثال: ۰۰۱۲۳۴۵۶۷۸")
            pw = st.text_input("🔑 رمز عبور", type="password", key="s_pw",
                              placeholder="رمز پیش‌فرض: کد ملی")
            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
            if st.button("🚀 بزن بریم!", key="s_login", use_container_width=True):
                r = q("SELECT * FROM students WHERE national_id=? AND password=?",
                      (nid, hash_pw(pw)))
                if r.empty:
                    st.error("❌ کد ملی یا رمز اشتباهه، دوباره امتحان کن!")
                else:
                    st.session_state.user = {
                        "role": "student",
                        "id": int(r.iloc[0]["id"]),
                        "name": r.iloc[0]["full_name"]
                    }
                    st.balloons()
                    st.rerun()

        with tab2:
            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
            pw = st.text_input("🔒 رمز مربی", type="password", key="t_pw",
                              placeholder="رمز اختصاصی مربی")
            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
            if st.button("🎯 ورود به پنل", key="t_login", use_container_width=True):
                if pw == "parvaresh1404":
                    st.session_state.user = {"role": "teacher", "name": "مربی"}
                    st.rerun()
                else:
                    st.error("❌ رمز اشتباهه!")

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
        <div class="parent-link">
            <p>👨‍👩‍👧 والدین گرامی؟</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("📱 ورود به پنل والدین", key="parent_link", use_container_width=True):
            st.session_state.show_parent = True
            st.rerun()

        year_fa = to_fa_num(str(current_jyear()))
        st.markdown(f"""
        <div style='text-align: center; margin-top: 30px; color: rgba(255,255,255,0.7); font-size: 12px;'>
            © {year_fa} — سامانه پرورشیار | اداره آموزش و پرورش شهرستان آغاجاری
        </div>
        """, unsafe_allow_html=True)


# ============ داشبورد دانش‌آموز ============
def page_student_dashboard():
    sid = st.session_state.user["id"]
    name = st.session_state.user["name"]

    pts = total_points(sid)
    (lp, ln, li), nxt = get_level(pts)

    st.markdown(f'<div class="main-title-dark">سلام {name} 👋</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("امتیاز کل", to_fa_num(str(pts)))
    c2.metric("سطح", f"{li} {ln}")
    c3.metric("رتبه مدرسه", to_fa_num(f"#{get_rank(sid)}"))

    if nxt:
        needed = nxt[0] - pts
        prog = (pts - lp) / (nxt[0] - lp) if nxt[0] > lp else 1
        st.progress(min(prog, 1.0),
                    text=to_fa_num(f"{needed} امتیاز تا سطح {nxt[1]} {nxt[2]}"))

    st.markdown("### 🎖️ نشان‌های تو")
    badges = get_badges(sid)
    if badges:
        cols = st.columns(min(len(badges), 4))
        for i, (n, ic) in enumerate(badges):
            with cols[i % len(cols)]:
                st.markdown(
                    f'<div class="badge-card"><div class="emoji">{ic}</div>'
                    f'<div class="name">{n}</div></div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("هنوز نشانی نگرفتی. یه فعالیت ثبت کن!")

    st.markdown("### 📜 تاریخچه فعالیت‌ها")
    hist = q("""SELECT s.created_at, a.title, s.points
                FROM scores s JOIN activities a ON a.id=s.activity_id
                WHERE s.student_id=? ORDER BY s.id DESC LIMIT 20""", (sid,))
    if hist.empty:
        st.info("هنوز فعالیتی ثبت نشده.")
    else:
        hist["تاریخ"] = hist["created_at"].apply(to_jalali).apply(to_fa_num)
        hist["فعالیت"] = hist["title"]
        hist["امتیاز"] = hist["points"].apply(lambda x: to_fa_num(f"+{x}"))
        st.dataframe(hist[["تاریخ", "فعالیت", "امتیاز"]], use_container_width=True)


# ============ لیدربورد ============
def page_leaderboard():
    st.markdown('<div class="main-title-dark">🥇 لیدربورد مدرسه</div>', unsafe_allow_html=True)
    df = q("""SELECT s.full_name as نام, s.grade as پایه, SUM(sc.points) as امتیاز
              FROM students s JOIN scores sc ON sc.student_id=s.id
              GROUP BY s.id ORDER BY امتیاز DESC LIMIT 50""")
    if df.empty:
        st.info("هنوز امتیازی ثبت نشده.")
        return

    top3 = df.head(3).to_dict("records")
    cols = st.columns([1, 1.15, 1])
    order = [1, 0, 2]
    medals = ["🥇", "🥈", "🥉"]
    for i in order:
        if i < len(top3):
            with cols[i]:
                cls = "first" if i == 0 else ""
                score_fa = to_fa_num(str(top3[i]["امتیاز"]))
                st.markdown(
                    f'<div class="podium-item {cls}">'
                    f'<div class="medal">{medals[i]}</div>'
                    f'<div class="name">{top3[i]["نام"]}</div>'
                    f'<div class="score">{score_fa} امتیاز</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    df["رتبه"] = range(1, len(df) + 1)
    df["رتبه"] = df["رتبه"].apply(to_fa_num)
    df["امتیاز"] = df["امتیاز"].apply(to_fa_num)
    st.dataframe(df[["رتبه", "نام", "پایه", "امتیاز"]], use_container_width=True)


# ============ پنل مربی ============
def page_teacher():
    st.markdown('<div class="main-title-dark">🛠️ پنل مربی</div>', unsafe_allow_html=True)
    tab1, tab2, tab3, tab4 = st.tabs(
        ["➕ ثبت امتیاز", "👥 دانش‌آموزان", "🔥 چالش‌ها", "📊 گزارش"]
    )

    with tab1:
        st.subheader("ثبت امتیاز برای دانش‌آموز")
        nid = st.text_input("کد ملی دانش‌آموز")
        s = q("SELECT * FROM students WHERE national_id=?", (nid,)) if nid else pd.DataFrame()

        if nid and s.empty:
            st.warning("دانش‌آموز پیدا نشد. اول از تب «دانش‌آموزان» اضافه کن.")
        elif not s.empty:
            st.success(f"✅ دانش‌آموز: {s.iloc[0]['full_name']} — پایه {s.iloc[0]['grade']}")
            acts = q("SELECT * FROM activities ORDER BY category")
            opts = {f"{r['icon']} {r['title']} ({to_fa_num(r['points'])} امتیاز)": int(r["id"])
                    for _, r in acts.iterrows()}
            sel = st.selectbox("فعالیت", list(opts.keys()))
            note = st.text_input("توضیح (اختیاری)")
            if st.button("✅ ثبت امتیاز"):
                act = q("SELECT * FROM activities WHERE id=?", (opts[sel],)).iloc[0]
                exec_sql(
                    """INSERT INTO scores (student_id,activity_id,points,note,registered_by,created_at)
                       VALUES (?,?,?,?,?,?)""",
                    (int(s.iloc[0]["id"]), opts[sel], int(act["points"]), note, "مربی", now()),
                )
                st.balloons()
                st.success(f"✅ {to_fa_num(act['points'])} امتیاز به {s.iloc[0]['full_name']} اضافه شد!")

    with tab2:
        st.subheader("افزودن دانش‌آموز جدید")
        with st.form("add_student"):
            c1, c2 = st.columns(2)
            nid2 = c1.text_input("کد ملی")
            name = c2.text_input("نام و نام خانوادگی")
            c3, c4 = st.columns(2)
            grade = c3.text_input("پایه")
            school = c4.text_input("مدرسه")
            if st.form_submit_button("➕ افزودن"):
                if not nid2 or not name:
                    st.error("کد ملی و نام الزامی است.")
                else:
                    try:
                        exec_sql(
                            """INSERT INTO students
                               (national_id,full_name,grade,school,password,created_at)
                               VALUES (?,?,?,?,?,?)""",
                            (nid2, name, grade, school, hash_pw(nid2), now()),
                        )
                        st.success(f"✅ {name} اضافه شد. رمز پیش‌فرض: کد ملی")
                    except sqlite3.IntegrityError:
                        st.error("این کد ملی قبلاً ثبت شده.")

        st.subheader("لیست دانش‌آموزان")
        students = q("""SELECT s.id, s.national_id, s.full_name, s.grade, s.school,
                        COALESCE(SUM(sc.points),0) as امتیاز
                        FROM students s LEFT JOIN scores sc ON sc.student_id=s.id
                        GROUP BY s.id ORDER BY s.id DESC""")
        if not students.empty:
            display = students.copy()
            display["امتیاز"] = display["امتیاز"].apply(to_fa_num)
            st.dataframe(display, use_container_width=True)

        st.markdown("---")
        st.subheader("📄 کارنامه پرورشی PDF")
        if not students.empty:
            opts = {f"{r['full_name']} ({r['national_id']})": int(r["id"])
                    for _, r in students.iterrows()}
            sel = st.selectbox("دانش‌آموز را انتخاب کن", list(opts.keys()), key="pdf_sel")
            if st.button("📄 ساخت کارنامه"):
                try:
                    pdf = make_report_pdf(opts[sel])
                    st.download_button(
                        "⬇️ دانلود PDF",
                        pdf,
                        file_name=f"report_{opts[sel]}.pdf",
                        mime="application/pdf",
                        key="pdf_dl",
                    )
                except Exception as e:
                    st.error(f"خطا در ساخت PDF: {e}")
                    st.info("مطمئن شو فایل‌های فونت کنار کد هستن.")

    with tab3:
        st.subheader("ساخت چالش جدید")
        with st.form("new_ch"):
            t = st.text_input("عنوان چالش")
            d = st.text_area("توضیحات")
            p = st.number_input("امتیاز", 1, 100, 10)
            c1, c2 = st.columns(2)
            sd = c1.date_input("از", value=date.today())
            ed = c2.date_input("تا", value=date.today() + timedelta(days=7))
            if st.form_submit_button("➕ ایجاد"):
                exec_sql(
                    """INSERT INTO challenges (title,description,points,start_date,end_date,active)
                       VALUES (?,?,?,?,?,1)""",
                    (t, d, int(p), str(sd), str(ed)),
                )
                st.success("✅ چالش ایجاد شد.")

        chs = q("SELECT * FROM challenges WHERE active=1 ORDER BY id DESC")
        if not chs.empty:
            st.subheader("چالش‌های فعال")
            for _, ch in chs.iterrows():
                sd_j = to_jalali(ch['start_date'])
                ed_j = to_jalali(ch['end_date'])
                st.write(
                    f"**{ch['title']}** ({to_fa_num(ch['points'])} امتیاز) — "
                    f"{to_fa_num(sd_j)} تا {to_fa_num(ed_j)}"
                )

    with tab4:
        st.subheader("📊 گزارش کلی")
        ts = q("SELECT COUNT(*) as n FROM students")["n"][0]
        tp = q("SELECT COALESCE(SUM(points),0) as n FROM scores")["n"][0]
        act = q("SELECT COUNT(DISTINCT student_id) as n FROM scores")["n"][0]

        c1, c2, c3 = st.columns(3)
        c1.metric("کل دانش‌آموز", to_fa_num(ts))
        c2.metric("دانش‌آموز فعال", to_fa_num(act))
        c3.metric("کل امتیازات", to_fa_num(tp))

        if ts:
            percent = f"{act / ts * 100:.1f}"
            st.progress(min(act / ts, 1.0), text=to_fa_num(f"مشارکت: {percent}%"))

        st.subheader("توزیع بر اساس دسته")
        df = q("""SELECT a.category as دسته, SUM(s.points) as امتیاز
                  FROM scores s JOIN activities a ON a.id=s.activity_id
                  GROUP BY a.category ORDER BY امتیاز DESC""")
        if not df.empty:
            st.bar_chart(df.set_index("دسته"))

        st.subheader("🥇 ۱۰ نفر برتر")
        top = q("""SELECT s.full_name as نام, s.grade as پایه, SUM(sc.points) as امتیاز
                   FROM students s JOIN scores sc ON sc.student_id=s.id
                   GROUP BY s.id ORDER BY امتیاز DESC LIMIT 10""")
        if not top.empty:
            top_d = top.copy()
            top_d["امتیاز"] = top_d["امتیاز"].apply(to_fa_num)
            st.dataframe(top_d, use_container_width=True)


# ============ پنل والدین ============
def page_parent():
    if st.button("⬅️ بازگشت به صفحه ورود", key="back_to_login"):
        st.session_state.show_parent = False
        st.rerun()

    st.markdown('<div class="main-title-dark">👨‍👩‍👧 پیگیری والدین</div>', unsafe_allow_html=True)
    st.caption("با وارد کردن کد ملی فرزندتان، وضعیت فعالیت‌های پرورشی او را ببینید.")

    nid = st.text_input("کد ملی دانش‌آموز")
    if not nid:
        return

    s = q("SELECT * FROM students WHERE national_id=?", (nid,))
    if s.empty:
        st.error("دانش‌آموزی با این کد ملی پیدا نشد.")
        return

    student = s.iloc[0]
    sid = int(student["id"])
    pts = total_points(sid)
    (lp, ln, li), nxt = get_level(pts)
    rank = get_rank(sid)
    badges = get_badges(sid)

    st.success(f"✅ دانش‌آموز: {student['full_name']} — پایه {student['grade']}")

    c1, c2, c3 = st.columns(3)
    c1.metric("امتیاز کل", to_fa_num(pts))
    c2.metric("سطح", f"{li} {ln}")
    c3.metric("رتبه مدرسه", to_fa_num(f"#{rank}"))

    if nxt:
        needed = nxt[0] - pts
        prog = (pts - lp) / (nxt[0] - lp) if nxt[0] > lp else 1
        st.progress(min(prog, 1.0),
                    text=to_fa_num(f"{needed} امتیاز تا سطح {nxt[1]}"))

    st.markdown("### 🎖️ نشان‌های کسب‌شده")
    if badges:
        cols = st.columns(min(len(badges), 4))
        for i, (n, ic) in enumerate(badges):
            with cols[i % len(cols)]:
                st.markdown(
                    f'<div class="badge-card"><div class="emoji">{ic}</div>'
                    f'<div class="name">{n}</div></div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("فرزند شما هنوز نشانی کسب نکرده است.")

    st.markdown("### 📜 آخرین فعالیت‌ها")
    hist = q("""SELECT s.created_at, a.title, s.points
                FROM scores s JOIN activities a ON a.id=s.activity_id
                WHERE s.student_id=? ORDER BY s.id DESC LIMIT 15""", (sid,))
    if hist.empty:
        st.info("هنوز فعالیتی ثبت نشده.")
    else:
        hist["تاریخ"] = hist["created_at"].apply(to_jalali).apply(to_fa_num)
        hist["فعالیت"] = hist["title"]
        hist["امتیاز"] = hist["points"].apply(lambda x: to_fa_num(f"+{x}"))
        st.dataframe(hist[["تاریخ", "فعالیت", "امتیاز"]], use_container_width=True)


# ============ اپ اصلی ============
def main():
    st.set_page_config(page_title="پرورشیار | آغاجاری", page_icon="🌟", layout="wide")
    inject_css()
    init_db()

    if not HAS_RTL:
        st.sidebar.warning("⚠️ برای PDF فارسی: `pip install arabic-reshaper python-bidi`")
    if not HAS_JALALI:
        st.sidebar.warning("⚠️ برای تاریخ شمسی: `pip install jdatetime`")

    if "user" not in st.session_state or st.session_state.user is None:
        if st.session_state.get("show_parent", False):
            page_parent()
        else:
            page_login()
        return

    role = st.session_state.user["role"]

    with st.sidebar:
        st.markdown("### 🌟 پرورشیار")
        st.caption("آموزش و پرورش آغاجاری")
        st.markdown(f"**{st.session_state.user['name']}**")
        st.markdown("---")

        if role == "student":
            menu = st.radio("منو", ["🎓 داشبورد من", "🥇 لیدربورد"])
        else:
            menu = st.radio("منو", ["🛠️ پنل مربی", "🥇 لیدربورد"])

        st.markdown("---")
        if st.button("🚪 خروج"):
            st.session_state.user = None
            st.session_state.show_parent = False
            st.rerun()

    if menu == "🎓 داشبورد من":
        page_student_dashboard()
    elif menu == "🥇 لیدربورد":
        page_leaderboard()
    else:
        page_teacher()


if __name__ == "__main__":
    main()