import streamlit as st
import pandas as pd
import requests

st.set_page_config(
    page_title="جنرال رقمي | Digital General",
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
    .stButton>button { background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); color: white; border-radius: 10px; border: none; font-weight: 700; padding: 0.5rem 1rem; width: 100%; }
    h1, h2, h3 { color: #f3f4f6; font-weight: 900; }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("⚡ جنرال رقمي Pro")
    st.markdown("---")
    selected_tab = st.radio(
        "الانتقال السريع:",
        ["الرئيسية (Dashboard)", "التحليل الفني & Horizon AI", "سجل الصفقات (Trade Journal)", "ماسح السوق (Market Scanner)"],
        index=0
    )
    st.markdown("---")
    st.info("💡 تم تفعيل محرك البحث الذكي لأسواق Binance.")

def get_binance_price(symbol):
    try:
        # تنظيف الرمز المكتوب وتحويله إلى أحرف كبيرة
        clean = symbol.upper().strip().replace("/", "").replace("-", "")
        if not clean.endswith("USDT"):
            clean += "USDT"
            
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={clean}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "symbol": clean,
                "price": float(data["lastPrice"]),
                "change": float(data["priceChangePercent"]),
                "high": float(data["highPrice"]),
                "low": float(data["lowPrice"]),
                "volume": float(data["quoteVolume"])
            }
        return None
    except Exception as e:
        return None

if selected_tab == "الرئيسية (Dashboard)":
    st.subheader("📊 نظرة عامة على الأسواق والأداء الأسبوعي")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="نسبة صفقات الأسبوع الناجحة", value="66%", delta="ممتاز")
    with col2:
        st.metric(label="النتيجة الصافية (R-Multiple)", value="+736.45R", delta="عالي الأداء")
    with col3:
        st.metric(label="الذكاء الاصطناعي (Horizon)", value="77% صاعد", delta="توقع قوي")

    st.markdown("---")
    st.subheader("🔍 محرك البحث الفوري في أسواق Binance")
    
    # مربع البحث مع قيمة افتراضية BTC
    search_query = st.text_input("أدخل اسم العملة (مثال: BTC أو XRP أو SOL):", value="BTC")
    
    if search_query:
        with st.spinner("جاري جلب البيانات الحية من Binance..."):
            coin_data = get_binance_price(search_query)
            if coin_data:
                st.success(f"تم العثور على العملة بنجاح: {coin_data['symbol']}")
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("السعر الحالي", f"${coin_data['price']:,.4f}")
                with c2:
                    st.metric("التغير (24س)", f"{coin_data['change']:+.2f}%")
                with c3:
                    st.metric("أعلى سعر (24س)", f"${coin_data['high']:,.4f}")
                with c4:
                    st.metric("حجم التداول (USDT)", f"${coin_data['volume']:,.0f}")
            else:
                st.error(f"لم يتم العثور على عملة مطابقة لـ '{search_query}'. يرجى التأكد من الرمز (مثال: BTC, XRP, SOL).")

elif selected_tab == "التحليل الفني & Horizon AI":
    st.subheader("📈 التحليل الفني و توقعات Horizon AI")
    st.info("مدمج الآن مع محرك جلب الأسعار والشموع الفورية.")

elif selected_tab == "سجل الصفقات (Trade Journal)":
    st.subheader("📝 دفتر الصفقات الاحترافي")
    st.info("تسجيل ومتابعة صفقاتك بدقة R-Multiple.")

else:
    st.subheader("⚡ ماسح السوق الذكي")
    st.info("فحص العملات القوية وتنبيهات الأداء اللحظي.")
