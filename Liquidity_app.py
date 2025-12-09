import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Set page configuration
st.set_page_config(page_title="Market Checklist", layout="wide")

st.title("📊 Market Checklist")

# Initialize session state for manual inputs
if 'citi_score' not in st.session_state:
    st.session_state.citi_score = 0.0

# Create tabs for different sections
tab1, tab2 = st.tabs(["💧 Liquidity", "🎭 Sentiment"])

# Function to calculate percentage return
def calc_return(data, months):
    """Calculate return over specified months"""
    if len(data) < months * 21:  # Approximate trading days
        return None
    return ((data.iloc[-1] / data.iloc[-(months * 21)]) - 1) * 100

# Function to calculate moving average
def calc_ma(data, period):
    """Calculate moving average"""
    if len(data) < period:
        return None
    return data.tail(period).mean()

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_liquidity_data():
    """Fetch liquidity indicators data"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=400)
        
        bnd_df = yf.download('BND', start=start_date, end=end_date, progress=False)
        tip_df = yf.download('TIP', start=start_date, end=end_date, progress=False)
        ibit_df = yf.download('IBIT', start=start_date, end=end_date, progress=False)
        tbill_df = yf.download('^IRX', start=start_date, end=end_date, progress=False)
        
        bnd = bnd_df['Close'].squeeze() if isinstance(bnd_df['Close'], pd.DataFrame) else bnd_df['Close']
        tip = tip_df['Close'].squeeze() if isinstance(tip_df['Close'], pd.DataFrame) else tip_df['Close']
        ibit = ibit_df['Close'].squeeze() if isinstance(ibit_df['Close'], pd.DataFrame) else ibit_df['Close']
        tbill = tbill_df['Close'].squeeze() if isinstance(tbill_df['Close'], pd.DataFrame) else tbill_df['Close']
        
        bnd = bnd.dropna()
        tip = tip.dropna()
        ibit = ibit.dropna()
        tbill = tbill.dropna()
        
        return bnd, tip, ibit, tbill
    except Exception as e:
        st.error(f"Error fetching liquidity data: {str(e)}")
        return None, None, None, None

@st.cache_data(ttl=3600)
def fetch_sentiment_data():
    """Fetch sentiment indicators data"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=400)
        
        # Try different ticker variations for R3FI
        r3fi_df = None
        for ticker in ['$R3FI', 'R3FI', '^R3FI']:
            try:
                r3fi_df = yf.download(ticker, start=start_date, end=end_date, progress=False)
                if not r3fi_df.empty:
                    break
            except:
                continue
        
        xly_df = yf.download('XLY', start=start_date, end=end_date, progress=False)
        xlp_df = yf.download('XLP', start=start_date, end=end_date, progress=False)
        ffty_df = yf.download('FFTY', start=start_date, end=end_date, progress=False)
        
        # Extract and clean data
        r3fi = None
        if r3fi_df is not None and not r3fi_df.empty:
            r3fi = r3fi_df['Close'].squeeze() if isinstance(r3fi_df['Close'], pd.DataFrame) else r3fi_df['Close']
            r3fi = r3fi.dropna()
        
        xly = xly_df['Close'].squeeze() if isinstance(xly_df['Close'], pd.DataFrame) else xly_df['Close']
        xlp = xlp_df['Close'].squeeze() if isinstance(xlp_df['Close'], pd.DataFrame) else xlp_df['Close']
        ffty = ffty_df['Close'].squeeze() if isinstance(ffty_df['Close'], pd.DataFrame) else ffty_df['Close']
        
        xly = xly.dropna()
        xlp = xlp.dropna()
        ffty = ffty.dropna()
        
        return r3fi, xly, xlp, ffty
    except Exception as e:
        st.error(f"Error fetching sentiment data: {str(e)}")
        return None, None, None, None

# ==================== TAB 1: LIQUIDITY ====================
with tab1:
    st.header("Part 1: Liquidity Indicators")
    
    with st.spinner("Fetching liquidity data..."):
        bnd_data, tip_data, ibit_data, tbill_data = fetch_liquidity_data()
    
    if bnd_data is not None:
        st.info(f"📅 Data last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        scores_liq = {}
        
        # === INDICATOR 1: BND vs 3M T-Bill ===
        st.subheader("1️⃣ BND Monthly Returns vs 3M T-Bill")
        
        try:
            bnd_3m = calc_return(bnd_data, 3)
            bnd_5m = calc_return(bnd_data, 5)
            bnd_11m = calc_return(bnd_data, 11)
            
            if isinstance(tbill_data, pd.Series):
                tbill_rate = float(tbill_data.iloc[-1])
            else:
                tbill_rate = float(tbill_data)
            
            bnd_weighted = (bnd_3m * 0.33 + bnd_5m * 0.33 + bnd_11m * 0.34)
            tbill_3m_return = (tbill_rate / 100) * 0.25
            
            indicator1_score = 1 if bnd_weighted > tbill_3m_return else 0
            scores_liq['indicator1'] = indicator1_score
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("BND Weighted Return", f"{bnd_weighted:.2f}%")
                st.caption(f"3M: {bnd_3m:.2f}% (33%) | 5M: {bnd_5m:.2f}% (33%) | 11M: {bnd_11m:.2f}% (34%)")
            with col2:
                st.metric("3M T-Bill Rate (3M equiv.)", f"{tbill_3m_return:.2f}%")
                st.caption(f"Annual rate: {tbill_rate:.2f}%")
            
            st.metric("**Score**", f"{indicator1_score}/1", 
                      delta="✅ Positive" if indicator1_score == 1 else "❌ Negative")
        except Exception as e:
            st.error(f"Error calculating Indicator 1: {str(e)}")
            scores_liq['indicator1'] = 0
        
        st.divider()
        
        # === INDICATOR 2: TIP Moving Averages ===
        st.subheader("2️⃣ TIP: 5-day MA vs 20-day MA")
        
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
        total_score_liq = sum(scores_liq.values())
        st.header("📈 Liquidity Total Score")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            st.metric("Total Score", f"{total_score_liq}/3")
        with col2:
            percentage_liq = (total_score_liq / 3) * 100
            st.metric("Percentage", f"{percentage_liq:.0f}%")
        with col3:
            if total_score_liq == 3:
                st.success("🟢 **Strong Liquidity** - All indicators positive")
            elif total_score_liq == 2:
                st.warning("🟡 **Moderate Liquidity** - Mixed signals")
            elif total_score_liq == 1:
                st.warning("🟠 **Weak Liquidity** - Limited positive signals")
            else:
                st.error("🔴 **Poor Liquidity** - All indicators negative")
        
        # Summary table
        st.subheader("📋 Summary")
        summary_df_liq = pd.DataFrame({
            'Indicator': [
                '1. BND vs T-Bill',
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
    st.header("Part 2: Sentiment Indicators")
    
    with st.spinner("Fetching sentiment data..."):
        r3fi_data, xly_data, xlp_data, ffty_data = fetch_sentiment_data()
    
    st.info(f"📅 Data last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    scores_sent = {}
    
    # === INDICATOR 1: Citi Economic Surprise Index (MANUAL) ===
    st.subheader("1️⃣ Citi Economic Surprise Index (Manual Input)")
    
    st.info("💡 **Scoring Rules**: Value > 0 gets 0.5 points | MoM% positive gets 0.5 points")
    
    col1, col2 = st.columns(2)
    with col1:
        citi_value = st.number_input(
            "Current Citi Index Value",
            value=0.0,
            step=0.1,
            format="%.2f",
            help="Enter the latest Citi Economic Surprise Index value"
        )
    with col2:
        citi_prev = st.number_input(
            "Previous Month Value",
            value=0.0,
            step=0.1,
            format="%.2f",
            help="Enter previous month's value for MoM calculation"
        )
    
    # Calculate score
    score_above_zero = 0.5 if citi_value > 0 else 0
    citi_mom = ((citi_value - citi_prev) / abs(citi_prev)) * 100 if citi_prev != 0 else 0
    score_mom_positive = 0.5 if citi_mom > 0 else 0
    indicator1_sent = score_above_zero + score_mom_positive
    scores_sent['indicator1'] = indicator1_sent
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Value", f"{citi_value:.2f}", 
                  delta="Above 0" if citi_value > 0 else "Below 0")
    with col2:
        st.metric("MoM Change", f"{citi_mom:.2f}%",
                  delta="Positive" if citi_mom > 0 else "Negative")
    with col3:
        st.metric("**Score**", f"{indicator1_sent:.1f}/1",
                  help=f"Above 0: {score_above_zero} pts | MoM+: {score_mom_positive} pts")
    
    st.divider()
    
    # === INDICATOR 2: Russell 3000 Stocks Above 50-Day MA ===
    st.subheader("2️⃣ Russell 3000 Stocks Above 50-Day MA")
    
    if r3fi_data is not None and len(r3fi_data) > 0:
        try:
            latest_r3fi = float(r3fi_data.iloc[-1])
            indicator2_sent = 1 if latest_r3fi > 50 else 0
            scores_sent['indicator2'] = indicator2_sent
            
            st.metric("% Above 50-Day MA", f"{latest_r3fi:.2f}%")
            st.metric("**Score**", f"{indicator2_sent}/1",
                      delta="✅ Bullish" if indicator2_sent == 1 else "❌ Bearish")
        except Exception as e:
            st.warning(f"Error processing R3FI data: {str(e)}")
            st.info("📝 Please enter the value manually:")
            r3fi_manual = st.number_input("R3FI Value (%)", value=50.0, step=0.1)
            indicator2_sent = 1 if r3fi_manual > 50 else 0
            scores_sent['indicator2'] = indicator2_sent
            st.metric("**Score**", f"{indicator2_sent}/1")
    else:
        st.warning("⚠️ Unable to fetch $R3FI data automatically.")
        st.info("📝 Please enter the value manually:")
        r3fi_manual = st.number_input("Russell 3000 % Above 50-Day MA", value=50.0, step=0.1)
        indicator2_sent = 1 if r3fi_manual > 50 else 0
        scores_sent['indicator2'] = indicator2_sent
        st.metric("**Score**", f"{indicator2_sent}/1",
                  delta="✅ Bullish" if indicator2_sent == 1 else "❌ Bearish")
    
    st.divider()
    
    # === INDICATOR 3: XLY/XLP Ratio ===
    st.subheader("3️⃣ XLY/XLP Ratio: 3-day MA vs 8-day MA")
    
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
            st.metric("XLY/XLP 3-day MA", f"{ratio_3ma:.4f}")
        with col2:
            st.metric("XLY/XLP 8-day MA", f"{ratio_8ma:.4f}")
        
        st.metric("**Score**", f"{indicator3_sent}/1",
                  delta="✅ Risk-On" if indicator3_sent == 1 else "❌ Risk-Off")
    except Exception as e:
        st.error(f"Error calculating XLY/XLP ratio: {str(e)}")
        scores_sent['indicator3'] = 0
    
    st.divider()
    
    # === INDICATOR 4: FFTY ===
    st.subheader("4️⃣ FFTY: 3-day MA vs 8-day MA")
    
    try:
        ffty_3ma = calc_ma(ffty_data, 3)
        ffty_8ma = calc_ma(ffty_data, 8)
        
        ffty_3ma = float(ffty_3ma) if ffty_3ma is not None else 0
        ffty_8ma = float(ffty_8ma) if ffty_8ma is not None else 0
        
        indicator4_sent = 1 if ffty_3ma > ffty_8ma else 0
        scores_sent['indicator4'] = indicator4_sent
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("FFTY 3-day MA", f"${ffty_3ma:.2f}")
        with col2:
            st.metric("FFTY 8-day MA", f"${ffty_8ma:.2f}")
        
        st.metric("**Score**", f"{indicator4_sent}/1",
                  delta="✅ Bullish" if indicator4_sent == 1 else "❌ Bearish")
    except Exception as e:
        st.error(f"Error calculating FFTY: {str(e)}")
        scores_sent['indicator4'] = 0
    
    st.divider()
    
    # === TOTAL SCORE ===
    total_score_sent = sum(scores_sent.values())
    st.header("🎭 Sentiment Total Score")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        st.metric("Total Score", f"{total_score_sent:.1f}/4")
    with col2:
        percentage_sent = (total_score_sent / 4) * 100
        st.metric("Percentage", f"{percentage_sent:.0f}%")
    with col3:
        if total_score_sent >= 3.5:
            st.success("🟢 **Very Positive Sentiment** - Strong bullish signals")
        elif total_score_sent >= 2.5:
            st.info("🟡 **Positive Sentiment** - Moderately bullish")
        elif total_score_sent >= 1.5:
            st.warning("🟠 **Neutral Sentiment** - Mixed signals")
        else:
            st.error("🔴 **Negative Sentiment** - Bearish signals")
    
    # Summary table
    st.subheader("📋 Summary")
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

# Refresh button
st.divider()
if st.button("🔄 Refresh All Data"):
    st.cache_data.clear()
    st.rerun()

st.caption("⚠️ This is for educational purposes only. Not financial advice.")
