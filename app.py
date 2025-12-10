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
    if uploaded_file.name.lower().endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        try:
            df = pd.read_excel(uploaded_file)
        except:
            df = pd.read_excel(uploaded_file, engine='xlrd')
    
    df = df.dropna(subset=['ServiceOrder'])
    
    cols = ['ReqQty', 'ActQty', 'TotalSales']
    for col in cols:
        if col in df.columns:
            if df[col].dtype == 'object':
                # Split regex to be safe
                df[col] = df[col].astype(str).str.replace(r'[^\d.-]', '', regex=True)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0.0
    return df

# --- LOGIC ---
def classify_order_status(group):
    group['Shortage'] = (group['ReqQty'] - group['ActQty']).clip(lower=0)
    
    def is_billing(desc):
        keywords = ['BILLING', 'PAYMENT', 'DEPOSIT', 'FEE']
        return any(x in str(desc).upper() for x in keywords)
    
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
        'Manager': group
