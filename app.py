import streamlit as st
import pandas as pd

# --- CONFIGURATION ---
st.set_page_config(page_title="Service Order Tracker", page_icon="📦", layout="wide")
st.markdown("""
    <style>
    .stAlert { padding: 10px; border-radius: 5px; }
    .big-money { font-size: 24px; font-weight: bold; color: #28a745; }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Logistics & Financial Tracker Pro")

# --- DATA LOADING ---
@st.cache_data
def load_data(uploaded_file):
    # 1. Determine Engine
    if uploaded_file.name.lower().endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        try:
            df = pd.read_excel(uploaded_file)
        except:
            df = pd.read_excel(uploaded_file, engine='xlrd')
    
    # 2. Cleanup
    df = df.dropna(subset=['ServiceOrder'])
    
    # 3. Numeric Cleaning
    cols = ['ReqQty', 'ActQty', 'TotalSales']
    for col in cols:
        if col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace(r'[^\d.-]', '', regex=True)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0.0
    return df

# --- LOGIC ---
def classify_order_status(group):
    group['Shortage'] = (group['ReqQty'] - group['ActQty']).clip(lower=0)
    
    def is_billing(desc):
        return any(x in str(desc).upper() for x in ['BILLING', 'PAYMENT', 'DEPOSIT', 'FEE'])
    
    group['Type'] = group['ItemDescription'].apply(lambda x: 'Billing' if is_billing(x) else 'Part')

    missing_parts = group[(group['Type'] == 'Part') & (group['Shortage'] > 0)]
    missing_pymt = group[(group['Type'] == 'Billing') & (group['Shortage'] > 0)]

    if not missing_parts.empty:
        status = "Waiting for Parts"
        items = [str(x) for x in missing_parts['ItemDescription'].unique() if pd.notna(x)]
        summary = f"Missing: {', '.join(items[:2])}"
        priority = 1
    elif not missing_pymt.empty:
        status = "Pending Payment"
        summary = "Waiting for Billing"
        priority = 2
    else:
        status = "Ready"
        summary = "OK"
        priority = 3

    return pd.Series({
        'Customer': group['OwnerName'].iloc[0],
        'Branch': group['Branch'].iloc[0],
        'Manager': group['Manager'].iloc[0],
        'Infor_Status': group['SOStatus'].iloc[0],
        'Quotation_Value': group['TotalSales'].max(), 
        'Calc_Status': status,
        'Summary': summary,
        'Priority': priority
    })

# --- SIDEBAR (THE FIX IS HERE) ---
with st.sidebar:
    st.header("1. Select Mode")
    app_mode = st.radio("View:", ["Daily Dashboard", "Period Comparison"])
    
    st.divider()
    st.header("2. Upload Data")
    
    # KEY PARAMETER ADDED TO FIX DISAPPEARING BUTTONS
    if app_mode == "Daily Dashboard":
        file_curr = st.file_uploader("Upload Current Report", type=['csv', 'xls', 'xlsx'], key="daily_uploader")
        file_hist = None
    else:
        file_curr = st.file_uploader("New Report (End)", type=['csv', 'xls', 'xlsx'], key="comp_new")
        file_hist = st.file_uploader("Old Report (Start)", type=['csv', 'xls', 'xlsx'], key="comp_old")

# --- MAIN APP ---
if file_curr is not None:
    try:
        df = load_data(file_curr)
        
        # --- FILTERS ---
        with st.sidebar:
            st.divider()
            st.header("3. Filter Data")
            def get_opts(col):
                vals = df[col].unique()
                return sorted([str(x) for x in vals if pd.notna(x)])

            sel_branch = st.multiselect("Branch", get_opts('Branch'))
            sel_mgr = st.multiselect("Manager", get_opts('Manager'))
            sel_stat = st.multiselect("Infor Status", get_opts('SOStatus'))
            sel_cust = st.multiselect("Customer", get_opts('OwnerName'))

        # Apply Filters
        if sel_branch: df = df[df['Branch'].astype(str).isin(sel_branch)]
        if sel_mgr: df = df[df['Manager'].astype(str).isin(sel_mgr)]
        if sel_stat: df = df[df['SOStatus'].astype(str).isin(sel_stat)]
        if sel_cust: df = df[df['OwnerName'].astype(str).isin(sel_cust)]

        if df.empty:
            st.warning("No data matches filters.")
        else:
            if app_mode == "Daily Dashboard":
                # Aggregate
                summ_df = df.groupby('ServiceOrder').apply(classify_order_status).reset_index()
                
                # Metrics
                tot_val = summ_df['Quotation_Value'].sum()
                costed = summ_df[summ_df['Infor_Status']=='Costed']['Quotation_Value'].sum()
                
                st.markdown("### 💵 Financial Snapshot")
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Value", f"${tot_val:,.2f}")
                c2.metric("Costed", f"${costed:,.2f}")
                c3.metric("In Progress", f"${(tot_val - costed):,.2f}")
                
                st.divider()
                
                # Ops Metrics
                waiting = len(summ_df[summ_df['Calc_Status'].str.contains("Waiting")])
                ready = len(summ_df[summ_df['Calc_Status'].str.contains("Ready")])
                
                st.markdown("### 📦 Operational Snapshot")
                o1, o2 = st.columns(2)
                o1.metric("🔴 Waiting", waiting)
                o2.metric("✅ Ready", ready)
                
                # Table
                st.dataframe(
                    summ_df[['ServiceOrder', 'Customer', 'Infor_Status', 'Quotation_Value', 'Calc_Status', 'Manager']],
                    use_container_width=True,
                    hide_index=True
                )

            elif app_mode == "Period Comparison"
