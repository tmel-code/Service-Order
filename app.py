import streamlit as st
import pandas as pd

# 1. Config
st.set_page_config(layout="wide")
st.title("📦 Logistics Tracker")

# 2. Loader
@st.cache_data
def load_data(file):
    # Check extension
    name = file.name.lower()
    if name.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        try:
            df = pd.read_excel(file)
        except:
            # Fallback engine
            df = pd.read_excel(file, engine='xlrd')

    # Drop bad rows
    df = df.dropna(subset=['ServiceOrder'])

    # Clean Numbers
    cols = ['ReqQty','ActQty','TotalSales']
    for c in cols:
        if c not in df.columns:
            df[c] = 0.0
        
        # String cleanup
        if df[c].dtype == 'object':
            s = df[c].astype(str)
            # Safe regex pattern
            pat = r'[^\d.-]'
            s = s.str.replace(pat,'',regex=True)
            df[c] = pd.to_numeric(s, errors='coerce')
        else:
            df[c] = pd.to_numeric(df[c], errors='coerce
