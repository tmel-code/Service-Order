import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("📦 Logistics Tracker")

# ==========================================
# 1. LOAD FUNCTION
# ==========================================
def load(file):
    if file.name.lower().endswith('.csv'):
        df = pd.read_csv(file)
    else:
        try:
            df = pd.read_excel(file)
        except:
            df = pd.read_excel(file, engine='xlrd')

    df = df.dropna(subset=['ServiceOrder'])
    
    # Clean Numbers
    for c in ['ReqQty', 'ActQty', 'TotalSales']:
        if c not in df.columns:
            df[c] = 0.0
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        
    return df


# ==========================================
# 2. PROCESS FUNCTION
# ==========================================
def process(grp):
    req = grp['ReqQty']
    act = grp['ActQty']
    short = (req - act).clip(lower=0)
    
    desc = grp['ItemDescription'].astype(str).str.upper()
    is_bill = desc.str.contains('BILLING|PAYMENT')
    
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


# ==========================================
# 3. MAIN APP
# ==========================================
with st.sidebar:
    st.header("1. Setup")
    mode = st.radio("Mode", ["Daily", "Compare"])
    st.divider()
    
    if mode == "Daily":
        f1 = st.file_uploader("Current", key="u1")
        f2 = None
    else:
        f1 = st.file_uploader("New", key="u2")
        f2 = st.file_uploader("Old", key="u3")

if f1:
    try:
        df = load(f1)
        
        # FILTERS
        with st.sidebar:
            st.divider()
            st.header("2. Filters")
            
            u_br = sorted(df['Branch'].unique().astype(str))
            u_mg = sorted(df['Manager'].unique().astype(str))
            u_cu = sorted(df['OwnerName'].unique().astype(str))
            
            br = st.multiselect("Branch", u_br)
            mg = st.multiselect("Manager", u_mg)
            
            st_fil = []
            if mode == "Daily":
                u_st = sorted(df['SOStatus'].unique().astype(str))
                st_fil = st.multiselect("Status", u_st)
            
            cu = st.multiselect("Customer", u_cu)

        # APPLY FILTERS
        if br: df = df[df['Branch'].astype(str).isin(br)]
        if mg: df = df[df['Manager'].astype(str).isin(mg)]
        if st_fil: df = df[df['SOStatus'].astype(str).isin(st_fil)]
        if cu: df = df[df['OwnerName'].astype(str).isin
