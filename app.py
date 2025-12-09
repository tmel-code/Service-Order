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
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    # 1. Clean Key Columns
    df = df.dropna(subset=['ServiceOrder'])
    
    # 2. Clean Financials
    if 'TotalSales' in df.columns:
        df['TotalSales'] = df['TotalSales'].astype(str).str.replace(r'[^\d.-]', '', regex=True)
        df['TotalSales'] = pd.to_numeric(df['TotalSales'], errors='coerce').fillna(0)
    else:
        df['TotalSales'] = 0.0

    # 3. Clean Quantities
    for col in ['ReqQty', 'ActQty']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
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
        summary = f"Missing: {', '.join(missing_parts['ItemDescription'].unique()[:2])}"
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
        st.info("To compare, upload two files (e.g. This Month vs Last Month).")
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
                return sorted(df[col].astype(str).unique().tolist())

            sel_branch = st.multiselect("Branch", get_options('Branch'))
            sel_manager = st.multiselect("Manager", get_options('Manager'))
            sel
