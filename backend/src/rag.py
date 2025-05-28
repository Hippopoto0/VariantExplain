import json
import requests
import logging
from bs4 import BeautifulSoup
from collections import defaultdict
from typing import Tuple, Dict, Any, List, Optional
import re
import time
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import random # For random jitter in sleep
from models import parse_trait_summary

# --- Configuration ---
NCBI_EMAIL = "kbkyeofzdwcccsjzzy@nespj.com"  # Replace with your real email for NCBI API
# Adjusted to align with original script's likely parallelism for GWAS calls
MAX_WORKERS_GWAS = 20
MAX_WORKERS_PUBMED = 15 # This seemed consistent with original intent

# File paths
VEP_ANNOTATION_FILE = "generated_annotation/annotation.json"
OUTPUT_RESULTS_FILE = "generated_annotation/gwas_associations_with_abstracts_optimized.json"

class RAG:
    """
    RAG class for identifying damaging variants from VEP output, searching GWAS catalog
    associations for these variants, and fetching corresponding PubMed abstracts.
    """
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': f'Python RAG Module ({NCBI_EMAIL})'})
        self.processed_pmids = set()

    def _fetch_gwas_associations_for_rsid(self, variant_details: Tuple[str, str, str]) -> List[Dict[str, Any]]:
        extracted_associations = []
        gene_symbol, rsid, vep_risk_allele = variant_details
        
        if not vep_risk_allele:
            logging.debug(f"Skipping rsID {rsid} for gene {gene_symbol} due to missing VEP risk allele.")
            return []

        assoc_url = f"https://www.ebi.ac.uk/gwas/api/v2/variants/{rsid}/associations?size=30&page=0&sort=pValue,asc"
        
        try:
            # Adjusted sleep to align with original script's likely delay
            time.sleep(random.uniform(0.1, 0.3))
            response = self.session.get(assoc_url, timeout=20)
            response.raise_for_status()
            data = response.json()
            associations = data.get("_embedded", {}).get("associations", [])

            for assoc in associations:
                trait_info_list = assoc.get("traitName", [])
                trait_name = trait_info_list[0] if trait_info_list else "N/A"
                
                beta_object = assoc.get("beta")
                beta_value = "N/A"
                if isinstance(beta_object, dict):
                    beta_value = beta_object.get("betaValue", "N/A")
                elif isinstance(beta_object, (int, float)):
                    beta_value = beta_object

                pubmed_id = assoc.get("pubmedId", "N/A")
                
                api_reported_alleles = assoc.get("riskAllele", [])
                is_correct_risk_allele_for_assoc = False
                matched_api_allele_representation = "N/A"

                if not api_reported_alleles:
                    logging.debug(f"No risk allele info in GWAS association for rsID {rsid}, trait '{trait_name}'. Skipping entry.")
                    continue

                for ra_obj in api_reported_alleles:
                    allele_char_from_key = ra_obj.get("key") 
                    allele_char_from_label = None
                    label_val = ra_obj.get("label")

                    if label_val:
                        if '-' in label_val:
                            allele_char_from_label = label_val.split('-')[-1]
                        else:
                            allele_char_from_label = label_val
                    
                    if allele_char_from_key == vep_risk_allele:
                        is_correct_risk_allele_for_assoc = True
                        matched_api_allele_representation = label_val or allele_char_from_key
                        break
                    if allele_char_from_label == vep_risk_allele:
                        is_correct_risk_allele_for_assoc = True
                        matched_api_allele_representation = label_val
                        break
                
                if not is_correct_risk_allele_for_assoc:
                    continue

                p_value_exponent = assoc.get("pValueExponent")
                p_value_mantissa = assoc.get("pValue")
                calculated_p_value = (
                    f"{p_value_mantissa}e{p_value_exponent}" if p_value_exponent is not None and p_value_mantissa is not None else "N/A"
                )
                
                odds_ratio = assoc.get("orValue")
                if odds_ratio is None:
                    odds_ratio = assoc.get("oddsRatio", "N/A")

                if odds_ratio != "N/A" or (isinstance(beta_value, (int, float))):
                    extracted_associations.append({
                        "traitName": trait_name,
                        "beta": beta_value,
                        "pubmedId": pubmed_id,
                        "riskAllele_GWAS": matched_api_allele_representation,
                        "pValue": calculated_p_value,
                        "OR": odds_ratio,
                        "gene_symbol_from_vep": gene_symbol,
                        "rsid_from_vep": rsid,
                        "risk_allele_from_vep": vep_risk_allele
                    })
            
        except requests.exceptions.RequestException as e:
            logging.warning(f"Request failed for GWAS associations for rsID {rsid} (Gene: {gene_symbol}): {e}")
        except json.JSONDecodeError:
            # It's good to see the response text if JSON decoding fails
            response_text = "N/A"
            if 'response' in locals() and hasattr(response, 'text'):
                response_text = response.text[:200]
            logging.warning(f"JSON decode failed for GWAS associations for rsID {rsid} (Gene: {gene_symbol}). Response: {response_text}...")
        return extracted_associations

    def find_damaging_variants_info(self, variants_data: List[Dict[str, Any]]) -> List[Tuple[str, str, str]]:
        damaging_info = set()
        if not isinstance(variants_data, list):
            logging.error("Input VEP data must be a list of variant objects.")
            return []

        for variant in variants_data:
            if not isinstance(variant, dict):
                logging.warning(f"Skipping non-dictionary item in variants_data: {variant}")
                continue

            rsid = variant.get("id")
            if not rsid or not rsid.startswith("rs"):
                input_str_parts = variant.get("input", "").split()
                if len(input_str_parts) > 2 and input_str_parts[2].startswith("rs"):
                    rsid = input_str_parts[2]
                else:
                    continue

            transcript_consequences = variant.get("transcript_consequences")
            if not transcript_consequences or not isinstance(transcript_consequences, list):
                continue

            for tc in transcript_consequences:
                if not isinstance(tc, dict):
                    logging.warning(f"Skipping non-dictionary transcript consequence for rsID {rsid}: {tc}")
                    continue

                gene_symbol = tc.get("gene_symbol")
                variant_allele = tc.get("variant_allele")

                if not gene_symbol or not variant_allele:
                    continue

                impact = tc.get("impact")
                sift_pred = tc.get("sift_prediction")
                polyphen_pred = tc.get("polyphen_prediction")
                
                is_damaging_transcript = False
                if impact == "HIGH":
                    is_damaging_transcript = True
                elif impact == "MODERATE":
                    if sift_pred == "deleterious" or \
                       polyphen_pred in ["probably_damaging", "possibly_damaging"]:
                        is_damaging_transcript = True
                
                if is_damaging_transcript:
                    damaging_info.add((gene_symbol, rsid, variant_allele))
        
        return sorted(list(damaging_info))

    def _fetch_abstract_from_pubmed_id(self, pubmed_id: str) -> Optional[str]:
        if not pubmed_id or pubmed_id == 'N/A':
            return None
        try:
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/"
            # Adjusted sleep to align with original script's likely delay
            time.sleep(random.uniform(0.1, 0.4))

            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            abstract_div = soup.find('div', {'class': 'abstract-content selected'})
            if not abstract_div:
                abstract_div = soup.find('div', id='abstract') 
            if not abstract_div:
                 abstract_div = soup.find('div', class_=re.compile(r'\babstract\b', re.I))

            if abstract_div:
                text_parts = [p.get_text(strip=True) for p in abstract_div.find_all(['p', 'strong'])]
                full_abstract = "\n".join(filter(None, text_parts))
                return full_abstract if full_abstract else None
            else:
                logging.debug(f"No abstract content found for PubMed ID {pubmed_id} using common selectors.")
                return None
        except requests.exceptions.RequestException as e:
            logging.warning(f"Request failed for PubMed ID {pubmed_id}: {e}")
            return None
        except Exception as e:
            logging.warning(f"Unexpected error fetching abstract for PubMed ID {pubmed_id}: {e}")
            return None

    def append_pubmed_abstracts(self, gwas_associations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pmids_to_fetch_map = defaultdict(list)
        for assoc_item in gwas_associations:
            pmid = assoc_item.get('pubmedId')
            if pmid and pmid != 'N/A' and pmid not in self.processed_pmids:
                pmids_to_fetch_map[pmid].append(assoc_item)
            # Ensure 'abstract' key exists even if pmid is invalid/processed or already fetched
            if 'abstract' not in assoc_item: 
                 assoc_item['abstract'] = None # Default to None
        
        if not pmids_to_fetch_map:
            logging.info("No new unique PubMed IDs to fetch abstracts for in this batch.")
            return gwas_associations

        unique_pmids_list = list(pmids_to_fetch_map.keys())
        logging.info(f"Fetching abstracts for {len(unique_pmids_list)} new unique PubMed IDs.")
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS_PUBMED) as executor:
            future_to_pmid = {
                executor.submit(self._fetch_abstract_from_pubmed_id, pmid): pmid
                for pmid in unique_pmids_list
            }
            
            # Initialize thread-safe counter for completed fetches
            from threading import Lock
            completed_count = 0
            counter_lock = Lock()
            total_pmids = len(unique_pmids_list)

            def update_progress():
                nonlocal completed_count
                with counter_lock:
                    completed_count += 1
                    progress = int((completed_count / total_pmids) * 100)
                    self._update_progress("fetch_pubmed_abstracts", progress, 100, "in_progress")

            for future in tqdm(as_completed(future_to_pmid), total=total_pmids, desc="Fetching PubMed abstracts"):
                pmid = future_to_pmid[future]
                update_progress()
                try:
                    abstract = future.result()
                    self.processed_pmids.add(pmid) # Mark as processed (even if abstract is None)
                    for assoc_item_ref in pmids_to_fetch_map[pmid]:
                        assoc_item_ref["abstract"] = abstract
                except Exception as exc:
                    logging.error(f"Error processing abstract future for PMID {pmid}: {exc}")
                    for assoc_item_ref in pmids_to_fetch_map[pmid]: # Ensure abstract is None on error
                        assoc_item_ref["abstract"] = None
        
        return gwas_associations

    def _update_progress(self, step: str, current: int, total: int, status: str = "in_progress") -> None:
        """Update the progress file with the current step's progress."""
        progress = {
            "step": step,
            "current": current,
            "total": total,
            "percentage": round(100 * current / total, 1) if total > 0 else 0,
            "status": status,
            "timestamp": time.time()
        }
        progress_file = "generated_annotation/rag_progress.json"
        try:
            with open(progress_file, "w") as pf:
                json.dump(progress, pf)
        except Exception as e:
            logging.error(f"Failed to write progress file: {e}")

    def process_vep_data(self, vep_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        logging.info("Initiating VEP data processing workflow...")
        
        # Initialize progress tracking - use vep_annotation as the initial status
        self._update_progress("vep_annotation", 0, 1, "in_progress")
        
        logging.info("Identifying potentially damaging variants...")
        self._update_progress("find_damaging_variants", 0, 1, "in_progress")
        damaging_variant_tuples = self.find_damaging_variants_info(vep_data)
        num_variants = len(damaging_variant_tuples)
        logging.info(f"Found {num_variants} potentially damaging variant tuples (gene, rsID, allele).")
        
        if not damaging_variant_tuples:
            logging.info("No damaging variants found. Terminating process.")
            self._update_progress("vep_annotation", 0, 0, "completed")
            self._update_progress("find_damaging_variants", 0, 0, "completed")
            self._update_progress("fetch_gwas_associations", 0, 0, "skipped")
            self._update_progress("fetch_pubmed_abstracts", 0, 0, "skipped")
            return []
            
        logging.info(f"Sample damaging variants (first 3 if available): {damaging_variant_tuples[:3]}")

        # Process GWAS associations
        logging.info(f"Fetching GWAS associations using up to {MAX_WORKERS_GWAS} workers...")
        all_gwas_associations = []
        completed_variants = 0
        
        # Update status to fetch_gwas_associations
        self._update_progress("fetch_gwas_associations", 0, num_variants, "in_progress")
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS_GWAS) as executor:
            future_to_variant_tuple = {
                executor.submit(self._fetch_gwas_associations_for_rsid, vt): vt 
                for vt in damaging_variant_tuples
            }
            for future in tqdm(as_completed(future_to_variant_tuple), total=len(damaging_variant_tuples), desc="Fetching GWAS associations"):
                variant_tuple_key = future_to_variant_tuple[future]
                completed_variants += 1
                self._update_progress("fetch_gwas_associations", completed_variants, num_variants, "in_progress")
                
                try:
                    associations_for_variant = future.result()
                    if associations_for_variant:
                        all_gwas_associations.extend(associations_for_variant)
                except Exception as exc:
                    logging.error(f"Error processing future for variant {variant_tuple_key} during GWAS fetch: {exc}")
        
        logging.info(f"Fetched a total of {len(all_gwas_associations)} GWAS associations.")
        self._update_progress("fetch_gwas_associations", completed_variants, num_variants, "completed")

        if not all_gwas_associations:
            logging.info("No relevant GWAS associations found for the damaging variants after filtering. Terminating process.")
            self._update_progress("fetch_pubmed_abstracts", 0, 0, "skipped")
            return []
            
        logging.info(f"Sample GWAS associations (first 1 if available): {all_gwas_associations[:1]}")

        # Process PubMed abstracts
        logging.info(f"Appending PubMed abstracts using up to {MAX_WORKERS_PUBMED} workers...")
        
        if all_gwas_associations:
            # Update status to fetch_pubmed_abstracts
            self._update_progress("fetch_pubmed_abstracts", 0, len(all_gwas_associations), "in_progress")
            
            results_with_abstracts = self.append_pubmed_abstracts(all_gwas_associations)
            
            num_with_abstracts = sum(1 for item in results_with_abstracts if item.get('abstract'))
            logging.info(f"PubMed abstract processing complete. {num_with_abstracts} out of {len(results_with_abstracts)} associations now have abstract data (or attempted fetch).")
            
            self._update_progress("fetch_pubmed_abstracts", len(results_with_abstracts), len(results_with_abstracts), "completed")
        else:
            logging.info("No GWAS associations to process PubMed abstracts for.")
            results_with_abstracts = []
            self._update_progress("fetch_pubmed_abstracts", 0, 0, "completed")
        # --- Summarise Traits and Fetch Images ---
        from agent import Agent
        agent = Agent()
        self._update_progress("summarise_traits", 0, 1, "in_progress")
        try:
            trait_summaries = agent.summarise_traits(results_with_abstracts)
            self._update_progress("summarise_traits", 1, 1, "completed")

            trait_summaries_as_models = [parse_trait_summary(ts) for ts in trait_summaries]
        except Exception as e:
            logging.error(f"Trait summarisation failed: {e}")
            self._update_progress("summarise_traits", 0, 1, "error")
            trait_summaries_as_models = []

        self._update_progress("completed", 1, 1, "completed")
        return trait_summaries_as_models

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    
    vep_data_from_file = []
    try:
        with open(VEP_ANNOTATION_FILE, "r") as f:
            vep_output_json_str = f.read()
        vep_data_from_file = json.loads(vep_output_json_str)
    except FileNotFoundError:
        logging.error(f"VEP annotation file not found: {VEP_ANNOTATION_FILE}. Please ensure it exists.")
        exit(1)
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON in VEP annotation file: {VEP_ANNOTATION_FILE}.")
        exit(1)

    rag_handler = RAG()
    
    logging.info(f"Starting RAG processing for VEP data from {VEP_ANNOTATION_FILE}...")
    start_time_total = time.time()
    final_results = rag_handler.process_vep_data(vep_data_from_file)
    end_time_total = time.time()
    logging.info(f"Total RAG processing time: {end_time_total - start_time_total:.2f} seconds.")
    
    if final_results:
        logging.info(f"Processing complete. Obtained {len(final_results)} final association records.")
        logging.info("Sample results (first 2 examples, if available):")
        for i, item in enumerate(final_results[:2]):
            abstract_len = len(item.get('abstract') or '')
            logging.info(f"  - Trait: {item.get('traitName')}, PMID: {item.get('pubmedId')}, Gene (VEP): {item.get('gene_symbol_from_vep')}, Abstract Length: {abstract_len} chars")
        if len(final_results) > 2:
            logging.info(f"  ...and {len(final_results) - 2} more processed associations.")

        try:
            with open(OUTPUT_RESULTS_FILE, "w") as f:
                json.dump(final_results, f, indent=2)
            logging.info(f"All results saved to {OUTPUT_RESULTS_FILE}")
        except IOError as e:
            logging.error(f"Could not write results to {OUTPUT_RESULTS_FILE}: {e}")
    else:
        logging.info("Processing complete. No results were generated or all processing paths led to empty data.")