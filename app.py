import streamlit as st
import pandas as pd
import traceback

st.set_page_config(page_title="Debug Mode", layout="wide")
st.title("🛠️ App Debugger")

st.info("This mode will tell us exactly why the file is failing.")

uploaded_file = st.file_uploader("Upload your file", type=['csv', 'xls', 'xlsx'])

if uploaded_file is not None:
    try:
        st.write("1. Attempting to load file...")
        
        # Robust Loader
        if uploaded_file.name.lower().endswith('.csv'):
            df = pd.read_csv(uploaded_file)
            st.success("✅ Loaded as CSV")
        else:
            # Try default first, then specific engines
            try:
                df = pd.read_excel(uploaded_file)
                st.success("✅ Loaded as Excel (Auto-Engine)")
            except Exception as e_default:
                st.warning(f"Default excel engine failed: {e_default}")
                st.write("Trying 'xlrd' engine for older Excel files...")
                df = pd.read_excel(uploaded_file, engine='xlrd')
                st.success("✅ Loaded as Excel (xlrd)")

        st.write(f"2. File has {len(df)} rows.")
        st.write("3. Columns found:", df.columns.tolist())
        
        # Check for required columns
        required = ['ServiceOrder', 'ReqQty', 'ActQty']
        missing = [col for col in required if col not in df.columns]
        
        if missing:
            st.error(f"❌ CRITICAL ERROR: The app cannot find these columns: {missing}")
            st.write("Please check your Excel file header names.")
        else:
            st.success("✅ Critical columns found. Attempting math...")
            
            # Attempt Math
            df['Shortage'] = (pd.to_numeric(df['ReqQty'], errors='coerce').fillna(0) - 
                              pd.to_numeric(df['ActQty'], errors='coerce').fillna(0))
            st.success("✅ Math calculations successful.")
            
            # Show preview
            st.dataframe(df.head())

    except Exception as e:
        st.error("❌ A FATAL ERROR OCCURRED")
        st.code(traceback.format_exc()) # This prints the exact error logic
