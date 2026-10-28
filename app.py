import streamlit as st
import pandas as pd
import requests
import time
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
    [data-testid="stSidebar"] .stRadio label, [data-testid="stSidebar"] .stTextInput input, [data-testid="stSidebar"] .stMarkdown { direction: rtl; text-align: right; }
    h1, h2, h3 { color: #f3f4f6; font-weight: 900; }
    .stButton>button { background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); color: white; border-radius: 10px; border: none; font-weight: 700; padding: 0.6rem 1rem; width: 100%; }
    .positive { color: #22c55e; }
    .negative { color: #ef4444; }
    </style>
""", unsafe_allow_html=True)

# ============================================================
# 3) دوال مساعدة
# ============================================================
def safe_float(value, default=0.0):
    try:
        if value is None: return default
        return float(value)
    except (TypeError, ValueError):
        return default

def fmt_price(value, decimals=4):
    try: return f"${float(value):,.{decimals}f}"
    except (TypeError, ValueError): return "N/A"

def fmt_pct(value):
    try: return f"{float(value):+.2f}%"
    except (TypeError, ValueError): return "N/A"

# ============================================================
# 4) الفريمات الزمنية
# ============================================================
TIMEFRAMES = {
    "5 دقائق (5m)": {"binance": "5m", "paprika": 1},
    "15 دقيقة (15m)": {"binance": "15m", "paprika": 1},
    "1 ساعة (1h)": {"binance": "1h", "paprika": 2},
    "4 ساعات (4h)": {"binance": "4h", "paprika": 3},
    "يومي (1D)": {"binance": "1d", "paprika": 7},
    "أسبوعي (1W)": {"binance": "1w", "paprika": 30},
}

# ============================================================
# 5) دوال المؤشرات الفنية (RSI الحقيقي و SMA)
# ============================================================
def calculate_real_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    deltas = pd.Series(closes).diff().dropna()
    gains = deltas.where(deltas > 0, 0)
    losses = -deltas.where(deltas < 0, 0)
    avg_gain = gains.rolling(window=period).mean().iloc[-1]
    avg_loss = losses.rolling(window=period).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def interpret_rsi(rsi):
    if rsi >= 70:
        return "تشبع شرائي (احتمال تصحيح 🔴)", "negative"
    elif rsi <= 30:
        return "تشبع بيعي (فرصة شراء 🟢)", "positive"
    elif 40 <= rsi <= 60:
        return "منطقة حياد (لا تداول 🟡)", "neutral"
    elif rsi > 60:
        return "زخم إيجابي (استمرار الصعود 🟢)", "positive"
    else:
        return "زخم سلبي (استمرار الهبوط 🔴)", "negative"

# ============================================================
# 6) جلب البيانات التاريخية (Klines) - قلبه المحرك
# ============================================================
@st.cache_data(ttl=60, show_spinner=False)
def get_klines_data(symbol, timeframe_key):
    clean = symbol.upper().strip().replace("USDT", "").replace("/", "")
    if not clean: return None
    
    # 1. محاولة Binance (الأفضل)
    interval = TIMEFRAMES[timeframe_key]["binance"]
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
                df['volume'] = df['qv'].astype(float) # Quote Volume
                return {"df": df, "source": "Binance"}
    except Exception:
        pass

    # 2. محاولة CoinPaprika (للعملات الصغيرة التي لا توجد في Binance)
    try:
        # البحث عن الـ ID أولاً
        s_url = f"https://api.coinpaprika.com/v1/search?q={clean}&c=currencies&limit=5"
        s_res = requests.get(s_url, timeout=6)
        if s_res.status_code == 200:
            currencies = s_res.json().get('currencies', [])
            target = next((c for c in currencies if c.get('symbol','').upper() == clean), currencies[0] if currencies else None)
            if target:
                coin_id = target['id']
                days = TIMEFRAMES[timeframe_key]["paprika"]
                h_url = f"https://api.coinpaprika.com/v1/coins/{coin_id}/ohlcv/latest?quote=USD" # تقريبي
                # في حال عدم توفر OHLCV للفريمات القصيرة في المجاني، نستخدم Tickers
                t_url = f"https://api.coinpaprika.com/v1/tickers/{coin_id}?quotes=USD"
                t_res = requests.get(t_url, timeout=6)
                if t_res.status_code == 200:
                    t_data = t_res.json()
                    quotes = t_data.get('quotes', {}).get('USD', {})
                    if quotes:
                        # نبني DF وهمي بسيط ليعمل الكود (لأن المجاني لا يعطي شموع دقيقة)
                        price = safe_float(quotes.get('price'))
                        df = pd.DataFrame({
                            'close': [price],
                            'high': [price * 1.01],
                            'low': [price * 0.99],
                            'volume': [safe_float(quotes.get('volume_24h'))]
                        })
                        return {"df": df, "source": "CoinPaprika (تقديري)"}
    except Exception:
        pass

    return None

# ============================================================
# 7) الماسح الضوئي اللحظي (يستخدم CoinPaprika)
# ============================================================
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
                except Exception:
                    continue
    except Exception:
        pass
    opportunities.sort(key=lambda x: x["التغير (24س)"], reverse=True)
    return opportunities[:10]

# ============================================================
# 8) الشريط الجانبي
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
    st.info("💡 تم تحديث المحرك ليدعم الفريمات الزمنية الحقيقية.")

# ============================================================
# 9) التبويب 1: الرئيسية
# ============================================================
if selected_tab == "الرئيسية (Dashboard)":
    st.subheader("📊 محرك التحليل الفني والبحث")
    
    col_input, col_tf = st.columns([3, 1])
    user_input = col_input.text_input("أدخل رمز العملة (مثل CLO, BTC):", value="BTC").strip()
    selected_tf = col_tf.selectbox("الفريم الزمني:", list(TIMEFRAMES.keys()), index=4) # افتراضي يومي

    if user_input:
        with st.spinner(f"جاري تحليل {user_input} على فريم {selected_tf}..."):
            data = get_klines_data(user_input, selected_tf)

            if data and not data['df'].empty:
                df = data['df']
                price = df['close'].iloc[-1]
                change = 0.0
                if len(df) > 1:
                    change = ((price - df['close'].iloc[0]) / df['close'].iloc[0]) * 100
                
                high = df['high'].max()
                low = df['low'].min()
                volume = df['volume'].iloc[-1]
                rsi = calculate_real_rsi(df['close'])
                rsi_text, rsi_color = interpret_rsi(rsi)
                source = data['source']

                st.success(f"تم جلب التحليل: {user_input.upper()} | المصدر: {source} | الفريم: {selected_tf}")

                # 1. السعر والمؤشرات
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("السعر الحالي", fmt_price(price))
                c2.metric("التغير", fmt_pct(change))
                c3.metric("RSI (14)", f"{rsi:.1f}")
                c4.metric("السيولة", f"${volume:,.0f}")

                # قراءة RSI بشكل منطقي
                if rsi_color == "negative":
                    st.warning(f"⚠️ قراءة RSI: {rsi_text} (المؤشر فوق 70، خطر تصحيح، يفضل البيع أو الانتظار).")
                elif rsi_color == "positive":
                    st.success(f"✅ قراءة RSI: {rsi_text} (المؤشر تحت 30، فرصة شراء مع بداية الانعكاس).")
                else:
                    st.info(f"ℹ️ قراءة RSI: {rsi_text} (لا توجد إشارة قوية، انتظر خروج المؤشر من هذه المنطقة).")

                st.markdown("---")
                st.markdown("### 🎯 خطة التداول")
                
                # نقاط الدخول والخروج مبنية على فريم الساعة الحالي
                entry = price * 0.995
                stop = price * 0.97
                t1 = price * 1.03
                t2 = price * 1.06
                
                ca, cb = st.columns(2)
                with ca:
                    st.markdown(f"**🟢 الدخول:** `{fmt_price(entry)}`\n\n**🔴 الوقف:** `{fmt_price(stop)}`")
                with cb:
                    st.markdown(f"**🎯 الهدف 1:** `{fmt_price(t1)}`\n\n**🎯 الهدف 2:** `{fmt_price(t2)}`")

                st.markdown("---")
                st.markdown("### ⚖️ أسباب الدخول وإبطال الفكرة")
                ra, rb = st.columns(2)
                with ra:
                    st.markdown(f"""
                    **✅ أسباب الدخول:**
                    *   **الاتجاه:** السعر الحالي {fmt_price(price)} وهو {'أعلى' if change > 0 else 'أقل'} من سعر الافتتاح ({fmt_price(df['close'].iloc[0])}).
                    *   **RSI:** المؤشر عند {rsi:.1f} مما يعني ({rsi_text}).
                    *   **السيولة:** حجم التداول {f'مرتفع' if volume > 1_000_000 else 'متوسط'} بقيمة ${volume:,.0f}.
                    """)
                with rb:
                    # أسباب منطقية إبطال الصفقة
                    st.markdown(f"""
                    **❌ أسباب إبطال الفكرة:**
                    *   **كسر الوقف:** إذا أغلقت الشمعة تحت `${stop:,.4f}`.
                    *   **انعكاس RSI:** إذا كسر RSI مستوى **70** لأسفل بعد تشبع شرائي (بداية هبوط).
                    *   **فشل الاختراق:** إذا فشل السعر في تجاوز المقاومة عند `${t1:,.4f}`.
                    *   **خبر سلبي:** أي خبر مؤسسي أو تنظيمي سلبي على العملة.
                    """)

                st.markdown("---")
                st.markdown("### 📋 نص الصفقة للنسخ:")
                post_text = f"""🔥 تحليل: {user_input.upper()} ({selected_tf})
📍 السعر: {fmt_price(price)}
🟢 الدخول: {fmt_price(entry)}
🔴 الوقف: {fmt_price(stop)}
🎯 الهدف 1: {fmt_price(t1)}
🎯 الهدف 2: {fmt_price(t2)}
📊 RSI: {rsi:.1f} | السيولة: ${volume:,.0f}"""
                st.code(post_text, language="text")

            else:
                st.error(f"لم يتم العثور على '{user_input}'. حاول استخدام رمز صحيح أو فريم مختلف.")

# ============================================================
# 10) التبويب 2: سجل الصفقات
# ============================================================
elif selected_tab == "سجل الصفقات (Trade Journal)":
    st.subheader("📝 دفتر الصفقات")
    if "trades" not in st.session_state:
        st.session_state.trades = []

    with st.expander("➕ إضافة صفقة جديدة"):
        with st.form("new_trade"):
            f1, f2 = st.columns(2)
            t_symbol = f1.text_input("الرمز", "BTC")
            t_direction = f1.selectbox("الاتجاه", ["شراء", "بيع"])
            t_entry = f2.number_input("الدخول", min_value=0.0, step=0.0001)
            t_stop = f2.number_input("الوقف", min_value=0.0, step=0.0001)
            t_exit = f2.number_input("الخروج (0 للمفتوحة)", min_value=0.0, step=0.0001)
            
            if st.form_submit_button("حفظ"):
                if t_entry > 0 and t_stop > 0:
                    st.session_state.trades.append({
                        "symbol": t_symbol, "direction": t_direction,
                        "entry": t_entry, "stop": t_stop, "exit": t_exit if t_exit > 0 else None,
                        "date": datetime.now().strftime("%Y-%m-%d")
                    })
                    st.rerun()
    
    if st.session_state.trades:
        st.dataframe(pd.DataFrame(st.session_state.trades), use_container_width=True)

# ============================================================
# 11) التبويب 3: ماسح السوق
# ============================================================
elif selected_tab == "ماسح السوق اللحظي":
    st.subheader("⚡ ماسح السوق الديناميكي")
    st.markdown("يعرض أفضل الفرص بناءً على سيولة عالية وتغير سعري قوي (+5% أو أكثر).")
    
    with st.spinner("جاري تحليل السوق..."):
        opportunities = get_market_scanner_opportunities()

    if opportunities:
        df = pd.DataFrame(opportunities)
        df['السعر'] = df['السعر'].apply(lambda x: f"${x:,.4f}")
        df['التغير (24س)'] = df['التغير (24س)'].apply(lambda x: f"{x:+.2f}%")
        df['حجم التداول'] = df['حجم التداول'].apply(lambda x: f"${x:,.0f}")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ لم يتم العثور على فرص حالياً.")
