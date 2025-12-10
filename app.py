import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("📦 Logistics Tracker")

# --- 1. LOAD DATA ---
@st.cache_data
def load(file):
    if file.name.lower().endswith('.csv'):
        df = pd.read_csv(file)
    else:
        try:
            df = pd.read_excel(file)
        except:
            df = pd.read_excel(file, engine='xlrd')

    df = df.dropna(subset=['ServiceOrder'])

    for c in ['ReqQty', 'ActQty', 'TotalSales']:
        if c not in df.columns:
            df[c] = 0.0
        
        if df[c].dtype == 'object':
            s = df[c].astype(str)
            s = s.str.replace(r'[^\d.-]','',regex=True)
            df[c] = pd.to_numeric(s, errors='coerce')
        else:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        
        df[c] = df[c].fillna(0)
    return df

# --- 2. LOGIC ---
def process_row(grp):
    req = grp['ReqQty']
    act = grp['ActQty']
    short = (req - act).clip(lower=0)
    
    def check_bill(t):
        txt = str(t).upper()
        return 'BILLING' in txt or 'PAYMENT' in txt

    is_bill = grp['ItemDescription'].apply(check_bill)
    
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

# --- 3. MAIN UI ---
st.write("### 1. Setup")
mode = st.radio("Mode:", ["Daily", "Compare"], horizontal=True)

if mode == "Daily":
    f1 = st.file_uploader("Upload Current File", key="u1")
    f2 = None
else:
    c1, c2 = st.columns(2)
    f1 = c1.file_uploader("New File (End)", key="u2")
    f2 = c2.file_uploader("Old File (Start)", key="u3")

if f1:
    try:
        df = load(f1)
        
        # FILTERS (On Left)
        with st.sidebar:
            st.header("Filters")
            def get_opt(c):
                u = df[c].unique()
                return sorted([str(x) for x in u if pd.notna(x)])

            br = st.multiselect("Branch", get_opt('Branch'))
            mg = st.multiselect("Manager", get_opt('Manager'))
            cu = st.multiselect("Customer", get_opt('OwnerName'))

        if br: df = df[df['Branch'].astype(str).isin(br)]
        if mg: df = df[df['Manager'].astype(str).isin(mg)]
        if cu: df = df[df['OwnerName'].astype(str).isin(cu)]

        if df.empty:
            st.warning("No data found.")
        else:
            # --- DAILY VIEW ---
            if mode == "Daily":
                gb = df.groupby('ServiceOrder')
                res = gb.apply(process_row).reset_index()
                
                tot = res['Value'].sum()
                
                msk = res['Status'] == 'Costed'
                vc = res[msk]['Value'].sum()
                vo = tot - vc
                
                k1, k2, k3 = st.columns(3)
                k1.metric("Total", f"${tot:,.0f}")
                k2.metric("Costed", f"${vc:,.0f}")
                k3.metric("Open", f"${vo:,.0
