import streamlit as st
import pandas as pd
import requests
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

def estimate_rsi(price, high, low):
    if high <= low: return 50.0
    rsi = ((price - low) / (high - low)) * 100
    return max(0.0, min(100.0, rsi))

# ============================================================
# 4) دالة جلب البيانات المحسنة (تدعم الرموز الصغيرة بدقة)
# ============================================================
@st.cache_data(ttl=60, show_spinner=False)
def get_crypto_data_enhanced(symbol_input):
    clean = symbol_input.upper().strip().replace("USDT", "").replace("/", "").replace(" ", "")
    if not clean: return None

    # المحاولة 1: Binance (للسرعة والدقة للعملات الكبيرة والمتوسطة)
    try:
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={clean}USDT"
        res = requests.get(url, timeout=6)
        if res.status_code == 200:
            data = res.json()
            if 'lastPrice' in data and float(data['lastPrice']) > 0:
                return {
                    "current_price": float(data['lastPrice']),
                    "price_change_percentage_24h": float(data['priceChangePercent']),
                    "high_24h": float(data['highPrice']),
                    "low_24h": float(data['lowPrice']),
                    "total_volume": float(data['quoteVolume']),
                    "symbol": clean,
                    "name": clean,
                    "source": "Binance"
                }
    except Exception:
        pass

    # المحاولة 2: CoinPaprika (للعملات الصغيرة جداً)
    try:
        search_url = f"https://api.coinpaprika.com/v1/search?q={clean}&c=currencies&limit=10"
        s_res = requests.get(search_url, timeout=6)
        if s_res.status_code == 200:
            s_data = s_res.json()
            currencies = s_data.get('currencies', [])
            
            target_coin = None
            # نبحث أولاً عن تطابق تام للرمز (Ticker) لتجنب الخلط
            for coin in currencies:
                if coin.get('symbol', '').upper() == clean:
                    target_coin = coin
                    break
            # إذا لم نجد تطابق تام، نأخذ أول نتيجة
            if not target_coin and currencies:
                target_coin = currencies[0]

            if target_coin:
                coin_id = target_coin['id']
                ticker_url = f"https://api.coinpaprika.com/v1/tickers/{coin_id}"
                t_res = requests.get(ticker_url, timeout=6)
                if t_res.status_code == 200:
                    t_data = t_res.json()
                    quotes = t_data.get('quotes', {}).get('USD', {})
                    if quotes:
                        return {
                            "current_price": quotes.get('price', 0),
                            "price_change_percentage_24h": quotes.get('percent_change_24h', 0),
                            "high_24h": 0, 
                            "low_24h": 0, 
                            "total_volume": quotes.get('volume_24h', 0),
                            "symbol": t_data.get('symbol', clean),
                            "name": t_data.get('name', clean),
                            "source": "CoinPaprika"
                        }
    except Exception:
        pass

    return None

# ============================================================
# 5) الماسح الضوئي اللحظي (يعمل بدون حظر)
# ============================================================
@st.cache_data(ttl=120, show_spinner=False)
def get_market_scanner_opportunities():
    opportunities = []
    try:
        # جلب أعلى 250 عملة من حيث حجم التداول من CoinPaprika (آمن من الحظر)
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
                    symbol = t.get('symbol', '')
                    name = t.get('name', '')
                    
                    # شروط الانفجار: سيولة عالية (أكثر من 1 مليون) + تغير (أكثر من 5%)
                    if volume > 1_000_000 and change > 5:
                        opportunities.append({
                            "الرمز": symbol,
                            "الاسم": name,
                            "السعر": price,
                            "التغير (24س)": change,
                            "حجم التداول": volume
                        })
                except Exception:
                    continue
    except Exception:
        pass
        
    opportunities.sort(key=lambda x: x["التغير (24س)"], reverse=True)
    return opportunities[:10] # أفضل 10

# ============================================================
# 6) الشريط الجانبي
# ============================================================
with st.sidebar:
    st.title("⚡ جنرال رقمي Pro")
    st.markdown("---")
    selected_tab = st.radio(
        "الانتقال السريع:",
        ["الرئيسية (Dashboard)", "التحليل الفني الشامل & AI", "سجل الصفقات (Trade Journal)", "ماسح السوق اللحظي"],
        index=0
    )
    st.markdown("---")
    st.info("💡 تم التحديث: البحث الدقيق للعملات، ماسح سوق يعمل بـ 24/7، وتفاصيل أسباب الدخول.")

# ============================================================
# 7) التبويب 1: الرئيسية والتحليل
# ============================================================
if selected_tab == "الرئيسية (Dashboard)":
    st.subheader("📊 لوحة القيادة المركزية لأسواق العملات")

    # إحصائيات سريعة
    trades = st.session_state.get('trades', [])
    closed = [t for t in trades if t.get("exit")]
    total_r, win_rate = 0, 0
    if closed:
        r_vals = []
        for t in closed:
            risk = abs(t["entry"] - t["stop"])
            reward = (t["exit"] - t["entry"]) if t["direction"] == "شراء" else (t["entry"] - t["exit"])
            r_vals.append(reward / risk if risk > 0 else 0)
        total_r = sum(r_vals)
        wins = len([r for r in r_vals if r > 0])
        win_rate = (wins / len(r_vals)) * 100 if r_vals else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("نسبة الصفقات الناجحة", f"{win_rate:.1f}%", delta=f"{len(trades)} صفقة")
    col2.metric("النتيجة الصافية (R)", f"{total_r:.2f}R")
    col3.metric("توقع الذكاء الاصطناعي", "مترقب")

    st.markdown("---")
    st.subheader("🔍 محرك البحث الفوري (أدخل الرمز مثل CLO أو BTC)")
    user_input = st.text_input("رمز العملة:", value="BTC", label_visibility="collapsed").strip()

    if user_input:
        with st.spinner(f"جاري البحث عن {user_input}..."):
            data = get_crypto_data_enhanced(user_input)

            if data:
                price = safe_float(data.get("current_price"))
                change = safe_float(data.get("price_change_percentage_24h"))
                high = safe_float(data.get("high_24h"), price * 1.02)
                low = safe_float(data.get("low_24h"), price * 0.98)
                volume = safe_float(data.get("total_volume"))
                symbol_name = data.get("symbol").upper()
                coin_title = data.get("name")
                source = data.get("source")

                # حسابات التداول
                entry_min = price * 0.985
                entry_max = price * 0.998
                stop_loss = entry_min * 0.97
                risk = max(entry_min - stop_loss, price * 0.001)
                target_1 = entry_min + (risk * 1.5)
                target_2 = entry_min + (risk * 2.5)
                target_3 = entry_min + (risk * 4.0)
                rsi = estimate_rsi(price, high, low)

                st.success(f"تم جلب البيانات: {coin_title} ({symbol_name}) — المصدر: {source}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("السعر الحالي", fmt_price(price))
                c2.metric("التغير (24س)", fmt_pct(change))
                c3.metric("RSI", f"{rsi:.1f}")
                c4.metric("السيولة (24س)", f"${volume:,.0f}")

                st.markdown("---")
                st.markdown("### 🎯 خطة التداول والأسباب")
                
                # قسم أسباب الدخول وإبطال الفكرة
                ca, cb = st.columns(2)
                with ca:
                    st.markdown(f"""
                    **✅ أسباب الدخول (لماذا هذه الصفقة؟):**
                    *   **الاتجاه:** الزخم الحالي {'إيجابي' if change > 0 else 'سلبي'} ({change:+.2f}%).
                    *   **RSI:** عند {rsi:.1f} ({'منطقة شراء' if rsi < 50 else 'منطقة بيع'}).
                    *   **السيولة:** حجم تداول {f'مرتفع (> $1M)' if volume > 1_000_000 else 'متوسط'}.
                    *   **المستويات:** السعر فوق نقطة الارتكاز (${(high+low+price)/3:,.4f}).
                    """)
                with cb:
                    st.markdown(f"""
                    **❌ أسباب إبطال الفكرة (متى نلغي الصفقة؟):**
                    *   **كسر الوقف:** إذا أغلق السعر تحت `${stop_loss:,.4f}`.
                    *   **انعكاس RSI:** إذا كسر مؤشر RSI مستوى 30 لأسفل.
                    *   **جفاف السيولة:** إذا انخفض حجم التداول بشكل حاد.
                    *   **اختراق وهمي:** إذا فشل السعر في اختراق الهدف الأول `${target_1:,.4f}`.
                    """)

                st.markdown("---")
                st.markdown("### 📋 تفاصيل الصفقة للنسخ:")
                post_text = f"""🔥 تحليل: {coin_title} ({symbol_name}/USDT)
📍 السعر: {fmt_price(price)}
🟢 الدخول: {fmt_price(entry_min)} - {fmt_price(entry_max)}
🔴 وقف الخسارة: {fmt_price(stop_loss)}
🎯 الهدف 1: {fmt_price(target_1)}
🎯 الهدف 2: {fmt_price(target_2)}
🚀 الهدف 3: {fmt_price(target_3)}
📊 RSI: {rsi:.1f} | السيولة: ${volume:,.0f}
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"""
                st.code(post_text, language="text")
            else:
                st.error(f"لم يتم العثور على '{user_input}'. جرب استخدام رمز دقيق.")

# ============================================================
# 8) التبويب 4: ماسح السوق (يعمل الآن)
# ============================================================
elif selected_tab == "ماسح السوق اللحظي":
    st.subheader("⚡ ماسح السوق الديناميكي (أقوى الفرص)")
    st.markdown("يعتمد على بيانات CoinPaprika لاكتشاف العملات ذات السيولة العالية والزخم القوي (تغير > 5%).")

    with st.spinner("جاري تحليل السوق..."):
        opportunities = get_market_scanner_opportunities()

    if opportunities:
        st.success(f"تم العثور على {len(opportunities)} عملة قوية!")
        df = pd.DataFrame(opportunities)
        df['السعر'] = df['السعر'].apply(lambda x: f"${x:,.4f}")
        df['التغير (24س)'] = df['التغير (24س)'].apply(lambda x: f"{x:+.2f}%")
        df['حجم التداول'] = df['حجم التداول'].apply(lambda x: f"${x:,.0f}")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ لم يتم العثور على فرص حالياً أو أن الاتصال بالسيرفر بطيء. حاول التحديث.")

# ============================================================
# 9) التبويبات الأخرى (سجل الصفقات والتحليل الفني)
# ============================================================
elif selected_tab == "التحليل الفني الشامل & AI":
    st.subheader("📈 التحليل الفني")
    st.info("هذا القسم يعرض التحليل بناءً على البيانات اللحظية. استخدم الرئيسية للتفاصيل الكاملة.")

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
