import streamlit as st
import requests
from streamlit_chat import message

# Set page title
st.title("Variant Explain App")

# st.set_page_config(
#     page_title="Variant Explain",
#     page_icon=":robot:"
# )

# Add description
st.markdown("""
Welcome to the Variant Explain App! This application helps you analyze and understand genetic variants.
""")

# # Add a simple input widget
# with st.sidebar:
#     st.header("Settings")
#     variant_input = st.text_input("Enter variant information:")

# Main content area

st.write("### Variant Analysis")
if variant_input:
    st.write(f"You entered: {variant_input}")
    st.write("This is where the analysis results will appear.")

st.status("Variant Explain is running", state="running")


# Add a footer
st.markdown("---")
footer = """
Created with Streamlit 🎈
"""
st.markdown(footer)