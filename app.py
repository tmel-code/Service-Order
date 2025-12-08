import streamlit as st
import pandas as pd

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Service Order Tracker", page_icon="📦", layout="wide")

# --- CSS FOR STYLING ---
st.markdown("""
    <style>
    .stAlert { padding: 10px; border-radius: 5px; }
    .status-waiting { color: #d9534f; font-weight: bold; } /* Red */
    .status-payment { color: #f0ad4e; font-weight: bold; } /* Orange */
    .status-ready { color: #5cb85c; font-weight: bold; } /* Green */
    </style>
""", unsafe_allow_html=True)

# --- TITLE & SIDEBAR ---
st.title("📦 Logistics & Service Order Tracker")
st.markdown("Upload your **Infor LN Export** to generate the daily summary.")

# Sidebar for User Settings
with st.sidebar:
    st.header("User Settings")
    # This simulates your "Designated Group" logic
    # In a real app, this would be auto-detected from login
    selected_branch = st.selectbox(
        "Select Your Branch/Group:",
        ["ALL", "JOHOR", "KUALA LUMPUR", "PENANG", "SABAH"] 
    )
    st.info(f"Viewing orders for: **{selected_branch}**")

# --- LOGIC FUNCTIONS ---

def classify_order_status(group):
    """
    Analyzes all lines in a Service Order to determine the Overall Status.
    """
    # 1. Calculate Shortages for this specific order
    # (Clip ensures we don't get negative numbers if we have extra stock)
    group['Shortage'] = (group['ReqQty'] - group['ActQty']).clip(lower=0)
    
    # 2. Separate Physical Parts from Billing/Service Items
    # We look for keywords like "BILLING", "PAYMENT", "DEPOSIT"
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
        # List top 2 missing parts for the summary
        items = missing_parts['ItemDescription'].unique()
        summary = f"Missing: {', '.join(items[:2])}"
        if len(items) > 2: summary += ", ..."
        priority = 1 # High priority for sorting
        
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
        'Overall_Status': status,
        'Summary': summary,
        'Priority': priority,
        'Date': group['OrderDate'].iloc[0]
    })

# --- MAIN APP LOGIC ---

uploaded_file = st.file_uploader("Drop your Infor LN Excel/CSV file here", type=['csv', 'xls', 'xlsx'])

if uploaded_file is not None:
    try:
        # Load the file
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # Basic Cleanup: Remove rows with no Service Order ID
        df = df.dropna(subset=['ServiceOrder'])

        # Ensure numeric columns are actually numbers (fixes "10 pcs" text issues)
        cols_to_clean = ['ReqQty', 'ActQty']
        for col in cols_to_clean:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # --- STEP 1: FILTER BY GROUP ---
        # If user selected a specific branch (e.g., "JOHOR"), filter raw data first
        if selected_branch != "ALL":
            # Normalize strings to avoid case mismatch (Johor vs JOHOR)
            df = df[df['Branch'].astype(str).str.upper() == selected_branch]

        if df.empty:
            st.warning(f"No orders found for branch: {selected_branch}")
        else:
            # --- STEP 2: AGGREGATE DATA ---
            # Group by Service Order and apply our logic function
            summary_df = df.groupby('ServiceOrder').apply(classify_order_status).reset_index()
            
            # Sort by Priority (Waiting -> Payment -> Ready)
            summary_df = summary_df.sort_values(by=['Priority', 'ServiceOrder'])

            # --- STEP 3: DISPLAY DASHBOARD ---
            
            # Key Metrics
            col1, col2, col3 = st.columns(3)
            # Safe checking for string matches
            waiting_mask = summary_df['Overall_Status'].astype(str).str.contains("Waiting")
            payment_mask = summary_df['Overall_Status'].astype(str).str.contains("Pending")
            ready_mask = summary_df['Overall_Status'].astype(str).str.contains("Ready")

            waiting_count = len(summary_df[waiting_mask])
            payment_count = len(summary_df[payment_mask])
            ready_count = len(summary_df[ready_mask])
            
            col1.metric("🔴 Waiting for Parts", waiting_count)
            col2.metric("🟠 Pending Payment", payment_count)
            col3.metric("✅ Ready for Service", ready_count)

            st.divider()

            # The Main Table
            st.subheader("📋 Order Status Overview")
            
            # We use st.dataframe for a sortable, filterable table
            st.dataframe(
                summary_df[['ServiceOrder', 'Customer', 'Overall_Status', 'Summary', 'Branch']],
                use_container_width=True,
                column_config={
                    "ServiceOrder": "Order ID",
                    "Overall_Status": "Status",
                    "Summary": "Action Item",
                },
                hide_index=True
            )

            # --- STEP 4: DETAILED BREAKDOWN ---
            st.subheader("🔍 Drill Down")
            st.info("Click on an order below to see exactly which parts are missing.")

            # Filter mostly for "Waiting" or "Pending" orders to keep list clean
            problem_orders = summary_df[summary_df['Priority'] < 3]['ServiceOrder'].tolist()
            
            for order_id in problem_orders:
                order_row = summary_df[summary_df['ServiceOrder'] == order_id].iloc[0]
                
                with st.expander(f"**{order_id}** - {order_row['Customer']} ({order_row['Overall_Status']})"):
                    # Get the raw lines for this order
                    details = df[df['ServiceOrder'] == order_id].copy()
                    
                    # Calculate shortage for display
                    details['Shortage'] = (details['ReqQty'] - details['ActQty']).clip(lower=0)
                    
                    # Style the table: Highlight missing items
                    def highlight_missing(row):
                        if row['Shortage'] > 0:
                            return ['background-color: #ffcccc'] * len(row) # Light red
                        return [''] * len(row)

                    display_cols = ['ItemCode', 'ItemDescription', 'ReqQty', 'ActQty', 'Shortage']
                    st.table(details[display_cols].style.apply(highlight_missing, axis=1))

    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
        st.write("Please ensure you uploaded the correct Infor LN CSV/Excel file.")

else:
    st.info("👈 Upload your file in the sidebar to get started.")
