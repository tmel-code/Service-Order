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

# --- MAIN APP ---
mode = st.radio("Mode", ["Daily", "Compare"])

if mode == "Daily":
    f1 = st.file_uploader("Current File", key="u1")
    f2 = None
else:
    f1 = st.file_uploader("New File", key="u2")
    f2 = st.file_uploader("Old File", key="u3")

if f1:
    try:
        df = load(f1)
        
        # Filters
        with st.sidebar:
            st.header("Filters")
            br = st.multiselect("Branch", df['Branch'].unique())
            mg = st.multiselect("Manager", df['Manager'].unique())
            cu = st.multiselect("Customer", df['OwnerName'].unique())

        if br: df = df[df['Branch'].isin(br)]
        if mg: df = df[df['Manager'].isin(mg)]
        if cu: df = df[df['OwnerName'].isin(cu)]

        if df.empty:
            st.warning("No data.")
        else:
            if mode == "Daily":
                res = df.groupby('ServiceOrder').apply(process).reset_index()
                
                tot = res['Value'].sum()
                costed = res[res['Status']=='Costed']['Value'].sum()
                
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
                    f_fr = st.multiselect("From", chg['SOStatus_O'].unique())
                    f_to = st.multiselect("To", chg['SOStatus_N'].unique())
                    
                    if f_fr: chg = chg[chg['SOStatus_O'].isin(f_fr)]
                    if f_to: chg = chg[chg['SOStatus_N'].isin(f_to)]
                    
                    cnt = len(chg)
                    val = chg[chg['SOStatus_N']=='Costed']['TotalSales_N'].sum()
                    
                    c1,c2 = st.columns(2)
                    c1.metric("Count", cnt)
                    c2.metric("To Costed", f"${val:,.0f}")
                    
                    st.dataframe(chg, hide_index=True)
                else:
                    st.info("Upload Old File.")

    except Exception as e:
        st.error(f"Error: {e}")
