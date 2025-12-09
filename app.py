import streamlit as st
import pandas as pd

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Service Order Financial Tracker", page_icon="💰", layout="wide")

# --- CSS FOR STYLING ---
st.markdown("""
    <style>
    .stAlert { padding: 10px; border-radius: 5px; }
    .big-money { font-size: 24px; font-weight: bold; color: #28a745; }
    </style>
""", unsafe_allow_html=True)

st.title("💰 Logistics & Financial Tracker")

# --- DATA PROCESSING ---
@st.cache_data
def load_data(uploaded_file):
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    # 1. Clean Key Columns
    df = df.dropna(subset=['ServiceOrder'])
    
    # 2. Clean Financials (Remove currency symbols, commas)
    if 'TotalSales' in df.columns:
        df['TotalSales'] = df['TotalSales'].astype(str).str.replace(r'[^\d.-]', '', regex=True)
        df['TotalSales'] = pd.to_numeric(df['TotalSales'], errors='coerce').fillna(0)
    else:
        df['TotalSales'] = 0.0

    # 3. Clean Quantities
    for col in ['ReqQty', 'ActQty']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
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
        summary = f"Missing: {', '.join(missing_parts['ItemDescription'].unique()[:2])}"
        priority = 1
    elif not missing_payment.empty:
        status = "Pending Payment"
        summary = "Waiting for Billing"
        priority = 2
    else:
        status = "Ready"
        summary = "OK"
        priority = 3

    # CRITICAL: We take the MAX of TotalSales for the group, 
    # assuming TotalSales is an Order Header value repeated on lines.
    order_val = group['TotalSales'].max()

    return pd.Series({
        'Customer': group['OwnerName'].iloc[0],
        'Branch': group['Branch'].iloc[0],
        'Manager': group['Manager'].iloc[0],
        'Infor_Status': group['SOStatus'].iloc[0],
        'Quotation_Value': order_val, 
        'Calc_Status': status,
        'Summary': summary,
        'Priority': priority
    })

# --- MAIN APP ---
with st.sidebar:
    st.header("📂 1. Upload Data")
    uploaded_file = st.file_uploader("Upload Infor LN Report", type=['csv', 'xls', 'xlsx'])

if uploaded_file is not None:
    try:
        # Load Data
        df = load_data(uploaded_file)
        
        # --- SIDEBAR FILTERS ---
        with st.sidebar:
            st.divider()
            st.header("🔍 2. Filter Data")
            
            # Helper to get sorted unique lists
            def get_options(col):
                return sorted(df[col].astype(str).unique().tolist())

            # A. Branch Filter
            sel_branch = st.multiselect("Branch", get_options('Branch'))
            
            # B. Manager Filter
            sel_manager = st.multiselect("Manager", get_options('Manager'))
            
            # C. Infor Status Filter
            sel_status = st.multiselect("Infor Status (e.g. Costed)", get_options('SOStatus'))
            
            # D. Customer Filter
            # (Customers list can be huge, so we usually don't select all by default)
            sel_customer = st.multiselect("Customer", get_options('OwnerName'))

        # --- APPLY FILTERS ---
        # We filter the RAW data first
        if sel_branch:
            df = df[df['Branch'].isin(sel_branch)]
        if sel_manager:
            df = df[df['Manager'].isin(sel_manager)]
        if sel_status:
            df = df[df['SOStatus'].isin(sel_status)]
        if sel_customer:
            df = df[df['OwnerName'].isin(sel_customer)]

        # Check if data remains
        if df.empty:
            st.warning("No data matches your filters.")
        else:
            # --- AGGREGATION ---
            # Turn raw lines into "One Row Per Order"
            summary_df = df.groupby('ServiceOrder').apply(classify_order_status).reset_index()
            
            # --- FINANCIAL METRICS ---
            # Sum the 'Quotation_Value' of the UNIQUE orders
            total_value = summary_df['Quotation_Value'].sum()
            total_orders = len(summary_df)
            
            # Calculate breakdown
            costed_val = summary_df[summary_df['Infor_Status'] == 'Costed']['Quotation_Value'].sum()
            open_val = total_value - costed_val
            
            # --- DISPLAY TOP METRICS ---
            st.markdown("### 💵 Financial Summary (Filtered)")
            col1, col2, col3, col4 = st.columns(4)
            
            col1.metric("Total Quotation Value", f"${total_value:,.2f}")
            col2.metric("Total Orders", total_orders)
            col3.metric("Value (Costed)", f"${costed_val:,.2f}")
            col4.metric("Value (In Progress)", f"${open_val:,.2f}")
            
            st.divider()

            # --- DISPLAY TABLE ---
            st.subheader(f"📋 Order Details ({total_orders} orders)")
            
            st.dataframe(
                summary_df[['ServiceOrder', 'Customer', 'Infor_Status', 'Quotation_Value', 'Calc_Status', 'Manager', 'Branch']],
                use_container_width=True,
                column_config={
                    "Quotation_Value": st.column_config.NumberColumn("Value", format="$%.2f"),
                    "ServiceOrder": "Order ID",
                    "Calc_Status": "Parts Status",
                    "Infor_Status": "LN Status"
                },
                hide_index=True
            )
            
            # --- EXPORT BUTTON ---
            # Allow user to download the filtered result
            csv = summary_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Filtered Result",
                csv,
                "filtered_financial_report.csv",
                "text/csv"
            )

    except Exception as e:
        st.error(f"Error: {e}")
        st.write("Ensure your file has columns: TotalSales, ServiceOrder, OwnerName, etc.")

else:
    st.info("👈 Upload your file to start the dashboard.")
