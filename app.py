import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("📦 Logistics Tracker")

@st.cache_data
def load(file):
    # Check type
    if file.name.lower().endswith('.csv'):
        df = pd.read_csv(file)
    else:
        try:
            df = pd.read_excel(file)
        except:
            df = pd.read_excel(
                file, engine='xlrd'
            )

    # Clean
    df = df.dropna(subset=['ServiceOrder'])
    
    # Numeric cols
    cols = ['ReqQty','ActQty','TotalSales']
    for c in cols:
        if c not in df.columns:
            df[c] = 0.0
        
        # Safe convert
        df[c] = pd.to_numeric(
            df[c], errors='coerce'
        )
        df[c] = df[c].fillna(0)
    return df

def process(grp):
    # Calc Shortage
    r = grp['ReqQty']
    a = grp['ActQty']
    short = (r - a).clip(lower=0)
    
    # Check Bill
    def chk(t):
        x = str(t).upper()
        return 'BILLING' in x or 'PAYMENT' in x

    desc = grp['ItemDescription']
    is_bill = desc.apply(chk)
    
    # Logic
    m1 = (~is_bill) & (short > 0)
    m2 = (is_bill) & (short > 0)
    
    if m1.any():
        s = "Waiting for Parts"
    elif m2.any():
        s = "Pending Payment"
    else:
        s = "Ready"
        
    # Result
    return pd.Series({
        'Customer': grp['OwnerName'].iloc[0],
        'Branch': grp['Branch'].iloc[0],
        'Manager': grp['Manager'].iloc[0],
        'Status': grp['SOStatus'].iloc[0],
        'Value': grp['TotalSales'].max(),
        'Calc_Status': s
    })

# --- MAIN ---
mode = st.radio("Mode", ["Daily", "Compare"])

if mode == "Daily":
    f1 = st.file_uploader("Current", key="u1")
    f2 = None
else:
    f1 = st.file_uploader("New", key="u2")
    f2 = st.file_uploader("Old", key="u3")

if f1:
    try:
        df = load(f1)
        
        # Sidebar
        with st.sidebar:
            st.header("Filters")
            
            # Helper
            def opts(c):
                u = df[c].unique()
                s = [str(x) for x in u]
                return sorted(s)

            br = st.multiselect("Branch", opts('Branch'))
            mg = st.multiselect("Manager", opts('Manager'))
            cu = st.multiselect("Customer", opts('OwnerName'))

        # Filter Logic
        if br:
            df = df[df['Branch'].isin(br)]
        if mg:
            df = df[df['Manager'].isin(mg)]
        if cu:
            df = df[df['OwnerName'].isin(cu)]

        if df.empty:
            st.warning("No data.")
        else:
            # VIEW: DAILY
            if mode == "Daily":
                gb = df.groupby('ServiceOrder')
                res = gb.apply
