"""
RAG module for retrieving GWAS trait associations and PubMed abstracts.
"""
import json
import requests
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import re
import time
from tqdm import tqdm

NCBI_EMAIL = "kbkyeofzdwcccsjzzy@nespj.com"  # Replace with your real email for NCBI API
EUTILS_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
REQUEST_DELAY_SECONDS = 0.4

class RAG:
    """
    RAG class for searching GWAS associations and fetching PubMed abstracts.
    """
    def __init__(self) -> None:
        pass

    def search_annotations(self, annotations_raw: str) -> List[Dict[str, Any]]:
        """
        Search GWAS associations for genes found in VEP annotation.
        Args:
            annotations_raw (str): Raw JSON annotation string.
        Returns:
            List[Dict]: List of association dicts.
        """
        vep_data = json.loads(annotations_raw)
        GWAS_data = []
        hugoes = re.findall(r'HGNC:([0-9]+)', annotations_raw)
        hugoes = list(dict.fromkeys(hugoes))
        print(f"Found {len(hugoes)} unique genes to search GWAS for.")
        for hugo in tqdm(hugoes):
            url = (
                f"https://www.ebi.ac.uk/gwas/api/search?q=(text%3A%22HGNC%3A{hugo}%22+OR+title%3A%22HGNC%3A{hugo}%22+OR+synonyms%3A%22HGNC%3A{hugo}%22)"
                "+AND+-resourcename%3Astudy&generalTextQuery=true&size=100&sort=studyCount,desc"
            )
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                docs = response.json()['response']['docs']
            except Exception as e:
                logging.warning(f"Failed to fetch GWAS docs for HGNC:{hugo}: {e}")
                continue
            results = [
                {'title': doc.get('title'), 'studyCount': doc.get('studyCount')}
                for doc in docs
                if doc.get('title') and doc.get('studyCount', 0) > 10
            ]
            GWAS_data.append(results)
        extracted_associations = []
        for gene_and_title in GWAS_data:
            if not gene_and_title:
                continue
            gene = gene_and_title[0]['title']
            try:
                assoc_url = f"https://www.ebi.ac.uk/gwas/api/v2/genes/{gene}/associations?size=30&page=0&sort=pValue,asc"
                response = requests.get(assoc_url, timeout=10)
                response.raise_for_status()
                associations = response.json().get("_embedded", {}).get("associations", [])
            except Exception as e:
                logging.warning(f"Failed to fetch associations for gene {gene}: {e}")
                continue
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
                )
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
        return extracted_associations

    def append_pubmed_abstracts(self, associated_traits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Append PubMed abstracts to each trait in the list.
        Args:
            associated_traits (List[Dict]): List of association dicts.
        Returns:
            List[Dict]: List with 'abstract' field added to each trait.
        """
        for trait in associated_traits:
            pmid = trait.get("pubmedId")
            if pmid and pmid != "N/A":
                trait["abstract"] = self.fetch_abstract_from_pubmed_id(pmid)
            else:
                trait["abstract"] = None
        return associated_traits

    def fetch_abstract_from_pubmed_id(self, pubmed_id: str) -> str:
        """
        Fetch abstract text from PubMed by PubMed ID.
        Args:
            pubmed_id (str): PubMed ID.
        Returns:
            str: Abstract text or None.
        """
        try:
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            abstract_tag = soup.find('div', {'class': 'abstract-content'})
            if abstract_tag:
                return abstract_tag.get_text(strip=True)
        except Exception as e:
            logging.warning(f"Failed to fetch abstract for PubMed ID {pubmed_id}: {e}")
        return None

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    with open("generated_annotation/annotation.json", "r") as f:
        annotations_raw = f.read()
    rag = RAG()
    print("Searching GWAS for VEP variants...")
    associated_traits = rag.search_annotations(annotations_raw)
    print("Finding relevant articles...")
    associated_and_abstracts = rag.append_pubmed_abstracts(associated_traits)
    print("Found articles:")
    print(associated_and_abstracts)
