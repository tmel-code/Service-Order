import streamlit as st
import pandas as pd

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Service Order Tracker", page_icon="📦", layout="wide")

# --- CSS FOR STYLING ---
st.markdown("""
    <style>
    .stAlert { padding: 10px; border-radius: 5px; }
    .status-waiting { color: #d9534f; font-weight: bold; } 
    .status-payment { color: #f0ad4e; font-weight: bold; } 
    .status-ready { color: #5cb85c; font-weight: bold; } 
    </style>
""", unsafe_allow_html=True)

# --- TITLE ---
st.title("📦 Logistics & Service Order Tracker")
st.markdown("Upload your **Infor LN Export** to generate the daily summary.")

# --- LOGIC FUNCTIONS ---
def classify_order_status(group):
    """
    Analyzes all lines in a Service Order to determine the Overall Status.
    """
    # 1. Calculate Shortages for this specific order
    group['Shortage'] = (group['ReqQty'] - group['ActQty']).clip(lower=0)
    
    # 2. Separate Physical Parts from Billing/Service Items
    def is_billing(desc):
        d = str(desc).upper()
        return any(x in d for x in ['BILLING', 'PAYMENT', 'DEPOSIT', 'FEE'])

    group['Type'] = group['ItemDescription'].apply(lambda x: 'Billing' if is_billing(x) else 'Part')

    # 3. Check for Shortages
    missing_parts = group[(group['Type'] == 'Part') & (group['Shortage'] > 0)]
    missing_payment = group[(group['Type'] == 'Billing') & (group['Shortage'] > 0)]

    # 4. Determine Status Hierarchy
    if not missing_parts.empty:
        status = "🔴 Waiting for Parts"
        items = missing_parts['ItemDescription'].unique()
        summary = f"Missing: {', '.join(items[:2])}"
        if len(items) > 2: summary += ", ..."
        priority = 1
        
    elif not missing_payment.empty:
        status = "🟠 Pending Payment"
        summary = "Service Order generated. Waiting for payment/billing."
        priority = 2
        
    else:
        status = "✅ Ready"
        summary = "All parts allocated & Payment cleared"
        priority = 3

    return pd.Series({
        'Customer': group['OwnerName'].iloc[0],
        'Jobsite': group['Jobsite'].iloc[0],
        'Branch': group['Branch'].iloc[0],
        'Manager': group['Manager'].iloc[0],  # Added Manager Column
        'Overall_Status': status,
        'Summary': summary,
        'Priority': priority,
        'Date': group['OrderDate'].iloc[0]
    })

# --- MAIN APP LOGIC ---

# 1. File Uploader First
uploaded_file = st.file_uploader("Drop your Infor LN Excel/CSV file here", type=['csv', 'xls', 'xlsx'])

if uploaded_file is not None:
    try:
        # Load the file
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Basic Cleanup
        df = df.dropna(subset=['ServiceOrder'])
        
        # Ensure numeric columns
        cols_to_clean = ['ReqQty', 'ActQty']
        for col in cols_to_clean:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # --- DYNAMIC FILTERS (NEW!) ---
        # We put this sidebar logic AFTER loading the file, 
        # so we can scan the file to find the actual Names.
        
        with st.sidebar:
            st.header("🔍 Filters")
            
            # 1. Branch Filter (Auto-detected)
            # We get unique branches from the file, sort them, and add "ALL"
            available_branches = ["ALL"] + sorted(df['Branch'].astype(str).unique().tolist())
            selected_branch = st.selectbox("Filter by Branch:", available_branches)

            # 2. Manager Filter (Auto-detected)
            # We get unique managers from the file
            available_managers = ["ALL"] + sorted(df['Manager'].astype(str).unique().tolist())
            selected_manager = st.selectbox("Filter by Manager:", available_managers)
            
            st.divider()
            st.info("Filters update the dashboard automatically.")

        # --- APPLY FILTERS ---
        # Filter 1: Branch
        if selected_branch != "ALL":
            df = df[df['Branch'].astype(str) == selected_branch]
            
        # Filter 2: Manager
        if selected_manager != "ALL":
            df = df[df['Manager'].astype(str) == selected_manager]

        # Check if data still exists after filtering
        if df.empty:
            st.warning("No orders found matching these filters.")
        else:
            # --- AGGREGATE DATA ---
            summary_df = df.groupby('ServiceOrder').apply(classify_order_status).reset_index()
            summary_df = summary_df.sort_values(by=['Priority', 'ServiceOrder'])

            # --- DISPLAY METRICS ---
            st.divider()
            col1, col2, col3 = st.columns(3)
            
            waiting_count = len(summary_df[summary_df['Overall_Status'].astype(str).str.contains("Waiting")])
            payment_count = len(summary_df[summary_df['Overall_Status'].astype(str).str.contains("Pending")])
            ready_count = len(summary_df[summary_df['Overall_Status'].astype(str).str.contains("Ready")])
            
            col1.metric("🔴 Waiting for Parts", waiting_count)
            col2.metric("🟠 Pending Payment", payment_count)
            col3.metric("✅ Ready for Service", ready_count)

            # --- DISPLAY TABLE ---
            st.subheader(f"📋 Orders for {selected_manager if selected_manager != 'ALL' else 'All Managers'}")
            
            st.dataframe(
                summary_df[['ServiceOrder', 'Customer', 'Overall_Status', 'Summary', 'Manager', 'Branch']],
                use_container_width=True,
                column_config={
                    "ServiceOrder": "Order ID",
                    "Overall_Status": "Status",
                    "Summary": "Action Item",
                },
                hide_index=True
            )

            # --- DRILL DOWN ---
            st.subheader("🔍 Drill Down Details")
            
            problem_orders = summary_df[summary_df['Priority'] < 3]['ServiceOrder'].tolist()
            if not problem_orders:
                st.success("🎉 No issues found! All orders are ready.")
            
            for order_id in problem_orders:
                order_row = summary_df[summary_df['ServiceOrder'] == order_id].iloc[0]
                
                with st.expander(f"**{order_id}** - {order_row['Customer']} ({order_row['Overall_Status']})"):
                    details = df[df['ServiceOrder'] == order_id].copy()
                    details['Shortage'] = (details['ReqQty'] - details['ActQty']).clip(lower=0)
                    
                    def highlight_missing(row):
                        return ['background-color: #ffcccc'] * len(row) if row['Shortage'] > 0 else [''] * len(row)

                    display_cols = ['ItemCode', 'ItemDescription', 'ReqQty', 'ActQty', 'Shortage']
                    st.table(details[display_cols].style.apply(highlight_missing, axis=1))

    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.write("Tip: Ensure your Excel file has columns: 'ServiceOrder', 'Manager', 'Branch', 'ReqQty', 'ActQty'")

else:
    # Sidebar placeholder when no file is uploaded
    with st.sidebar:
        st.header("User Settings")
        st.info("👈 Upload a file to see filters.")
