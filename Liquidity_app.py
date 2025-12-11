import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import calendar

# Set page configuration
st.set_page_config(page_title="Market Checklist", layout="wide")

# Custom CSS for compact layout
st.markdown("""
<style>
    /* Reduce font sizes */
    .stMetric label { font-size: 0.9rem !important; }
    .stMetric .metric-value { font-size: 1.3rem !important; }
    h1 { font-size: 1.8rem !important; margin-bottom: 0.5rem !important; }
    h2 { font-size: 1.3rem !important; margin-top: 0.5rem !important; margin-bottom: 0.3rem !important; }
    h3 { font-size: 1.1rem !important; margin-top: 0.3rem !important; margin-bottom: 0.3rem !important; }
    
    /* Reduce spacing */
    .element-container { margin-bottom: 0.3rem !important; }
    .stButton button { padding: 0.25rem 0.75rem !important; }
    div[data-testid="stExpander"] { margin: 0.3rem 0 !important; }
    
    /* Reduce padding in columns */
    div[data-testid="column"] { padding: 0.3rem !important; }
    
    /* Compact tables */
    table { font-size: 0.85rem !important; }
    
    /* Reduce divider spacing */
    hr { margin: 0.5rem 0 !important; }
</style>
""", unsafe_allow_html=True)

st.title("📊 Market Checklist")

# Initialize session state for manual inputs and scores
if 'citi_score' not in st.session_state:
    st.session_state.citi_score = 0.0
if 'r3fi_manual' not in st.session_state:
    st.session_state.r3fi_manual = 50.0
if 'total_score_liq' not in st.session_state:
    st.session_state.total_score_liq = 0
if 'total_score_sent' not in st.session_state:
    st.session_state.total_score_sent = 0
if 'total_score_trend' not in st.session_state:
    st.session_state.total_score_trend = 0

# ==================== OVERALL SUMMARY (TOP) ====================
st.header("🎯 Overall Market Checklist")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("💧 Liquidity", f"{st.session_state.total_score_liq}/3", help="Click Liquidity tab for details")
with col2:
    st.metric("🎭 Sentiment", f"{st.session_state.total_score_sent:.1f}/4", help="Click Sentiment tab for details")
with col3:
    st.metric("📊 Trend", f"{st.session_state.total_score_trend:.1f}/3", help="Click Trend tab for details")
with col4:
    overall_total = st.session_state.total_score_liq + st.session_state.total_score_sent + st.session_state.total_score_trend
    st.metric("🎯 OVERALL", f"{overall_total:.1f}/10", help="Total score across all categories")

st.caption("💡 Enter data in each tab below to calculate scores")

st.divider()

# ==================== TABS FOR DETAILS ====================
# Create tabs for different sections
tab1, tab2, tab3 = st.tabs(["💧 Liquidity", "🎭 Sentiment", "📊 Trend"])

# Helper function to get month-end date
def get_month_end_date(year, month):
    """Get the last day of a given month"""
    last_day = calendar.monthrange(year, month)[1]
    return datetime(year, month, last_day)

def get_latest_month_end():
    """Get the most recent completed month-end"""
    today = datetime.now()
    # If we're past the 5th of the month, use last month's end
    # Otherwise use the month before that
    if today.day > 5:
        target_month = today.month - 1 if today.month > 1 else 12
        target_year = today.year if today.month > 1 else today.year - 1
    else:
        target_month = today.month - 2 if today.month > 2 else (12 + today.month - 2)
        target_year = today.year if today.month > 2 else today.year - 1
    
    return get_month_end_date(target_year, target_month)

# Function to calculate monthly percentage return from month-end prices
def calc_monthly_return(data, months_back, reference_date):
    """Calculate return over specified months using month-end data"""
    try:
        # Get reference month-end price
        ref_prices = data[data.index <= reference_date]
        if len(ref_prices) == 0:
            return None
        ref_price = ref_prices.iloc[-1]
        
        # Calculate the target date (months_back before reference)
        target_year = reference_date.year
        target_month = reference_date.month - months_back
        
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        
        target_date = get_month_end_date(target_year, target_month)
        
        # Get target month-end price
        target_prices = data[data.index <= target_date]
        if len(target_prices) == 0:
            return None
        target_price = target_prices.iloc[-1]
        
        # Calculate percentage return
        return ((ref_price / target_price) - 1) * 100
    except:
        return None

# Function to calculate compounded return from IRX yields
def calc_irx_compounded_return(irx_data, months_back, reference_date):
    """Calculate compounded return from IRX monthly yields"""
    try:
        # Get monthly returns for the period
        monthly_returns = []
        
        for i in range(months_back):
            # Calculate the month we need
            target_year = reference_date.year
            target_month = reference_date.month - i
            
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            
            month_end = get_month_end_date(target_year, target_month)
            
            # Get IRX value at that month-end
            month_data = irx_data[irx_data.index <= month_end]
            if len(month_data) == 0:
                return None
            
            irx_yield = float(month_data.iloc[-1])
            # Convert annual yield to monthly return: r_monthly = (IRX/100) / 12
            monthly_return = (irx_yield / 100) / 12
            monthly_returns.append(monthly_return)
        
        # Compound the returns: (1+r1) × (1+r2) × ... × (1+rn) - 1
        compounded = 1.0
        for r in monthly_returns:
            compounded *= (1 + r)
        
        # Convert to percentage
        return (compounded - 1) * 100
        
    except Exception as e:
        return None

# Function to calculate moving average
def calc_ma(data, period):
    """Calculate moving average"""
    if len(data) < period:
        return None
    return data.tail(period).mean()

# Function to calculate VWMA
def calc_vwma(close_data, volume_data, period):
    """Calculate Volume Weighted Moving Average"""
    if len(close_data) < period or len(volume_data) < period:
        return None
    recent_close = close_data.tail(period)
    recent_volume = volume_data.tail(period)
    return (recent_close * recent_volume).sum() / recent_volume.sum()

@st.cache_data(ttl=3600)
def fetch_liquidity_data():
    """Fetch liquidity indicators data"""
    try:
        # Get 2 years of data to ensure we have enough monthly data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=730)
        
        # Fetch monthly adjusted data for BND
        bnd_df = yf.download('BND', start=start_date, end=end_date, interval='1mo', progress=False)
        
        # Fetch daily data for IRX (we'll extract month-end values)
        irx_df = yf.download('^IRX', start=start_date, end=end_date, progress=False)
        
        # For daily data (TIP, IBIT)
        start_date_daily = end_date - timedelta(days=100)
        tip_df = yf.download('TIP', start=start_date_daily, end=end_date, progress=False)
        ibit_df = yf.download('IBIT', start=start_date_daily, end=end_date, progress=False)
        
        # Extract adjusted close for BND (for total return)
        bnd = bnd_df['Adj Close'].squeeze() if 'Adj Close' in bnd_df else bnd_df['Close'].squeeze()
        
        # Extract close for IRX
        irx = irx_df['Close'].squeeze() if isinstance(irx_df['Close'], pd.DataFrame) else irx_df['Close']
        
        # Extract close for daily data
        tip = tip_df['Close'].squeeze() if isinstance(tip_df['Close'], pd.DataFrame) else tip_df['Close']
        ibit = ibit_df['Close'].squeeze() if isinstance(ibit_df['Close'], pd.DataFrame) else ibit_df['Close']
        
        # Ensure Series format
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
        st.error(f"Error fetching liquidity data: {str(e)}")
        return None, None, None, None

@st.cache_data(ttl=3600)
def fetch_sentiment_data():
    """Fetch sentiment indicators data"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=400)
        
        xly_df = yf.download('XLY', start=start_date, end=end_date, progress=False)
        xlp_df = yf.download('XLP', start=start_date, end=end_date, progress=False)
        ffty_df = yf.download('FFTY', start=start_date, end=end_date, progress=False)
        
        xly = xly_df['Close'].squeeze() if isinstance(xly_df['Close'], pd.DataFrame) else xly_df['Close']
        xlp = xlp_df['Close'].squeeze() if isinstance(xlp_df['Close'], pd.DataFrame) else xlp_df['Close']
        ffty = ffty_df['Close'].squeeze() if isinstance(ffty_df['Close'], pd.DataFrame) else ffty_df['Close']
        
        xly = xly.dropna()
        xlp = xlp.dropna()
        ffty = ffty.dropna()
        
        return xly, xlp, ffty
    except Exception as e:
        st.error(f"Error fetching sentiment data: {str(e)}")
        return None, None, None

@st.cache_data(ttl=3600)
def fetch_trend_data():
    """Fetch trend indicators data for multiple indices"""
    try:
        end_date = datetime.now()
        # Fetch more data to ensure we have 200+ trading days (need ~300 calendar days minimum)
        start_date = end_date - timedelta(days=500)
        
        indices = {
            'NDX (Nasdaq 100)': ['^NDX'],
            'SPX (S&P 500)': ['^GSPC'],
            'HSI (Hang Seng)': ['^HSI'],
            'HSTECH (Hang Seng TECH)': ['HSTECH.HK', '^HSTECH', 'HSI:HSTECH']  # Try multiple formats
        }
        
        data = {}
        for name, tickers in indices.items():
            success = False
            for ticker in tickers:
                try:
                    df = yf.download(ticker, start=start_date, end=end_date, progress=False, timeout=10)
                    if not df.empty and len(df) > 0:
                        close = df['Close'].squeeze() if isinstance(df['Close'], pd.DataFrame) else df['Close']
                        clean_data = close.dropna()
                        if len(clean_data) > 0:
                            data[name] = clean_data
                            success = True
                            break
                except Exception as e:
                    continue
            
            if not success:
                data[name] = None
        
        return data
    except Exception as e:
        st.error(f"Error fetching trend data: {str(e)}")
        return {}

def calculate_stage(price, ma50, ma150, ma200):
    """Calculate market stage based on moving averages"""
    try:
        current_price = float(price)
        ma_50 = float(ma50)
        ma_150 = float(ma150)
        ma_200 = float(ma200)
        
        # S2: Price>50MA, 50MA>150MA, 150MA>200MA
        if current_price > ma_50 and ma_50 > ma_150 and ma_150 > ma_200:
            return "S2", 1.0
        
        # S1: Price>50MA, 50MA>150MA, 150MA<200MA
        elif current_price > ma_50 and ma_50 > ma_150 and ma_150 < ma_200:
            return "S1", 0.5
        
        # S3 Strong: Price>50MA, 50MA<150MA, 150MA>200MA
        elif current_price > ma_50 and ma_50 < ma_150 and ma_150 > ma_200:
            return "S3 Strong", 0.5
        
        # All other scenarios
        else:
            return "Other", 0.0
            
    except:
        return "Error", 0.0

# ==================== TAB 1: LIQUIDITY ====================
with tab1:
    st.subheader("Part 1: Liquidity Indicators")
    
    # Fetch data when tab is accessed
    with st.spinner("Loading liquidity data..."):
        bnd_data, irx_data, tip_data, ibit_data = fetch_liquidity_data()
    
    if bnd_data is not None and irx_data is not None:
        # Get latest month-end reference date
        latest_month_end = get_latest_month_end()
        st.caption(f"📅 Using month-end data: {latest_month_end.strftime('%B %Y')}")
        
        scores_liq = {}
        
        # === INDICATOR 1: BND vs IRX (T-Bill) ===
        st.markdown("##### 1️⃣ BND vs T-Bill (IRX)")
        
        try:
            # Calculate BND returns using month-end adjusted prices
            bnd_3m = calc_monthly_return(bnd_data, 3, latest_month_end)
            bnd_6m = calc_monthly_return(bnd_data, 6, latest_month_end)
            bnd_11m = calc_monthly_return(bnd_data, 11, latest_month_end)
            
            # Calculate IRX compounded returns
            irx_3m = calc_irx_compounded_return(irx_data, 3, latest_month_end)
            irx_6m = calc_irx_compounded_return(irx_data, 6, latest_month_end)
            irx_11m = calc_irx_compounded_return(irx_data, 11, latest_month_end)
            
            # Calculate weighted scores
            bnd_weighted = (bnd_3m * 0.33 + bnd_6m * 0.33 + bnd_11m * 0.34)
            irx_weighted = (irx_3m * 0.33 + irx_6m * 0.33 + irx_11m * 0.34)
            
            # Score
            indicator1_score = 1 if bnd_weighted > irx_weighted else 0
            scores_liq['indicator1'] = indicator1_score
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("BND Weighted", f"{bnd_weighted:.2f}%")
                st.caption(f"3M: {bnd_3m:.2f}% | 6M: {bnd_6m:.2f}% | 11M: {bnd_11m:.2f}%")
            with col2:
                st.metric("T-Bill Weighted", f"{irx_weighted:.2f}%")
                st.caption(f"3M: {irx_3m:.2f}% | 6M: {irx_6m:.2f}% | 11M: {irx_11m:.2f}%")
            
            st.metric("Score", f"{indicator1_score}/1", 
                      delta="✅ BND" if indicator1_score == 1 else "❌ T-Bill")
        except Exception as e:
            st.error(f"Error calculating Indicator 1: {str(e)}")
            scores_liq['indicator1'] = 0
        
        st.markdown("---")
        
        # === INDICATOR 2: TIP Moving Averages ===
        st.markdown("##### 2️⃣ TIP: 5-day MA vs 20-day MA")
        
        try:
            tip_5ma = calc_ma(tip_data, 5)
            tip_20ma = calc_ma(tip_data, 20)
            
            tip_5ma = float(tip_5ma) if tip_5ma is not None else 0
            tip_20ma = float(tip_20ma) if tip_20ma is not None else 0
            
            indicator2_score = 1 if tip_5ma > tip_20ma else 0
            scores_liq['indicator2'] = indicator2_score
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("TIP 5-day MA", f"${tip_5ma:.2f}")
            with col2:
                st.metric("TIP 20-day MA", f"${tip_20ma:.2f}")
            
            st.metric("**Score**", f"{indicator2_score}/1",
                      delta="✅ Bullish" if indicator2_score == 1 else "❌ Bearish")
        except Exception as e:
            st.error(f"Error calculating Indicator 2: {str(e)}")
            scores_liq['indicator2'] = 0
        
        st.divider()
        
        # === INDICATOR 3: IBIT Moving Averages ===
        st.subheader("3️⃣ IBIT: 3-day MA vs 8-day MA")
        
        try:
            ibit_3ma = calc_ma(ibit_data, 3)
            ibit_8ma = calc_ma(ibit_data, 8)
            
            ibit_3ma = float(ibit_3ma) if ibit_3ma is not None else 0
            ibit_8ma = float(ibit_8ma) if ibit_8ma is not None else 0
            
            indicator3_score = 1 if ibit_3ma > ibit_8ma else 0
            scores_liq['indicator3'] = indicator3_score
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("IBIT 3-day MA", f"${ibit_3ma:.2f}")
            with col2:
                st.metric("IBIT 8-day MA", f"${ibit_8ma:.2f}")
            
            st.metric("**Score**", f"{indicator3_score}/1",
                      delta="✅ Bullish" if indicator3_score == 1 else "❌ Bearish")
        except Exception as e:
            st.error(f"Error calculating Indicator 3: {str(e)}")
            scores_liq['indicator3'] = 0
        
        st.divider()
        
        # === TOTAL SCORE ===
        st.session_state.total_score_liq = sum(scores_liq.values())
        total_score_liq = st.session_state.total_score_liq
        
        st.header("📈 Liquidity Total Score")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total", f"{total_score_liq}/3")
        with col2:
            percentage_liq = (total_score_liq / 3) * 100
            st.metric("Percentage", f"{percentage_liq:.0f}%")
        with col3:
            if total_score_liq == 3:
                st.success("🟢 Strong")
            elif total_score_liq == 2:
                st.warning("🟡 Moderate")
            elif total_score_liq == 1:
                st.warning("🟠 Weak")
            else:
                st.error("🔴 Poor")
        
        # Summary table
        with st.expander("📋 Detailed Summary"):
            summary_df_liq = pd.DataFrame({
                'Indicator': [
                    '1. BND vs T-Bill (IRX)',
                    '2. TIP MA Cross',
                    '3. IBIT MA Cross',
                    '**TOTAL**'
                ],
                'Score': [
                    f"{scores_liq['indicator1']}/1",
                    f"{scores_liq['indicator2']}/1",
                    f"{scores_liq['indicator3']}/1",
                    f"**{total_score_liq}/3**"
                ],
                'Status': [
                    '✅' if scores_liq['indicator1'] == 1 else '❌',
                    '✅' if scores_liq['indicator2'] == 1 else '❌',
                    '✅' if scores_liq['indicator3'] == 1 else '❌',
                    f"**{percentage_liq:.0f}%**"
                ]
            })
            st.table(summary_df_liq)
    else:
        st.error("Unable to fetch liquidity data.")

# ==================== TAB 2: SENTIMENT ====================
with tab2:
    st.subheader("Part 2: Sentiment Indicators")
    
    st.caption(f"📅 Data last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Fetch data when tab is accessed
    with st.spinner("Loading sentiment data..."):
        xly_data, xlp_data, ffty_data = fetch_sentiment_data()
    
    scores_sent = {}
    
    # === INDICATOR 1: Citi Economic Surprise Index (MANUAL) ===
    st.markdown("##### 1️⃣ Citi Economic Surprise Index")
    
    with st.expander("ℹ️ Scoring & Data Source"):
        st.write("**Scoring:** Value > 0 = 0.5pts | MoM% positive = 0.5pts")
        st.write("**Check data:** https://en.macromicro.me/charts/45866/global-citi-surprise-index")
    
    col1, col2 = st.columns(2)
    with col1:
        citi_value = st.number_input(
            "Current Value",
            value=0.0,
            step=0.1,
            format="%.2f"
        )
    with col2:
        citi_prev = st.number_input(
            "Previous Month",
            value=0.0,
            step=0.1,
            format="%.2f"
        )
    
    # Calculate score
    score_above_zero = 0.5 if citi_value > 0 else 0
    citi_mom = ((citi_value - citi_prev) / abs(citi_prev)) * 100 if citi_prev != 0 else 0
    score_mom_positive = 0.5 if citi_mom > 0 else 0
    indicator1_sent = score_above_zero + score_mom_positive
    scores_sent['indicator1'] = indicator1_sent
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current", f"{citi_value:.2f}", 
                  delta="Above 0" if citi_value > 0 else "Below 0")
    with col2:
        st.metric("MoM%", f"{citi_mom:.1f}%")
    with col3:
        st.metric("Score", f"{indicator1_sent:.1f}/1")
    
    st.markdown("---")
    
    # === INDICATOR 2: Russell 3000 Stocks Above 50-Day MA (MANUAL) ===
    st.markdown("##### 2️⃣ Russell 3000 Above 50-Day MA")
    
    with st.expander("🔗 Data Source"):
        st.write("https://www.barchart.com/stocks/quotes/$R3FI/price-history/historical")
    
    r3fi_manual = st.number_input("% Above 50-Day MA", value=50.0, step=0.1, min_value=0.0, max_value=100.0)
    indicator2_sent = 1 if r3fi_manual > 50 else 0
    scores_sent['indicator2'] = indicator2_sent
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("R3000", f"{r3fi_manual:.1f}%")
    with col2:
        st.metric("Score", f"{indicator2_sent}/1",
                  delta="✅ >50%" if indicator2_sent == 1 else "❌ ≤50%")
    
    st.markdown("---")
    
    # === INDICATOR 3: XLY/XLP Ratio ===
    st.markdown("##### 3️⃣ XLY/XLP Ratio")
    
    if xly_data is not None and xlp_data is not None:
        try:
            # Calculate XLY/XLP ratio
            xly_xlp_ratio = xly_data / xlp_data
            
            ratio_3ma = calc_ma(xly_xlp_ratio, 3)
            ratio_8ma = calc_ma(xly_xlp_ratio, 8)
            
            ratio_3ma = float(ratio_3ma) if ratio_3ma is not None else 0
            ratio_8ma = float(ratio_8ma) if ratio_8ma is not None else 0
            
            indicator3_sent = 1 if ratio_3ma > ratio_8ma else 0
            scores_sent['indicator3'] = indicator3_sent
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("3-day MA", f"{ratio_3ma:.4f}")
            with col2:
                st.metric("8-day MA", f"{ratio_8ma:.4f}")
            
            st.metric("Score", f"{indicator3_sent}/1",
                      delta="✅ Risk-On" if indicator3_sent == 1 else "❌ Risk-Off")
        except Exception as e:
            st.error(f"Error calculating XLY/XLP ratio: {str(e)}")
            scores_sent['indicator3'] = 0
    else:
        scores_sent['indicator3'] = 0
    
    st.markdown("---")
    
    # === INDICATOR 4: FFTY ===
    st.markdown("##### 4️⃣ FFTY")
    
    if ffty_data is not None:
        try:
            ffty_3ma = calc_ma(ffty_data, 3)
            ffty_8ma = calc_ma(ffty_data, 8)
            
            ffty_3ma = float(ffty_3ma) if ffty_3ma is not None else 0
            ffty_8ma = float(ffty_8ma) if ffty_8ma is not None else 0
            
            indicator4_sent = 1 if ffty_3ma > ffty_8ma else 0
            scores_sent['indicator4'] = indicator4_sent
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("3-day MA", f"${ffty_3ma:.2f}")
            with col2:
                st.metric("8-day MA", f"${ffty_8ma:.2f}")
            
            st.metric("Score", f"{indicator4_sent}/1",
                      delta="✅ Bullish" if indicator4_sent == 1 else "❌ Bearish")
        except Exception as e:
            st.error(f"Error calculating FFTY: {str(e)}")
            scores_sent['indicator4'] = 0
    else:
        scores_sent['indicator4'] = 0
    
    st.markdown("---")
    
    # === TOTAL SCORE ===
    st.session_state.total_score_sent = sum(scores_sent.values())
    total_score_sent = st.session_state.total_score_sent
    
    st.markdown("#### 🎭 Sentiment Summary")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total", f"{total_score_sent:.1f}/4")
    with col2:
        percentage_sent = (total_score_sent / 4) * 100
        st.metric("Percentage", f"{percentage_sent:.0f}%")
    with col3:
        if total_score_sent >= 3.5:
            st.success("🟢 Very Positive")
        elif total_score_sent >= 2.5:
            st.info("🟡 Positive")
        elif total_score_sent >= 1.5:
            st.warning("🟠 Neutral")
        else:
            st.error("🔴 Negative")
    
    # Summary table
    with st.expander("📋 Detailed Summary"):
        summary_df_sent = pd.DataFrame({
            'Indicator': [
                '1. Citi Surprise Index',
                '2. R3000 Above 50-Day MA',
                '3. XLY/XLP Ratio',
                '4. FFTY MA Cross',
                '**TOTAL**'
            ],
            'Score': [
                f"{scores_sent['indicator1']:.1f}/1",
                f"{scores_sent['indicator2']}/1",
                f"{scores_sent['indicator3']}/1",
                f"{scores_sent['indicator4']}/1",
                f"**{total_score_sent:.1f}/4**"
            ],
            'Status': [
                '✅' if scores_sent['indicator1'] >= 0.5 else '❌',
                '✅' if scores_sent['indicator2'] == 1 else '❌',
                '✅' if scores_sent['indicator3'] == 1 else '❌',
                '✅' if scores_sent['indicator4'] == 1 else '❌',
                f"**{percentage_sent:.0f}%**"
            ]
        })
        st.table(summary_df_sent)

# ==================== TAB 3: TREND ====================
with tab3:
    st.subheader("Part 3: Trend Indicators")
    
    # Fetch data when tab is accessed
    with st.spinner("Loading trend data..."):
        index_data = fetch_trend_data()
    
    scores_trend = {}
    
    # === INDICATOR 1: Manual Uptrend Confirmation ===
    st.markdown("##### 1️⃣ Uptrend Confirmation")
    
    uptrend_status = st.selectbox(
        "Select Market Status:",
        ["Confirmed Uptrend", "Under Pressure/Correction", "Ambiguous Follow-through"],
        help="Your assessment of the current market trend"
    )
    
    if uptrend_status == "Confirmed Uptrend":
        indicator1_trend = 1.0
        status_color = "🟢"
    elif uptrend_status == "Ambiguous Follow-through":
        indicator1_trend = 0.5
        status_color = "🟡"
    else:
        indicator1_trend = 0.0
        status_color = "🔴"
    
    scores_trend['indicator1'] = indicator1_trend
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.metric("Trend Status", f"{uptrend_status} {status_color}")
    with col2:
        st.metric("Score", f"{indicator1_trend}/1")
    
    st.markdown("---")
    
    # === INDICATOR 2: Stage 2 Multi-Index ===
    st.markdown("##### 2️⃣ Stage 2 Indicator")
    
    # Index selector
    selected_index = st.selectbox(
        "Select Index to Analyze:",
        ['NDX (Nasdaq 100)', 'SPX (S&P 500)', 'HSI (Hang Seng)', 'HSTECH (Hang Seng TECH) - Manual'],
        help="Choose which index to use for Stage 2 calculation"
    )
    
    with st.expander("ℹ️ Stage Definitions", expanded=False):
        st.markdown("""
        - **S2** (Score 1.0): Price > 50MA, 50MA > 150MA, 150MA > 200MA
        - **S1** (Score 0.5): Price > 50MA, 50MA > 150MA, 150MA < 200MA
        - **S3 Strong** (Score 0.5): Price > 50MA, 50MA < 150MA, 150MA > 200MA
        - **Other** (Score 0): All other scenarios
        """)
    
    # Check if HSTECH manual mode
    if "Manual" in selected_index:
        st.info("⚠️ HSTECH data not available via API. Please enter stage manually.")
        
        manual_stage = st.selectbox(
            "Select HSTECH Stage:",
            ["S2", "S1", "S3 Strong", "Other"],
            help="Check TradingView or other sources for HSTECH stage"
        )
        
        if manual_stage == "S2":
            indicator2_trend = 1.0
            stage_emoji = "🟢"
        elif manual_stage in ["S1", "S3 Strong"]:
            indicator2_trend = 0.5
            stage_emoji = "🟡"
        else:
            indicator2_trend = 0.0
            stage_emoji = "🔴"
        
        scores_trend['indicator2'] = indicator2_trend
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.metric(f"HSTECH Stage", f"{manual_stage} {stage_emoji}")
        with col2:
            st.metric("Score", f"{indicator2_trend}/1")
    
    else:
        # Automated calculation for other indices
        with st.spinner(f"Fetching {selected_index} data..."):
            index_data = fetch_trend_data()
        
        if index_data and selected_index in index_data:
            # Get selected index data
            data = index_data[selected_index]
            
            if data is not None and len(data) >= 200:
                try:
                    current_price = float(data.iloc[-1])
                    ma_50 = calc_ma(data, 50)
                    ma_150 = calc_ma(data, 150)
                    ma_200 = calc_ma(data, 200)
                    
                    if ma_50 is None or ma_150 is None or ma_200 is None:
                        st.warning(f"Unable to calculate moving averages for {selected_index}")
                        scores_trend['indicator2'] = 0
                    else:
                        stage, score = calculate_stage(current_price, ma_50, ma_150, ma_200)
                        indicator2_trend = score
                        scores_trend['indicator2'] = indicator2_trend
                        
                        # Compact display
                        stage_emoji = "🟢" if score == 1.0 else ("🟡" if score == 0.5 else "🔴")
                        
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.metric(f"{selected_index} Stage", f"{stage} {stage_emoji}")
                        with col2:
                            st.metric("Score", f"{score}/1")
                        
                        # Compact details
                        with st.expander("📊 Moving Average Details"):
                            detail_col1, detail_col2 = st.columns(2)
                            with detail_col1:
                                st.write(f"**Price:** {current_price:.2f}")
                                st.write(f"**50 MA:** {ma_50:.2f}")
                            with detail_col2:
                                st.write(f"**150 MA:** {ma_150:.2f}")
                                st.write(f"**200 MA:** {ma_200:.2f}")
                    
                except Exception as e:
                    st.error(f"Error calculating {selected_index}: {str(e)}")
                    scores_trend['indicator2'] = 0
            else:
                st.warning(f"Insufficient data for {selected_index} (need 200+ days, got {len(data) if data is not None else 0})")
                scores_trend['indicator2'] = 0
        else:
            st.error(f"Unable to fetch data for {selected_index}")
            scores_trend['indicator2'] = 0
    
    st.markdown("---")
    
    # === INDICATOR 3: Market Pulse (MANUAL) ===
    st.markdown("##### 3️⃣ Market Pulse")
    
    with st.expander("ℹ️ Market Pulse Stages", expanded=False):
        st.markdown("""
        - **Green (Acceleration)**: Price > 10VMA; VWMA8 > VWMA21 > VWMA34
        - **Grey Strong (Accumulation)**: Price > 10VMA; VWMAs not stacked
        - **Grey Weak (Distribution)**: Price < 10VMA; VWMAs not stacked
        - **Red (Deceleration)**: Price < 10VMA; VWMA8 < VWMA21 < VWMA34
        """)
    
    market_pulse = st.selectbox(
        "Select Market Pulse Stage:",
        ["Green - Acceleration", "Grey Strong - Accumulation", "Grey Weak - Distribution", "Red - Deceleration"],
        help="Check TradingView Market Pulse indicator"
    )
    
    if market_pulse == "Green - Acceleration":
        indicator3_trend = 1.0
        pulse_emoji = "🟢"
    elif market_pulse == "Grey Strong - Accumulation":
        indicator3_trend = 0.5
        pulse_emoji = "🟡"
    else:
        indicator3_trend = 0.0
        pulse_emoji = "🔴"
    
    scores_trend['indicator3'] = indicator3_trend
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.metric("Market Pulse", f"{market_pulse.split(' - ')[1]} {pulse_emoji}")
    with col2:
        st.metric("Score", f"{indicator3_trend}/1")
    
    st.markdown("---")
    
    # === TOTAL SCORE ===
    st.session_state.total_score_trend = sum(scores_trend.values())
    total_score_trend = st.session_state.total_score_trend
    max_score_trend = 3.0
    
    st.markdown("#### 📊 Trend Summary")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total", f"{total_score_trend:.2f}/{max_score_trend}")
    with col2:
        percentage_trend = (total_score_trend / max_score_trend) * 100
        st.metric("Percentage", f"{percentage_trend:.0f}%")
    with col3:
        if total_score_trend >= 2.5:
            st.success("🟢 Strong Uptrend")
        elif total_score_trend >= 1.5:
            st.info("🟡 Mixed Trend")
        elif total_score_trend >= 0.5:
            st.warning("🟠 Weak Trend")
        else:
            st.error("🔴 Downtrend")
    
    # Summary table
    with st.expander("📋 Detailed Summary"):
        summary_df_trend = pd.DataFrame({
            'Indicator': [
                '1. Uptrend Confirmation',
                '2. Stage 2 (Multi-Index)',
                '3. Market Pulse',
                '**TOTAL**'
            ],
            'Score': [
                f"{scores_trend['indicator1']:.1f}/1",
                f"{scores_trend['indicator2']:.2f}/1",
                f"{scores_trend['indicator3']:.1f}/1",
                f"**{total_score_trend:.2f}/3**"
            ],
            'Status': [
                '✅' if scores_trend['indicator1'] >= 0.5 else '❌',
                '✅' if scores_trend['indicator2'] >= 0.5 else '❌',
                '✅' if scores_trend['indicator3'] >= 0.5 else '❌',
                f"**{percentage_trend:.0f}%**"
            ]
        })
        st.table(summary_df_trend)

# ==================== REFRESH BUTTON ====================
st.markdown("---")
if st.button("🔄 Refresh All Data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.caption("⚠️ This is for educational purposes only. Not financial advice.")
