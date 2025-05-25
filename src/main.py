from streamlit.runtime.uploaded_file_manager import UploadedFile
import streamlit as st
import requests
from parse import VCFParser
from rag import RAG
import tempfile
import json

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
    st.header("Abstracts")
    for item in abstracts:
        with st.expander(f"{item['traitName']}"):
            st.write(item)

