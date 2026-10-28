import streamlit as st
import pandas as pd
import requests
import numpy as np
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
# 2) CSS
# ============================================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
    * { font-family: 'Cairo', sans-serif !important; }
    .stApp { background-color: #0b0e14; color: #ffffff; direction: rtl; text-align: right; }
    [data-testid="stSidebar"] { background-color: #12161f; border-left: 1px solid #1e222d; direction: rtl; }
    h1, h2, h3 { color: #f3f4f6; font-weight: 900; }
    .stButton>button { background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); color: white; border-radius: 10px; border: none; font-weight: 700; padding: 0.6rem 1rem; width: 100%; }
    </style>
""", unsafe_allow_html=True)

# ============================================================
# 3) دوال مساعدة (مع دعم الأصفار العشرية)
# ============================================================
def safe_float(value, default=0.0):
    try:
        if value is None: return default
        return float(value)
    except (TypeError, ValueError):
        return default

def get_decimal_places(price):
    """اكتشاف عدد الخانات العشرية المطلوبة تلقائياً"""
    if price == 0: return 4
    if price < 0.00001: return 8
    if price < 0.001: return 6
    if price < 1: return 4
    return 2

def fmt_price(value, decimals=None):
    try:
        p = float(value)
        if decimals is None:
            decimals = get_decimal_places(p)
        return f"${p:,.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"

def fmt_pct(value):
    try: return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "N/A"

# ============================================================
# 4) الفريمات الزمنية
# ============================================================
TIMEFRAMES = {
    "5 دقائق": "5m",
    "15 دقيقة": "15m",
    "1 ساعة": "1h",
    "4 ساعات": "4h",
    "يومي": "1d",
    "أسبوعي": "1w",
}

# ============================================================
# 5) دوال المؤشرات الفنية
# ============================================================
def calculate_rsi(closes, period=14):
    if len(closes) < period + 1: return 50.0
    deltas = pd.Series(closes).diff().dropna()
    gains = deltas.where(deltas > 0, 0)
    losses = -deltas.where(deltas < 0, 0)
    avg_gain = gains.rolling(window=period).mean().iloc[-1]
    avg_loss = losses.rolling(window=period).mean().iloc[-1]
    if avg_loss == 0: return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_atr(df, period=14):
    """حساب ATR لتحديد الوقف والهدف"""
    if len(df) < period + 1: return df['high'].iloc[-1] - df['low'].iloc[-1]
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean().iloc[-1]
    return atr if not pd.isna(atr) else tr.iloc[-1]

def interpret_rsi(rsi):
    if rsi >= 70: return "تشبع شرائي (احتمال تصحيح)", "negative"
    elif rsi <= 30: return "تشبع بيعي (فرصة شراء)", "positive"
    elif 40 <= rsi <= 60: return "منطقة حياد (لا تداول)", "neutral"
    elif rsi > 60: return "زخم إيجابي (استمرار الصعود)", "positive"
    else: return "زخم سلبي (استمرار الهبوط)", "negative"

# ============================================================
# 6) جلب البيانات
# ============================================================
@st.cache_data(ttl=60, show_spinner=False)
def get_klines_data(symbol, timeframe_key):
    clean = symbol.upper().strip().replace("USDT", "").replace("/", "")
    if not clean: return None
    interval = TIMEFRAMES[timeframe_key]
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={clean}USDT&interval={interval}&limit=100"
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            data = res.json()
            if len(data) > 0:
                df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'ct', 'qv', 'n', 'tb', 'tq', 'ig'])
                df['close'] = df['close'].astype(float)
                df['high'] = df['high'].astype(float)
                df['low'] = df['low'].astype(float)
                df['volume'] = df['qv'].astype(float)
                return {"df": df, "source": "Binance"}
    except Exception:
        pass
    return None

@st.cache_data(ttl=120, show_spinner=False)
def get_market_scanner_opportunities():
    opportunities = []
    try:
        url = "https://api.coinpaprika.com/v1/tickers?limit=250"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            for t in data:
                try:
                    quotes = t.get('quotes', {}).get('USD', {})
                    if not quotes: continue
                    change = safe_float(quotes.get('percent_change_24h', 0))
                    volume = safe_float(quotes.get('volume_24h', 0))
                    price = safe_float(quotes.get('price', 0))
                    if volume > 1_000_000 and change > 5:
                        opportunities.append({
                            "الرمز": t.get('symbol', ''),
                            "الاسم": t.get('name', ''),
                            "السعر": price,
                            "التغير (24س)": change,
                            "حجم التداول": volume
                        })
                except Exception: continue
    except Exception: pass
    opportunities.sort(key=lambda x: x["التغير (24س)"], reverse=True)
    return opportunities[:10]

# ============================================================
# 7) الشريط الجانبي
# ============================================================
with st.sidebar:
    st.title("⚡ جنرال رقمي Pro")
    st.markdown("---")
    selected_tab = st.radio(
        "الانتقال السريع:",
        ["الرئيسية (Dashboard)", "سجل الصفقات (Trade Journal)", "ماسح السوق اللحظي"],
        index=0
    )
    st.markdown("---")
    st.info("💡 المحرك الاحترافي: يعتمد على ATR و RSI وإدارة رأس المال.")

# ============================================================
# 8) التبويب 1: الرئيسية (التحليل الاحترافي)
# ============================================================
if selected_tab == "الرئيسية (Dashboard)":
    st.subheader("📊 محرك التحليل الفني الاحترافي")
    
    col_input, col_tf = st.columns([3, 1])
    user_input = col_input.text_input("أدخل رمز العملة (مثل CLO, BTC):", value="BTC").strip()
    selected_tf = col_tf.selectbox("الفريم الزمني:", list(TIMEFRAMES.keys()), index=4)

    if user_input:
        with st.spinner(f"جاري تحليل {user_input}..."):
            data = get_klines_data(user_input, selected_tf)

            if data and not data['df'].empty:
                df = data['df']
                price = df['close'].iloc[-1]
                change = ((price - df['close'].iloc[0]) / df['close'].iloc[0]) * 100 if len(df) > 1 else 0
                volume = df['volume'].iloc[-1]
                
                rsi = calculate_rsi(df['close'])
                rsi_text, rsi_color = interpret_rsi(rsi)
                atr = calculate_atr(df)
                decimals = get_decimal_places(price)

                st.success(f"تم جلب التحليل: {user_input.upper()} | الفريم: {selected_tf} | المصدر: {data['source']}")

                # --- بطاقات المعلومات ---
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("السعر الحالي", fmt_price(price, decimals))
                c2.metric("التغير", fmt_pct(change))
                c3.metric("RSI (14)", f"{rsi:.1f}")
                c4.metric("ATR (تقلب)", fmt_price(atr, decimals))

                # --- قراءة RSI ---
                if rsi_color == "negative":
                    st.warning(f"⚠️ {rsi_text} (المؤشر فوق 70، خطر تصحيح).")
                elif rsi_color == "positive":
                    st.success(f"✅ {rsi_text} (المؤشر تحت 30، فرصة شراء).")
                else:
                    st.info(f"ℹ️ {rsi_text} (انتظر إشارة أوضح).")

                st.markdown("---")
                st.markdown("### 🎯 خطة التداول (مبنية على ATR)")
                
                # --- الحساب الاحترافي للوقف والهدف ---
                # الوقف = 1.5 * ATR تحت السعر الحالي (لصفقة شراء)
                stop_loss = price - (atr * 1.5)
                risk_per_unit = price - stop_loss
                
                # الأهداف = 2x, 3x, 4x من المخاطرة
                target_1 = price + (risk_per_unit * 2.0)
                target_2 = price + (risk_per_unit * 3.0)
                target_3 = price + (risk_per_unit * 4.0)

                ca, cb = st.columns(2)
                with ca:
                    st.markdown(f"""
                    **🟢 منطقة الدخول:** `{fmt_price(price, decimals)}`
                    **🔴 وقف الخسارة (1.5 ATR):** `{fmt_price(stop_loss, decimals)}`
                    **📉 المخاطرة/وحدة:** `{fmt_price(risk_per_unit, decimals)}`
                    """)
                with cb:
                    st.markdown(f"""
                    **🎯 الهدف 1 (2R):** `{fmt_price(target_1, decimals)}`
                    **🎯 الهدف 2 (3R):** `{fmt_price(target_2, decimals)}`
                    **🚀 الهدف 3 (4R):** `{fmt_price(target_3, decimals)}`
                    """)

                st.markdown("---")
                st.markdown("### ⚖️ أسباب الدخول وإبطال الفكرة")
                
                # --- الأسباب المنطقية ---
                reasons_buy = []
                reasons_invalidate = []

                if rsi < 30:
                    reasons_buy.append("RSI في منطقة تشبع بيعي (فرصة شراء).")
                elif rsi > 70:
                    reasons_buy.append("RSI في منطقة تشبع شرائي (احتمال استمرار الزخم، لكن بحذر).")
                
                if change > 0:
                    reasons_buy.append(f"الزخم الحالي إيجابي ({change:+.2f}%).")
                else:
                    reasons_buy.append(f"الزخم الحالي سلبي ({change:+.2f}%)، الدخول عكس الاتجاه يحتاج حذراً.")

                if volume > 1_000_000:
                    reasons_buy.append("حجم التداول مرتفع (سيولة جيدة).")
                else:
                    reasons_buy.append("حجم التداول متوسط.")

                # إبطال الفكرة
                reasons_invalidate.append(f"إذا أغلقت الشمعة تحت الوقف (`{fmt_price(stop_loss, decimals)}`).")
                if rsi >= 70:
                    reasons_invalidate.append("إذا كسر RSI مستوى 70 لأسفل (بداية هبوط).")
                else:
                    reasons_invalidate.append("إذا استمر RSI في الهبوط وكسر 30 لأسفل (استمرار الهبوط).")
                reasons_invalidate.append(f"إذا فشل السعر في اختراق الهدف الأول (`{fmt_price(target_1, decimals)}`).")

                ra, rb = st.columns(2)
                with ra:
                    st.markdown("**✅ أسباب الدخول:**")
                    for r in reasons_buy:
                        st.write(f"- {r}")
                with rb:
                    st.markdown("**❌ أسباب إبطال الفكرة:**")
                    for r in reasons_invalidate:
                        st.write(f"- {r}")

                st.markdown("---")
                st.markdown("### 📋 نص الصفقة للنسخ:")
                post_text = f"""🔥 تحليل: {user_input.upper()} ({selected_tf})
📍 السعر: {fmt_price(price, decimals)}
🟢 الدخول: {fmt_price(price, decimals)}
🔴 الوقف (1.5 ATR): {fmt_price(stop_loss, decimals)}
🎯 الهدف 1 (2R): {fmt_price(target_1, decimals)}
🎯 الهدف 2 (3R): {fmt_price(target_2, decimals)}
📊 RSI: {rsi:.1f} | ATR: {fmt_price(atr, decimals)}"""
                st.code(post_text, language="text")

            else:
                st.error(f"لم يتم العثور على '{user_input}'.")

# ============================================================
# 9) التبويب 2: سجل الصفقات (مع حساب الحجم والكمية)
# ============================================================
elif selected_tab == "سجل الصفقات (Trade Journal)":
    st.subheader("📝 دفتر الصفقات (إدارة رأس المال)")
    
    if "trades" not in st.session_state:
        st.session_state.trades = []

    with st.expander("➕ إضافة صفقة جديدة", expanded=True):
        with st.form("new_trade_form"):
            f1, f2 = st.columns(2)
            
            with f1:
                t_symbol = st.text_input("رمز العملة", "BTC").upper()
                t_direction = st.selectbox("الاتجاه", ["شراء", "بيع"])
                t_entry = st.number_input("سعر الدخول", min_value=0.0, value=0.0, step=0.00000001, format="%.8f")
            
            with f2:
                t_capital = st.number_input("رأس المال (بالدولار)", min_value=10.0, value=1000.0, step=100.0)
                t_risk_pct = st.slider("نسبة المخاطرة من رأس المال (%)", 0.5, 5.0, 1.0, 0.5)
                t_stop = st.number_input("وقف الخسارة", min_value=0.0, value=0.0, step=0.00000001, format="%.8f")

            submitted = st.form_submit_button("💾 حفظ وحساب الحجم")

            if submitted:
                if t_entry > 0 and t_stop > 0 and t_capital > 0:
                    # حساب الحجم الاحترافي
                    risk_amount = t_capital * (t_risk_pct / 100.0)
                    risk_per_unit = abs(t_entry - t_stop)
                    
                    if risk_per_unit == 0:
                        st.error("الوقف لا يمكن أن يكون مساوياً لسعر الدخول.")
                    else:
                        position_size = risk_amount / risk_per_unit
                        position_value = position_size * t_entry
                        
                        st.session_state.trades.append({
                            "symbol": t_symbol,
                            "direction": t_direction,
                            "entry": t_entry,
                            "stop": t_stop,
                            "exit": None,
                            "capital": t_capital,
                            "risk_pct": t_risk_pct,
                            "position_size": position_size,
                            "position_value": position_value,
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
                        st.success(f"✅ تم الحفظ! حجم الصفقة: {position_size:,.4f} وحدة (بقيمة {fmt_price(position_value, 2)}).")
                        st.rerun()
                else:
                    st.error("تأكد من إدخال سعر الدخول والوقف ورأس المال.")

    if st.session_state.trades:
        st.markdown("---")
        st.markdown("### 📋 الصفقات المسجلة")
        
        display_data = []
        for t in st.session_state.trades:
            display_data.append({
                "العملة": t["symbol"],
                "الاتجاه": t["direction"],
                "الدخول": t["entry"],
                "الوقف": t["stop"],
                "رأس المال": t["capital"],
                "المخاطرة %": t["risk_pct"],
                "حجم الصفقة (كمية)": t["position_size"],
                "قيمة الصفقة": t["position_value"],
                "التاريخ": t["date"]
            })
        
        st.dataframe(pd.DataFrame(display_data), use_container_width=True)

# ============================================================
# 10) التبويب 3: ماسح السوق
# ============================================================
elif selected_tab == "ماسح السوق اللحظي":
    st.subheader("⚡ ماسح السوق الديناميكي")
    
    with st.spinner("جاري تحليل السوق..."):
        opportunities = get_market_scanner_opportunities()

    if opportunities:
        df = pd.DataFrame(opportunities)
        # تنسيق السعر بشكل ذكي
        df['السعر'] = df['السعر'].apply(lambda x: fmt_price(x))
        df['التغير (24س)'] = df['التغير (24س)'].apply(lambda x: f"{x:+.2f}%")
        df['حجم التداول'] = df['حجم التداول'].apply(lambda x: f"${x:,.0f}")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ لا توجد فرص حالياً.")
