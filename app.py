import streamlit as st
import pandas as pd

# 1. Config
st.set_page_config(layout="wide")
st.title("📦 Logistics Tracker")

# 2. Loader
@st.cache_data
def load_data(file):
    if file.name.lower().endswith('.csv'):
        df = pd.read_csv(file)
    else:
        try:
            df = pd.read_excel(file)
        except:
            df = pd.read_excel(file, engine='xlrd')

    df = df.dropna(subset=['ServiceOrder'])

    # Clean Numbers
    cols = ['ReqQty','ActQty','TotalSales']
    for c in cols:
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

# 3. Logic
def classify(grp):
    req = grp['ReqQty']
    act = grp['ActQty']
    short = (req - act).clip(lower=0)
    
    # Check Bill
    def check(txt):
        t = str(txt).upper()
        return 'BILLING' in t or 'PAYMENT' in t

    desc = grp['ItemDescription']
    is_bill = desc.apply(check)
    
    # Masks
    m_part = (~is_bill) & (short > 0)
    m_bill = (is_bill) & (short > 0)
    
    if m_part.any():
        stat = "Waiting for Parts"
        prio = 1
    elif m_bill.any():
        stat = "Pending Payment"
        prio = 2
    else:
        stat = "Ready"
        prio = 3
        
    return pd.Series({
        'Customer': grp['OwnerName'].iloc[0],
        'Branch': grp['Branch'].iloc[0],
        'Manager': grp['Manager'].iloc[0],
        'Infor_Status': grp['SOStatus'].iloc[0],
        'Value': grp['TotalSales'].max(),
        'Calc_Status': stat,
        'Priority': prio
    })

# 4. Sidebar
with st.sidebar:
    st.header("Mode")
    mode = st.radio("View", ["Daily", "Compare"])
    st.divider()
    
    if mode == "Daily":
        k1 = "d_up"
        f1 = st.file_uploader("Current", key=k1)
        f2 = None
    else:
        k2 = "c_new"
        k3 = "c_old"
        f1 = st.file_uploader("New", key=k2)
        f2 = st.file_uploader("Old", key=k3)

# 5. Main
if f1:
    try:
        df = load_data(f1)
        
        # Filters
        with st.sidebar:
            st.divider()
            def get_opts(c):
                u = df[c].unique()
                cln = [str(x) for x in u if pd.notna(x)]
                return sorted(cln)

            br = st.multiselect("Branch", get_opts('Branch'))
            mg = st.multiselect("Manager", get_opts('Manager'))
            st_f = []
            if mode == "Daily":
                st_f = st.multiselect("Status", get_opts('SOStatus'))
            cu = st.multiselect("Customer", get_opts('OwnerName'))

        # Apply
        if br: df = df[df['Branch'].isin(br)]
        if mg: df = df[df['Manager'].isin(mg)]
        if st_f: df = df[df['SOStatus'].isin(st_f)]
        if cu: df = df[df['OwnerName'].isin(cu)]

        if df.empty:
            st.warning("No data.")
        else:
            # DAILY
            if mode == "Daily":
                res = df.groupby('ServiceOrder').apply(classify).reset_index()
                
                # Metrics
                tot = res['Value'].sum()
                mask_c = res['Infor_Status'] == 'Costed'
                vc = res[mask_c]['Value'].sum()
                vo = tot - vc
                
                c1,c2,c3 = st.columns(3)
                c1.metric("Total", f"${tot:,.0f}")
                c2.metric("Costed", f"${vc:,.0f}")
                c3.metric("Open", f"${vo:,.0f}")
                
                cols = ['ServiceOrder','Customer','Infor_Status','Value','Calc_Status']
                st.dataframe(res[cols], hide_index=True)
                
            # COMPARE
            elif mode == "
