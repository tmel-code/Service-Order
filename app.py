import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("📦 Logistics Tracker")

# --- 1. LOAD FUNCTION ---
def load(file):
    # Determine type
    if file.name.lower().endswith('.csv'):
        df = pd.read_csv(file)
    else:
        try:
            df = pd.read_excel(file)
        except:
            df = pd.read_excel(file, engine='xlrd')

    # Basic Cleaning
    df = df.dropna(subset=['ServiceOrder'])
    
    # Numeric Cleanup
    cols = ['ReqQty', 'ActQty', 'TotalSales']
    for c in cols:
        if c not in df.columns:
            df[c] = 0.0
        
        # Clean currency strings
        df[c] = pd.to_numeric(
            df[c], errors='coerce'
        ).fillna(0)
        
    return df

# --- 2. PROCESS FUNCTION ---
def process(grp):
    # Shortage Calculation
    req = grp['ReqQty']
    act = grp['ActQty']
    short = (req - act).clip(lower=0)
    
    # Check for Billing Items
    desc = grp['ItemDescription']
    desc = desc.astype(str).str.upper()
    is_bill = desc.str.contains('BILLING|PAYMENT')
    
    # Logic Masks
    m_part = (~is_bill) & (short > 0)
    m_bill = (is_bill) & (short > 0)
    
    # Determine Status
    if m_part.any():
        s = "Waiting for Parts"
    elif m_bill.any():
        s = "Pending Payment"
    else:
        s = "Ready"
        
    # Return One Row per Order
    return pd.Series({
        'Customer': grp['OwnerName'].iloc[0],
        'Branch': grp['Branch'].iloc[0],
        'Manager': grp['Manager'].iloc[0],
        'Status': grp['SOStatus'].iloc[0],
        'Value': grp['TotalSales'].max(),
        'Calc_Status': s
    })

# --- 3. MAIN APPLICATION ---
with st.sidebar:
    st.header("1. Setup")
    mode = st.radio("Mode", ["Daily", "Compare"])
    st.divider()
    
    if mode == "Daily":
        f1 = st.file_uploader("Current File", key="u1")
        f2 = None
    else:
        f1 = st.file_uploader("New File", key="u2")
        f2 = st.file_uploader("Old File", key="u3")

if f1:
    try:
        df = load(f1)
        
        # GLOBAL FILTERS
        with st.sidebar:
            st.divider()
            st.header("2. Filters")
            
            # Use all unique values from file
            u_br = sorted(df['Branch'].unique().astype(str))
            u_mg = sorted(df['Manager'].unique().astype(str))
            u_cu = sorted(df['OwnerName'].unique().astype(str))
            
            br = st.multiselect("Branch", u_br)
            mg = st.multiselect("Manager", u_mg)
            
            st_fil = []
            if mode == "Daily
