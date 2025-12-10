import streamlit as st
import pandas as pd

# 1. Config
st.set_page_config(layout="wide")
st.title("📦 Logistics Tracker")

# 2. Loader
@st.cache_data
def load_data(file):
    # Check Type
    n = file.name.lower()
    if n.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        try:
            df = pd.read_excel(file)
        except:
            df = pd.read_excel(
                file,
                engine='xlrd'
            )

    # Drop Empty
    df = df.dropna(
        subset=['ServiceOrder']
    )

    # Clean Columns
    targets = [
        'ReqQty',
        'ActQty',
        'TotalSales'
    ]
    
    for c in targets:
        # Create if missing
        if c not in df.columns:
            df[c] = 0.0
        
        # String Clean
        if df[c].dtype == 'object':
            s = df[c].astype(str)
            # Regex
            pat = r'[^\d.-]'
            s = s.str.replace(
                pat,
                '',
                regex=True
            )
            # Convert
            df[c] = pd.to_numeric(
                s,
                errors='coerce'
            )
        else:
            # Force convert
            df[c] = pd.to_numeric(
                df[c],
                errors='coerce'
            )
            
        # Fill NaN
        df[c] = df[c].fillna(0)
        
    return df

# 3. Logic
def classify(grp):
    # Math
    r = grp['ReqQty']
    a = grp['ActQty']
    diff = r - a
    short = diff.clip(lower=0)
    
    # Billing Check
    def check(x):
        t = str(x).upper()
        # Keywords
        k1 = 'BILLING'
        k2 = 'PAYMENT'
        k3 = 'DEPOSIT'
        return k1 in t or k2 in t or k3 in t

    # Apply Check
    desc = grp['ItemDescription']
    is_bill = desc.apply(check)
