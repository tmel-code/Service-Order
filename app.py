import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("📦 Logistics Tracker")

def load(file):
    # Determine file type
    if file.name.lower().endswith('.csv'):
        df = pd.read_csv(file)
    else:
        try:
            df = pd.read_excel(file)
        except:
            df = pd.read_excel(file, engine='xlrd')
            
    # Basic cleanup
    df = df.dropna(subset=['ServiceOrder'])
    cols = ['ReqQty', 'ActQty', 'TotalSales']
    for c in cols:
        if c not in df.columns:
            df[c] = 0.0
        # Convert to numeric, forcing errors to NaN then 0
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    return df

def process(grp):
    # Logic for row status
    req = grp['ReqQty']
    act = grp['ActQty']
    short = (req - act).clip(lower=0)
    
    desc = grp['ItemDescription'].astype(str).str.upper()
    is_bill = desc.str.contains('BILLING|PAYMENT|DEPOSIT')
    
    m_part = (~is_bill) & (short > 0)
    m_bill = (is_bill) & (short > 0)
    
    if m_part.any():
        s = "Waiting for Parts"
    elif m_bill.any():
        s = "Pending Payment"
    else:
        s = "Ready"
        
    return pd.Series({
        'Customer': grp['OwnerName'].iloc[0],
        'Branch': grp['Branch'].iloc[0],
        'Manager': grp['Manager'].iloc[0],
        'Status': grp['SOStatus'].iloc[0],
        'Value': grp['TotalSales'].max(),
        'Calc_Status': s
    })

# --- SIDEBAR: SETUP ---
with st.sidebar:
    st.header("1. Setup")
    mode = st.radio("Mode", ["Daily", "Compare"])
    st.divider()
    
    if mode == "Daily":
        f1 = st.file_uploader("Current File", key="u1")
        f2 = None
    else:
        f1 = st.file_uploader("New File (End)", key="u2")
        f2 = st.file_uploader("Old File (Start)", key="u3")

# --- MAIN APP LOGIC ---
if f1:
    try:
        df = load(f1)
        
        # --- SIDEBAR: FILTERS ---
        with st.sidebar:
            st.divider()
            st.header("2. Filters")
            
            # Helper to get sorted unique options
            def opts(c):
                u = df[c].unique()
                return sorted([str(x) for x in u])

            br = st.multiselect("Branch
