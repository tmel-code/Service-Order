import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("📦 Logistics Tracker")

# --- LOAD FUNCTION ---
def load(file):
    # Check type
    if file.name.lower().endswith('.csv'):
        df = pd.read_csv(file)
    else:
        try:
            df = pd.read_excel(file)
        except:
            df = pd.read_excel(file, engine='xlrd')

    # Basic Cleanup
    df = df.dropna(subset=['ServiceOrder'])
    
    # Numeric Cleanup
    cols = ['ReqQty', 'ActQty', 'TotalSales']
    for c in cols:
        if c not in df.columns:
            df[c] = 0.0
        
        # Clean string currency
        df[c] = pd.to_numeric(
            df[c], errors='coerce'
        ).fillna(0)
        
    return df


# --- PROCESS FUNCTION ---
def process(grp):
    # Shortage
    req = grp['ReqQty']
    act = grp['ActQty']
    short = (req - act).clip(lower=0)
    
    # Check Bill
    desc = grp['ItemDescription']
    desc = desc.astype(str).str.upper()
    is_bill = desc.str.contains('BILLING|PAYMENT')
    
    # Logic
    m_part = (~is_bill) & (short > 0)
    m_bill = (is_bill) & (short > 0)
    
    if m_part.any():
        s = "Waiting for Parts"
    elif m_bill.any():
        s = "Pending Payment"
    else:
        s = "Ready"
        
    # Result Series
    return pd.Series({
        'Customer': grp['OwnerName'].iloc[0],
        'Branch': grp['Branch'].iloc[0],
        'Manager': grp['Manager'].iloc[0],
        'Status': grp['SOStatus'].iloc[0],
        'Value': grp['TotalSales'].max(),
        'Calc_Status': s
    })


# --- MAIN APP ---
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
            
            # Get Options
            u_br = df['Branch'].unique()
            u_mg = df['Manager'].unique()
            u_cu = df['OwnerName'].unique()
            
            br = st.multiselect("Branch", u_br)
            mg = st.multiselect("Manager", u_mg)
            
            st_fil = []
            if mode == "Daily":
                u_st = df['SOStatus'].unique()
                st_fil = st.multiselect("Status", u_st)
            
            cu = st.multiselect("Customer", u_cu)

        # Apply Filters
        if br: df = df[df['Branch'].isin(br)]
        if mg: df = df[df['Manager'].isin(mg)]
        if st_fil: df = df[df['SOStatus'].isin(st_fil)]
        if cu: df = df[df['OwnerName'].isin(cu)]

        if df.empty:
            st.warning("No data.")
        else:
            # DAILY VIEW
            if mode == "Daily":
                gb = df.groupby('ServiceOrder')
                res = gb.apply(process).reset_index()
                
                tot = res['Value'].sum()
                
                msk = res['Status']=='Costed'
                costed = res[msk]['Value'].sum()
                
                c1,c2,c3 = st.columns(3)
                c1.metric("Total", f"${tot:,.0f}")
                c2.metric("Costed", f"${costed:,.0f}")
                c3.metric("Open", f"${(tot-costed):,.0f}")
                
                st.dataframe(res, hide_index=True)

            # COMPARE VIEW
            elif mode == "Compare":
                if f2:
                    df_old = load(f2)
                    
                    # Group New
                    g1 = df.groupby('ServiceOrder')
                    n = g1.agg({
                        'SOStatus':'first',
                        'TotalSales':'max'
                    }).reset_index()
                    
                    # Group Old
                    g2 = df_old.groupby('ServiceOrder')
                    o = g2.agg({
                        'SOStatus':'first',
                        'TotalSales':'max'
                    }).reset_index()
                    
                    # Merge
                    m = n.merge(o, on='ServiceOrder', suffixes=('_N','_O'))
                    
                    # Diff
                    mask = m['SOStatus_N'] != m['SOStatus_O']
                    chg = m[mask].copy()
                    
                    st.subheader("Changes")
                    
                    # Compare Filters
                    c1,c2 = st.columns(2)
                    opt_fr = chg['SOStatus_O'].unique()
                    opt_to = chg['SOStatus_N'].unique()
                    
                    fr = c1.multiselect("From", opt_fr)
                    to = c2.multiselect("To", opt_to)
                    
                    if fr: chg = chg[chg['SOStatus_O'].isin(fr)]
                    if to: chg = chg[chg['SOStatus_N'].isin(to)]
                    
                    # Value Calc
                    st.write("---")
                    target = st.multiselect(
                        "Calc Value To:", opt_to
                    )
                    
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
