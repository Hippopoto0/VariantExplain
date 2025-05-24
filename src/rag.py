import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import time

NCBI_EMAIL = "kbkyeofzdwcccsjzzy@nespj.com" # <--- IMPORTANT: Change this to your email
EUTILS_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

REQUEST_DELAY_SECONDS = 0.4 # Slightly more than 1/3 for safety

class RAG:
    def __init__(self):
        pass

    def search_annotations(self, annotations_raw: str):
        vep_data = json.loads(annotations_raw)
        GWAS_data = []

        print("Searching GWAS for VEP variants...")
        
        hugoes = []
        import re
        hugoes = re.findall(r'HGNC:([0-9]+)', annotations_raw)
        hugoes = list(set(hugoes))

        for hugo in hugoes[:10]:
            print(f"Searching GWAS for {hugo}...")
            # something like this https://www.ebi.ac.uk/gwas/search?query=HGNC:8977
            # that renders dynamically, but gets request from here
            # https://www.ebi.ac.uk/gwas/api/search?q=(text%3A%22HGNC%3A12500%22+OR+title%3A%22HGNC%3A12500%22+OR+synonyms%3A%22HGNC%3A12500%22)+AND+-resourcename%3Astudy&generalTextQuery=true

            # format like this - note title, study count found in responseHeader.
            # {"responseHeader":{"status":0,"QTime":0,"params":{"q":"(text:\"HGNC:12500\" OR title:\"HGNC:12500\" OR synonyms:\"HGNC:12500\") AND -resourcename:study","facet.field":"resourcename","defType":"edismax","qf":"title^2.0 synonyms^20.0 parent^2.0 text^1.0","start":"0","rows":"1000","wt":"json","facet":"true"}},"response":{"numFound":1,"start":0,"docs":[{"resourcename":"gene","id":"gene:ENSG00000130939","ensemblID":"ENSG00000130939","rsIDs":["rs77954449","rs11121525","rs11806008","rs12144133","rs3828081","rs11801734","rs61782937","rs149622283","rs7539725","rs113304383","rs12092513","rs6661326","rs6696978","rs139279718","rs61782892","rs187585530","rs4333851","rs115486679","rs3903151"],"studyCount":27,"associationCount":31,"chromosomeStart":10032832,"chromosomeEnd":10181239,"chromosomeName":"1","biotype":"protein_coding","title":"UBE4B","ensemblDescription":"ubiquitination factor E4B","crossRefs":"HGNC:12500|OTTHUMG00000001797|uc001aqr.5|AF091093|NM_006048|MGI:1927086|O95155","entrez_id":"10277","cytobands":"1p36.22","description":"ubiquitination factor E4B|1:10032832-10181239|1p36.22|protein_coding","_version_":1831968093979541507}]},"facet_counts":{"facet_queries":{},"facet_fields":{"resourcename":["gene",1,"publication",0,"study",0,"trait",0,"variant",0]},"facet_dates":{},"facet_ranges":{},"facet_intervals":{},"facet_heatmaps":{}}}
            
            response = requests.get(f"https://www.ebi.ac.uk/gwas/api/search?q=(text%3A%22HGNC%3A{hugo}%22+OR+title%3A%22HGNC%3A{hugo}%22+OR+synonyms%3A%22HGNC%3A{hugo}%22)+AND+-resourcename%3Astudy&generalTextQuery=true")
            response_json = response.json()
            docs = response_json['response']['docs']
            results = []
            for doc in docs:
                title = doc.get('title')
                study_count = doc.get('studyCount')
                
                if title is not None and study_count is not None and study_count > 10:
                    results.append({
                        'title': title,
                        'studyCount': study_count
                    })
            GWAS_data.append(results)

        # now we need to go to the gene page e.g. https://www.ebi.ac.uk/gwas/genes/UBE4B
        # this has three tabs, associations, studies, and traits
        # we want traits, might be rendered dynamically, in which case I need to find the link
        # yup, rendered dynamically, but this seems to give json to traits: https://www.ebi.ac.uk/gwas/api/v2/genes/UBE4B/traits?size=5&page=0

        traits = []
        print(GWAS_data)
        for gene_and_title in GWAS_data:
            if len(gene_and_title) == 0:
                continue
            gene = gene_and_title[0]['title']
            response = requests.get(f"https://www.ebi.ac.uk/gwas/api/v2/genes/{gene}/associations?size=30&page=0")
            response_json_raw = response.text
            # print(response_json_raw)

            pattern = r'"label"\s*:\s*"([^"]*)"'
            labels = re.findall(pattern, response_json_raw)

            # if "rheumatoid arthritis" in labels:
            #     print(gene + " has rheumatoid arthritis")
            print(f"gene: {gene}, {labels=}")
            traits += labels     
            
        # print(traits)
        return traits
    # def search_annotations(self, annotations_raw: str):
    #     vep_data = json.loads(annotations_raw)
    #     retrieved_articles_by_variant = {}
    #     retrieved_clinvar_data_by_variant = {} # New dictionary for ClinVar data    

    #     print("Searching PubMed for VEP variants...")

    #     for i, variant in enumerate(vep_data):
    #         chrom = variant.get("seq_region_name")
    #         start = variant.get("start")
    #         end = variant.get("end")
    #         consequence = variant.get("most_severe_consequence")
    #         allele_string = variant.get("allele_string")
    #         rs_id = variant.get("id") # Check if VEP provides rsID here

    #         if not chrom or not start:
    #             print(f"Skipping variant {i} due to missing chromosome or start position.")
    #             continue

    #         variant_label = f"chr{chrom}:{start}-{end}" # Consistent label for storage

    #         print(f"\n--- Processing Variant {i+1} ({variant_label}, Consequence: {consequence}) ---")

    #         # --- PubMed Search ---
    #         functional_terms = [
    #             "regulatory",
    #             "enhancer",
    #             "promoter",
    #             "eQTL",
    #             "GWAS",
    #             "disease susceptibility",
    #             "non-coding"
    #         ]
    #         base_pubmed_query = f'"chromosome {chrom}" AND "intergenic variant"'
    #         pubmed_query = f"{base_pubmed_query} AND ({' OR '.join(functional_terms)})"

    #         print(f"PubMed Query: '{pubmed_query}'")
    #         pmids = self.search_pubmed(pubmed_query, retmax=5)
    #         if pmids:
    #             print(f"Found {len(pmids)} PubMed PMIDs: {pmids}")
    #             articles = self.fetch_pubmed_articles(pmids)
    #             retrieved_articles_by_variant[variant_label] = articles
    #             for article in articles:
    #                 print(f"  - PubMed PMID: {article['pmid']}, Year: {article['publication_year']}, Title: {article['title']}")
    #         else:
    #             print("No PubMed articles found for this variant.")

    #         # --- ClinVar Search ---
    #         # Attempt to construct a ClinVar-friendly query
    #         # For intergenic, direct genomic coordinates are the best bet if no rsID/gene
    #         # Format: chrom[chrpos]start-end OR chrom:start-end
    #         # ClinVar search also understands VCF-like or HGVS: "chr1:100:A>G"
    #         clinvar_query = f"{chrom}[chrpos]{start}-{end}"
    #         if allele_string and allele_string != '.':
    #             # Try to infer Ref/Alt from allele_string for VCF-like query if appropriate
    #             parts = allele_string.split('/')
    #             if len(parts) == 2:
    #                 ref_allele, alt_allele = parts[0], parts[1]
    #                 if len(ref_allele) == 1 and len(alt_allele) == 1: # SNP
    #                     # ClinVar sometimes takes "chrom:pos:ref>alt" (though often for specific variants)
    #                     clinvar_query = f"{chrom}:{start}:{ref_allele}>{alt_allele}"
    #                 elif len(ref_allele) > 1 and alt_allele == '-': # Deletion
    #                     # For deletions, using a range is more appropriate
    #                     clinvar_query = f"{chrom}[chrpos]{start}-{end}"
    #                 elif len(alt_allele) > 1 and ref_allele == '-': # Insertion
    #                     # For insertions, start-end range is more appropriate
    #                     clinvar_query = f"{chrom}[chrpos]{start}-{end}"
                
    #         if rs_id and rs_id != '.': # Prioritize rsID if available
    #             clinvar_query = rs_id
    #         elif "gene_symbol" in variant: # If you had gene symbols in your VEP data (e.g., from an annotation step)
    #             gene_symbol = variant.get("gene_symbol") # Hypothetical VEP field
    #             if gene_symbol:
    #                 clinvar_query = f'"{gene_symbol}"[Gene]'


    #         print(f"ClinVar Query: '{clinvar_query}'")
    #         rcv_ids = self.search_clinvar(clinvar_query, retmax=5) # Limit to 5 ClinVar entries
    #         if rcv_ids:
    #             print(f"Found {len(rcv_ids)} ClinVar RCV IDs: {rcv_ids}")
    #             clinvar_data = self.fetch_clinvar_data(rcv_ids)
    #             retrieved_clinvar_data_by_variant[variant_label] = clinvar_data
    #             for entry in clinvar_data:
    #                 print(f"  - ClinVar RCV: {entry['rcv_accession']}, Gene: {entry['gene_symbol']}, Sig: {entry['clinical_significance']}, Review: {entry['review_status']}")
    #         else:
    #             print("No ClinVar entries found for this variant.")

    #     print("\n--- Summary of Retrieved Articles ---")
    #     for variant_id, articles in retrieved_articles_by_variant.items():
    #         print(f"\nVariant: {variant_id}")
    #         if articles:
    #             for article in articles:
    #                 print(f"  PMID: {article['pmid']}, Title: {article['title']}")
    #                 print(f"  Abstract (excerpt): {article['abstract'][:200]}...") # Print first 200 chars
    #         else:
    #             print("  No articles found.")

    #     print("\n--- Summary of Retrieved ClinVar Data ---")
    #     for variant_id, clinvar_entries in retrieved_clinvar_data_by_variant.items():
    #         print(f"\nVariant: {variant_id}")
    #         if clinvar_entries:
    #             for entry in clinvar_entries:
    #                 print(f"  RCV: {entry['rcv_accession']}, Gene: {entry['gene_symbol']}")
    #                 print(f"  Significance: {entry['clinical_significance']}, Review Status: {entry['review_status']}")
    #                 print(f"  Text for embedding (excerpt): {entry['text_for_embedding'][:150]}...")
    #         else:
    #             print("  No ClinVar entries found.")


    # def search_pubmed(self, query: str, retmax: int = 5) -> List[str]:
    #     """
    #     Searches PubMed for articles and returns a list of PMIDs using BeautifulSoup.
    #     """
    #     params = {
    #         "db": "pubmed",
    #         "term": query,
    #         "retmax": retmax,
    #         "retmode": "xml",
    #         "email": NCBI_EMAIL
    #     }
    #     esearch_url = f"{EUTILS_BASE_URL}esearch.fcgi"
    #     try:
    #         response = requests.get(esearch_url, params=params)
    #         response.raise_for_status() # Raise an exception for HTTP errors

    #         # Use BeautifulSoup to parse the XML
    #         soup = BeautifulSoup(response.content, 'xml') # Specify 'xml' parser for XML content

    #         pmids = [id_tag.text for id_tag in soup.find_all('Id')]
    #         return pmids
    #     except requests.exceptions.RequestException as e:
    #         print(f"Error searching PubMed: {e}")
    #         return []
    #     except Exception as e: # Catch BeautifulSoup parsing errors too
    #         print(f"Error parsing ESearch XML with BeautifulSoup: {e}")
    #         print(f"Response content: {response.content.decode()}")
    #         return []

    # def fetch_pubmed_articles(self, pmids: List[str]) -> List[Dict[str, Any]]:
    #     """
    #     Fetches details (title, abstract, year) for a list of PMIDs using BeautifulSoup.
    #     """
    #     if not pmids:
    #         return []

    #     pmid_str = ",".join(pmids)
    #     params = {
    #         "db": "pubmed",
    #         "id": pmid_str,
    #         "retmode": "xml",
    #         "rettype": "abstract",
    #         "email": NCBI_EMAIL
    #     }
    #     efetch_url = f"{EUTILS_BASE_URL}efetch.fcgi"
    #     articles_data = []
    #     try:
    #         response = requests.get(efetch_url, params=params)
    #         response.raise_for_status() # Raise an exception for HTTP errors

    #         # Use BeautifulSoup to parse the XML
    #         soup = BeautifulSoup(response.content, 'xml') # Specify 'xml' parser

    #         for article_tag in soup.find_all('PubmedArticle'):
    #             pmid_tag = article_tag.find('PMID')
    #             title_tag = article_tag.find('ArticleTitle')
    #             abstract_text_tags = article_tag.find_all('AbstractText')
    #             journal_title_tag = article_tag.find('Journal').find('Title') if article_tag.find('Journal') else None
    #             # Extract year, trying a couple of common XML paths for PubDate
    #             pub_year_tag = article_tag.find('PubDate').find('Year') if article_tag.find('PubDate') else None
    #             if not pub_year_tag: # Fallback for MedlineDate if Year isn't direct
    #                 pub_year_tag = article_tag.find('PubDate').find('MedlineDate') if article_tag.find('PubDate') else None


    #             pmid_val = pmid_tag.text if pmid_tag else "N/A"
    #             article_title = title_tag.text if title_tag else "N/A"
    #             # Join all abstract text elements, handling cases where they might be split
    #             abstract = "\n".join([at.text for at in abstract_text_tags if at.text]) if abstract_text_tags else "N/A"
    #             journal = journal_title_tag.text if journal_title_tag else "N/A"
    #             year = pub_year_tag.text if pub_year_tag else "N/A"
    #             # If MedlineDate was used (e.g., "2024 Spring"), try to extract just the year
    #             if year != "N/A" and len(year) > 4 and any(c.isalpha() for c in year):
    #                 year = year.split(' ')[0] # Take the first part, usually the year

    #             articles_data.append({
    #                 "pmid": pmid_val,
    #                 "title": article_title,
    #                 "abstract": abstract,
    #                 "journal": journal,
    #                 "publication_year": year
    #             })
    #         return articles_data
    #     except requests.exceptions.RequestException as e:
    #         print(f"Error fetching PubMed articles: {e}")
    #         return []
    #     except Exception as e: # Catch BeautifulSoup parsing errors too
    #         print(f"Error parsing EFetch XML with BeautifulSoup: {e}")
    #         print(f"Response content: {response.content.decode()}")
    #         return []

    # def search_clinvar(self, query: str, retmax: int = 5) -> List[str]:
    #     """
    #     Searches ClinVar for variants and returns a list of RCV (Reference Clinical Variant) IDs.
    #     """
    #     params = {
    #         "db": "clinvar",
    #         "term": query,
    #         "retmax": retmax,
    #         "retmode": "xml",
    #         "email": NCBI_EMAIL
    #     }
    #     esearch_url = f"{EUTILS_BASE_URL}esearch.fcgi"
    #     try:
    #         response = requests.get(esearch_url, params=params)
    #         response.raise_for_status()
    #         soup = BeautifulSoup(response.content, 'xml')
    #         rcv_ids = [id_tag.text for id_tag in soup.find_all('Id')]
    #         return rcv_ids
    #     except requests.exceptions.RequestException as e:
    #         print(f"Error searching ClinVar: {e}")
    #         return []
    #     except Exception as e:
    #         print(f"Error parsing ClinVar ESearch XML with BeautifulSoup: {e}")
    #         print(f"Response content: {response.content.decode()}")
    #         return []
    #     finally:
    #         time.sleep(REQUEST_DELAY_SECONDS) # Respect NCBI rate limits

    # def fetch_clinvar_data(self, rcv_ids: List[str]) -> List[Dict[str, Any]]:
    #     """
    #     Fetches detailed ClinVar data for a list of RCV IDs using rettype=vcv.
    #     """
    #     if not rcv_ids:
    #         return []

    #     chunk_size = 50
    #     all_clinvar_data = []

    #     for i in range(0, len(rcv_ids), chunk_size):
    #         rcv_chunk = rcv_ids[i:i + chunk_size]
    #         rcv_str = ",".join(rcv_chunk)
    #         params = {
    #             "db": "clinvar",
    #             "id": rcv_str,
    #             "retmode": "xml",
    #             "rettype": "vcv", # <-- IMPORTANT CHANGE: Using rettype=vcv
    #             "email": NCBI_EMAIL
    #         }
    #         efetch_url = f"{EUTILS_BASE_URL}efetch.fcgi"
    #         try:
    #             response = requests.get(efetch_url, params=params)
    #             response.raise_for_status()
    #             soup = BeautifulSoup(response.content, 'xml')

    #             # The VCV XML often has ClinVarResultBody as the top-level container for multiple VCVs
    #             # Or just VariationArchive directly if fetching a single one.
    #             # Let's find all VariationArchive tags, as each corresponds to a VCV record.
    #             for var_archive_tag in soup.find_all('VariationArchive'):
    #                 clinvar_entry = {}

    #                 # RCV Accession (often an attribute of VariationArchive)
    #                 clinvar_entry['rcv_accession'] = var_archive_tag.get('Accession')

    #                 # ReferenceClinVarAssertion holds most of the key info for the VCV
    #                 ref_assertion_tag = var_archive_tag.find('ReferenceClinVarAssertion')
    #                 if ref_assertion_tag:
    #                     # Clinical Significance
    #                     clin_sig_tag = ref_assertion_tag.find('ClinicalSignificance')
    #                     clinvar_entry['clinical_significance'] = clin_sig_tag.find('Description').text if clin_sig_tag and clin_sig_tag.find('Description') else "N/A"
    #                     clinvar_entry['review_status'] = clin_sig_tag.get('ReviewStatus') if clin_sig_tag else "N/A"

    #                     # Associated conditions/traits (can be multiple)
    #                     traits = []
    #                     for trait_set_tag in ref_assertion_tag.find_all('TraitSet'):
    #                         for trait_tag in trait_set_tag.find_all('Trait'):
    #                             trait_name_tag = trait_tag.find('Name').find('ElementValue', {'Type': 'Preferred'}) if trait_tag.find('Name') else None
    #                             if trait_name_tag:
    #                                 traits.append(trait_name_tag.text)
    #                     clinvar_entry['associated_conditions'] = ", ".join(traits) if traits else "N/A"

    #                     # Gene Symbol(s) - found under MeasureSet -> Measure -> Gene
    #                     gene_symbols = []
    #                     measure_set_tag = ref_assertion_tag.find('MeasureSet')
    #                     if measure_set_tag:
    #                         measure_tag = measure_set_tag.find('Measure')
    #                         if measure_tag:
    #                             for gene_tag in measure_tag.find_all('Gene'):
    #                                 gene_symbol = gene_tag.get('Symbol')
    #                                 if gene_symbol:
    #                                     gene_symbols.append(gene_symbol)
    #                     clinvar_entry['gene_symbol'] = ", ".join(gene_symbols) if gene_symbols else "N/A"

    #                     # Variant Description
    #                     variant_desc_tag = measure_tag.find('Name').find('ElementValue', {'Type': 'Preferred'}) if measure_tag and measure_tag.find('Name') else None
    #                     # Fallback to Description tag which is more common
    #                     if not variant_desc_tag:
    #                         variant_desc_tag = measure_tag.find('Description') if measure_tag else None

    #                     clinvar_entry['variant_description'] = variant_desc_tag.text if variant_desc_tag else "N/A"

    #                     # Variant Identifiers (rsID, HGVS, genomic locations)
    #                     clinvar_entry['rs_id'] = "N/A"
    #                     clinvar_entry['hgvs_expressions'] = []
    #                     clinvar_entry['genomic_locations'] = []

    #                     if measure_tag:
    #                         # rsID
    #                         rs_id_tag = measure_tag.find('XRef', {'DB': 'dbSNP'})
    #                         clinvar_entry['rs_id'] = rs_id_tag.get('ID') if rs_id_tag else "N/A"

    #                         # HGVS expressions
    #                         for hgvs_tag in measure_tag.find_all('HGVS'):
    #                             hgvs_expression = hgvs_tag.get('Expression')
    #                             if hgvs_expression:
    #                                 clinvar_entry['hgvs_expressions'].append(hgvs_expression)

    #                         # Genomic locations (prefer GRCh38)
    #                         for loc_tag in measure_tag.find_all('SequenceLocation'):
    #                             if loc_tag.get('Assembly') == 'GRCh38':
    #                                 clinvar_entry['genomic_locations'].append({
    #                                     'assembly': loc_tag.get('Assembly'),
    #                                     'chr': loc_tag.get('Chr'),
    #                                     'start': loc_tag.get('start'),
    #                                     'end': loc_tag.get('stop'),
    #                                     'reference': loc_tag.get('referenceAllele'),
    #                                     'alternate': loc_tag.get('alternateAllele')
    #                                 })
    #                 else: # Fallback for cases where ReferenceClinVarAssertion might be missing or structure is different
    #                     print(f"  Warning: ReferenceClinVarAssertion not found for RCV {clinvar_entry.get('rcv_accession', 'N/A')}. Data may be incomplete.")
    #                     # Fill with N/A or default values if the main section isn't found
    #                     clinvar_entry.update({
    #                         'clinical_significance': "N/A", 'review_status': "N/A",
    #                         'associated_conditions': "N/A", 'gene_symbol': "N/A",
    #                         'variant_description': "N/A", 'rs_id': "N/A",
    #                         'hgvs_expressions': [], 'genomic_locations': []
    #                     })


    #                 # Construct text for embedding (using .get for safety)
    #                 text_to_embed = f"ClinVar entry. "
    #                 text_to_embed += f"RCV Accession: {clinvar_entry.get('rcv_accession', 'N/A')}. "
    #                 if clinvar_entry.get('gene_symbol') and clinvar_entry['gene_symbol'] != "N/A":
    #                     text_to_embed += f"Gene: {clinvar_entry['gene_symbol']}. "
    #                 if clinvar_entry.get('variant_description') and clinvar_entry['variant_description'] != "N/A":
    #                     text_to_embed += f"Variant description: {clinvar_entry['variant_description']}. "
    #                 if clinvar_entry.get('clinical_significance') and clinvar_entry['clinical_significance'] != "N/A":
    #                     text_to_embed += f"Clinical significance: {clinvar_entry['clinical_significance']}. "
    #                 if clinvar_entry.get('review_status') and clinvar_entry['review_status'] != "N/A":
    #                     text_to_embed += f"Review status: {clinvar_entry['review_status']}. "
    #                 if clinvar_entry.get('associated_conditions') and clinvar_entry['associated_conditions'] != "N/A":
    #                     text_to_embed += f"Associated conditions: {clinvar_entry['associated_conditions']}. "
    #                 if clinvar_entry.get('rs_id') and clinvar_entry['rs_id'] != "N/A":
    #                     text_to_embed += f"dbSNP ID: {clinvar_entry['rs_id']}. "
    #                 if clinvar_entry.get('hgvs_expressions'):
    #                     text_to_embed += f"HGVS: {', '.join(clinvar_entry['hgvs_expressions'])}. "
    #                 if clinvar_entry.get('genomic_locations'):
    #                     first_loc = clinvar_entry['genomic_locations'][0]
    #                     text_to_embed += f"Genomic location (GRCh38): chr{first_loc['chr']}:{first_loc['start']}-{first_loc['end']} ({first_loc['reference']}>{first_loc['alternate']})."
                    
    #                 clinvar_entry['text_for_embedding'] = text_to_embed.strip()
    #                 all_clinvar_data.append(clinvar_entry)

    #         except requests.exceptions.RequestException as e:
    #             print(f"Error fetching ClinVar data chunk: {e}")
    #         except Exception as e:
    #             print(f"Error parsing ClinVar EFetch XML chunk with BeautifulSoup: {e}")
    #             # print(f"Response content (partial): {response.content[:1000].decode()}...") # Uncomment for detailed debug
    #         finally:
    #             time.sleep(REQUEST_DELAY_SECONDS)

    #     return all_clinvar_data
    #     """
    #     Fetches detailed ClinVar data for a list of RCV IDs.
    #     """
    #     if not rcv_ids:
    #         return []

    #     # Similar to PubMed EFetch, chunking for large ID lists
    #     chunk_size = 50 # ClinVar EFetch responses can be quite large
    #     all_clinvar_data = []

    #     for i in range(0, len(rcv_ids), chunk_size):
    #         rcv_chunk = rcv_ids[i:i + chunk_size]
    #         rcv_str = ",".join(rcv_chunk)
    #         params = {
    #             "db": "clinvar",
    #             "id": rcv_str,
    #             "retmode": "xml",
    #             "rettype": "variation" # Request detailed variation record
    #             # "retmax": chunk_size # Redundant if using 'id'
    #         }
    #         efetch_url = f"{EUTILS_BASE_URL}efetch.fcgi"
    #         try:
    #             response = requests.get(efetch_url, params=params)
    #             response.raise_for_status()
    #             soup = BeautifulSoup(response.content, 'xml')
    #             print(soup.prettify())

    #             # Iterate through each VariationArchive in the XML response
    #             for var_archive_tag in soup.find_all('VariationArchive'):
    #                 clinvar_entry = {}

    #                 # RCV Accession
    #                 rcv_accession = var_archive_tag.get('Accession')
    #                 clinvar_entry['rcv_accession'] = rcv_accession

    #                 # Clinical Significance
    #                 clin_sig_tag = var_archive_tag.find('ClinicalSignificance')
    #                 clinvar_entry['clinical_significance'] = clin_sig_tag.find('Description').text if clin_sig_tag and clin_sig_tag.find('Description') else "N/A"
    #                 clinvar_entry['review_status'] = clin_sig_tag.get('ReviewStatus') if clin_sig_tag else "N/A"

    #                 # Reference ClinVarAssertion ID (useful for linking to raw assertion)
    #                 clinvar_entry['assertion_id'] = var_archive_tag.find('ClinVarAssertion').get('ID') if var_archive_tag.find('ClinVarAssertion') else "N/A"

    #                 # Variant ID (e.g., rsID, HGVS)
    #                 # This part can be complex as variants can have multiple identifiers.
    #                 # Let's try to get a common representation or rsID
    #                 measure_tag = var_archive_tag.find('Measure')
    #                 if measure_tag:
    #                     clinvar_entry['variant_id'] = measure_tag.get('ID') # ClinVar internal ID
    #                     clinvar_entry['variant_type'] = measure_tag.get('Type') # e.g., 'Variation'

    #                     # Try to get rsID if available
    #                     rs_id_tag = measure_tag.find('XRef', {'DB': 'dbSNP'})
    #                     clinvar_entry['rs_id'] = rs_id_tag.get('ID') if rs_id_tag else "N/A"

    #                     # Get HGVS expressions
    #                     hgvs_list = []
    #                     for hgvs_tag in measure_tag.find_all('HGVS'):
    #                         hgvs_expression = hgvs_tag.get('Expression')
    #                         if hgvs_expression:
    #                             hgvs_list.append(hgvs_expression)
    #                     clinvar_entry['hgvs_expressions'] = hgvs_list if hgvs_list else []

    #                     # Get genomic locations if available (GRCh38 preferred)
    #                     location_tags = measure_tag.find_all('SequenceLocation')
    #                     clinvar_entry['genomic_locations'] = []
    #                     for loc in location_tags:
    #                         if loc.get('Assembly') == 'GRCh38':
    #                             clinvar_entry['genomic_locations'].append({
    #                                 'assembly': loc.get('Assembly'),
    #                                 'chr': loc.get('Chr'),
    #                                 'start': loc.get('start'),
    #                                 'end': loc.get('stop'), # ClinVar uses 'stop'
    #                                 'reference': loc.get('referenceAllele'),
    #                                 'alternate': loc.get('alternateAllele')
    #                             })


    #                 # Gene Symbol(s)
    #                 gene_symbols = []
    #                 for gene_tag in var_archive_tag.find_all('Gene'):
    #                     gene_symbol = gene_tag.get('Symbol')
    #                     if gene_symbol:
    #                         gene_symbols.append(gene_symbol)
    #                 clinvar_entry['gene_symbol'] = ", ".join(gene_symbols) if gene_symbols else "N/A"

    #                 # Variation Description (often detailed)
    #                 variation_desc_tag = var_archive_tag.find('Description')
    #                 clinvar_entry['variant_description'] = variation_desc_tag.text if variation_desc_tag else "N/A"

    #                 # Interpretation / Explanation (from ClinVarAssertion) - often long text
    #                 # This is a bit deeper in the XML, often within "Interpretation"
    #                 # For brevity, we might just get the description, but can dig further.
    #                 # For this example, we'll try to get assertion-level descriptions.
    #                 assertion_description_tag = var_archive_tag.find('ClinVarAssertion').find('Description') if var_archive_tag.find('ClinVarAssertion') else None
    #                 clinvar_entry['assertion_description'] = assertion_description_tag.text if assertion_description_tag else "N/A"


    #                 # Combine extracted fields into a coherent text string for embedding
    #                 text_to_embed = f"ClinVar assertion for gene {clinvar_entry['gene_symbol']}. " \
    #                                 f"Variant description: {clinvar_entry['variant_description']}. " \
    #                                 f"Clinical significance: {clinvar_entry['clinical_significance']}. " \
    #                                 f"Review status: {clinvar_entry['review_status']}. "
    #                 if clinvar_entry['assertion_description'] != "N/A":
    #                     text_to_embed += f"Detailed assertion: {clinvar_entry['assertion_description']}."
    #                 if clinvar_entry['rs_id'] != "N/A":
    #                     text_to_embed += f" dbSNP ID: {clinvar_entry['rs_id']}."
    #                 if clinvar_entry['genomic_locations']:
    #                     first_loc = clinvar_entry['genomic_locations'][0]
    #                     text_to_embed += f" Genomic location (GRCh38): chr{first_loc['chr']}:{first_loc['start']}-{first_loc['end']} ({first_loc['reference']}>{first_loc['alternate']})."


    #                 clinvar_entry['text_for_embedding'] = text_to_embed
    #                 all_clinvar_data.append(clinvar_entry)

    #         except requests.exceptions.RequestException as e:
    #             print(f"Error fetching ClinVar data chunk: {e}")
    #         except Exception as e:
    #             print(f"Error parsing ClinVar EFetch XML chunk with BeautifulSoup: {e}")
    #             print(f"Response content (partial): {response.content[:500].decode()}...")
    #         finally:
    #             time.sleep(REQUEST_DELAY_SECONDS) # Respect NCBI rate limits

    #     return all_clinvar_data
            

# --- Your VEP Data (example snippet) ---
annotations_raw = ""
# annotations_raw = """
# [
#   {
#     "assembly_name": "GRCh38",
#     "intergenic_consequences": [
#       {
#         "impact": "MODIFIER",
#         "variant_allele": "-",
#         "consequence_terms": [
#           "intergenic_variant"
#         ]
#       }
#     ],
#     "start": 101,
#     "id": ".",
#     "strand": 1,
#     "input": "1 100 . GTTT G",
#     "seq_region_name": "1",
#     "end": 103,
#     "allele_string": "TTT/-",
#     "most_severe_consequence": "intergenic_variant"
#   },
#   {
#     "most_severe_consequence": "intergenic_variant",
#     "allele_string": "C/T",
#     "end": 105,
#     "input": "1 105 . C T",
#     "seq_region_name": "1",
#     "strand": 1,
#     "id": ".",
#     "start": 105,
#     "intergenic_consequences": [
#       {
#         "impact": "MODIFIER",
#         "variant_allele": "T",
#         "consequence_terms": [
#           "intergenic_variant"
#         ]
#       }
#     ],
#     "assembly_name": "GRCh38"
#   },
#   {
#     "id": ".",
#     "strand": 1,
#     "input": "1 106 . C A",
#     "seq_region_name": "1",
#     "start": 106,
#     "intergenic_consequences": [
#       {
#         "consequence_terms": [
#           "intergenic_variant"
#         ],
#         "variant_allele": "A",
#         "impact": "MODIFIER"
#       }
#     ],
#     "assembly_name": "GRCh38",
#     "most_severe_consequence": "intergenic_variant",
#     "allele_string": "C/A",
#     "end": 106
#   },
#   {
#     "assembly_name": "GRCh38",
#     "intergenic_consequences": [
#       {
#         "consequence_terms": [
#           "intergenic_variant"
#         ],
#         "impact": "MODIFIER",
#         "variant_allele": "G"
#       }
#     ],
#     "start": 110,
#     "seq_region_name": "2",
#     "id": ".",
#     "strand": 1,
#     "input": "2 110 . A G",
#     "end": 110,
#     "allele_string": "A/G",
#     "most_severe_consequence": "intergenic_variant"
#   }
# ]
# """
with open("src/annotation.json", "r") as f:
    annotations_raw = f.read()


if __name__ == '__main__':
    
    rag = RAG()
    rag.search_annotations(annotations_raw)

