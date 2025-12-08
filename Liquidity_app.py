import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Set page configuration
st.set_page_config(page_title="Market Checklist", layout="wide")

st.title("📊 Market Checklist")
st.header("Part 1: Liquidity Indicators")

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
def fetch_data():
    """Fetch all required market data"""
    try:
        # Define date range - get extra data for calculations
        end_date = datetime.now()
        start_date = end_date - timedelta(days=400)
        
        # Fetch data - ensure we get Series by using squeeze or direct extraction
        bnd_df = yf.download('BND', start=start_date, end=end_date, progress=False)
        tip_df = yf.download('TIP', start=start_date, end=end_date, progress=False)
        ibit_df = yf.download('IBIT', start=start_date, end=end_date, progress=False)
        tbill_df = yf.download('^IRX', start=start_date, end=end_date, progress=False)
        
        # Extract Close prices and ensure they're Series with proper index
        bnd = bnd_df['Close'].squeeze() if isinstance(bnd_df['Close'], pd.DataFrame) else bnd_df['Close']
        tip = tip_df['Close'].squeeze() if isinstance(tip_df['Close'], pd.DataFrame) else tip_df['Close']
        ibit = ibit_df['Close'].squeeze() if isinstance(ibit_df['Close'], pd.DataFrame) else ibit_df['Close']
        tbill = tbill_df['Close'].squeeze() if isinstance(tbill_df['Close'], pd.DataFrame) else tbill_df['Close']
        
        # Drop any NaN values
        bnd = bnd.dropna()
        tip = tip.dropna()
        ibit = ibit.dropna()
        tbill = tbill.dropna()
        
        return bnd, tip, ibit, tbill
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return None, None, None, None

# Fetch data
with st.spinner("Fetching market data..."):
    bnd_data, tip_data, ibit_data, tbill_data = fetch_data()

if bnd_data is not None:
    # Display last update time
    st.info(f"📅 Data last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize scores
    scores = {}
    
    # === INDICATOR 1: BND vs 3M T-Bill ===
    st.subheader("1️⃣ BND Monthly Returns vs 3M T-Bill")
    
    try:
        # Calculate BND returns
        bnd_3m = calc_return(bnd_data, 3)
        bnd_5m = calc_return(bnd_data, 5)
        bnd_11m = calc_return(bnd_data, 11)
        
        # Get latest T-bill rate (annualized) - handle both Series and scalar
        if isinstance(tbill_data, pd.Series):
            tbill_rate = float(tbill_data.iloc[-1])
        else:
            tbill_rate = float(tbill_data)
        
        # Calculate weighted BND score
        bnd_weighted = (bnd_3m * 0.33 + bnd_5m * 0.33 + bnd_11m * 0.34)
        
        # Calculate T-bill equivalent for comparison (3-month return)
        tbill_3m_return = (tbill_rate / 100) * 0.25  # Convert annual to 3-month
        
        # Score
        indicator1_score = 1 if bnd_weighted > tbill_3m_return else 0
        scores['indicator1'] = indicator1_score
        
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
        scores['indicator1'] = 0
    
    st.divider()
    
    # === INDICATOR 2: TIP Moving Averages ===
    st.subheader("2️⃣ TIP: 5-day MA vs 20-day MA")
    
    try:
        tip_5ma = calc_ma(tip_data, 5)
        tip_20ma = calc_ma(tip_data, 20)
        
        # Ensure we have float values for comparison
        tip_5ma = float(tip_5ma) if tip_5ma is not None else 0
        tip_20ma = float(tip_20ma) if tip_20ma is not None else 0
        
        indicator2_score = 1 if tip_5ma > tip_20ma else 0
        scores['indicator2'] = indicator2_score
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("TIP 5-day MA", f"${tip_5ma:.2f}")
        with col2:
            st.metric("TIP 20-day MA", f"${tip_20ma:.2f}")
        
        st.metric("**Score**", f"{indicator2_score}/1",
                  delta="✅ Bullish" if indicator2_score == 1 else "❌ Bearish")
    except Exception as e:
        st.error(f"Error calculating Indicator 2: {str(e)}")
        scores['indicator2'] = 0
    
    st.divider()
    
    # === INDICATOR 3: IBIT Moving Averages ===
    st.subheader("3️⃣ IBIT: 3-day MA vs 8-day MA")
    
    try:
        ibit_3ma = calc_ma(ibit_data, 3)
        ibit_8ma = calc_ma(ibit_data, 8)
        
        # Ensure we have float values for comparison
        ibit_3ma = float(ibit_3ma) if ibit_3ma is not None else 0
        ibit_8ma = float(ibit_8ma) if ibit_8ma is not None else 0
        
        indicator3_score = 1 if ibit_3ma > ibit_8ma else 0
        scores['indicator3'] = indicator3_score
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("IBIT 3-day MA", f"${ibit_3ma:.2f}")
        with col2:
            st.metric("IBIT 8-day MA", f"${ibit_8ma:.2f}")
        
        st.metric("**Score**", f"{indicator3_score}/1",
                  delta="✅ Bullish" if indicator3_score == 1 else "❌ Bearish")
    except Exception as e:
        st.error(f"Error calculating Indicator 3: {str(e)}")
        scores['indicator3'] = 0
    
    st.divider()
    
    # === TOTAL SCORE ===
    total_score = sum(scores.values())
    st.header("📈 Liquidity Total Score")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        st.metric("Total Score", f"{total_score}/3")
    with col2:
        percentage = (total_score / 3) * 100
        st.metric("Percentage", f"{percentage:.0f}%")
    with col3:
        if total_score == 3:
            st.success("🟢 **Strong Liquidity** - All indicators positive")
        elif total_score == 2:
            st.warning("🟡 **Moderate Liquidity** - Mixed signals")
        elif total_score == 1:
            st.warning("🟠 **Weak Liquidity** - Limited positive signals")
        else:
            st.error("🔴 **Poor Liquidity** - All indicators negative")
    
    # Summary table
    st.subheader("📋 Summary")
    summary_df = pd.DataFrame({
        'Indicator': [
            '1. BND vs T-Bill',
            '2. TIP MA Cross',
            '3. IBIT MA Cross',
            '**TOTAL**'
        ],
        'Score': [
            f"{scores['indicator1']}/1",
            f"{scores['indicator2']}/1",
            f"{scores['indicator3']}/1",
            f"**{total_score}/3**"
        ],
        'Status': [
            '✅' if scores['indicator1'] == 1 else '❌',
            '✅' if scores['indicator2'] == 1 else '❌',
            '✅' if scores['indicator3'] == 1 else '❌',
            f"**{percentage:.0f}%**"
        ]
    })
    st.table(summary_df)
    
    # Refresh button
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

else:
    st.error("Unable to fetch market data. Please check your internet connection and try again.")
    if st.button("Retry"):
        st.cache_data.clear()
        st.rerun()

st.divider()
st.caption("⚠️ This is for educational purposes only. Not financial advice.")
