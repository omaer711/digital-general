import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime

# ============================================================
# 1) إعدادات الصفحة
# ============================================================
st.set_page_config(
    page_title="جنرال رقمي | Digital General Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 2) CSS محسّن (RTL كامل + تصميم احترافي)
# ============================================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
    * { font-family: 'Cairo', sans-serif !important; }
    .stApp { background-color: #0b0e14; color: #ffffff; direction: rtl; text-align: right; }
    [data-testid="stSidebar"] { background-color: #12161f; border-left: 1px solid #1e222d; direction: rtl; }
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stTextInput input,
    [data-testid="stSidebar"] .stMarkdown { direction: rtl; text-align: right; }
    .metric-card { background-color: #1e222d; border: 1px solid #2a2e39; padding: 20px; border-radius: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); margin-bottom: 20px; }
    .stButton>button { background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); color: white; border-radius: 10px; border: none; font-weight: 700; padding: 0.6rem 1rem; width: 100%; }
    h1, h2, h3 { color: #f3f4f6; font-weight: 900; }
    .price-tag { font-size: 1.4rem; font-weight: 900; color: #6366f1; }
    </style>
""", unsafe_allow_html=True)

# ============================================================
# 3) دوال مساعدة
# ============================================================
def safe_float(value, default=0.0):
    """تحويل آمن لأي قيمة لرقم"""
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default

def fmt_price(value, decimals=4):
    """تنسيق آمن للسعر"""
    try:
        return f"${float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"

def fmt_pct(value):
    """تنسيق آمن للنسبة"""
    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "N/A"

# ============================================================
# 4) خريطة الرموز
# ============================================================
SYMBOL_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "SHIB": "shiba-inu",
    "BNB": "binancecoin",
    "SUI": "sui",
    "PEPE": "pepe",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "MATIC": "matic-network",
    "DOT": "polkadot",
    "TON": "the-open-network",
}

# ============================================================
# 5) جلب بيانات عملة واحدة (مع cache آمن)
# ============================================================
@st.cache_data(ttl=60, show_spinner=False)
def get_crypto_data(symbol):
    clean = symbol.upper().strip().replace("USDT", "").replace("/", "").replace(" ", "")
    if not clean:
        return None

    coin_id = SYMBOL_MAP.get(clean, clean.lower())

    # محاولة 1: الـ ID المباشر
    try:
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={coin_id}"
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0]
    except requests.RequestException:
        pass

    # محاولة 2: البحث بالاسم
    try:
        search_url = f"https://api.coingecko.com/api/v3/search?query={clean}"
        s_res = requests.get(search_url, timeout=8)
        if s_res.status_code == 200:
            coins = s_res.json().get("coins", [])
            if coins:
                target_id = coins[0]["id"]
                detail_url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={target_id}"
                d_res = requests.get(detail_url, timeout=8)
                if d_res.status_code == 200:
                    data = d_res.json()
                    if isinstance(data, list) and len(data) > 0:
                        return data[0]
    except requests.RequestException:
        pass

    return None

# ============================================================
# 6) جلب عدة عملات بطلب واحد (للماسح) — يوفر 7 طلبات
# ============================================================
@st.cache_data(ttl=60, show_spinner=False)
def get_multiple_coins(symbols_list):
    ids = [SYMBOL_MAP.get(s.upper(), s.lower()) for s in symbols_list]
    ids_str = ",".join(ids)
    try:
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={ids_str}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.json()
    except requests.RequestException:
        pass
    return []

# ============================================================
# 7) حساب RSI تقريبي من high/low/current
# ============================================================
def estimate_rsi(price, high, low):
    if high <= low:
        return 50.0
    rsi = ((price - low) / (high - low)) * 100
    return max(0.0, min(100.0, rsi))

def rsi_label(rsi):
    if rsi >= 70:
        return f"{rsi:.1f} (تشبع شرائي 🔴)"
    elif rsi <= 30:
        return f"{rsi:.1f} (تشبع بيعي 🟢)"
    elif rsi >= 50:
        return f"{rsi:.1f} (زخم إيجابي)"
    else:
        return f"{rsi:.1f} (زخم سلبي)"

# ============================================================
# 8) حساب نسبة الثقة بناءً على بيانات حقيقية
# ============================================================
def calc_confidence(change, high, low, price, volume):
    try:
        volatility = ((high - low) / price * 100) if price > 0 else 0
        base = 50 + min(abs(change) * 3, 30)
        if volatility < 3:
            base += 8
        elif volatility > 8:
            base -= 5
        if volume and volume > 1_000_000:
            base += 5
        return max(10, min(base, 95))
    except Exception:
        return 50.0

# ============================================================
# 9) الشريط الجانبي
# ============================================================
with st.sidebar:
    st.title("⚡ جنرال رقمي Pro")
    st.markdown("---")
    selected_tab = st.radio(
        "الانتقال السريع:",
        ["الرئيسية (Dashboard)", "التحليل الفني الشامل & AI",
         "سجل الصفقات (Trade Journal)", "ماسح السوق اللحظي"],
        index=0
    )
    st.markdown("---")
    st.info("💡 منصة تداول حية متصلة بالأسواق العالمية.")

# ============================================================
# 10) التبويب 1: الرئيسية
# ============================================================
if selected_tab == "الرئيسية (Dashboard)":
    st.subheader("📊 لوحة القيادة المركزية لأسواق العملات")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="نسبة صفقات الأسبوع الناجحة", value="0%", delta="جاهز للبدء")
    with col2:
        st.metric(label="النتيجة الصافية (R-Multiple)", value="0.00R", delta="الحساب نظيف")
    with col3:
        st.metric(label="توقع الذكاء الاصطناعي العام", value="مترقب", delta="بانتظار التحليل")

    st.markdown("---")
    st.subheader("🔍 محرك البحث الفوري برمز العملة")
    user_input = st.text_input(
        "أدخل رمز العملة (مثل: BTC, XRP, ETH, ADA, PEPE):",
        value="XRP"
    ).strip()

    if user_input:
        with st.spinner(f"جاري جلب السعر والبيانات الحية لـ {user_input}..."):
            data = get_crypto_data(user_input)

            if data:
                # --- استخراج آمن ---
                price = safe_float(data.get("current_price"))
                change = safe_float(data.get("price_change_percentage_24h"))
                high = safe_float(data.get("high_24h"), price * 1.02)
                low = safe_float(data.get("low_24h"), price * 0.98)
                volume = safe_float(data.get("total_volume"))
                symbol_name = (data.get("symbol") or "COIN").upper()
                coin_title = data.get("name") or "Asset"

                # --- خطة تداول بمنطق R:R صحيح ---
                entry_min = price * 0.985
                entry_max = price * 0.998
                stop_loss = entry_min * 0.97          # -3% من أدنى دخول
                risk = max(entry_min - stop_loss, price * 0.001)
                target_1 = entry_min + (risk * 1.5)   # R:R = 1.5
                target_2 = entry_min + (risk * 2.5)   # R:R = 2.5
                target_3 = entry_min + (risk * 4.0)   # R:R = 4.0
                pivot = (high + low + price) / 3

                # --- حساب RSI تقريبي حقيقي ---
                rsi = estimate_rsi(price, high, low)
                rsi_text = rsi_label(rsi)

                # --- نسبة ثقة حقيقية ---
                conf_value = calc_confidence(change, high, low, price, volume)
                if conf_value >= 80:
                    conf_desc = "قوية جداً"
                elif conf_value >= 65:
                    conf_desc = "قوية"
                elif conf_value >= 50:
                    conf_desc = "متوسطة"
                else:
                    conf_desc = "حذرة"
                confidence_score = f"{conf_value:.1f}% ({conf_desc})"

                trend_status = "🟢 صاعد قوي (Bullish)" if change > 0 else "🔴 تصحيحي (Bearish)"

                st.success(f"تم بنجاح جلب التحليل الفني لـ: {coin_title} ({symbol_name})")

                # --- السعر والتغير ---
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("السعر الحالي", fmt_price(price))
                with c2:
                    st.metric("التغير (24س)", fmt_pct(change))
                with c3:
                    st.metric("أعلى سعر (24س)", fmt_price(high))
                with c4:
                    st.metric("أدنى سعر (24س)", fmt_price(low))

                st.markdown("---")
                st.markdown("### 🤖 مؤشرات الثقة وتحليل الذكاء الاصطناعي (Horizon AI)")
                ai_col1, ai_col2, ai_col3 = st.columns(3)
                with ai_col1:
                    st.metric("نسبة الثقة", confidence_score)
                with ai_col2:
                    st.metric("حالة الاتجاه العام", trend_status)
                with ai_col3:
                    st.metric("مؤشر القوة النسبية RSI", rsi_text)

                st.markdown("---")
                st.markdown("### 🎯 خطة التداول الفورية ومستويات الدخول والهدف")

                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"""
* **🟢 منطقة الدخول المقترحة:** `{fmt_price(entry_min)} - {fmt_price(entry_max)}`
* **🔴 وقف الخسارة:** `{fmt_price(stop_loss)}`
* **📉 نقطة الارتكاز (Pivot):** `{fmt_price(pivot)}`
""")
                with col_b:
                    st.markdown(f"""
* **🎯 الهدف الأول (R:R 1.5):** `{fmt_price(target_1)}`
* **🎯 الهدف الثاني (R:R 2.5):** `{fmt_price(target_2)}`
* **🚀 الهدف الثالث (R:R 4.0):** `{fmt_price(target_3)}`
""")

                # --- نص البوست ---
                post_text = f"""🔥 تحليل وتوصية عملة: {coin_title} ({symbol_name}/USDT)
📍 السعر الحالي: {fmt_price(price)}
🟢 منطقة الدخول: {fmt_price(entry_min)} - {fmt_price(entry_max)}
🔴 وقف الخسارة: {fmt_price(stop_loss)}
🎯 الهدف الأول: {fmt_price(target_1)}
🎯 الهدف الثاني: {fmt_price(target_2)}
🚀 الهدف الثالث: {fmt_price(target_3)}
📊 نسبة الثقة: {confidence_score} | الاتجاه: {trend_status}
⏰ آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M')}
---
منصة جنرال رقمي Pro ⚡"""

                st.markdown("---")
                st.subheader("📋 نص الصفقة الجاهز للنسخ والنشر:")
                st.code(post_text, language="text")

            else:
                st.error(
                    f"عذراً، لم يتم العثور على العملة '{user_input}'. "
                    f"تأكد من كتابة الرمز بشكل صحيح (مثل: BTC, XRP, ETH, SOL)."
                )

# ============================================================
# 11) التبويب 2: التحليل الفني الشامل
# ============================================================
elif selected_tab == "التحليل الفني الشامل & AI":
    st.subheader("📈 التحليل الفني المتقدم وتوقعات Horizon AI")
    st.info("🚧 هذا القسم قيد التطوير — سيتم إطلاقه قريباً.")
    st.caption("💡 استخدم التبويب 'الرئيسية' حالياً للحصول على تحليل كامل لكل عملة.")

# ============================================================
# 12) التبويب 3: سجل الصفقات
# ============================================================
elif selected_tab == "سجل الصفقات (Trade Journal)":
    st.subheader("📝 دفتر الصفقات الاحترافي (R-Multiple)")
    st.info("🚧 هذا القسم قيد التطوير — سيتم إطلاقه قريباً.")
    st.caption("💡 سيتمكن قريباً من تسجيل صفقاتك وحساب أدائك بدقة.")

# ============================================================
# 13) التبويب 4: ماسح السوق (بطلب واحد فقط!)
# ============================================================
else:
    st.subheader("⚡ ماسح السوق اللحظي الشامل للعملات")
    st.markdown("قائمة حية لأبرز العملات الرقمية وأدائها:")

    scanner_coins = ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "PEPE", "SUI"]

    with st.spinner("جاري تحميل بيانات السوق..."):
        results = get_multiple_coins(scanner_coins)

    if results:
        table_data = []
        for res in results:
            table_data.append({
                "العملة": (res.get("symbol") or "").upper() + "/USDT",
                "الاسم": res.get("name") or "-",
                "السعر ($)": fmt_price(safe_float(res.get("current_price"))),
                "التغير (24س)": fmt_pct(safe_float(res.get("price_change_percentage_24h"))),
                "أعلى سعر": fmt_price(safe_float(res.get("high_24h"))),
                "أدنى سعر": fmt_price(safe_float(res.get("low_24h"))),
                "حجم التداول": f"${safe_float(res.get('total_volume')):,.0f}",
            })

        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"⏰ آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        st.warning("⚠️ تعذّر تحميل بيانات السوق الآن. حاول تحديث الصفحة بعد لحظات.")
