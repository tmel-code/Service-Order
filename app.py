import streamlit as st
import pandas as pd

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Service Order Tracker Pro", page_icon="📦", layout="wide")

# --- CSS FOR STYLING ---
st.markdown("""
    <style>
    .stAlert { padding: 10px; border-radius: 5px; }
    .big-money { font-size: 24px; font-weight: bold; color: #28a745; }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Logistics & Financial Tracker Pro")

# --- DATA PROCESSING ---
@st.cache_data
def load_data(uploaded_file):
    # 1. Determine Engine
    if uploaded_file.name.lower().endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        # Using specific engine for older .xls files just in case
        try:
            df = pd.read_excel(uploaded_file)
        except:
            df = pd.read_excel(uploaded_file, engine='xlrd')
    
    # 2. Drop empty rows
    df = df.dropna(subset=['ServiceOrder'])
    
    # 3. ROBUST CLEANING (The Fix)
    # Force columns to numeric, turn errors into 0
    cols_to_clean = ['ReqQty', 'ActQty', 'TotalSales']
    for col in cols_to_clean:
        if col in df.columns:
            # Remove any currency symbols like '$' or ',' if they exist as text
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace(r'[^\d.-]', '', regex=True)
            # Convert to number
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0.0 # Create column if missing
        
    return df

def classify_order_status(group):
    # Logic to determine if "Waiting" or "Ready"
    group['Shortage'] = (group['ReqQty'] - group['ActQty']).clip(lower=0)
    
    def is_billing(desc):
        d = str(desc).upper()
        return any(x in d for x in ['BILLING', 'PAYMENT', 'DEPOSIT', 'FEE'])
    group['Type'] = group['ItemDescription'].apply(lambda x: 'Billing' if is_billing(x) else 'Part')

    missing_parts = group[(group['Type'] == 'Part') & (group['Shortage'] > 0)]
    missing_payment = group[(group['Type'] == 'Billing') & (group['Shortage'] > 0)]

    if not missing_parts.empty:
        status = "Waiting for Parts"
        # Safe string joining
        items = [str(x) for x in missing_parts['ItemDescription'].unique() if pd.notna(x)]
        summary = f"Missing: {', '.join(items[:2])}"
        priority = 1
    elif not missing_payment.empty:
        status = "Pending Payment"
        summary = "Waiting for Billing"
        priority = 2
    else:
        status = "Ready"
        summary = "OK"
        priority = 3

    # CRITICAL: We take the MAX of TotalSales for the group
    # Using 'first' or 'max' depending on data structure. Max is safer for 0s.
    order_val = group['TotalSales'].max()

    return pd.Series({
        'Customer': group['OwnerName'].iloc[0],
        'Branch': group['Branch'].iloc[0],
        'Manager': group['Manager'].iloc[0],
        'Infor_Status': group['SOStatus'].iloc[0],
        'Quotation_Value': order_val, 
        'Calc_Status': status,
        'Summary': summary,
        'Priority': priority
    })

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("1. Select Mode")
    app_mode = st.radio("Choose View:", ["Daily Dashboard", "Period Comparison"])
    
    st.divider()
    st.header("2. Upload Data")
    
    if app_mode == "Daily Dashboard":
        file_current = st.file_uploader("Upload Current Report", type=['csv', 'xls', 'xlsx'])
        file_history = None
    else:
        st.info("To compare, upload two files.")
        file_current = st.file_uploader("Upload NEW Report (End of Period)", type=['csv', 'xls', 'xlsx'])
        file_history = st.file_uploader("Upload OLD Report (Start of Period)", type=['csv', 'xls', 'xlsx'])

# --- MAIN APP ---

if file_current is not None:
    try:
        # Load Current Data
        df = load_data(file_current)
        
        # --- COMMON FILTERS (Apply to both modes) ---
        with st.sidebar:
            st.divider()
            st.header("3. Filter Data")
            
            def get_options(col):
                # Handle possible mixed types (float/str) in filter columns
                unique_vals = df[col].unique()
                clean_vals = [str(x) for x in unique_vals if pd.notna(x)]
                return sorted(clean_vals)

            sel_branch = st.multiselect("Branch", get_options('Branch'))
            sel_manager = st.multiselect("Manager", get_options('Manager'))
            sel_status = st.multiselect("Infor Status", get_options('SOStatus'))
            sel_customer = st.multiselect("Customer", get_options('OwnerName'))

        # --- APPLY FILTERS ---
        if sel_branch: df = df[df['Branch'].astype(str).isin(sel_branch)]
        if sel_manager: df = df[df['Manager'].astype(str).isin(sel_manager)]
        if sel_status: df = df[df['SOStatus'].astype(str).isin(sel_status)]
        if sel_customer: df = df[df['OwnerName'].astype(str).isin(sel_customer)]

        if df.empty:
            st.warning("No data matches your filters.")
        else:
            # --- MODE 1: DAILY DASHBOARD ---
            if app_mode == "Daily Dashboard":
                
                # Aggregate
                summary_df = df.groupby('ServiceOrder').apply(classify_order_status).reset_index()
                
                # Financial Metrics
                total_value = summary_df['Quotation_Value'].sum()
                costed_val = summary_df[summary_df['Infor_Status'] == 'Costed']['Quotation_Value'].sum()
                open_val = total_value - costed_val
                
                st.markdown("### 💵 Financial Snapshot")
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Pipeline Value", f"${total_value:,.2f}")
                c2.metric("Value (Costed)", f"${costed_val:,.2f}")
                c3.metric("Value (In Progress)", f"${open_val:,.2f}")
                
                st.divider()
                
                # Operational Metrics
                waiting = len(summary_
