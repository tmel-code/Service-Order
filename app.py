import streamlit as st
import pandas as pd

# 1. Config
st.set_page_config(layout="wide")
st.title("📦 Logistics Tracker")

# 2. Loader
@st.cache_data
def load_data(file):
    name = file.name.lower()
    if name.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        try:
            df = pd.read_excel(file)
        except:
            df = pd.read_excel(file, engine='xlrd')

    # Remove empty rows
    df = df.dropna(subset=['ServiceOrder'])

    # Clean Numbers
    cols = ['ReqQty', 'ActQty', 'TotalSales']
    for c in cols:
        if c not in df.columns:
            df[c] = 0.0
        elif df[c].dtype == 'object':
            df[c] = df[c].astype(str).str.replace(
                r'[^\d.-]', '', regex=True
            )
            df[c] = pd.to_numeric(
                df[c], errors='coerce'
            ).fillna(0)
        else:
            df[c] = pd.to_numeric(
                df[c], errors='coerce'
            ).fillna(0)
    return df

# 3. Logic
def classify(grp):
    req = grp['ReqQty']
    act = grp['ActQty']
    short = (req - act).clip(lower=0)
    
    # Helper
    def check(txt):
        t = str(txt).upper()
        return 'BILLING' in t or 'PAYMENT' in t

    is_bill = grp['ItemDescription'].
