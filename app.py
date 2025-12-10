import streamlit as st
import pandas as pd

st.set_page_config(page_title="Service Order Tracker", page_icon="📦", layout="wide")
st.title("📦 Logistics & Financial Tracker Pro")

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
    
    for c in ['ReqQty', 'ActQty', 'TotalSales']:
        if c in df.columns:
            if df[c].dtype == 'object':
                df[c] = df[c].astype(str).str.replace(r'[^\d.-]', '', regex=True)
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        else:
            df[c] = 0.0
    return df

def classify_order_status(group):
    group['Shortage'] = (group['ReqQty'] - group['ActQty']).clip(lower=0)
    
    def is_bill(d):
        return any(x in str(d).upper() for x in ['BILLING', 'PAYMENT', 'DEPOSIT'])
    
    group['Type'] = group['ItemDescription'].apply(lambda x: 'Billing' if is_bill(x) else 'Part')

    miss_part = group[(group['Type'] == 'Part') & (group['Shortage'] > 0)]
    miss_pay = group[(group['Type'] == 'Billing') & (group['Shortage'] > 0)]

    if not miss_part.empty:
        status = "Waiting for Parts"
        items = [str(x) for x in miss_part['ItemDescription'].unique() if pd.notna(x)]
        summary = f"Missing: {', '.join(items[:2])}"
        priority = 1
    elif not miss_pay.empty:
        status = "Pending Payment"
        summary = "Waiting for Billing"
        priority = 2
    else:
        status = "Ready"
        summary = "OK"
        priority = 3

    # Build dictionary step-by-step to prevent SyntaxError
    res = {}
    res['Customer'] = group['OwnerName'].iloc[0]
    res['Branch'] = group['Branch'].iloc[0]
    res['Manager'] = group['Manager'].iloc[0]
    res['Infor_Status'] = group['SOStatus'].iloc[0]
    res['Quotation_Value'] = group['TotalSales'].max()
    res['Calc_Status'] = status
    res['Summary'] = summary
    
    return pd.Series(res)

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Select Mode")
    mode = st.radio("View:", ["Daily Dashboard", "Period Comparison"])
    st.divider()
    
    if mode == "Daily Dashboard":
        f1 = st.file_uploader("Current Report", type=['csv','xls','xlsx'], key="d_up")
        f2 = None
    else:
        f1 = st.file_uploader("New Report (End)", type=['csv','xls','xlsx'], key="c_new")
        f2 = st.file_uploader("Old Report (Start)", type=['csv','xls','xlsx'], key="c_old")

# --- MAIN ---
if f1:
    try:
        df = load_data(f1)
        
        with st.sidebar:
            st.divider()
            st.header("3. Filters")
            
            def get_opt(c):
                return sorted([str(x) for x in df[c].unique() if pd.notna(x)])

            br = st.multiselect("Branch", get_opt('Branch'))
            mg = st.multiselect("Manager", get_opt('Manager'))
            st_filter = []
            if mode == "Daily Dashboard":
                st_filter = st.multiselect("Status", get_opt('SOStatus'))
            cust = st.multiselect("Customer", get_opt('OwnerName'))

        if br: df = df[df['Branch'].astype(str).isin(br)]
        if mg: df = df[df['Manager'].astype(str).isin(mg)]
        if st_filter: df = df[df['SOStatus'].astype(str).isin(st_filter)]
        if cust: df = df[df['OwnerName'].astype(str).isin(cust)]

        if df.empty:
            st.warning("No data found.")
        else:
            if mode == "Daily Dashboard":
                summ = df.groupby('ServiceOrder').apply(classify_order_status).reset_index()
                
                total = summ['Quotation_Value'].sum()
                costed = summ[summ['Infor_Status']=='Costed']['Quotation_Value'].sum()
                
                st.markdown("### 💵 Financials")
                c1, c2, c3 = st.columns(3)
                c1.metric("Total", f"${total:,.2f}")
                c2.metric("Costed", f"${costed:,.2f}")
                c3.metric("Open", f"${(total-costed):,.2f}")
                
                st.dataframe(summ[['ServiceOrder','Customer','Infor_Status','Quotation_Value','Calc_Status']], use_container_width=True, hide_index=True)

            elif mode == "Period Comparison" and f2:
                df_old = load_data(f2)
                
                curr = df.groupby('ServiceOrder').agg({'SOStatus':'first', 'TotalSales':'max'}).reset_index()
                hist = df_old.groupby('ServiceOrder').agg({'SOStatus':'first', 'TotalSales':'max'}).reset_index()
                
                merged = curr.merge(hist, on='ServiceOrder', how='inner', suffixes=('_New', '_Old'))
                chg = merged[merged['SOStatus_New'] != merged['SOStatus_Old']].copy()
                
                st.subheader("📊 Comparison")
                with st.expander("Filter Changes", expanded=True):
                    c1, c2 = st.columns(2)
                    old_s = sorted(chg['SOStatus_Old'].astype(str).unique())
                    new
