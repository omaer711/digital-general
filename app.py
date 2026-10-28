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
# 2) CSS محسّن
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

def rsi_label(rsi):
    if rsi >= 70: return f"{rsi:.1f} (تشبع شرائي 🔴)"
    elif rsi <= 30: return f"{rsi:.1f} (تشبع بيعي 🟢)"
    elif rsi >= 50: return f"{rsi:.1f} (زخم إيجابي)"
    else: return f"{rsi:.1f} (زخم سلبي)"

def calc_confidence(change, high, low, price, volume):
    try:
        volatility = ((high - low) / price * 100) if price > 0 else 0
        base = 50 + min(abs(change) * 3, 30)
        if volatility < 3: base += 8
        elif volatility > 8: base -= 5
        if volume and volume > 1_000_000: base += 5
        return max(10, min(base, 95))
    except Exception: return 50.0

# ============================================================
# 4) خريطة الرموز (للاستخدام مع Binance)
# ============================================================
# بعض العملات لها رموز مختلفة قليلاً في Binance، لكن البحث المباشر بـ USDT هو الأفضل
SYMBOL_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "ripple",
    "ADA": "cardano", "DOGE": "dogecoin", "SHIB": "shiba-inu", "BNB": "binancecoin",
    "SUI": "sui", "PEPE": "pepe", "AVAX": "avalanche-2", "LINK": "chainlink",
    "MATIC": "matic-network", "DOT": "polkadot", "TON": "the-open-network",
}

# ============================================================
# 5) الدالة المحورية: جلب بيانات عملة واحدة (Binance أولاً، ثم CoinPaprika)
# ============================================================
@st.cache_data(ttl=60, show_spinner=False)
def get_crypto_data_enhanced(symbol_input):
    clean = symbol_input.upper().strip().replace("USDT", "").replace("/", "").replace(" ", "")
    if not clean: return None

    # --- المحاولة 1: Binance API (الأفضل للعملات الصغيرة والسيولة) ---
    binance_pair = f"{clean}USDT"
    try:
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={binance_pair}"
        res = requests.get(url, timeout=6)
        if res.status_code == 200:
            data = res.json()
            # التحقق من وجود السعر لتجنب الردود الفارغة
            if 'lastPrice' in data and float(data['lastPrice']) > 0:
                return {
                    "current_price": float(data['lastPrice']),
                    "price_change_percentage_24h": float(data['priceChangePercent']),
                    "high_24h": float(data['highPrice']),
                    "low_24h": float(data['lowPrice']),
                    "total_volume": float(data['quoteVolume']),
                    "symbol": clean,
                    "name": clean, # Binance لا يعطي الاسم الكامل، سنستخدم الرمز
                    "source": "Binance"
                }
    except Exception:
        pass # ننتقل للمصدر التالي

    # --- المحاولة 2: CoinPaprika (يغطي 12,000+ عملة، مفيد إذا فشل Binance) ---
    try:
        # CoinPaprika يحتاج للبحث عن الـ ID أولاً
        search_url = f"https://api.coinpaprika.com/v1/search?q={clean}&c=currencies&limit=1"
        s_res = requests.get(search_url, timeout=6)
        if s_res.status_code == 200:
            s_data = s_res.json()
            if s_data.get('currencies'):
                coin_id = s_data['currencies'][0]['id']
                # جلب بيانات Ticker
                ticker_url = f"https://api.coinpaprika.com/v1/tickers/{coin_id}"
                t_res = requests.get(ticker_url, timeout=6)
                if t_res.status_code == 200:
                    t_data = t_res.json()
                    quotes = t_data.get('quotes', {}).get('USD', {})
                    if quotes:
                        return {
                            "current_price": quotes.get('price', 0),
                            "price_change_percentage_24h": quotes.get('percent_change_24h', 0),
                            "high_24h": quotes.get('ath_price', 0), # تقريب
                            "low_24h": 0, # غير متوفر بسهولة
                            "total_volume": quotes.get('volume_24h', 0),
                            "symbol": t_data.get('symbol', clean),
                            "name": t_data.get('name', clean),
                            "source": "CoinPaprika"
                        }
    except Exception:
        pass

    return None

# ============================================================
# 6) ماسح السوق الديناميكي (يعتمد على Binance لاكتشاف الفرص)
# ============================================================
@st.cache_data(ttl=120, show_spinner=False) # كاش دقيقتين لتقليل الضغط
def get_market_scanner_opportunities():
    opportunities = []
    try:
        # جلب كل أزواج USDT دفعة واحدة (طلب واحد فقط!)
        url = "https://api.binance.com/api/v3/ticker/24hr"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            all_tickers = res.json()
            for t in all_tickers:
                if t['symbol'].endswith('USDT'):
                    try:
                        change = float(t['priceChangePercent'])
                        volume = float(t['quoteVolume'])
                        price = float(t['lastPrice'])
                        # شروط الانفجار: سيولة عالية (> 500 ألف دولار) + ارتفاع قوي (> 5%)
                        if volume > 500_000 and change > 5:
                            opportunities.append({
                                "العملة": t['symbol'].replace('USDT', ''),
                                "السعر": price,
                                "التغير (24س)": change,
                                "حجم التداول": volume,
                                "قوة الزخم": change
                            })
                    except (ValueError, KeyError):
                        continue
    except Exception:
        pass
    # ترتيب حسب الأقوى زخماً
    opportunities.sort(key=lambda x: x["التغير (24س)"], reverse=True)
    return opportunities[:10] # أفضل 10 فرص

# ============================================================
# 7) الشريط الجانبي
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
    st.info("💡 منصة تداول حية متصلة بالأسواق العالمية (Binance + CoinPaprika).")

# ============================================================
# 8) التبويب 1: الرئيسية
# ============================================================
if selected_tab == "الرئيسية (Dashboard)":
    st.subheader("📊 لوحة القيادة المركزية لأسواق العملات")

    # إحصائيات حقيقية من دفتر الصفقات
    trades = st.session_state.get('trades', [])
    if trades:
        closed = [t for t in trades if t.get("exit")]
        if closed:
            def calc_r(t):
                try:
                    entry, stop, exit_p = t["entry"], t["stop"], t["exit"]
                    risk = abs(entry - stop)
                    if risk == 0: return 0
                    reward = (exit_p - entry) if t["direction"] == "شراء" else (entry - exit_p)
                    return reward / risk
                except: return 0
            r_vals = [calc_r(t) for t in closed]
            total_r = sum(r_vals)
            wins = len([r for r in r_vals if r > 0])
            win_rate = (wins / len(r_vals)) * 100 if r_vals else 0
        else:
            total_r, win_rate = 0, 0
    else:
        total_r, win_rate = 0, 0

    col1, col2, col3 = st.columns(3)
    col1.metric("نسبة الصفقات الناجحة", f"{win_rate:.1f}%", delta=f"{len(trades)} صفقة")
    col2.metric("النتيجة الصافية (R)", f"{total_r:.2f}R", delta="ربح ✅" if total_r > 0 else ("خسارة ❌" if total_r < 0 else "متعادل"))
    col3.metric("توقع الذكاء الاصطناعي", "مترقب", delta="بانتظار التحليل")

    st.markdown("---")
    st.subheader("🔍 محرك البحث الفوري برمز العملة")
    user_input = st.text_input("أدخل رمز العملة (مثل: BTC, XRP, ETH, ADA, PEPE):", value="BTC").strip()

    if user_input:
        with st.spinner(f"جاري جلب البيانات لـ {user_input}..."):
            data = get_crypto_data_enhanced(user_input)

            if data:
                price = safe_float(data.get("current_price"))
                change = safe_float(data.get("price_change_percentage_24h"))
                high = safe_float(data.get("high_24h"), price * 1.02)
                low = safe_float(data.get("low_24h"), price * 0.98)
                volume = safe_float(data.get("total_volume"))
                symbol_name = (data.get("symbol") or "COIN").upper()
                coin_title = data.get("name") or "Asset"
                source = data.get("source", "API")

                # خطة التداول
                entry_min = price * 0.985
                entry_max = price * 0.998
                stop_loss = entry_min * 0.97
                risk = max(entry_min - stop_loss, price * 0.001)
                target_1 = entry_min + (risk * 1.5)
                target_2 = entry_min + (risk * 2.5)
                target_3 = entry_min + (risk * 4.0)
                pivot = (high + low + price) / 3

                rsi = estimate_rsi(price, high, low)
                rsi_text = rsi_label(rsi)
                conf_value = calc_confidence(change, high, low, price, volume)
                conf_desc = "قوية جداً" if conf_value >= 80 else ("قوية" if conf_value >= 65 else ("متوسطة" if conf_value >= 50 else "حذرة"))
                confidence_score = f"{conf_value:.1f}% ({conf_desc})"
                trend_status = "🟢 صاعد قوي" if change > 0 else "🔴 تصحيحي"

                st.success(f"تم جلب التحليل لـ: {coin_title} ({symbol_name}) — المصدر: {source}")

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("السعر الحالي", fmt_price(price))
                c2.metric("التغير (24س)", fmt_pct(change))
                c3.metric("أعلى (24س)", fmt_price(high))
                c4.metric("أدنى (24س)", fmt_price(low))

                st.markdown("---")
                st.markdown("### 🤖 مؤشرات الثقة (Horizon AI)")
                a1, a2, a3 = st.columns(3)
                a1.metric("نسبة الثقة", confidence_score)
                a2.metric("الاتجاه العام", trend_status)
                a3.metric("RSI", rsi_text)

                st.markdown("---")
                st.markdown("### 🎯 خطة التداول")
                ca, cb = st.columns(2)
                with ca:
                    st.markdown(f"""
* **🟢 الدخول:** `{fmt_price(entry_min)} - {fmt_price(entry_max)}`
* **🔴 وقف الخسارة:** `{fmt_price(stop_loss)}`
* **📉 Pivot:** `{fmt_price(pivot)}`
""")
                with cb:
                    st.markdown(f"""
* **🎯 الهدف 1 (R:R 1.5):** `{fmt_price(target_1)}`
* **🎯 الهدف 2 (R:R 2.5):** `{fmt_price(target_2)}`
* **🚀 الهدف 3 (R:R 4.0):** `{fmt_price(target_3)}`
""")

                post_text = f"""🔥 تحليل: {coin_title} ({symbol_name}/USDT)
📍 السعر: {fmt_price(price)}
🟢 الدخول: {fmt_price(entry_min)} - {fmt_price(entry_max)}
🔴 وقف الخسارة: {fmt_price(stop_loss)}
🎯 الهدف 1: {fmt_price(target_1)}
🎯 الهدف 2: {fmt_price(target_2)}
🚀 الهدف 3: {fmt_price(target_3)}
📊 الثقة: {confidence_score} | الاتجاه: {trend_status}
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}
---
جنرال رقمي Pro ⚡"""

                st.markdown("---")
                st.subheader("📋 نص الصفقة للنسخ:")
                st.code(post_text, language="text")
            else:
                st.error(f"لم يتم العثور على '{user_input}' في Binance أو CoinPaprika. تأكد من كتابة الرمز بشكل صحيح (مثل: BTC, FHE, CLO).")

# ============================================================
# 9) التبويب 2: التحليل الفني المتقدم (مبسط ليعمل مع Binance)
# ============================================================
elif selected_tab == "التحليل الفني الشامل & AI":
    st.subheader("📈 التحليل الفني المتقدم وتوقعات Horizon AI")
    adv_input = st.text_input("أدخل رمز العملة للتحليل المتقدم:", value="BTC").strip()

    if adv_input:
        with st.spinner("جاري تحميل البيانات التاريخية والتحليل..."):
            # نجلب البيانات الأساسية أولاً للتأكد من وجود العملة
            current = get_crypto_data_enhanced(adv_input)
            if current:
                price = safe_float(current.get("current_price"))
                high = safe_float(current.get("high_24h"))
                low = safe_float(current.get("low_24h"))
                change = safe_float(current.get("price_change_percentage_24h"))
                symbol = current.get("symbol")

                # حساب RSI تقريبي وسريع (لأن جلب التاريخي من Binance يحتاج شموع، سنبسط هنا)
                rsi = estimate_rsi(price, high, low)
                trend = "🟢 صاعد قوي" if change > 2 else ("🔴 هابط" if change < -2 else "🟡 متذبذب")

                st.markdown("### 📊 المؤشرات الفنية")
                m1, m2, m3 = st.columns(3)
                m1.metric("RSI (تقريبي)", f"{rsi:.1f}")
                m2.metric("الاتجاه (24س)", trend)
                m3.metric("التغير", fmt_pct(change))

                st.markdown("---")
                st.markdown("### 🤖 توصية Horizon AI")
                if rsi < 30 and change > 0:
                    rec = "🟢 شراء قوي (Strong Buy) - تشبع بيعي مع بداية تعافي"
                elif rsi > 70:
                    rec = "🔴 بيع (Sell) - تشبع شرائي"
                elif change > 5:
                    rec = "🟢 شراء (Buy) - زخم قوي"
                else:
                    rec = "🟡 حياد (Hold) - بانتظار إشارة أوضح"
                st.metric("التوصية", rec)
            else:
                st.warning(f"⚠️ لا تتوفر بيانات لـ '{adv_input}'. جرّب BTC أو أي عملة متاحة في Binance.")

# ============================================================
# 10) التبويب 3: دفتر الصفقات (مع إصلاح session_state)
# ============================================================
elif selected_tab == "سجل الصفقات (Trade Journal)":
    st.subheader("📝 دفتر الصفقات الاحترافي (R-Multiple)")

    # تهيئة الحالة إذا لم تكن موجودة
    if "trades" not in st.session_state:
        st.session_state.trades = []

    with st.expander("➕ إضافة صفقة جديدة", expanded=(len(st.session_state.trades) == 0)):
        with st.form("new_trade_form", clear_on_submit=True):
            f1, f2 = st.columns(2)
            with f1:
                t_symbol = st.text_input("رمز العملة", value="BTC").upper().strip()
                t_direction = st.selectbox("الاتجاه", ["شراء", "بيع"])
                t_entry = st.number_input("سعر الدخول", min_value=0.0, value=0.0, step=0.0001, format="%.4f")
            with f2:
                t_stop = st.number_input("وقف الخسارة", min_value=0.0, value=0.0, step=0.0001, format="%.4f")
                t_exit = st.number_input("سعر الخروج (اتركه 0 لو مفتوحة)", min_value=0.0, value=0.0, step=0.0001, format="%.4f")
                t_notes = st.text_input("ملاحظات (اختياري)", value="")

            submitted = st.form_submit_button("💾 حفظ الصفقة")

            if submitted:
                if t_entry > 0 and t_stop > 0 and t_symbol:
                    st.session_state.trades.append({
                        "symbol": t_symbol,
                        "direction": t_direction,
                        "entry": t_entry,
                        "stop": t_stop,
                        "exit": t_exit if t_exit > 0 else None,
                        "notes": t_notes,
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    })
                    st.success("✅ تم حفظ الصفقة!")
                    st.rerun()
                else:
                    st.error("يجب إدخال الرمز، سعر الدخول، ووقف الخسارة.")

    st.markdown("---")
    if st.session_state.trades:
        st.markdown(f"### 📋 الصفقات المسجلة ({len(st.session_state.trades)})")
        rows = []
        for i, t in enumerate(st.session_state.trades):
            if t["exit"]:
                entry, stop, exit_p = t["entry"], t["stop"], t["exit"]
                risk = abs(entry - stop)
                reward = (exit_p - entry) if t["direction"] == "شراء" else (entry - exit_p)
                r = reward / risk if risk > 0 else 0
                status = "✅ ربح" if r > 0 else ("❌ خسارة" if r < 0 else "⚖️ تعادل")
                r_display = f"{r:+.2f}R"
            else:
                status = "🔄 مفتوحة"
                r_display = "—"
            rows.append({
                "#": i + 1, "العملة": t["symbol"], "الاتجاه": t["direction"],
                "الدخول": f"${t['entry']:,.4f}", "الوقف": f"${t['stop']:,.4f}",
                "الخروج": f"${t['exit']:,.4f}" if t["exit"] else "—",
                "R-Multiple": r_display, "الحالة": status, "التاريخ": t["date"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # إحصائيات
        closed = [t for t in st.session_state.trades if t["exit"]]
        if closed:
            def calc_r(t):
                try:
                    risk = abs(t["entry"] - t["stop"])
                    if risk == 0: return 0
                    reward = (t["exit"] - t["entry"]) if t["direction"] == "شراء" else (t["entry"] - t["exit"])
                    return reward / risk
                except: return 0
            r_vals = [calc_r(t) for t in closed]
            total_r = sum(r_vals)
            wins = len([r for r in r_vals if r > 0])
            win_rate = (wins / len(r_vals)) * 100 if r_vals else 0
            avg_r = total_r / len(r_vals) if r_vals else 0
            st.markdown("---")
            st.markdown("### 📊 إحصائيات الأداء")
            s1, s2, s3 = st.columns(3)
            s1.metric("إجمالي R", f"{total_r:+.2f}R")
            s2.metric("نسبة النجاح", f"{win_rate:.1f}%", delta=f"{wins} ربح / {len(r_vals)-wins} خسارة")
            s3.metric("متوسط R", f"{avg_r:+.2f}R")

        # تصدير
        export_df = pd.DataFrame(st.session_state.trades)
        csv = export_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 تصدير الصفقات (CSV)", data=csv, file_name=f"trades_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
    else:
        st.info("📭 لم تسجّل أي صفقات بعد. أضف صفقتك الأولى من النموذج أعلاه.")

# ============================================================
# 11) التبويب 4: ماسح السوق الديناميكي (يعمل الآن!)
# ============================================================
else:
    st.subheader("⚡ ماسح السوق الديناميكي - أقوى العملات الآن")
    st.markdown("يتم تحليل آلاف الأزواج لاكتشاف العملات ذات السيولة العالية والزخم القوي (شروط الانفجار: سيولة > 500 ألف دولار + تغير > 5%).")

    with st.spinner("جاري تحليل السوق للبحث عن الفرص..."):
        opportunities = get_market_scanner_opportunities()

    if opportunities:
        st.success(f"تم العثور على {len(opportunities)} عملة قوية! (مرتبة من الأقوى زخماً)")
        df = pd.DataFrame(opportunities)
        df['السعر'] = df['السعر'].apply(lambda x: f"${x:,.4f}")
        df['التغير (24س)'] = df['التغير (24س)'].apply(lambda x: f"{x:+.2f}%")
        df['حجم التداول'] = df['حجم التداول'].apply(lambda x: f"${x:,.0f}")
        # إخفاء عمود قوة الزخم لأنه مكرر مع التغير
        df = df.drop(columns=['قوة الزخم'])
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"⏰ آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        st.warning("⚠️ لم يتم العثور على فرص حالياً تطابق المعايير، أو أن Binance محظور جغرافياً. حاول تحديث الصفحة بعد قليل.")
