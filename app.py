import streamlit as st
import pandas as pd

st.set_page_config(page_title="Service Order Tracker", page_icon="📦", layout="wide")

st.markdown("""
    <style>
    .stAlert { padding: 10px; border-radius: 5px; }
    .big-money { font-size: 24px; font-weight: bold; color: #28a745; }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Logistics & Financial Tracker Pro")

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

def classify_order_status(group):
    # Logic
    group['Shortage'] = (group['ReqQty'] - group['ActQty']).clip(lower=0)
    
    def is_billing(desc):
        return any(x in str(desc).upper() for x in ['BILLING', 'PAYMENT', 'DEPOSIT', 'FEE'])
    
    group['Type'] = group['ItemDescription'].apply(lambda x: 'Billing' if is_billing(x) else 'Part')

    missing_parts = group[(group['Type'] == 'Part') & (group['Shortage'] > 0)]
    missing_pymt = group[(group['Type'] == 'Billing') & (group['Shortage'] > 0)]

    if not missing_parts.empty:
        status = "Waiting for Parts"
        # Safe string list creation
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

    # Return series
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

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Select Mode")
    app_mode = st.radio("View:", ["Daily Dashboard", "Period Comparison"])
    st.divider()
