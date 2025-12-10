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
    
    # Numeric Cleanup
    cols = ['ReqQty', 'ActQty', 'TotalSales']
    for c in cols:
        if c not in df.columns:
            df[c] = 0.0
        # Force numeric
        df[c] = pd.to_numeric(
            df[c], errors='coerce'
        ).fillna(0)
    return df
    def process(grp):
    req = grp['ReqQty']
    act = grp['ActQty']
    short = (req - act).clip(lower=0)
    
    # Check Bill
    d = grp['ItemDescription']
    d = d.astype(str).str.upper()
    is_bill = d.str.contains('BILLING|PAYMENT')
    
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
        
        with st.sidebar:
            st.divider()
            st.header("2. Filters")
            
            # Options
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

        # Apply
        if br: df = df[df['Branch'].isin(br)]
        if mg: df = df[df['Manager'].isin(mg)]
        if st_fil: df = df[df['SOStatus'].isin(st_fil)]
        if cu: df = df[df['OwnerName'].isin(cu)]
            if df.empty:
            st.warning("No data.")
        else:
            if mode == "Daily":
                gb = df.groupby('ServiceOrder')
                res = gb.apply(process).reset_index()
                
                tot = res['Value'].sum()
                msk = res['Status'].astype(str) == 'Costed'
                costed = res[msk]['Value'].sum()
                
                c1,c2,c3 = st.columns(3)
                c1.metric("Total", f"${tot:,.0f}")
                c2.metric("Costed", f"${costed:,.0f}")
                c3.metric("Open", f"${(tot-costed):,.0f}")
                st.dataframe(res, hide_index=True)

            elif mode == "Compare":
                if f2:
                    df_old = load(f2)
                    g1 = df.groupby('ServiceOrder')
                    n = g1.agg({'SOStatus':'first','TotalSales':'max'}).reset_index()
                    g2 = df_old.groupby('ServiceOrder')
                    o = g2.agg({'SOStatus':'first','TotalSales':'max'}).reset_index()
                    
                    m = n.merge(o, on='ServiceOrder', suffixes=('_N','_O'))
                    chg = m[m['SOStatus_N'] != m['SOStatus_O']].copy()
                    
                    st.subheader("Changes")
                    c1,c2 = st.columns(2)
                    
                    # Full Option Lists
                    lst_old = sorted(o['SOStatus'].unique().astype(str))
                    lst_new = sorted(n['SOStatus'].unique().astype(str))
                    
                    fr = c1.multiselect("From", lst_old)
                    to = c2.multiselect("To", lst_new)
                    
                    if fr: chg = chg[chg['SOStatus_O'].isin(fr)]
                    if to: chg = chg[chg['SOStatus_N'].isin(to)]
                    
                    st.write("---")
                    target = st.multiselect("Calc Value To:", lst_new)
                    
                    val = 0
                    if target:
                        msk = chg['SOStatus_N'].isin(target)
                        val = chg[msk]['TotalSales_N'].sum()
                    
                    z1,z2 = st.columns(2)
                    z1.metric("Count", len(chg))
                    z2.metric("Value", f"${val:,.0f}")
                    st.dataframe(chg, hide_index=True)
                else:
                    st.info("Upload Old File.")

    except Exception as e:
        st.error(f"Error: {e}")
