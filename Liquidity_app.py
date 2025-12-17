import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import calendar
import json
import os

# Set page configuration
st.set_page_config(page_title="Market Checklist", layout="wide")

# ==================== PERSISTENT STORAGE FUNCTIONS ====================
USER_INPUTS_FILE = "user_inputs.json"

def load_user_inputs():
    """Load previously saved user inputs from JSON file"""
    if os.path.exists(USER_INPUTS_FILE):
        try:
            with open(USER_INPUTS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading saved inputs: {str(e)}")
            return {}
    return {}

def save_user_inputs(inputs):
    """Save user inputs to JSON file"""
    try:
        with open(USER_INPUTS_FILE, 'w') as f:
            json.dump(inputs, f, indent=2)
    except Exception as e:
        st.error(f"Error saving inputs: {str(e)}")

# Load saved inputs at startup
saved_inputs = load_user_inputs()

# Custom CSS for compact layout
st.markdown("""
<style>
    /* Reduce font sizes */
    .stMetric label { font-size: 0.85rem !important; }
    .stMetric .metric-value { font-size: 1.2rem !important; }
    h1 { font-size: 1.6rem !important; margin-bottom: 0.5rem !important; }
    h2 { font-size: 1.2rem !important; margin-top: 0.5rem !important; margin-bottom: 0.3rem !important; }
    h3 { font-size: 1.0rem !important; margin-top: 0.3rem !important; margin-bottom: 0.3rem !important; }
    h4 { font-size: 0.95rem !important; }
    h5 { font-size: 0.9rem !important; }
    
    /* Reduce spacing */
    .element-container { margin-bottom: 0.2rem !important; }
    .stButton button { padding: 0.25rem 0.75rem !important; font-size: 0.85rem !important; }
    div[data-testid="stExpander"] { margin: 0.2rem 0 !important; }
    
    /* Reduce padding in columns */
    div[data-testid="column"] { padding: 0.2rem !important; }
    
    /* Compact tables */
    table { font-size: 0.8rem !important; }
    
    /* Reduce divider spacing */
    hr { margin: 0.3rem 0 !important; }
    
    /* Compact selectbox */
    .stSelectbox { margin-bottom: 0.2rem !important; }
</style>
""", unsafe_allow_html=True)

# ==================== HELPER FUNCTIONS ====================
def get_month_end_date(year, month):
    """Get the last day of a given month"""
    last_day = calendar.monthrange(year, month)[1]
    return datetime(year, month, last_day)

def get_latest_month_end():
    """Get the most recent completed month-end"""
    today = datetime.now()
    if today.day > 5:
        target_month = today.month - 1 if today.month > 1 else 12
        target_year = today.year if today.month > 1 else today.year - 1
    else:
        target_month = today.month - 2 if today.month > 2 else (12 + today.month - 2)
        target_year = today.year if today.month > 2 else today.year - 1
    
    return get_month_end_date(target_year, target_month)

def calc_monthly_return(data, months_back, reference_date):
    """Calculate return over specified months using month-end data"""
    try:
        ref_prices = data[data.index <= reference_date]
        if len(ref_prices) == 0:
            return None
        ref_price = ref_prices.iloc[-1]
        
        target_year = reference_date.year
        target_month = reference_date.month - months_back
        
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        
        target_date = get_month_end_date(target_year, target_month)
        
        target_prices = data[data.index <= target_date]
        if len(target_prices) == 0:
            return None
        target_price = target_prices.iloc[-1]
        
        return ((ref_price / target_price) - 1) * 100
    except:
        return None

def calc_irx_compounded_return(irx_data, months_back, reference_date):
    """Calculate compounded return from IRX monthly yields"""
    try:
        monthly_returns = []
        
        for i in range(months_back):
            target_year = reference_date.year
            target_month = reference_date.month - i
            
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            
            month_end = get_month_end_date(target_year, target_month)
            
            month_data = irx_data[irx_data.index <= month_end]
            if len(month_data) == 0:
                return None
            
            irx_yield = float(month_data.iloc[-1])
            monthly_return = (irx_yield / 100) / 12
            monthly_returns.append(monthly_return)
        
        compounded = 1.0
        for r in monthly_returns:
            compounded *= (1 + r)
        
        return (compounded - 1) * 100
        
    except Exception as e:
        return None

def calc_ma(data, period):
    """Calculate moving average"""
    if len(data) < period:
        return None
    return data.tail(period).mean()

def calculate_stage(price, ma50, ma150, ma200):
    """Calculate market stage based on moving averages"""
    try:
        current_price = float(price)
        ma_50 = float(ma50)
        ma_150 = float(ma150)
        ma_200 = float(ma200)
        
        if current_price > ma_50 and ma_50 > ma_150 and ma_150 > ma_200:
            return "S2", 1.0
        elif current_price > ma_50 and ma_50 > ma_150 and ma_150 < ma_200:
            return "S1", 0.5
        elif current_price > ma_50 and ma_50 < ma_150 and ma_150 > ma_200:
            return "S3 Strong", 0.5
        else:
            return "Other", 0.0
            
    except:
        return "Error", 0.0

@st.cache_data(ttl=3600)
def fetch_liquidity_data():
    """Fetch liquidity indicators data"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=730)
        
        bnd_df = yf.download('BND', start=start_date, end=end_date, interval='1mo', progress=False)
        irx_df = yf.download('^IRX', start=start_date, end=end_date, progress=False)
        
        start_date_daily = end_date - timedelta(days=100)
        tip_df = yf.download('TIP', start=start_date_daily, end=end_date, progress=False)
        ibit_df = yf.download('IBIT', start=start_date_daily, end=end_date, progress=False)
        
        bnd = bnd_df['Adj Close'].squeeze() if 'Adj Close' in bnd_df else bnd_df['Close'].squeeze()
        irx = irx_df['Close'].squeeze() if isinstance(irx_df['Close'], pd.DataFrame) else irx_df['Close']
        tip = tip_df['Close'].squeeze() if isinstance(tip_df['Close'], pd.DataFrame) else tip_df['Close']
        ibit = ibit_df['Close'].squeeze() if isinstance(ibit_df['Close'], pd.DataFrame) else ibit_df['Close']
        
        if isinstance(bnd, pd.DataFrame):
            bnd = bnd.iloc[:, 0]
        if isinstance(irx, pd.DataFrame):
            irx = irx.iloc[:, 0]
        
        bnd = bnd.dropna()
        irx = irx.dropna()
        tip = tip.dropna()
        ibit = ibit.dropna()
        
        return bnd, irx, tip, ibit
    except Exception as e:
        return None, None, None, None

@st.cache_data(ttl=3600)
def fetch_sentiment_data():
    """Fetch sentiment indicators data for both US and HK markets"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=400)
        
        # US tickers
        xly_df = yf.download('XLY', start=start_date, end=end_date, progress=False)
        xlp_df = yf.download('XLP', start=start_date, end=end_date, progress=False)
        ffty_df = yf.download('FFTY', start=start_date, end=end_date, progress=False)
        
        # HK tickers
        hk_3109_df = yf.download('3109.HK', start=start_date, end=end_date, progress=False)
        hk_3437_df = yf.download('3437.HK', start=start_date, end=end_date, progress=False)
        hk_3067_df = yf.download('3067.HK', start=start_date, end=end_date, progress=False)
        
        # Extract and clean US data
        xly = xly_df['Close'].squeeze() if isinstance(xly_df['Close'], pd.DataFrame) else xly_df['Close']
        xlp = xlp_df['Close'].squeeze() if isinstance(xlp_df['Close'], pd.DataFrame) else xlp_df['Close']
        ffty = ffty_df['Close'].squeeze() if isinstance(ffty_df['Close'], pd.DataFrame) else ffty_df['Close']
        
        # Extract and clean HK data
        hk_3109 = hk_3109_df['Close'].squeeze() if isinstance(hk_3109_df['Close'], pd.DataFrame) else hk_3109_df['Close']
        hk_3437 = hk_3437_df['Close'].squeeze() if isinstance(hk_3437_df['Close'], pd.DataFrame) else hk_3437_df['Close']
        hk_3067 = hk_3067_df['Close'].squeeze() if isinstance(hk_3067_df['Close'], pd.DataFrame) else hk_3067_df['Close']
        
        xly = xly.dropna()
        xlp = xlp.dropna()
        ffty = ffty.dropna()
        hk_3109 = hk_3109.dropna()
        hk_3437 = hk_3437.dropna()
        hk_3067 = hk_3067.dropna()
        
        return xly, xlp, ffty, hk_3109, hk_3437, hk_3067
    except Exception as e:
        return None, None, None, None, None, None

@st.cache_data(ttl=3600)
def fetch_trend_data():
    """Fetch trend indicators data for SPX, NDX, and HSI"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=500)
        
        indices = {
            'SPX': '^GSPC',
            'NDX': '^NDX',
            'HSI': '^HSI'
        }
        
        data = {}
        for name, ticker in indices.items():
            try:
                df = yf.download(ticker, start=start_date, end=end_date, progress=False, timeout=10)
                if not df.empty and len(df) > 0:
                    close = df['Close'].squeeze() if isinstance(df['Close'], pd.DataFrame) else df['Close']
                    clean_data = close.dropna()
                    if len(clean_data) > 0:
                        data[name] = clean_data
                    else:
                        data[name] = None
                else:
                    data[name] = None
            except Exception as e:
                data[name] = None
        
        return data
    except Exception as e:
        return {}

def calculate_position_percentage(score):
    """Calculate position percentage based on total score"""
    position_map = {
        10.0: 90, 9.0: 100, 8.0: 80, 7.0: 60, 6.0: 50, 5.0: 40
    }
    
    rounded_score = round(score * 2) / 2
    
    if rounded_score in position_map:
        return position_map[rounded_score]
    
    if rounded_score >= 9:
        return 100
    
    if rounded_score > 5:
        lower = int(rounded_score)
        upper = lower + 1
        
        if lower in position_map and upper in position_map:
            weight = rounded_score - lower
            return int(position_map[lower] + (position_map[upper] - position_map[lower]) * weight)
    
    if rounded_score < 5:
        return int((rounded_score / 5.0) * 40)
    
    return 0

st.title("📊 Market Checklist")

# Initialize session state
if 'citi_value' not in st.session_state:
    st.session_state.citi_value = saved_inputs.get('citi_value', 0.0)
if 'citi_prev' not in st.session_state:
    st.session_state.citi_prev = saved_inputs.get('citi_prev', 0.0)
if 'r3fi_manual' not in st.session_state:
    st.session_state.r3fi_manual = saved_inputs.get('r3fi_manual', 50.0)

# Separate manual inputs for SPX, NDX, and HSI
if 'uptrend_status_spx' not in st.session_state:
    st.session_state.uptrend_status_spx = saved_inputs.get('uptrend_status_spx', "Under Pressure/Correction")
if 'uptrend_status_ndx' not in st.session_state:
    st.session_state.uptrend_status_ndx = saved_inputs.get('uptrend_status_ndx', "Under Pressure/Correction")
if 'uptrend_status_hsi' not in st.session_state:
    st.session_state.uptrend_status_hsi = saved_inputs.get('uptrend_status_hsi', "Under Pressure/Correction")

if 'market_pulse_spx' not in st.session_state:
    st.session_state.market_pulse_spx = saved_inputs.get('market_pulse_spx', "Red - Deceleration")
if 'market_pulse_ndx' not in st.session_state:
    st.session_state.market_pulse_ndx = saved_inputs.get('market_pulse_ndx', "Red - Deceleration")
if 'market_pulse_hsi' not in st.session_state:
    st.session_state.market_pulse_hsi = saved_inputs.get('market_pulse_hsi', "Red - Deceleration")

# Score tracking
if 'total_score_liq' not in st.session_state:
    st.session_state.total_score_liq = 0
if 'total_score_spx' not in st.session_state:
    st.session_state.total_score_spx = 0
if 'total_score_ndx' not in st.session_state:
    st.session_state.total_score_ndx = 0
if 'total_score_hsi' not in st.session_state:
    st.session_state.total_score_hsi = 0

# Store individual component scores for breakdown display
if 'score_sent_spx' not in st.session_state:
    st.session_state.score_sent_spx = 0
if 'score_sent_ndx' not in st.session_state:
    st.session_state.score_sent_ndx = 0
if 'score_sent_hsi' not in st.session_state:
    st.session_state.score_sent_hsi = 0
if 'score_trend_spx' not in st.session_state:
    st.session_state.score_trend_spx = 0
if 'score_trend_ndx' not in st.session_state:
    st.session_state.score_trend_ndx = 0
if 'score_trend_hsi' not in st.session_state:
    st.session_state.score_trend_hsi = 0

# ==================== OVERALL SUMMARY (TOP) ====================
st.header("🎯 Overall Market Checklist")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📈 SPX (S&P 500)")
    spx_total = st.session_state.total_score_spx
    position_pct_spx = calculate_position_percentage(spx_total)
    
    subcol1, subcol2 = st.columns(2)
    with subcol1:
        st.metric("Total Score", f"{spx_total:.1f}/10")
    with subcol2:
        st.metric("Position %", f"{position_pct_spx}%")
    
    with st.expander("📊 Score Breakdown"):
        st.write(f"💧 **Liquidity:** {st.session_state.total_score_liq}/3")
        st.write(f"🎭 **Sentiment:** {st.session_state.score_sent_spx:.1f}/4")
        st.write(f"📊 **Trend:** {st.session_state.score_trend_spx:.1f}/3")

with col2:
    st.subheader("📊 NDX (Nasdaq 100)")
    ndx_total = st.session_state.total_score_ndx
    position_pct_ndx = calculate_position_percentage(ndx_total)
    
    subcol1, subcol2 = st.columns(2)
    with subcol1:
        st.metric("Total Score", f"{ndx_total:.1f}/10")
    with subcol2:
        st.metric("Position %", f"{position_pct_ndx}%")
    
    with st.expander("📊 Score Breakdown"):
        st.write(f"💧 **Liquidity:** {st.session_state.total_score_liq}/3")
        st.write(f"🎭 **Sentiment:** {st.session_state.score_sent_ndx:.1f}/4")
        st.write(f"📊 **Trend:** {st.session_state.score_trend_ndx:.1f}/3")

with col3:
    st.subheader("🌏 HSI (Hang Seng)")
    hsi_total = st.session_state.total_score_hsi
    position_pct_hsi = calculate_position_percentage(hsi_total)
    
    subcol1, subcol2 = st.columns(2)
    with subcol1:
        st.metric("Total Score", f"{hsi_total:.1f}/10")
    with subcol2:
        st.metric("Position %", f"{position_pct_hsi}%")
    
    with st.expander("📊 Score Breakdown"):
        st.write(f"💧 **Liquidity:** {st.session_state.total_score_liq}/3")
        st.write(f"🎭 **Sentiment:** {st.session_state.score_sent_hsi:.1f}/4")
        st.write(f"📊 **Trend:** {st.session_state.score_trend_hsi:.1f}/3")

st.caption("💡 Enter data in each tab below to calculate scores")

# Action buttons
col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("🔄 Calculate All Scores", type="primary"):
        st.cache_data.clear()
        st.rerun()
with col_btn2:
    if st.button("🗑️ Clear Saved Inputs"):
        if os.path.exists(USER_INPUTS_FILE):
            os.remove(USER_INPUTS_FILE)
            st.success("✅ Cleared! Refresh page to reset.")

st.divider()

# ==================== TABS FOR DETAILS ====================
tab1, tab2, tab3 = st.tabs(["💧 Liquidity", "🎭 Sentiment", "📊 Trend"])

# ==================== TAB 1: LIQUIDITY ====================
with tab1:
    st.markdown("#### Part 1: Liquidity Indicators (Same for all indices)")
    
    with st.spinner("Loading liquidity data..."):
        bnd_data, irx_data, tip_data, ibit_data = fetch_liquidity_data()
    
    if bnd_data is not None and irx_data is not None:
        latest_month_end = get_latest_month_end()
        st.caption(f"📅 Using month-end data: {latest_month_end.strftime('%B %Y')}")
        
        scores_liq = {}
        
        # === INDICATOR 1: BND vs IRX ===
        st.markdown("#### 1️⃣ BND vs T-Bill (IRX)")
        
        try:
            bnd_3m = calc_monthly_return(bnd_data, 3, latest_month_end)
            bnd_6m = calc_monthly_return(bnd_data, 6, latest_month_end)
            bnd_11m = calc_monthly_return(bnd_data, 11, latest_month_end)
            
            irx_3m = calc_irx_compounded_return(irx_data, 3, latest_month_end)
            irx_6m = calc_irx_compounded_return(irx_data, 6, latest_month_end)
            irx_11m = calc_irx_compounded_return(irx_data, 11, latest_month_end)
            
            bnd_weighted = (bnd_3m * 0.33 + bnd_6m * 0.33 + bnd_11m * 0.34)
            irx_weighted = (irx_3m * 0.33 + irx_6m * 0.33 + irx_11m * 0.34)
            
            indicator1_score = 1 if bnd_weighted > irx_weighted else 0
            scores_liq['indicator1'] = indicator1_score
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("BND Weighted", f"{bnd_weighted:.2f}%")
                st.caption(f"3M: {bnd_3m:.2f}% | 6M: {bnd_6m:.2f}% | 11M: {bnd_11m:.2f}%")
            with col2:
                st.metric("T-Bill Weighted", f"{irx_weighted:.2f}%")
                st.caption(f"3M: {irx_3m:.2f}% | 6M: {irx_6m:.2f}% | 11M: {irx_11m:.2f}%")
            with col3:
                st.metric("Score", f"{indicator1_score}/1", 
                          delta="✅ BND" if indicator1_score == 1 else "❌ T-Bill")
        except Exception as e:
            st.error(f"Error calculating Indicator 1: {str(e)}")
            scores_liq['indicator1'] = 0
        
        st.markdown("---")
        
        # === INDICATOR 2: TIP ===
        st.markdown("#### 2️⃣ TIP: 5-day MA vs 20-day MA")
        
        try:
            tip_5ma = calc_ma(tip_data, 5)
            tip_20ma = calc_ma(tip_data, 20)
            
            tip_5ma = float(tip_5ma) if tip_5ma is not None else 0
            tip_20ma = float(tip_20ma) if tip_20ma is not None else 0
            
            indicator2_score = 1 if tip_5ma > tip_20ma else 0
            scores_liq['indicator2'] = indicator2_score
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("TIP 5-day MA", f"${tip_5ma:.2f}")
            with col2:
                st.metric("TIP 20-day MA", f"${tip_20ma:.2f}")
            with col3:
                st.metric("Score", f"{indicator2_score}/1",
                          delta="✅ Bullish" if indicator2_score == 1 else "❌ Bearish")
        except Exception as e:
            st.error(f"Error calculating Indicator 2: {str(e)}")
            scores_liq['indicator2'] = 0
        
        st.divider()
        
        # === INDICATOR 3: IBIT ===
        st.markdown("#### 3️⃣ IBIT: 3-day MA vs 8-day MA")
        
        try:
            ibit_3ma = calc_ma(ibit_data, 3)
            ibit_8ma = calc_ma(ibit_data, 8)
            
            ibit_3ma = float(ibit_3ma) if ibit_3ma is not None else 0
            ibit_8ma = float(ibit_8ma) if ibit_8ma is not None else 0
            
            indicator3_score = 1 if ibit_3ma > ibit_8ma else 0
            scores_liq['indicator3'] = indicator3_score
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("IBIT 3-day MA", f"${ibit_3ma:.2f}")
            with col2:
                st.metric("IBIT 8-day MA", f"${ibit_8ma:.2f}")
            with col3:
                st.metric("Score", f"{indicator3_score}/1",
                          delta="✅ Bullish" if indicator3_score == 1 else "❌ Bearish")
        except Exception as e:
            st.error(f"Error calculating Indicator 3: {str(e)}")
            scores_liq['indicator3'] = 0
        
        st.divider()
        
        # Save liquidity score
        st.session_state.total_score_liq = sum(scores_liq.values())
    else:
        st.error("Unable to fetch liquidity data.")

# ==================== TAB 2: SENTIMENT ====================
with tab2:
    st.markdown("#### Part 2: Sentiment Indicators")
    
    st.caption(f"📅 Data last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    with st.spinner("Loading sentiment data..."):
        xly_data, xlp_data, ffty_data, hk_3109_data, hk_3437_data, hk_3067_data = fetch_sentiment_data()
    
    scores_sent_us = {}
    scores_sent_hsi = {}
    
    # === INDICATOR 1: Citi Economic Surprise Index (SHARED) ===
    st.markdown("#### 1️⃣ Citi Economic Surprise Index (Shared)")
    
    with st.expander("ℹ️ Scoring & Data Source"):
        st.write("**Scoring:** Value > 0 = 0.5pts | MoM% positive = 0.5pts")
        st.write("**Check data:** https://en.macromicro.me/charts/45866/global-citi-surprise-index")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        citi_value = st.number_input(
            "Current Value",
            value=st.session_state.citi_value,
            step=0.1,
            format="%.2f",
            key="citi_current"
        )
        if citi_value != st.session_state.citi_value:
            st.session_state.citi_value = citi_value
            saved_inputs['citi_value'] = citi_value
            save_user_inputs(saved_inputs)
    
    with col2:
        citi_prev = st.number_input(
            "Previous Month",
            value=st.session_state.citi_prev,
            step=0.1,
            format="%.2f",
            key="citi_prev_input"
        )
        if citi_prev != st.session_state.citi_prev:
            st.session_state.citi_prev = citi_prev
            saved_inputs['citi_prev'] = citi_prev
            save_user_inputs(saved_inputs)
    
    score_above_zero = 0.5 if citi_value > 0 else 0
    citi_mom = ((citi_value - citi_prev) / abs(citi_prev)) * 100 if citi_prev != 0 else 0
    score_mom_positive = 0.5 if citi_mom > 0 else 0
    indicator1_sent = score_above_zero + score_mom_positive
    scores_sent_us['indicator1'] = indicator1_sent
    scores_sent_hsi['indicator1'] = indicator1_sent  # Shared
    
    with col3:
        st.metric("MoM%", f"{citi_mom:.1f}%",
                  delta="Positive" if citi_mom > 0 else "Negative")
    with col4:
        st.metric("Score", f"{indicator1_sent:.1f}/1",
                  delta="✅" if indicator1_sent >= 0.5 else "❌")
    
    st.markdown("---")
    
    # === INDICATOR 2: Russell 3000 (SHARED) ===
    st.markdown("#### 2️⃣ Russell 3000 Above 50-Day MA (Shared)")
    
    with st.expander("🔗 Data Source"):
        st.write("https://www.barchart.com/stocks/quotes/$R3FI/price-history/historical")
    
    col1, col2 = st.columns(2)
    with col1:
        r3fi_manual = st.number_input(
            "% Above 50-Day MA", 
            value=st.session_state.r3fi_manual, 
            step=0.1, 
            min_value=0.0, 
            max_value=100.0, 
            key="r3fi_input"
        )
        if r3fi_manual != st.session_state.r3fi_manual:
            st.session_state.r3fi_manual = r3fi_manual
            saved_inputs['r3fi_manual'] = r3fi_manual
            save_user_inputs(saved_inputs)
    
    indicator2_sent = 1 if r3fi_manual > 50 else 0
    scores_sent_us['indicator2'] = indicator2_sent
    scores_sent_hsi['indicator2'] = indicator2_sent  # Shared
    
    with col2:
        st.metric("Score", f"{indicator2_sent}/1",
                  delta="✅ >50%" if indicator2_sent == 1 else "❌ ≤50%")
    
    st.markdown("---")
    
    # === INDICATOR 3: XLY/XLP vs 3109.HK/3437.HK ===
    st.markdown("#### 3️⃣ Consumer Discretionary/Staples Ratio")
    
    # US Version (XLY/XLP)
    st.markdown("**US Markets (SPX, NDX): XLY/XLP Ratio**")
    
    if xly_data is not None and xlp_data is not None:
        try:
            xly_xlp_ratio = xly_data / xlp_data
            
            ratio_3ma = calc_ma(xly_xlp_ratio, 3)
            ratio_8ma = calc_ma(xly_xlp_ratio, 8)
            
            ratio_3ma = float(ratio_3ma) if ratio_3ma is not None else 0
            ratio_8ma = float(ratio_8ma) if ratio_8ma is not None else 0
            
            indicator3_us = 1 if ratio_3ma > ratio_8ma else 0
            scores_sent_us['indicator3'] = indicator3_us
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("3-day MA", f"{ratio_3ma:.4f}")
            with col2:
                st.metric("8-day MA", f"{ratio_8ma:.4f}")
            with col3:
                st.metric("Score", f"{indicator3_us}/1",
                          delta="✅ Risk-On" if indicator3_us == 1 else "❌ Risk-Off")
        except Exception as e:
            st.error(f"Error calculating XLY/XLP ratio: {str(e)}")
            scores_sent_us['indicator3'] = 0
    else:
        scores_sent_us['indicator3'] = 0
    
    st.markdown("**HK Market (HSI): 3109.HK/3437.HK Ratio**")
    
    if hk_3109_data is not None and hk_3437_data is not None:
        try:
            hk_ratio = hk_3109_data / hk_3437_data
            
            hk_ratio_3ma = calc_ma(hk_ratio, 3)
            hk_ratio_8ma = calc_ma(hk_ratio, 8)
            
            hk_ratio_3ma = float(hk_ratio_3ma) if hk_ratio_3ma is not None else 0
            hk_ratio_8ma = float(hk_ratio_8ma) if hk_ratio_8ma is not None else 0
            
            indicator3_hsi = 1 if hk_ratio_3ma > hk_ratio_8ma else 0
            scores_sent_hsi['indicator3'] = indicator3_hsi
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("3-day MA", f"{hk_ratio_3ma:.4f}")
            with col2:
                st.metric("8-day MA", f"{hk_ratio_8ma:.4f}")
            with col3:
                st.metric("Score", f"{indicator3_hsi}/1",
                          delta="✅ Risk-On" if indicator3_hsi == 1 else "❌ Risk-Off")
        except Exception as e:
            st.error(f"Error calculating 3109.HK/3437.HK ratio: {str(e)}")
            scores_sent_hsi['indicator3'] = 0
    else:
        scores_sent_hsi['indicator3'] = 0
    
    st.markdown("---")
    
    # === INDICATOR 4: FFTY vs 3067.HK ===
    st.markdown("#### 4️⃣ Innovation/Growth Indicator")
    
    # US Version (FFTY)
    st.markdown("**US Markets (SPX, NDX): FFTY**")
    
    if ffty_data is not None:
        try:
            ffty_3ma = calc_ma(ffty_data, 3)
            ffty_8ma = calc_ma(ffty_data, 8)
            
            ffty_3ma = float(ffty_3ma) if ffty_3ma is not None else 0
            ffty_8ma = float(ffty_8ma) if ffty_8ma is not None else 0
            
            indicator4_us = 1 if ffty_3ma > ffty_8ma else 0
            scores_sent_us['indicator4'] = indicator4_us
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("3-day MA", f"${ffty_3ma:.2f}")
            with col2:
                st.metric("8-day MA", f"${ffty_8ma:.2f}")
            with col3:
                st.metric("Score", f"{indicator4_us}/1",
                          delta="✅ Bullish" if indicator4_us == 1 else "❌ Bearish")
        except Exception as e:
            st.error(f"Error calculating FFTY: {str(e)}")
            scores_sent_us['indicator4'] = 0
    else:
        scores_sent_us['indicator4'] = 0
    
    st.markdown("**HK Market (HSI): 3067.HK**")
    
    if hk_3067_data is not None:
        try:
            hk_3067_3ma = calc_ma(hk_3067_data, 3)
            hk_3067_8ma = calc_ma(hk_3067_data, 8)
            
            hk_3067_3ma = float(hk_3067_3ma) if hk_3067_3ma is not None else 0
            hk_3067_8ma = float(hk_3067_8ma) if hk_3067_8ma is not None else 0
            
            indicator4_hsi = 1 if hk_3067_3ma > hk_3067_8ma else 0
            scores_sent_hsi['indicator4'] = indicator4_hsi
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("3-day MA", f"${hk_3067_3ma:.2f}")
            with col2:
                st.metric("8-day MA", f"${hk_3067_8ma:.2f}")
            with col3:
                st.metric("Score", f"{indicator4_hsi}/1",
                          delta="✅ Bullish" if indicator4_hsi == 1 else "❌ Bearish")
        except Exception as e:
            st.error(f"Error calculating 3067.HK: {str(e)}")
            scores_sent_hsi['indicator4'] = 0
    else:
        scores_sent_hsi['indicator4'] = 0
    
    st.markdown("---")
    
    # Calculate sentiment scores for each index
    total_sent_us = sum(scores_sent_us.values())
    total_sent_hsi = sum(scores_sent_hsi.values())
    
    # Save to session state for breakdown display
    st.session_state.score_sent_spx = total_sent_us
    st.session_state.score_sent_ndx = total_sent_us
    st.session_state.score_sent_hsi = total_sent_hsi
    
    st.markdown("#### 🎭 Sentiment Scores by Index")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("SPX", f"{total_sent_us:.1f}/4")
    with col2:
        st.metric("NDX", f"{total_sent_us:.1f}/4")
    with col3:
        st.metric("HSI", f"{total_sent_hsi:.1f}/4")

# ==================== TAB 3: TREND ====================
with tab3:
    st.markdown("#### Part 3: Trend Indicators")
    
    with st.spinner("Loading trend data..."):
        index_data = fetch_trend_data()
    
    scores_trend_spx = {}
    scores_trend_ndx = {}
    scores_trend_hsi = {}
    
    # === INDICATOR 1: Uptrend Confirmation ===
    st.markdown("#### 1️⃣ Uptrend Confirmation")
    
    col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 2, 1, 2, 1])
    
    # SPX
    with col1:
        uptrend_status_spx = st.selectbox(
            "SPX",
            ["Confirmed Uptrend", "Under Pressure/Correction", "Ambiguous Follow-through"],
            index=["Confirmed Uptrend", "Under Pressure/Correction", "Ambiguous Follow-through"].index(st.session_state.uptrend_status_spx),
            key="uptrend_select_spx"
        )
        
        if uptrend_status_spx != st.session_state.uptrend_status_spx:
            st.session_state.uptrend_status_spx = uptrend_status_spx
            saved_inputs['uptrend_status_spx'] = uptrend_status_spx
            save_user_inputs(saved_inputs)
    
    with col2:
        if uptrend_status_spx == "Confirmed Uptrend":
            indicator1_spx = 1.0
            st.metric("Score", f"{indicator1_spx}/1", delta="🟢")
        elif uptrend_status_spx == "Ambiguous Follow-through":
            indicator1_spx = 0.5
            st.metric("Score", f"{indicator1_spx}/1", delta="🟡")
        else:
            indicator1_spx = 0.0
            st.metric("Score", f"{indicator1_spx}/1", delta="🔴")
    
    scores_trend_spx['indicator1'] = indicator1_spx
    
    # NDX
    with col3:
        uptrend_status_ndx = st.selectbox(
            "NDX",
            ["Confirmed Uptrend", "Under Pressure/Correction", "Ambiguous Follow-through"],
            index=["Confirmed Uptrend", "Under Pressure/Correction", "Ambiguous Follow-through"].index(st.session_state.uptrend_status_ndx),
            key="uptrend_select_ndx"
        )
        
        if uptrend_status_ndx != st.session_state.uptrend_status_ndx:
            st.session_state.uptrend_status_ndx = uptrend_status_ndx
            saved_inputs['uptrend_status_ndx'] = uptrend_status_ndx
            save_user_inputs(saved_inputs)
    
    with col4:
        if uptrend_status_ndx == "Confirmed Uptrend":
            indicator1_ndx = 1.0
            st.metric("Score", f"{indicator1_ndx}/1", delta="🟢")
        elif uptrend_status_ndx == "Ambiguous Follow-through":
            indicator1_ndx = 0.5
            st.metric("Score", f"{indicator1_ndx}/1", delta="🟡")
        else:
            indicator1_ndx = 0.0
            st.metric("Score", f"{indicator1_ndx}/1", delta="🔴")
    
    scores_trend_ndx['indicator1'] = indicator1_ndx
    
    # HSI
    with col5:
        uptrend_status_hsi = st.selectbox(
            "HSI",
            ["Confirmed Uptrend", "Under Pressure/Correction", "Ambiguous Follow-through"],
            index=["Confirmed Uptrend", "Under Pressure/Correction", "Ambiguous Follow-through"].index(st.session_state.uptrend_status_hsi),
            key="uptrend_select_hsi"
        )
        
        if uptrend_status_hsi != st.session_state.uptrend_status_hsi:
            st.session_state.uptrend_status_hsi = uptrend_status_hsi
            saved_inputs['uptrend_status_hsi'] = uptrend_status_hsi
            save_user_inputs(saved_inputs)
    
    with col6:
        if uptrend_status_hsi == "Confirmed Uptrend":
            indicator1_hsi = 1.0
            st.metric("Score", f"{indicator1_hsi}/1", delta="🟢")
        elif uptrend_status_hsi == "Ambiguous Follow-through":
            indicator1_hsi = 0.5
            st.metric("Score", f"{indicator1_hsi}/1", delta="🟡")
        else:
            indicator1_hsi = 0.0
            st.metric("Score", f"{indicator1_hsi}/1", delta="🔴")
    
    scores_trend_hsi['indicator1'] = indicator1_hsi
    
    st.markdown("---")
    
    # === INDICATOR 2: Stage 2 (All 3 Indices) ===
    st.markdown("#### 2️⃣ Stage 2 Indicator")
    
    with st.expander("ℹ️ Stage Definitions", expanded=False):
        st.markdown("""
        **S2** (1.0): Price > 50MA > 150MA > 200MA | **S1** (0.5): Price > 50MA > 150MA, 150MA < 200MA | **S3 Strong** (0.5): Price > 50MA, 50MA < 150MA > 200MA | **Other** (0): All else
        """)
    
    # Row 1: SPX, NDX, HSI - all in one row
    col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 1, 1, 1, 1])
    
    for idx, (idx_name, idx_key, score_dict, col_stage, col_score) in enumerate([
        ('SPX', 'SPX', scores_trend_spx, col1, col2),
        ('NDX', 'NDX', scores_trend_ndx, col3, col4),
        ('HSI', 'HSI', scores_trend_hsi, col5, col6)
    ]):
        if index_data and idx_key in index_data:
            data = index_data[idx_key]
            
            if data is not None and len(data) >= 200:
                try:
                    current_price = float(data.iloc[-1])
                    ma_50 = calc_ma(data, 50)
                    ma_150 = calc_ma(data, 150)
                    ma_200 = calc_ma(data, 200)
                    
                    if ma_50 is None or ma_150 is None or ma_200 is None:
                        score_dict['indicator2'] = 0
                        with col_stage:
                            st.metric(idx_name, "Error")
                        with col_score:
                            st.metric("Score", "0/1")
                    else:
                        stage, score = calculate_stage(current_price, ma_50, ma_150, ma_200)
                        score_dict['indicator2'] = score
                        
                        stage_emoji = "🟢" if score == 1.0 else ("🟡" if score == 0.5 else "🔴")
                        
                        with col_stage:
                            with st.popover(f"{idx_name}: {stage}"):
                                st.write(f"**Price:** {current_price:.2f}")
                                st.write(f"**50 MA:** {ma_50:.2f}")
                                st.write(f"**150 MA:** {ma_150:.2f}")
                                st.write(f"**200 MA:** {ma_200:.2f}")
                        
                        with col_score:
                            st.metric("Score", f"{score}/1", delta=stage_emoji)
                    
                except Exception as e:
                    score_dict['indicator2'] = 0
                    with col_stage:
                        st.metric(idx_name, "Error")
                    with col_score:
                        st.metric("Score", "0/1")
            else:
                score_dict['indicator2'] = 0
                with col_stage:
                    st.metric(idx_name, "No Data")
                with col_score:
                    st.metric("Score", "0/1")
        else:
            score_dict['indicator2'] = 0
            with col_stage:
                st.metric(idx_name, "Error")
            with col_score:
                st.metric("Score", "0/1")
    
    st.markdown("---")
    
    # === INDICATOR 3: Market Pulse ===
    st.markdown("#### 3️⃣ Market Pulse")
    
    with st.expander("ℹ️ Market Pulse Stages", expanded=False):
        st.markdown("""
        **Green** (1.0): Price > 10VMA; VWMA8 > VWMA21 > VWMA34 | **Grey Strong** (0.5): Price > 10VMA; VWMAs not stacked | **Grey Weak/Red** (0): Distribution or Deceleration
        """)
    
    col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 2, 1, 2, 1])
    
    # SPX
    with col1:
        market_pulse_spx = st.selectbox(
            "SPX",
            ["Green - Acceleration", "Grey Strong - Accumulation", "Grey Weak - Distribution", "Red - Deceleration"],
            index=["Green - Acceleration", "Grey Strong - Accumulation", "Grey Weak - Distribution", "Red - Deceleration"].index(st.session_state.market_pulse_spx),
            key="pulse_select_spx"
        )
        
        if market_pulse_spx != st.session_state.market_pulse_spx:
            st.session_state.market_pulse_spx = market_pulse_spx
            saved_inputs['market_pulse_spx'] = market_pulse_spx
            save_user_inputs(saved_inputs)
    
    with col2:
        if market_pulse_spx == "Green - Acceleration":
            indicator3_spx = 1.0
            st.metric("Score", f"{indicator3_spx}/1", delta="🟢")
        elif market_pulse_spx == "Grey Strong - Accumulation":
            indicator3_spx = 0.5
            st.metric("Score", f"{indicator3_spx}/1", delta="🟡")
        else:
            indicator3_spx = 0.0
            st.metric("Score", f"{indicator3_spx}/1", delta="🔴")
    
    scores_trend_spx['indicator3'] = indicator3_spx
    
    # NDX
    with col3:
        market_pulse_ndx = st.selectbox(
            "NDX",
            ["Green - Acceleration", "Grey Strong - Accumulation", "Grey Weak - Distribution", "Red - Deceleration"],
            index=["Green - Acceleration", "Grey Strong - Accumulation", "Grey Weak - Distribution", "Red - Deceleration"].index(st.session_state.market_pulse_ndx),
            key="pulse_select_ndx"
        )
        
        if market_pulse_ndx != st.session_state.market_pulse_ndx:
            st.session_state.market_pulse_ndx = market_pulse_ndx
            saved_inputs['market_pulse_ndx'] = market_pulse_ndx
            save_user_inputs(saved_inputs)
    
    with col4:
        if market_pulse_ndx == "Green - Acceleration":
            indicator3_ndx = 1.0
            st.metric("Score", f"{indicator3_ndx}/1", delta="🟢")
        elif market_pulse_ndx == "Grey Strong - Accumulation":
            indicator3_ndx = 0.5
            st.metric("Score", f"{indicator3_ndx}/1", delta="🟡")
        else:
            indicator3_ndx = 0.0
            st.metric("Score", f"{indicator3_ndx}/1", delta="🔴")
    
    scores_trend_ndx['indicator3'] = indicator3_ndx
    
    # HSI
    with col5:
        market_pulse_hsi = st.selectbox(
            "HSI",
            ["Green - Acceleration", "Grey Strong - Accumulation", "Grey Weak - Distribution", "Red - Deceleration"],
            index=["Green - Acceleration", "Grey Strong - Accumulation", "Grey Weak - Distribution", "Red - Deceleration"].index(st.session_state.market_pulse_hsi),
            key="pulse_select_hsi"
        )
        
        if market_pulse_hsi != st.session_state.market_pulse_hsi:
            st.session_state.market_pulse_hsi = market_pulse_hsi
            saved_inputs['market_pulse_hsi'] = market_pulse_hsi
            save_user_inputs(saved_inputs)
    
    with col6:
        if market_pulse_hsi == "Green - Acceleration":
            indicator3_hsi = 1.0
            st.metric("Score", f"{indicator3_hsi}/1", delta="🟢")
        elif market_pulse_hsi == "Grey Strong - Accumulation":
            indicator3_hsi = 0.5
            st.metric("Score", f"{indicator3_hsi}/1", delta="🟡")
        else:
            indicator3_hsi = 0.0
            st.metric("Score", f"{indicator3_hsi}/1", delta="🔴")
    
    scores_trend_hsi['indicator3'] = indicator3_hsi
    
    st.markdown("---")
    
    # Calculate total scores for each index
    total_trend_spx = sum(scores_trend_spx.values())
    total_trend_ndx = sum(scores_trend_ndx.values())
    total_trend_hsi = sum(scores_trend_hsi.values())
    
    # Save component scores to session state
    st.session_state.score_trend_spx = total_trend_spx
    st.session_state.score_trend_ndx = total_trend_ndx
    st.session_state.score_trend_hsi = total_trend_hsi
    
    # Calculate overall scores (Liquidity + Sentiment + Trend)
    st.session_state.total_score_spx = st.session_state.total_score_liq + st.session_state.score_sent_spx + total_trend_spx
    st.session_state.total_score_ndx = st.session_state.total_score_liq + st.session_state.score_sent_ndx + total_trend_ndx
    st.session_state.total_score_hsi = st.session_state.total_score_liq + st.session_state.score_sent_hsi + total_trend_hsi
    
    st.markdown("#### 📊 Trend Scores by Index")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("SPX", f"{total_trend_spx:.1f}/3")
    with col2:
        st.metric("NDX", f"{total_trend_ndx:.1f}/3")
    with col3:
        st.metric("HSI", f"{total_trend_hsi:.1f}/3")

# ==================== FOOTER ====================
st.markdown("---")

# Add positioning reference table in an expander
with st.expander("📊 Score → Position % Reference Table"):
    reference_df = pd.DataFrame({
        'Score': ['10', '9', '8', '7', '6', '5', '< 5'],
        'Position %': ['90%', '100%', '80%', '60%', '50%', '40%', 'Proportional (0-40%)']
    })
    st.table(reference_df)
    st.caption("💡 Scores between mapped values are interpolated linearly")

st.caption("⚠️ This is for educational purposes only. Not financial advice.")
st.caption("💾 Your manual inputs are automatically saved and will be restored on your next visit.")
