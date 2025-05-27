import json
import requests
import logging
from bs4 import BeautifulSoup
from collections import defaultdict
from typing import Tuple, Dict, Any, List
from typing import List, Dict, Any, Optional
import re
import time
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import random # For random jitter in sleep

# --- Configuration ---
NCBI_EMAIL = "kbkyeofzdwcccsjzzy@nespj.com"  # Replace with your real email for NCBI API
EUTILS_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
# Adjusted delay to accommodate parallel requests more gently, consider NCBI's guidelines
# For E-utilities, NCBI recommends no more than 3 requests per second without an API key,
# and 10 requests per second with one. Let's aim for a safe default.
REQUEST_DELAY_SECONDS = 0.4 # This was for sequential. For parallel, manage with max_workers.
MAX_WORKERS_GWAS = 10 # Number of parallel threads for GWAS gene searches
MAX_WORKERS_PUBMED = 15 # Number of parallel threads for PubMed abstract fetches

class RAG:
    """
    RAG class for searching GWAS associations and fetching PubMed abstracts.
    """
    def __init__(self) -> None:
        # It's good practice to set up a requests Session for connection pooling
        # if making many requests to the same host.
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': f'Python RAG Module ({NCBI_EMAIL})'})
        # Track processed PubMed IDs to avoid duplicate fetches
        self.processed_pmids = set()

    def _fetch_gwas_docs_for_hugo(self, hugo: str) -> List[Dict[str, Any]]:
        """Helper function to fetch GWAS docs for a single HGNC ID."""
        url = (
            f"https://www.ebi.ac.uk/gwas/api/search?q=(text%3A%22HGNC%3A{hugo}%22+OR+title%3A%22HGNC%3A{hugo}%22+OR+synonyms%3A%22HGNC%3A{hugo}%22)"
            "+AND+-resourcename%3Astudy&generalTextQuery=true&size=100&sort=studyCount,desc"
        )
        try:
            response = self.session.get(url, timeout=15) # Increased timeout slightly
            response.raise_for_status()
            docs = response.json().get('response', {}).get('docs', [])
            results = [
                {'title': doc.get('title'), 'studyCount': doc.get('studyCount')}
                for doc in docs
                if doc.get('title') and doc.get('studyCount', 0) > 10
            ]
            # EBI GWAS API might have rate limits. A small random delay can help.
            time.sleep(random.uniform(0.1, 0.3))
            return results
        except requests.exceptions.RequestException as e:
            logging.warning(f"Failed to fetch GWAS docs for HGNC:{hugo}: {e}")
            return []
        except json.JSONDecodeError:
            logging.warning(f"Failed to decode JSON for HGNC:{hugo}. Response: {response.text[:200]}...")
            return []

    def _fetch_gwas_associations_for_rsid(self, variantInfo: Tuple[str, str, str]) -> List[Dict[str, Any]]:
        """Helper function to fetch detailed GWAS associations for a single rsid."""
        extracted_associations = []
        try:
            rsid = variantInfo[1]
            gene_symbol = variantInfo[0]
            variant_risk_allele = variantInfo[2] # from of single letter: A, C, T etc
            assoc_url = f"https://www.ebi.ac.uk/gwas/api/v2/variants/{rsid}/associations?size=30&page=0&sort=pValue,asc"
            response = self.session.get(assoc_url, timeout=15) # Increased timeout
            response.raise_for_status()
            associations = response.json().get("_embedded", {}).get("associations", [])
            for assoc in associations:
                trait_name = assoc.get("traitName", ["N/A"])
                trait_name = trait_name[0] if trait_name else "N/A"
                beta = assoc.get("beta", "N/A")
                pubmed_id = assoc.get("pubmedId", "N/A")
                risk_allele_info = assoc.get("riskAllele", [])
                risk_allele = (
                    risk_allele_info[0].get("label")
                    if risk_allele_info and risk_allele_info[0].get("label")
                    else (risk_allele_info[0].get("key") if risk_allele_info else "N/A")
                ) # form of id-letter so rs493284902-A

                if risk_allele.split("-")[1] != variant_risk_allele:
                    continue
                p_value_exponent = assoc.get("pValueExponent")
                p_value_base = assoc.get("pValue")
                calculated_p_value = (
                    f"{p_value_base}e{p_value_exponent}" if p_value_exponent is not None and p_value_base is not None else "N/A"
                )
                odds_ratio = assoc.get("orValue") or assoc.get("oddsRatio", "N/A")
                if odds_ratio != "N/A":
                    extracted_associations.append({
                        "traitName": trait_name,
                        "beta": beta,
                        "pubmedId": pubmed_id,
                        "riskAllele": risk_allele,
                        "pValue": calculated_p_value,
                        "OR": odds_ratio
                    })
            time.sleep(random.uniform(0.1, 0.3)) # Small random delay
        except requests.exceptions.RequestException as e:
            logging.warning(f"Failed to fetch associations for rsid {rsid}: {e}")
        except json.JSONDecodeError:
            logging.warning(f"Failed to decode JSON for rsid {rsid}. Response: {response.text[:200]}...")
        return extracted_associations

    def find_damaging_variants_info(self, variants_data):
        """
        Identifies variants with damaging signs from a list of variant data.

        Args:
            variants_data (list): A list of dictionaries, where each dictionary
                                represents a variant and its annotations.

        Returns:
            list: A list of tuples, where each tuple contains (hugo_gene_symbol, rsid)
                for variants deemed potentially damaging. Returns unique pairs.
        """
        damaging_info = set()  # Use a set to store unique (gene_symbol, rsid) tuples

        if not isinstance(variants_data, list):
            print("Error: Input data must be a list of variant objects.")
            return []

        for variant in variants_data:
            if not isinstance(variant, dict):
                print(f"Warning: Skipping non-dictionary item in variants_data: {variant}")
                continue

            rsid = variant.get("id")
            # If the main 'id' (rsID) is missing for the variant, use a placeholder.
            if not rsid:
                # You could try to parse variant.get("input") if it reliably contains the rsID,
                # but it's safer to rely on the structured 'id' field.
                # For now, using a placeholder if 'id' is absent.
                # Example: check 'input' string like: "chr1 247896154 rs12135078 G A"
                input_str_parts = variant.get("input", "").split()
                if len(input_str_parts) > 2 and input_str_parts[2].startswith("rs"):
                    rsid = input_str_parts[2]
                else:
                    rsid = "unknown_rsid"


            transcript_consequences = variant.get("transcript_consequences")
            if not transcript_consequences or not isinstance(transcript_consequences, list):
                continue

            for tc in transcript_consequences:
                if not isinstance(tc, dict):
                    print(f"Warning: Skipping non-dictionary transcript consequence for rsID {rsid}: {tc}")
                    continue

                gene_symbol = tc.get("gene_symbol")
                # If gene_symbol is missing, use a placeholder.
                if not gene_symbol:
                    gene_symbol = "unknown_gene"

                impact = tc.get("impact")
                sift_pred = tc.get("sift_prediction")
                polyphen_pred = tc.get("polyphen_prediction")
                variant_allele = tc.get("variant_allele")

                is_damaging_transcript = False

                # Condition 1: HIGH impact
                if impact == "HIGH":
                    is_damaging_transcript = True
                # Condition 2: MODERATE impact AND SIFT/PolyPhen indicate damage
                elif impact == "MODERATE":
                    if sift_pred == "deleterious" or \
                    polyphen_pred in ["probably_damaging", "possibly_damaging"]:
                        is_damaging_transcript = True
                
                # You could add more lenient conditions if needed, e.g.:
                # elif sift_pred == "deleterious" or \
                #    polyphen_pred in ["probably_damaging", "possibly_damaging"]:
                #     is_damaging_transcript = True # If SIFT/PolyPhen are damaging, regardless of stated impact

                if is_damaging_transcript:
                    damaging_info.add((gene_symbol, rsid, variant_allele))
                    # Once a damaging transcript consequence is found for this gene-variant combination,
                    # we can break from iterating over other TCs for this specific variant if desired,
                    # but iterating through all ensures all affected genes by a variant are caught
                    # if a variant has consequences on multiple genes (rare for SNP, more for SVs).
                    # The set `damaging_info` handles uniqueness.

        return sorted(list(damaging_info))


    def search_annotations(self, annotations_raw: str) -> List[Dict[str, Any]]:
        """
        Search GWAS associations for genes found in VEP annotation using parallel processing.
        Args:
            annotations_raw (str): Raw JSON annotation string.
        Returns:
            List[Dict]: List of association dicts.
        """
        vep_data = json.loads(annotations_raw)
        hugoes = re.findall(r'HGNC:([0-9]+)', annotations_raw)
        hugoes = list(dict.fromkeys(hugoes)) # Ensure unique HGNC IDs
        
        if not hugoes:
            print("No unique HGNC IDs found in the annotations.")
            return []

        print(f"Found {len(hugoes)} unique HGNC IDs to search GWAS for.")
        
        gene_titles_to_process = set() # Use a set to avoid duplicate gene title fetches

        # Step 1: Parallel fetch initial GWAS docs for each HGNC ID
        with ThreadPoolExecutor(max_workers=MAX_WORKERS_GWAS) as executor:
            future_to_hugo = {executor.submit(self._fetch_gwas_docs_for_hugo, hugo): hugo for hugo in hugoes}
            
            for future in tqdm(as_completed(future_to_hugo), total=len(hugoes), desc="Fetching GWAS initial docs"):
                hugo = future_to_hugo[future]
                try:
                    docs = future.result()
                    for doc in docs:
                        if doc.get('title'):
                            gene_titles_to_process.add(doc['title']) # Collect unique gene titles
                except Exception as exc:
                    logging.error(f"Error fetching docs for HGNC:{hugo}: {exc}")
        
        if not gene_titles_to_process:
            print("No gene titles found from initial GWAS searches.")
            return []

        print(f"Found {len(gene_titles_to_process)} unique gene titles to fetch detailed associations for.")
        
        all_extracted_associations = []
        # Step 2: Parallel fetch detailed associations for each unique gene title
        with ThreadPoolExecutor(max_workers=MAX_WORKERS_GWAS) as executor: # Reuse GWAS workers
            future_to_gene_title = {executor.submit(self._fetch_gwas_associations_for_gene, gene_title): gene_title for gene_title in gene_titles_to_process}

            for future in tqdm(as_completed(future_to_gene_title), total=len(gene_titles_to_process), desc="Fetching detailed GWAS associations"):
                gene_title = future_to_gene_title[future]
                try:
                    associations = future.result()
                    if associations:
                        all_extracted_associations.extend(associations)
                except Exception as exc:
                    logging.error(f"Error fetching associations for gene {gene_title}: {exc}")

        return all_extracted_associations

    def _fetch_abstract_from_pubmed_id(self, pubmed_id: str) -> Optional[str]:
        """
        Helper function to fetch abstract text from PubMed by PubMed ID.
        Includes user-agent and respects NCBI E-utilities usage policies.
        """
        try:
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}"
            # Add email to URL params for E-utilities, though requests.get on pubmed.ncbi.nlm.nih.gov
            # doesn't directly use it like eutils.ncbi.nlm.nih.gov
            # For compliance, it's better to use E-utilities directly for abstracts if possible.
            # However, for parsing the HTML, a direct GET to pubmed.ncbi.nlm.nih.gov is common.
            
            # Adding a small random delay for each request to be gentle on PubMed server
            time.sleep(random.uniform(0.1, 0.4))

            response = self.session.get(url, timeout=15) # Increased timeout
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            abstract_tag = soup.find('div', {'class': 'abstract-content'})
            if abstract_tag:
                return abstract_tag.get_text(strip=True)
            else:
                logging.debug(f"No abstract-content tag found for PubMed ID {pubmed_id}")
                return None
        except requests.exceptions.RequestException as e:
            logging.warning(f"Failed to fetch abstract for PubMed ID {pubmed_id}: {e}")
            return None
        except Exception as e:
            logging.warning(f"An unexpected error occurred fetching abstract for PubMed ID {pubmed_id}: {e}")
            return None

    def append_pubmed_abstracts(self, associated_traits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Append PubMed abstracts to each trait in the list using parallel processing.
        Args:
            associated_traits (List[Dict]): List of association dicts.
        Returns:
            List[Dict]: List with 'abstract' field added to each trait.
        """
        pmids_to_fetch = defaultdict(list)
        for trait in associated_traits:
            if 'pubmedId' in trait and trait['pubmedId'] and trait['pubmedId'] != 'N/A':
                pmid = trait['pubmedId']
                if pmid not in self.processed_pmids:
                    pmids_to_fetch[pmid].append(trait)
                    self.processed_pmids.add(pmid)
        
        if not pmids_to_fetch:
            print("No unique PubMed IDs found to fetch abstracts for.")
            return associated_traits

        print(f"Found {len(pmids_to_fetch)} unique PubMed IDs to fetch abstracts for.")
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS_PUBMED) as executor:
            # Submit tasks for unique PubMed IDs
            future_to_pmid = {
                executor.submit(self._fetch_abstract_from_pubmed_id, pmid): pmid
                for pmid in pmids_to_fetch.keys()
            }

            for future in tqdm(as_completed(future_to_pmid), total=len(pmids_to_fetch), desc="Fetching PubMed abstracts"):
                pmid = future_to_pmid[future]
                try:
                    abstract = future.result()
                    # Update all trait entries that share this PubMed ID
                    if pmid in pmids_to_fetch:
                        for trait_ref in pmids_to_fetch[pmid]:
                            trait_ref["abstract"] = abstract
                except Exception as exc:
                    logging.error(f"Error processing future for PMID {pmid}: {exc}")
                    # If an error occurs, set abstract to None for affected traits
                    if pmid in pmids_to_fetch:
                        for trait_ref in pmids_to_fetch[pmid]:
                            trait_ref["abstract"] = None

        return associated_traits

    def fetch_variant_info(self, variant: Tuple[str, str, str]) -> Dict[str, Any]:
        """
        Fetch information about a variant from the Ensembl REST API.
        Args:
            variant (Tuple[str, str, str]): Tuple of (gene_symbol, rsid, variant_allele).
        Returns:
            Dict[str, Any]: Variant information.
        """
        gene_symbol, rsid, variant_allele = variant
        # https://www.ebi.ac.uk/gwas/api/v2/variants/rs3093017/associations?includeChildTraits=false&includeBgTraits=false&size=5&page=0&_=1748291083635
        url = f"https://www.ebi.ac.uk/gwas/api/v2/variants/{rsid}/associations?includeChildTraits=false&includeBgTraits=false&size=5&page=0"
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO) # Set to DEBUG for more verbose output
    
    # Create a dummy annotation.json if it doesn't exist for testing
    try:
        with open("generated_annotation/annotation.json", "r") as f:
            annotations_raw = f.read()
    except FileNotFoundError:
        raise FileNotFoundError("Annotation file not found. Please run VEP first.")

    rag = RAG()

    print("Finding damaging variants")
    damaging_variants = rag.find_damaging_variants_info(json.loads(annotations_raw))
    print(f"Found {len(damaging_variants)} damaging variants.")
    print(damaging_variants[:20])
    print("Fetching variant information in parallel...")
    start_time = time.time()
    
    # Process variants in parallel
    with ThreadPoolExecutor(max_workers=20) as executor:
        # Create a future for each variant
        future_to_variant = {
            executor.submit(rag.fetch_variant_info, variant): variant
            for variant in damaging_variants
        }
        
        # Process results as they complete
        successes = []
        for future in tqdm(as_completed(future_to_variant), total=len(damaging_variants)):
            variant = future_to_variant[future]
            try:
                if future.result() is not None:
                    successes.append(variant)
            except Exception as e:
                logging.warning(f"Error processing variant {variant}: {str(e)}")
    
        end_time = time.time()
        print(f"Found {len(successes)} variants with information (took {end_time - start_time:.2f} seconds).")
        print(successes[:20])

        all_extracted_associations = []
        # Step 2: Parallel fetch detailed associations for each unique gene title
        with ThreadPoolExecutor(max_workers=20) as executor: # Reuse GWAS workers
            # variant[1] gets the rsid only
            future_to_variant = {executor.submit(rag._fetch_gwas_associations_for_rsid, variant): variant for variant in successes}

            for future in tqdm(as_completed(future_to_variant), total=len(successes), desc="Fetching detailed GWAS associations"):
                variant = future_to_variant[future]
                try:
                    associations = future.result()
                    if associations:
                        all_extracted_associations.extend(associations)
                except Exception as exc:
                    logging.error(f"Error fetching associations for rsid {variant}: {exc}")

        print(f"Found {len(all_extracted_associations)} associations.")
        print(all_extracted_associations[:20])

        start_time_pubmed = time.time()
        # Pass only traits that have PubMed IDs to avoid unnecessary processing
        associated_and_abstracts = rag.append_pubmed_abstracts(all_extracted_associations)
        end_time_pubmed = time.time()
        print(f"PubMed abstract fetching completed in {end_time_pubmed - start_time_pubmed:.2f} seconds.")
        print("Found articles (first 5 examples):")
        # Print only a few for brevity
        for i, trait in enumerate(associated_and_abstracts[:5]):
            print(f"- Trait: {trait.get('traitName')}, PMID: {trait.get('pubmedId')}, Abstract Length: {len(trait.get('abstract') or '')} chars")
        if len(associated_and_abstracts) > 5:
            print(f"...and {len(associated_and_abstracts) - 5} more.")

        with open("generated_annotation/final_rag_results_from_rsid_danger.json", "w") as f:
            json.dump(associated_and_abstracts, f, indent=2)
        print(f"Results saved to final_rag_results_from_rsid_danger.json")
    
    # print("Searching GWAS for VEP variants in parallel...")
    # start_time_gwas = time.time()
    # associated_traits = rag.search_annotations(annotations_raw)
    # end_time_gwas = time.time()
    # print(f"GWAS search completed in {end_time_gwas - start_time_gwas:.2f} seconds.")
    
    # # Filter out associations that don't have a pubmedId for abstract fetching
    # traits_with_pmids = [t for t in associated_traits if t.get('pubmedId') and t['pubmedId'] != 'N/A']
    # if not traits_with_pmids:
    #     print("No associations with PubMed IDs found. Skipping abstract fetching.")
    # else:
    #     print("Finding relevant articles in parallel...")
    #     start_time_pubmed = time.time()
    #     # Pass only traits that have PubMed IDs to avoid unnecessary processing
    #     associated_and_abstracts = rag.append_pubmed_abstracts(traits_with_pmids)
    #     end_time_pubmed = time.time()
    #     print(f"PubMed abstract fetching completed in {end_time_pubmed - start_time_pubmed:.2f} seconds.")
    #     print("Found articles (first 5 examples):")
    #     # Print only a few for brevity
    #     for i, trait in enumerate(associated_and_abstracts[:5]):
    #         print(f"- Trait: {trait.get('traitName')}, PMID: {trait.get('pubmedId')}, Abstract Length: {len(trait.get('abstract') or '')} chars")
    #     if len(associated_and_abstracts) > 5:
    #         print(f"...and {len(associated_and_abstracts) - 5} more.")

    #     # You might want to save the final results to a new JSON file
    #     with open("generated_annotation/final_rag_results.json", "w") as f:
    #         json.dump(associated_and_abstracts, f, indent=2)
    #     print(f"Results saved to final_rag_results.json")