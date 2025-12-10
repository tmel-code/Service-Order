import streamlit as st
import pandas as pd

st.set_page_config(page_title="Tracker", layout="wide")
st.title("📦 Logistics & Financial Tracker")

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

    # Clean Numbers
    for c in ['ReqQty', 'ActQty', 'TotalSales']:
        if c not in df.columns:
            df[c] = 0.0
        elif df[c].dtype == 'object':
            # Split regex line for safety
            df[c] = df[c].astype(str).str.replace(r'[^\d.-]', '', regex=True)
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        else:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    return df

# Logic
def classify(grp):
    # Shortage
    req = grp['ReqQty']
    act = grp['ActQty']
    grp['Shortage'] = (req - act).clip(lower=0)

    # Helper for type
    def get_type(desc):
        txt = str(desc).upper()
        keys = ['BILLING', 'PAYMENT', 'DEPOSIT']
        if any(k in txt for k in keys):
            return 'Billing'
        return 'Part'

    grp['Type'] = grp['ItemDescription'].apply(get_type)

    # Check shortages
    mask_part = (grp['Type'] == 'Part') & (grp['Shortage'] > 0)
    mask_pay = (grp['Type'] == 'Billing') & (grp['Shortage'] > 0)
    miss_part = grp[mask_part]
    miss_pay = grp[mask_pay]

    # Status
    if not miss_part.empty:
        status = "Waiting for Parts"
        # Safe join
        i_list = miss_part['ItemDescription'].unique()
        cln_list = [str(x) for x in i_list if pd.notna(x)]
        summary = f"Missing: {', '.join(cln_list[:2])}"
    elif not miss_pay.empty:
        status = "Pending Payment"
        summary = "Waiting for Billing"
    else:
        status = "Ready"
        summary = "OK"

    # Return Series
    return pd.Series({
        'Customer': grp['OwnerName'].iloc[0],
        'Branch': grp['Branch'].iloc[0],
        'Manager': grp['Manager'].iloc[0],
        'Infor_Status': grp['SOStatus'].iloc[0],
        'Quotation_Value': grp['TotalSales'].max(),
        'Calc_Status': status,
        'Summary': summary
    })

# UI
with st.sidebar:
    st.header("Mode")
    mode = st.radio("View", ["Daily", "Compare"])
    st.divider()
    if mode == "Daily":
        f1 = st.file_uploader("Current",
