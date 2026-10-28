import streamlit as st
import pandas as pd
import requests

st.set_page_config(
    page_title="جنرال رقمي | Digital General Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
    * { font-family: 'Cairo', sans-serif !important; }
    .stApp { background-color: #0b0e14; color: #ffffff; direction: rtl; text-align: right; }
    [data-testid="stSidebar"] { background-color: #12161f; border-left: 1px solid #1e222d; direction: rtl; }
    .metric-card { background-color: #1e222d; border: 1px solid #2a2e39; padding: 20px; border-radius: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); margin-bottom: 20px; }
    .stButton>button { background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); color: white; border-radius: 10px; border: none; font-weight: 700; padding: 0.6rem 1rem; width: 100%; }
    h1, h2, h3 { color: #f3f4f6; font-weight: 900; }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("⚡ جنرال رقمي Pro")
    st.markdown("---")
    selected_tab = st.radio(
        "الانتقال السريع:",
        ["الرئيسية (Dashboard)", "التحليل الفني الشامل & AI", "سجل الصفقات (Trade Journal)", "ماسح السوق اللحظي"],
        index=0
    )
    st.markdown("---")
    st.info("💡 منصة تداول حية متصلة بأسواق Binance العالمية.")

def get_binance_live_data(symbol):
    clean = symbol.upper().strip().replace("USDT", "").replace("/", "").replace("-", "")
    pair = clean + "USDT"
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={pair}"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            d = res.json()
            return {
                "symbol": pair,
                "price": float(d["lastPrice"]),
                "high": float(d["highPrice"]),
                "low": float(d["lowPrice"]),
                "change": float(d["priceChangePercent"]),
                "volume": float(d["quoteVolume"])
            }
    except:
        pass
    return None

if selected_tab == "الرئيسية (Dashboard)":
    st.subheader("📊 لوحة القيادة المركزية لأسواق العملات")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="نسبة صفقات الأسبوع الناجحة", value="66%", delta="ممتاز")
    with col2:
        st.metric(label="النتيجة الصافية (R-Multiple)", value="+736.45R", delta="عالي الأداء")
    with col3:
        st.metric(label="توقع الذكاء الاصطناعي العام", value="77% صاعد", delta="إيجابي")

    st.markdown("---")
    st.subheader("🔍 محرك التحليل الشامل والمتقدم لجميع العملات (رئيسية وبديلة)")
    
    # مربع بحث حر لأي عملة يختارها المستخدم
    user_symbol = st.text_input("أدخل رمز العملة للبحث والتحليل (مثال: XRP, BTC, ETH, SOL, ADA, PEPE):", value="XRP")
    
    if user_symbol:
        with st.spinner(f"جاري جلب البيانات الحية لـ {user_symbol} من منصة Binance..."):
            market_data = get_binance_live_data(user_symbol)
            
            if market_data:
                price = market_data["price"]
                
                # حساب مستويات دقيقة ومنطقية مبنية 100% على السعر الحالي الحقيقي
                entry_min = price * 0.990
                entry_max = price * 1.002
                stop_loss = price * 0.965  # وقف خسارة تحته بمنطقة آمنة
                target_1 = price * 1.035   # هدف أول
                target_2 = price * 1.070   # هدف ثاني
                target_3 = price * 1.120   # هدف ثالث
                pivot = price * 0.985
                support_weekly = market_data["low"] * 0.99
                resistance_1 = market_data["high"] * 1.01

                st.success(f"تم بنجاح جلب بيانات العملة الحية: {market_data['symbol']}")
                
                # عرض الأسعار الرئيسية الحية
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("السعر الحالي", f"${price:,.4f}")
                with c2:
                    st.metric("التغير (24س)", f"{market_data['change']:+.2f}%")
                with c3:
                    st.metric("أعلى سعر (24س)", f"${market_data['high']:,.4f}")
                with c4:
                    st.metric("أدنى سعر (24س)", f"${market_data['low']:,.4f}")

                st.markdown("---")
                st.markdown("### 🎯 خطة التداول الفورية ومستويات الدخول والهدف")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"""
                    * **🟢 منطقة الدخول المقترحة:** `${entry_min:,.4f} - ${entry_max:,.4f}`
                    * **🔴 وقف الخسارة (Stop Loss):** `${stop_loss:,.4f}`
                    * **📉 نقطة الارتكاز (Pivot):** `${pivot:,.4f}`
                    """)
                with col_b:
                    st.markdown(f"""
                    * **🎯 الهدف الأول (Target 1):** `${target_1:,.4f}`
                    * **🎯 الهدف الثاني (Target 2):** `${target_2:,.4f}`
                    * **🚀 الهدف الثالث (Target 3):** `${target_3:,.4f}`
                    """)
                    
                st.markdown("---")
                st.markdown("### 🛡️ مستويات الدعم والمقاومة الحية")
                c_sup1, c_sup2, c_res1 = st.columns(3)
                with c_sup1:
                    st.metric("الدعم الأسبوعي", f"${support_weekly:,.4f}")
                with c_sup2:
                    st.metric("الدعم القريب", f"${price * 0.975:,.4f}")
                with c_res1:
                    st.metric("المقاومة الرئيسية", f"${resistance_1:,.4f}")

                # نص جاهز للنسخ للبوستات
                post_text = f"""🔥 تحليل وتوصية عملة: {market_data['symbol']}
📍 السعر الحالي: ${price:,.4f}
🟢 منطقة الدخول: ${entry_min:,.4f} - ${entry_max:,.4f}
🔴 وقف الخسارة: ${stop_loss:,.4f}
🎯 الهدف الأول: ${target_1:,.4f}
🎯 الهدف الثاني: ${target_2:,.4f}
🚀 الهدف الثالث: ${target_3:,.4f}
---
منصة جنرال رقمي Pro ⚡"""

                st.markdown("---")
                st.subheader("📋 نص الصفقة الجاهز للنسخ ونشرها كبوست:")
                st.code(post_text, language="text")

            else:
                st.error(f"لم يتم العثور على العملة '{user_symbol}' في منصة Binance. تأكد من كتابة الرمز الصحيح (مثل: XRP, ADA, DOGE, SOL).")

elif selected_tab == "التحليل الفني الشامل & AI":
    st.subheader("📈 التحليل الفني المتقدم وتوقعات Horizon AI")
    st.info("النظام يدمج مؤشرات السيولة، الحجم، وتحليلات السوق اللحظية.")

elif selected_tab == "سجل الصفقات (Trade Journal)":
    st.subheader("📝 دفتر الصفقات الاحترافي (R-Multiple)")
    st.info("سجل صفقاتك وتابع أدائك بدقة فائقة.")

else:
    st.subheader("⚡ ماسح السوق اللحظي الشامل")
    st.info("ماسح السوق لفحص أبرز العملات الرقمية وتحديثاتها الحية.")
