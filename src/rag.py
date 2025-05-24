import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any

NCBI_EMAIL = "kbkyeofzdwcccsjzzy@nespj.com" # <--- IMPORTANT: Change this to your email
EUTILS_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

class RAG:
    def __init__(self):
        pass
    
    def search_annotations(self, annotations_raw: str):
        vep_data = json.loads(annotations_raw)
        retrieved_articles_by_variant = {}

        print("Searching PubMed for VEP variants...")

        for i, variant in enumerate(vep_data):
            chrom = variant.get("seq_region_name")
            start = variant.get("start")
            end = variant.get("end") # Can use end for deletions or broader range
            consequence = variant.get("most_severe_consequence")

            if not chrom or not start:
                print(f"Skipping variant {i} due to missing chromosome or start position.")
                continue

            # Construct a robust query for intergenic variants
            # Add common terms for intergenic regions
            query_terms = [
                f"chromosome {chrom}",
                f"position {start}", # More specific
                f"intergenic variant",
                "non-coding",
                "regulatory",
                "enhancer",
                "promoter",
                "eQTL",
                "disease susceptibility",
                "GWAS"
            ]
            pubmed_query = " AND ".join(query_terms)

            print(f"\n--- Processing Variant {i+1} (Chr {chrom}, Pos {start}, Consequence: {consequence}) ---")
            print(f"PubMed Query: '{pubmed_query}'")

            pmids = self.search_pubmed(pubmed_query, retmax=5) # Limit to 5 articles per variant
            if pmids:
                print(f"Found {len(pmids)} PMIDs: {pmids}")
                articles = fetch_pubmed_articles(pmids)
                retrieved_articles_by_variant[f"chr{chrom}:{start}-{end}"] = articles
                for article in articles:
                    print(f"  - PMID: {article['pmid']}, Year: {article['publication_year']}, Title: {article['title']}")
            else:
                print("No articles found for this variant.")

        print("\n--- Summary of Retrieved Articles ---")
        for variant_id, articles in retrieved_articles_by_variant.items():
            print(f"\nVariant: {variant_id}")
            if articles:
                for article in articles:
                    print(f"  PMID: {article['pmid']}, Title: {article['title']}")
                    print(f"  Abstract (excerpt): {article['abstract'][:200]}...") # Print first 200 chars
            else:
                print("  No articles found.")


    def search_pubmed(self, query: str, retmax: int = 5) -> List[str]:
        """
        Searches PubMed for articles and returns a list of PMIDs using BeautifulSoup.
        """
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": retmax,
            "retmode": "xml",
            "email": NCBI_EMAIL
        }
        esearch_url = f"{EUTILS_BASE_URL}esearch.fcgi"
        try:
            response = requests.get(esearch_url, params=params)
            response.raise_for_status() # Raise an exception for HTTP errors

            # Use BeautifulSoup to parse the XML
            soup = BeautifulSoup(response.content, 'xml') # Specify 'xml' parser for XML content

            pmids = [id_tag.text for id_tag in soup.find_all('Id')]
            return pmids
        except requests.exceptions.RequestException as e:
            print(f"Error searching PubMed: {e}")
            return []
        except Exception as e: # Catch BeautifulSoup parsing errors too
            print(f"Error parsing ESearch XML with BeautifulSoup: {e}")
            print(f"Response content: {response.content.decode()}")
            return []

    def fetch_pubmed_articles(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetches details (title, abstract, year) for a list of PMIDs using BeautifulSoup.
        """
        if not pmids:
            return []

        pmid_str = ",".join(pmids)
        params = {
            "db": "pubmed",
            "id": pmid_str,
            "retmode": "xml",
            "rettype": "abstract",
            "email": NCBI_EMAIL
        }
        efetch_url = f"{EUTILS_BASE_URL}efetch.fcgi"
        articles_data = []
        try:
            response = requests.get(efetch_url, params=params)
            response.raise_for_status() # Raise an exception for HTTP errors

            # Use BeautifulSoup to parse the XML
            soup = BeautifulSoup(response.content, 'xml') # Specify 'xml' parser

            for article_tag in soup.find_all('PubmedArticle'):
                pmid_tag = article_tag.find('PMID')
                title_tag = article_tag.find('ArticleTitle')
                abstract_text_tags = article_tag.find_all('AbstractText')
                journal_title_tag = article_tag.find('Journal').find('Title') if article_tag.find('Journal') else None
                # Extract year, trying a couple of common XML paths for PubDate
                pub_year_tag = article_tag.find('PubDate').find('Year') if article_tag.find('PubDate') else None
                if not pub_year_tag: # Fallback for MedlineDate if Year isn't direct
                    pub_year_tag = article_tag.find('PubDate').find('MedlineDate') if article_tag.find('PubDate') else None


                pmid_val = pmid_tag.text if pmid_tag else "N/A"
                article_title = title_tag.text if title_tag else "N/A"
                # Join all abstract text elements, handling cases where they might be split
                abstract = "\n".join([at.text for at in abstract_text_tags if at.text]) if abstract_text_tags else "N/A"
                journal = journal_title_tag.text if journal_title_tag else "N/A"
                year = pub_year_tag.text if pub_year_tag else "N/A"
                # If MedlineDate was used (e.g., "2024 Spring"), try to extract just the year
                if year != "N/A" and len(year) > 4 and any(c.isalpha() for c in year):
                    year = year.split(' ')[0] # Take the first part, usually the year

                articles_data.append({
                    "pmid": pmid_val,
                    "title": article_title,
                    "abstract": abstract,
                    "journal": journal,
                    "publication_year": year
                })
            return articles_data
        except requests.exceptions.RequestException as e:
            print(f"Error fetching PubMed articles: {e}")
            return []
        except Exception as e: # Catch BeautifulSoup parsing errors too
            print(f"Error parsing EFetch XML with BeautifulSoup: {e}")
            print(f"Response content: {response.content.decode()}")
            return []

            

# --- Your VEP Data (example snippet) ---
annotations_raw = """
[
  {
    "assembly_name": "GRCh38",
    "intergenic_consequences": [
      {
        "impact": "MODIFIER",
        "variant_allele": "-",
        "consequence_terms": [
          "intergenic_variant"
        ]
      }
    ],
    "start": 101,
    "id": ".",
    "strand": 1,
    "input": "1 100 . GTTT G",
    "seq_region_name": "1",
    "end": 103,
    "allele_string": "TTT/-",
    "most_severe_consequence": "intergenic_variant"
  },
  {
    "most_severe_consequence": "intergenic_variant",
    "allele_string": "C/T",
    "end": 105,
    "input": "1 105 . C T",
    "seq_region_name": "1",
    "strand": 1,
    "id": ".",
    "start": 105,
    "intergenic_consequences": [
      {
        "impact": "MODIFIER",
        "variant_allele": "T",
        "consequence_terms": [
          "intergenic_variant"
        ]
      }
    ],
    "assembly_name": "GRCh38"
  },
  {
    "id": ".",
    "strand": 1,
    "input": "1 106 . C A",
    "seq_region_name": "1",
    "start": 106,
    "intergenic_consequences": [
      {
        "consequence_terms": [
          "intergenic_variant"
        ],
        "variant_allele": "A",
        "impact": "MODIFIER"
      }
    ],
    "assembly_name": "GRCh38",
    "most_severe_consequence": "intergenic_variant",
    "allele_string": "C/A",
    "end": 106
  },
  {
    "assembly_name": "GRCh38",
    "intergenic_consequences": [
      {
        "consequence_terms": [
          "intergenic_variant"
        ],
        "impact": "MODIFIER",
        "variant_allele": "G"
      }
    ],
    "start": 110,
    "seq_region_name": "2",
    "id": ".",
    "strand": 1,
    "input": "2 110 . A G",
    "end": 110,
    "allele_string": "A/G",
    "most_severe_consequence": "intergenic_variant"
  }
]
"""


if __name__ == '__main__':
    
    rag = RAG()
    rag.search_annotations(annotations_raw)

