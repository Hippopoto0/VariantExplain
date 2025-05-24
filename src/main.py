import streamlit as st

# Set page title
st.title("Variant Explain App")

# Add description
st.markdown("""
Welcome to the Variant Explain App! This application helps you analyze and understand genetic variants.

## Features
- Basic variant analysis
- Visualization tools
- Data exploration
""")

# Add a simple input widget
with st.sidebar:
    st.header("Settings")
    variant_input = st.text_input("Enter variant information:")

# Main content area
st.write("### Variant Analysis")
if variant_input:
    st.write(f"You entered: {variant_input}")
    st.write("This is where the analysis results will appear.")

# Add a footer
st.markdown("---")
footer = """
Created with Streamlit 🎈
"""
st.markdown(footer)