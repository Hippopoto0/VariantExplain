from streamlit.runtime.uploaded_file_manager import UploadedFile
import streamlit as st
import requests
from parse import VCFParser
from rag import RAG
import tempfile
import json
import re
from agent import Agent

# Set page title
# st.title("Variant Explain App")

st.set_page_config(
    page_title="Variant Explain",
    page_icon=":dna:"
)

# Add description
st.markdown("""
# VariantExplain
Welcome to the Variant Explain App! This application helps you analyze and understand genetic variants.
""")


# # Add a simple input widget
# with st.sidebar:
#     st.header("Settings")
#     variant_input = st.text_input("Enter variant information:")

# Main content area

variant_input: UploadedFile = st.file_uploader("Upload a VCF file", type="vcf")

st.write("### Variant Analysis")
# if variant_input:
#     st.write(f"You uploaded: {variant_input}")
#     st.write("This is where the analysis results will appear.")

state_title = "Generating output"
if st.button("Run Variant Explain"):
    with st.status(state_title):
        st.write("Generating VEP annotations")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.vcf') as temp_vcf:
            temp_vcf.write(variant_input.read())
            temp_vcf_path = temp_vcf.name
        
        parser = VCFParser(temp_vcf_path)
        
        st.write("Querying GWAS...")
        
        rag = RAG()
        found_traits = rag.search_annotations(json.dumps(parser.annotation))

        st.write("Generating abstracts...")
        abstracts = rag.append_pubmed_abstracts(found_traits)

        st.write("Done!")

# Add a footer
st.markdown("---")

# Abstracts section
if 'abstracts' in locals() and abstracts:
    st.header("Your info")
    agent = Agent()
    trait_info_with_images = agent.summarise_traits(abstracts)
    
    for item in trait_info_with_images:
        # Extract percentage and determine color
        try:
            # Use regex to extract number from text like "18% increase" or "18% decrease"
            match = re.search(r'([\d.]+)%', item['increase_decrease'])
            if match:
                percentage = float(match.group(1))
                # Determine color based on whether it's an increase or decrease
                if item['good_or_bad'] == "Good":
                    color = "green"
                else:
                    color = "red"
            else:
                percentage = 0
                color = "yellow"
        except (ValueError, TypeError, AttributeError):
            percentage = 0
            color = "yellow"
        
        # Create columns for layout
        col1, col2 = st.columns([1, 3])
        
        with col1:
            # Display image if available
            if item['image_url']:
                st.image(item['image_url'], width=100)
        
        with col2:
            # Create columns for title and percentage
            title_col, perc_col = st.columns([2, 1])
            
            with title_col:
                # Create expander with title
                with st.expander(f"#### {item['trait_title']}", expanded=False):
                    # Display details
                    st.write(item['details'] if item['details'] else "No additional details available")
            
            with perc_col:
                # Display percentage with color
                st.markdown(f"<p style='color: {color}; font-size: 18px;'>{percentage:+.1f}%</p>", unsafe_allow_html=True)

