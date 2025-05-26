"""
Main Streamlit app for Variant Explain.
Handles file upload, variant annotation, GWAS trait search, and result display.
"""
import streamlit as st
import tempfile
import json
import re
import logging
from typing import Optional, Dict, Any
from streamlit.runtime.uploaded_file_manager import UploadedFile
from parse import VCFParser
from rag import RAG
from agent import Agent

st.set_page_config(
    page_title="Variant Explain",
    page_icon=":dna:"
)

st.markdown("""
# VariantExplain
Welcome to the Variant Explain App! This application helps you analyze and understand genetic variants.
""")

# --- Helper Functions ---
def extract_percentage_and_color(item: Dict[str, Any]) -> tuple[float, str]:
    """
    Extract the percentage and color code based on good/bad status.
    """
    try:
        match = re.search(r'([\d.]+)%', item.get('increase_decrease', ''))
        if match:
            percentage = float(match.group(1))
            color = "green" if item.get('good_or_bad', '').lower() == "good" else "red"
        else:
            percentage = 0.0
            color = "yellow"
    except (ValueError, TypeError, AttributeError):
        percentage = 0.0
        color = "yellow"
    return percentage, color

def display_trait_info(trait_info_with_images: list) -> None:
    """
    Display trait info cards in the Streamlit UI.
    """
    for item in trait_info_with_images:
        percentage, color = extract_percentage_and_color(item)
        col1, col2 = st.columns([1, 3])
        with col1:
            if item.get('image_url'):
                st.image(item['image_url'], width=100)
        with col2:
            title_col, perc_col = st.columns([2, 1])
            with title_col:
                with st.expander(f"#### {item.get('trait_title', '')}", expanded=False):
                    st.write(item.get('details', "No additional details available"))
            with perc_col:
                st.markdown(
                    f"<p style='color: {color}; font-size: 18px;'>{percentage:+.1f}%</p>",
                    unsafe_allow_html=True
                )

def handle_variant_explain(variant_input: UploadedFile) -> Optional[list]:
    """
    Handle the variant explain workflow: VEP annotation, GWAS search, abstract generation.
    """
    try:
        st.write("Generating VEP annotations...")
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
        return abstracts
    except Exception as e:
        logging.error(f"Error in variant explain workflow: {e}")
        st.error(f"An error occurred: {e}")
        return None

# --- Main App Logic ---
variant_input: UploadedFile = st.file_uploader("Upload a VCF file", type="vcf")

st.write("### Variant Analysis")

if st.button("Run Variant Explain") and variant_input:
    abstracts = handle_variant_explain(variant_input)
    if abstracts:
        st.markdown("---")
        st.header("Your info")
        agent = Agent()
        trait_info_with_images = agent.summarise_traits(abstracts)
        display_trait_info(trait_info_with_images)

