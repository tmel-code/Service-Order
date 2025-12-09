import streamlit as st
import pandas as pd

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Service Order Tracker", page_icon="📦", layout="wide")

# --- CSS FOR STYLING ---
st.markdown("""
    <style>
    .stAlert { padding: 10px; border-radius: 5px; }
    .status-stalled { background-color: #ffcccc; color: #a94442; }
    .status-new { background-color: #dff0d8; color: #3c763d; }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Logistics & Service Order Tracker")

# --- LOGIC FUNCTIONS ---
def classify_order_status(group):
    # 1. Calculate Shortages
    group['Shortage'] = (group['ReqQty'] - group['ActQty']).clip(lower=0)
    
    # 2. Identify Billing items
    def is_billing(desc):
        d = str(desc).upper()
        return any(x in d for x in ['BILLING', 'PAYMENT', 'DEPOSIT', 'FEE'])
    group['Type'] = group['ItemDescription'].apply(lambda x: 'Billing' if is_billing(x) else 'Part')

    # 3. Check for Shortages
    missing_parts = group[(group['Type'] == 'Part') & (group['Shortage'] > 0)]
    missing_payment = group[(group['Type'] == 'Billing') & (group['Shortage'] > 0)]

    # 4. Status Hierarchy
    if not missing_parts.empty:
        status = "Waiting for Parts"
        items = missing_parts['ItemDescription'].unique()
        summary = f"Missing: {', '.join(items[:2])}"
        if len(items) > 2: summary += ", ..."
        priority = 1
    elif not missing_payment.empty:
        status = "Pending Payment"
        summary = "Waiting for payment"
        priority = 2
    else:
        status = "Ready"
        summary = "All allocated"
        priority = 3

    return pd.Series({
        'Customer': group['OwnerName'].iloc[0],
        'Branch': group['Branch'].iloc[0],
        'Manager': group['Manager'].iloc[0],
        'Infor_Status': group['SOStatus'].iloc[0], # Keep original Infor Status
        'Calc_Status': status,                     # Our calculated status
        'Summary': summary,
        'Priority': priority
    })

def load_data(uploaded_file):
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    df = df.dropna(subset=['ServiceOrder'])
    for col in ['ReqQty', 'ActQty']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("📂 Data Upload")
    file_current = st.file_uploader("1. Upload TODAY'S File (Required)", type=['csv', 'xls', 'xlsx'])
    
    st.divider()
    
    st.header("📊 Compare Mode")
    enable_history = st.checkbox("Enable Weekly Comparison")
    file_history = None
    if enable_history:
        file_history = st.file_uploader("2. Upload LAST WEEK'S File", type=['csv', 'xls', 'xlsx'])

# --- MAIN LOGIC ---

if file_current is not None:
    try:
        # Process Current Data
        df_curr = load_data(file_current)
        
        # --- FILTERS (NEW!) ---
        with st.sidebar:
            st.header("🔍 Filters")
            
            # 1. Branch Filter
            branches = ["ALL"] + sorted(df_curr['Branch'].astype(str).unique().tolist())
            sel_branch = st.selectbox("Branch:", branches)
            
            # 2. Manager Filter
            managers = ["ALL"] + sorted(df_curr['Manager'].astype(str).unique().tolist())
            sel_manager = st.selectbox("Manager:", managers)
            
            # 3. SO Status Filter (New!)
            # We get all unique statuses (Costed, Released, Free, etc.)
            all_statuses = sorted(df_curr['SOStatus'].astype(str).unique().tolist())
            sel_status = st.multiselect(
                "Infor SO Status:", 
                options=all_statuses,
                default=all_statuses # Select all by default
            )
            
        # --- APPLY FILTERS ---
        if sel_branch != "ALL": 
            df_curr = df_curr[df_curr['Branch'].astype(str) == sel_branch]
        if sel_manager != "ALL": 
            df_curr = df_curr[df_curr['Manager'].astype(str) == sel_manager]
            
        # Filter by the Multi-Select Box
        if sel_status:
            df_curr = df_curr[df_curr['SOStatus'].isin(sel_status)]

        # Aggregate Current
        if df_curr.empty:
            st.warning("No orders found matching these filters.")
        else:
            summ_curr = df_curr.groupby('ServiceOrder').apply(classify_order_status).reset_index()

            # --- MODE 1: WEEKLY COMPARISON ---
            if enable_history and file_history is not None:
                st.subheader("🗓️ Weekly Progress Report")
                df_hist = load_data(file_history)
                summ_hist = df_hist.groupby('ServiceOrder').apply(classify_order_status).reset_index()
                
                merged = summ_curr.merge(summ_hist, on='ServiceOrder', how='left', suffixes=('', '_Old'))
                
                def get_trend(row):
                    if pd.isna(row['Calc_Status_Old']): return "🌟 New Order"
                    if "Waiting" in row['Calc_Status'] and "Waiting" in row['Calc_Status_Old']:
                        return "⚠️ STALLED (Still Waiting)"
                    if "Ready" in row['Calc_Status'] and "Waiting" in row['Calc_Status_Old']:
                        return "✅ RESOLVED"
                    return "No Change"

                merged['Trend'] = merged.apply(get_trend, axis=1)
                
                # Show Stalled Orders
                stalled = merged[merged['Trend'].str.contains("STALLED")]
                if not stalled.empty:
                    st.error(f"⚠️ {len(stalled)} Orders Stalled > 7 Days")
                    st.dataframe(stalled[['ServiceOrder', 'Customer', 'Summary', 'Manager']], hide_index=True, use_container_width=True)
                else:
                    st.success("No stalled orders found!")

            # --- MODE 2: DAILY SNAPSHOT ---
            else:
                st.subheader("📅 Daily Snapshot")
                
                # Metrics
                waiting = len(summ_curr[summ_curr['Calc_Status'].str.contains("Waiting")])
                ready = len(summ_curr[summ_curr['Calc_Status'].str.contains("Ready")])
                
                c1, c2 = st.columns(2)
                c1.metric("Waiting for Parts", waiting)
                c2.metric("Ready for Service", ready)
                
                # Main Table
                # Added 'Infor_Status' to the view so you can see if it's Costed/Released
                st.dataframe(
                    summ_curr[['ServiceOrder', 'Customer', 'Calc_Status', 'Summary', 'Infor_Status', 'Manager']], 
                    hide_index=True, 
                    use_container_width=True
                )
                
                # Drill Down
                st.write("---")
                st.subheader("🔍 Drill Down")
                
                issues = summ_curr[summ_curr['Calc_Status'].str.contains("Waiting") | summ_curr['Calc_Status'].str.contains("Pending")]
                
                for order_id in issues['ServiceOrder']:
                    row = issues[issues['ServiceOrder'] == order_id].iloc[0]
                    with st.expander(f"{order_id} - {row['Customer']} ({row['Calc_Status']})"):
                        details = df_curr[df_curr['ServiceOrder'] == order_id]
                        st.table(details[['ItemCode', 'ItemDescription', 'ReqQty', 'ActQty']])

    except Exception as e:
        st.error(f"Error: {e}")

else:
    st.info("👈 Upload Today's File to start.")
