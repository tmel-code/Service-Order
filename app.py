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

def classify_status(group):
    group['Shortage'] = (group['ReqQty'] - group['ActQty']).clip(lower=0)
    
    def is_bill(d): return any(x in str(d).upper() for x in ['BILLING','PAYMENT','DEPOSIT'])
    group['Type'] = group['ItemDescription'].apply(lambda x: 'Billing' if is_bill
