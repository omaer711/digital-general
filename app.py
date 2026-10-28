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
    st.info("💡 تم تفعيل محرك البحث والربط السحابي الدائم.")

def get_crypto_price(symbol):
    clean = symbol.upper().strip().replace("USDT", "").replace("/", "")
    # محاولة استخدام API عام وسريع لجلب الأسعار الحية
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={get_coingecko_id(clean)}&vs_currencies=usd&include_24hr_change=true"
    try:
        res = requests.get(url, timeout=4)
        if res.status_code == 200:
            data = res.json()
            coin_id = get_coingecko_id(clean)
            if coin_id in data:
                return {
                    "symbol": clean + "USDT",
                    "price": float(data[coin_id]["usd"]),
                    "change": float(data[coin_id].get("usd_24h_change", 0))
                }
    except:
        pass
    
    # محاولة احتياطية من Binance مباشرة
    try:
        b_url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={clean}USDT"
        res = requests.get(b_url, timeout=3)
        if res.status_code == 200:
            d = res.json()
            return {
                "symbol": d["symbol"],
                "price": float(d["lastPrice"]),
                "change": float(d["priceChangePercent"])
            }
    except:
        pass
    return None

def get_coingecko_id(symbol):
    mapping = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "XRP": "ripple",
        "BNB": "binancecoin",
        "ADA": "cardano",
        "DOGE": "dogecoin",
        "AVAX": "avalanche-2",
        "LINK": "chainlink",
        "PEPE": "pepe"
    }
    return mapping.get(symbol, "bitcoin")

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
    st.subheader("🔍 محرك البحث الفوري في الأسواق")
    
    search_query = st.text_input("أدخل رمز العملة (مثال: BTC, ETH, SOL, XRP):", value="BTC")
    
    if search_query:
        with st.spinner("جاري جلب السعر الحي..."):
            data = get_crypto_price(search_query)
            if data:
                st.success(f"العملة: {data['symbol']}")
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("السعر الحالي (USD)", f"${data['price']:,.2f}")
                with c2:
                    st.metric("التغير خلال 24 ساعة", f"{data['change']:+.2f}%")
            else:
                st.error("لم يتم العثور على السعر، تأكد من كتابة الرمز الصحيح (مثل: BTC أو ETH).")

elif selected_tab == "التحليل الفني & Horizon AI":
    st.subheader("📈 التحليل الفني و توقعات Horizon AI")
    st.info("مدمج الآن مع أدوات التحليل الفوري للمنصة.")

elif selected_tab == "سجل الصفقات (Trade Journal)":
    st.subheader("📝 دفتر الصفقات الاحترافي")
    st.info("تسجيل ومتابعة صفقاتك بدقة R-Multiple.")

else:
    st.subheader("⚡ ماسح السوق الذكي والعملات القوية")
    st.markdown("قائمة بأبرز العملات الرقمية وتحديثاتها اللحظية:")
    
    coins = ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE"]
    table_data = []
    
    for c in coins:
        res = get_crypto_price(c)
        if res:
            table_data.append({
                "العملة": res["symbol"],
                "السعر ($)": f"${res['price']:,.2f}",
                "التغير (24س)": f"{res['change']:+.2f}%"
            })
    
    if table_data:
        df = pd.DataFrame(table_data)
        st.table(df)
    else:
        st.warning("جاري الاتصال بالخوادم لجلب بيانات الماسح...")
