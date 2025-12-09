import streamlit as st
import pandas as pd

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Service Order Tracker", page_icon="📦", layout="wide")

# --- CSS FOR STYLING ---
st.markdown("""
    <style>
    .stAlert { padding: 10px; border-radius: 5px; }
    .status-money { color: #28a745; font-weight: bold; font-size: 1.2em; }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Logistics & Service Order Tracker")

# --- DATA LOADING & CLEANING ---
def load_data(uploaded_file):
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    # 1. Basic Filters
    df = df.dropna(subset=['ServiceOrder'])
    
    # 2. Clean Numeric Columns (Quantities)
    for col in ['ReqQty', 'ActQty']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
    # 3. Clean Financial Column (TotalSales)
    # Remove currency symbols if present, then convert to float
    if 'TotalSales' in df.columns:
        df['TotalSales'] = df['TotalSales'].astype(str).str.replace(r'[^\d.-]', '', regex=True)
        df['TotalSales'] = pd.to_numeric(df['TotalSales'], errors='coerce').fillna(0)
    else:
        df['TotalSales'] = 0.0
        
    return df

# --- LOGIC: CLASSIFY STATUS (Daily Ops) ---
def classify_order_status(group):
    group['Shortage'] = (group['ReqQty'] - group['ActQty']).clip(lower=0)
    
    def is_billing(desc):
        d = str(desc).upper()
        return any(x in d for x in ['BILLING', 'PAYMENT', 'DEPOSIT', 'FEE'])
    group['Type'] = group['ItemDescription'].apply(lambda x: 'Billing' if is_billing(x) else 'Part')

    missing_parts = group[(group['Type'] == 'Part') & (group['Shortage'] > 0)]
    missing_payment = group[(group['Type'] == 'Billing') & (group['Shortage'] > 0)]

    if not missing_parts.empty:
        status = "Waiting for Parts"
        priority = 1
    elif not missing_payment.empty:
        status = "Pending Payment"
        priority = 2
    else:
        status = "Ready"
        priority = 3

    return pd.Series({
        'Customer': group['OwnerName'].iloc[0],
        'Branch': group['Branch'].iloc[0],
        'Manager': group['Manager'].iloc[0],
        'Infor_Status': group['SOStatus'].iloc[0],
        'Total_Value': group['TotalSales'].sum(), # Sum value if multiple lines
        'Calc_Status': status,
        'Priority': priority
    })

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("📂 Data Upload")
    
    # Mode Selector
    app_mode = st.radio("Select Mode:", ["Daily Operations", "Monthly/Weekly Comparison"])
    
    st.divider()
    
    if app_mode == "Daily Operations":
        file_current = st.file_uploader("Upload TODAY'S File", type=['csv', 'xls', 'xlsx'])
        file_history = None
    else:
        st.info("Upload two files to compare changes over time.")
        file_current = st.file_uploader("1. Upload NEW Report (End of Month)", type=['csv', 'xls', 'xlsx'])
        file_history = st.file_uploader("2. Upload OLD Report (Start of Month)", type=['csv', 'xls', 'xlsx'])

# --- MAIN LOGIC ---

if file_current is not None:
    try:
        df_curr = load_data(file_current)
        
        # --- MODE 1: DAILY OPS ---
        if app_mode == "Daily Operations":
            # (Keep the existing Daily Logic - simplified for brevity)
            # Apply Filters
            with st.sidebar:
                st.header("🔍 Filters")
                branches = ["ALL"] + sorted(df_curr['Branch'].astype(str).unique().tolist())
                sel_branch = st.selectbox("Branch:", branches)
                statuses = sorted(df_curr['SOStatus'].astype(str).unique().tolist())
                sel_status = st.multiselect("Infor Status:", statuses, default=statuses)

            if sel_branch != "ALL": df_curr = df_curr[df_curr['Branch'].astype(str) == sel_branch]
            if sel_status: df_curr = df_curr[df_curr['SOStatus'].isin(sel_status)]

            if df_curr.empty:
                st.warning("No data found.")
            else:
                summ_curr = df_curr.groupby('ServiceOrder').apply(classify_order_status).reset_index()
                
                # Metrics
                waiting = len(summ_curr[summ_curr['Calc_Status'].str.contains("Waiting")])
                ready = len(summ_curr[summ_curr['Calc_Status'].str.contains("Ready")])
                
                c1, c2 = st.columns(2)
                c1.metric("🔴 Waiting for Parts", waiting)
                c2.metric("✅ Ready for Service", ready)
                
                st.dataframe(summ_curr, hide_index=True, use_container_width=True)

        # --- MODE 2: MONTHLY COMPARISON ---
        elif app_mode == "Monthly/Weekly Comparison" and file_history is not None:
            df_hist = load_data(file_history)
            
            # Group by Order to get Status and Value
            # We take the first row's status and the SUM of value for the order
            curr_grp = df_curr.groupby('ServiceOrder').agg({
                'SOStatus': 'first', 
                'TotalSales': 'sum', # Quotation Value
                'OwnerName': 'first'
            }).reset_index()
            
            hist_grp = df_hist.groupby('ServiceOrder').agg({
                'SOStatus': 'first', 
                'TotalSales': 'sum'
            }).reset_index()
            
            # Merge
            merged = curr_grp.merge(hist_grp, on='ServiceOrder', how='inner', suffixes=('_New', '_Old'))
            
            # Logic: Find Changes
            changes = merged[merged['SOStatus_New'] != merged['SOStatus_Old']].copy()
            
            # Logic: Specifically "Changed to COSTED"
            to_costed = changes[changes['SOStatus_New'].str.upper() == 'COSTED']
            
            # --- DISPLAY DASHBOARD ---
            st.subheader("💰 Monthly Financial Impact")
            
            # Metrics Row
            col1, col2, col3 = st.columns(3)
            
            # 1. Total Moved to Costed
            count_costed = len(to_costed)
            val_costed = to_costed['TotalSales_New'].sum()
            
            # 2. Total Status Changes
            total_changes = len(changes)
            
            col1.metric("Orders Changed to 'Costed'", count_costed)
            col2.metric("Total Value (Moved to Costed)", f"${val_costed:,.2f}")
            col3.metric("Total Status Updates", total_changes)
            
            st.divider()
            
            # Detailed Table for "To Costed"
            st.write("### 💵 Orders that became 'Costed' this month")
            if not to_costed.empty:
                st.dataframe(
                    to_costed[['ServiceOrder', 'OwnerName', 'SOStatus_Old', 'SOStatus_New', 'TotalSales_New']],
                    column_config={
                        "TotalSales_New": st.column_config.NumberColumn("Quotation Value", format="$%.2f"),
                        "SOStatus_Old": "Previous Status",
                        "SOStatus_New": "Current Status"
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("No orders moved to 'Costed' status in this comparison.")
                
            st.divider()
            
            # All Changes Summary
            st.write("### 📋 All Status Changes")
            if not changes.empty:
                st.dataframe(
                    changes[['ServiceOrder', 'OwnerName', 'SOStatus_Old', 'SOStatus_New', 'TotalSales_New']],
                    column_config={
                        "TotalSales_New": st.column_config.NumberColumn("Value", format="$%.2f")
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.success("No status changes detected between these two files.")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    if app_mode == "Monthly/Weekly Comparison":
        st.info("👈 Please upload BOTH files in the sidebar.")
    else:
        st.info("👈 Please upload a file to start.")
