import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("📦 Logistics Tracker")

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
    
    # Numeric Cleanup
    for c in ['ReqQty', 'ActQty', 'TotalSales']:
        if c not in df.columns:
            df[c] = 0.0
        
        # Convert safely
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    return df
    def process(grp):
    # Calculate Shortage
    r = grp['ReqQty']
    a = grp['ActQty']
    short = (r - a).clip(lower=0)
    
    # Check Billing
    def check(t):
        x = str(t).upper()
        return 'BILLING' in x or 'PAYMENT' in x

    desc = grp['ItemDescription']
    is_bill = desc.apply(check)
    
    # Status Logic
    m1 = (~is_bill) & (short > 0)
    m2 = (is_bill) & (short > 0)
    
    if m1.any():
        s = "Waiting for Parts"
    elif m2.any():
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
    # --- MAIN APP ---
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
        
        # Filters
        with st.sidebar:
            st.header("Filters")
            def opts(c):
                u = df[c].unique()
                return sorted([str(x) for x in u])

            br = st.multiselect("Branch", opts('Branch'))
            mg = st.multiselect("Manager", opts('Manager'))
            cu = st.multiselect("Customer", opts('OwnerName'))

        if br: df = df[df['Branch'].isin(br)]
        if mg: df = df[df['Manager'].isin(mg)]
        if cu: df = df[df['OwnerName'].isin(cu)]

        if df.empty:
            st.warning("No data.")
        else:
            if mode == "Daily":
                gb = df.groupby('ServiceOrder')
                res = gb.apply(process).reset_index()
                
                tot = res['Value'].sum()
                msk = res['Status'] == 'Costed'
                vc = res[msk]['Value'].sum()
                vo = tot - vc
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Total", f"${tot:,.0f}")
                c2.metric("Costed", f"${vc:,.0f}")
                c3.metric("Open", f"${vo:,.0f}")
                st.dataframe(res, hide_index=True)

            elif mode == "Compare":
                if f2:
                    df_old = load(f2)
                    g1 = df.groupby('ServiceOrder')
                    n = g1.agg({'SOStatus':'first','TotalSales':'max'}).reset_index()
                    g2 = df_old.groupby('ServiceOrder')
                    o = g2.agg({'SOStatus':'first','TotalSales':'max'}).reset_index()
                    
                    m = n.merge(o, on='ServiceOrder', suffixes=('_N','_O'))
                    msk = m['SOStatus_N'] != m['SOStatus_O']
                    chg = m[msk].copy()
                    
                    st.subheader("Changes")
                    with st.expander("Filter"):
                        k1, k2 = st.columns(2)
                        frm = k1.multiselect("From", chg['SOStatus_O'].unique())
                        to = k2.multiselect("To", chg['SOStatus_N'].unique())
                        
                    if frm: chg = chg[chg['SOStatus_O'].isin(frm)]
                    if to: chg = chg[chg['SOStatus_N'].isin(to)]
                        
                    cnt = len(chg)
                    v = 0
                    if not chg.empty:
                        msk = chg['SOStatus_N'].str.upper() == 'COSTED'
                        v = chg[msk]['TotalSales_N'].sum()
                        
                    z1, z2 = st.columns(2)
                    z1.metric("Count", cnt)
                    z2.metric("To Costed", f"${v:,.0f}")
                    
                    if not chg.empty: st.dataframe(chg, hide_index=True)
                    else: st.info("No changes.")
                else:
                    st.info("Upload Old File.")

    except Exception as e:
        st.error(f"Error: {e}")
