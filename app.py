import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("📦 Logistics Tracker")

def load(file):
    if file.name.lower().endswith('.csv'):
        df = pd.read_csv(file)
    else:
        try:
            df = pd.read_excel(file)
        except:
            df = pd.read_excel(file, engine='xlrd')
            
    df = df.dropna(subset=['ServiceOrder'])
    cols = ['ReqQty', 'ActQty', 'TotalSales']
    for c in cols:
        if c not in df.columns:
            df[c] = 0.0
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    return df

def process(grp):
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

# --- SIDEBAR ---
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

# --- MAIN APP ---
if f1:
    try:
        df = load(f1)
        
        # GLOBAL FILTERS
        with st.sidebar:
            st.divider()
            st.header("2. Filters")
            
            # Helper to get clean list
            def get_opts(col):
                u = df[col].unique()
                return sorted([str(x) for x in u])

            br = st.multiselect("Branch", get_opts('Branch'))
            mg = st.multiselect("Manager", get_opts('Manager'))
            
            # STATUS FILTER (Daily Mode Only)
            st_fil = []
            if mode == "Daily":
                st_fil = st.multiselect("Infor Status", get_opts('SOStatus'))
            
            cu = st.multiselect("Customer", get_opts('OwnerName'))

        # Apply Filters
        if br: df = df[df['Branch'].isin(br)]
        if mg: df = df[df['Manager'].isin(mg)]
        if st_fil: df = df[df['SOStatus'].isin(st_fil)]
        if cu: df = df[df['OwnerName'].isin(cu)]

        if df.empty:
            st.warning("No data.")
        else:
            # --- DAILY VIEW ---
            if mode == "Daily":
                res = df.groupby('ServiceOrder').apply(process).reset_index()
                
                tot = res['Value'].sum()
                costed = res[res['Status']=='Costed']['Value'].sum()
                
                c1,c2,c3 = st.columns(3)
                c1.metric("Total", f"${tot:,.0f}")
                c2.metric("Costed", f"${costed:,.0f}")
                c3.metric("Open", f"${(tot-costed):,.0f}")
                
                st.dataframe(res, hide_index=True)

            # --- COMPARE VIEW ---
            elif mode == "Compare":
                if f2:
                    df_old = load(f2)
                    
                    # Grouping
                    g1 = df.groupby('ServiceOrder')
                    n = g1.agg({'SOStatus':'first','TotalSales':'max'}).reset_index()
                    
                    g2 = df_old.groupby('ServiceOrder')
                   o = g2.agg({'SOStatus':'first','TotalSales':'max'}).reset_index()
except Exception as e:
    st.error(f"An error occurred: {e}") # Or print(e)
