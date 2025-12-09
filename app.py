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
    # Using 'max' is safer than 'sum' if the value repeats on every line
    order_val = group['TotalSales'].max()

    return pd.Series({
        'Customer': group['OwnerName'].iloc[0],
        'Branch': group['Branch'].iloc[0],
        'Manager': group['Manager'].iloc[0],
        '
