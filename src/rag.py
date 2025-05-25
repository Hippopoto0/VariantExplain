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
        hugoes = list(dict.fromkeys(hugoes))

        print(len(hugoes))
        for hugo in hugoes:
            print(f"Searching GWAS for {hugo}...")
            # something like this https://www.ebi.ac.uk/gwas/search?query=HGNC:8977
            # that renders dynamically, but gets request from here
            # https://www.ebi.ac.uk/gwas/api/search?q=(text%3A%22HGNC%3A12500%22+OR+title%3A%22HGNC%3A12500%22+OR+synonyms%3A%22HGNC%3A12500%22)+AND+-resourcename%3Astudy&generalTextQuery=true

            # format like this - note title, study count found in responseHeader.
            # {"responseHeader":{"status":0,"QTime":0,"params":{"q":"(text:\"HGNC:12500\" OR title:\"HGNC:12500\" OR synonyms:\"HGNC:12500\") AND -resourcename:study","facet.field":"resourcename","defType":"edismax","qf":"title^2.0 synonyms^20.0 parent^2.0 text^1.0","start":"0","rows":"1000","wt":"json","facet":"true"}},"response":{"numFound":1,"start":0,"docs":[{"resourcename":"gene","id":"gene:ENSG00000130939","ensemblID":"ENSG00000130939","rsIDs":["rs77954449","rs11121525","rs11806008","rs12144133","rs3828081","rs11801734","rs61782937","rs149622283","rs7539725","rs113304383","rs12092513","rs6661326","rs6696978","rs139279718","rs61782892","rs187585530","rs4333851","rs115486679","rs3903151"],"studyCount":27,"associationCount":31,"chromosomeStart":10032832,"chromosomeEnd":10181239,"chromosomeName":"1","biotype":"protein_coding","title":"UBE4B","ensemblDescription":"ubiquitination factor E4B","crossRefs":"HGNC:12500|OTTHUMG00000001797|uc001aqr.5|AF091093|NM_006048|MGI:1927086|O95155","entrez_id":"10277","cytobands":"1p36.22","description":"ubiquitination factor E4B|1:10032832-10181239|1p36.22|protein_coding","_version_":1831968093979541507}]},"facet_counts":{"facet_queries":{},"facet_fields":{"resourcename":["gene",1,"publication",0,"study",0,"trait",0,"variant",0]},"facet_dates":{},"facet_ranges":{},"facet_intervals":{},"facet_heatmaps":{}}}
            url = f"https://www.ebi.ac.uk/gwas/api/search?q=(text%3A%22HGNC%3A{hugo}%22+OR+title%3A%22HGNC%3A{hugo}%22+OR+synonyms%3A%22HGNC%3A{hugo}%22)+AND+-resourcename%3Astudy&generalTextQuery=true&size=100&sort=studyCount,desc"
            response = requests.get(url)
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
        print(GWAS_data)
        for gene_and_title in GWAS_data:
            if len(gene_and_title) == 0:
                continue
            gene = gene_and_title[0]['title']
            response = requests.get(f"https://www.ebi.ac.uk/gwas/api/v2/genes/{gene}/associations?size=30&page=0&sort=pValue,asc")
            response_json = response.json()
            
            # example allele data below
# gwas_json_data = {
#   "_embedded" : {
#     "associations" : [ {
#       "riskAllele" : [ {
#         "key" : "rs7518602",
#         "label" : "rs7518602-C"
#       } ],
#       "riskFrequency" : "0.391285",
#       "pValueExponent" : -27,
#       "pValue" : 2,
#       "beta" : "0.022113 SD unit decrease",
#       "ci" : "[0.018-0.026]",
#       "mappedGenes" : [ "PIK3CD" ],
#       "traitName" : [ "Eosinophil counts" ],
#       "efoTraits" : [ {
#         "key" : "EFO_0004842",
#         "label" : "eosinophil count"
#       } ],
#       "locations" : [ "1:9651286" ],
#       "author" : "Chen MH",
#       "publicationDate" : "2020-09-01",
#       "accessionId" : "GCST90002298",
#       "riskAlleleSep" : " x ",
#       "pubmedId" : "32888493",
#       "_links" : {
#         "self" : {
#           "href" : "https://www.ebi.ac.uk/gwas/api/v2/publications"
#         }
#       }
#     }, {
#       "riskAllele" : [ {
#         "key" : "rs11806839",
#         "label" : "rs11806839-C"
#       } ],
#       "riskFrequency" : "0.384008",
#       "pValueExponent" : -27,
#       "pValue" : 3,
#       "beta" : "0.024747888 unit decrease",
#       "ci" : "[0.02-0.029]",
#       "mappedGenes" : [ "PIK3CD" ],
#       "traitName" : [ "Eosinophil counts" ],
#       "efoTraits" : [ {
#         "key" : "EFO_0004842",
#         "label" : "eosinophil count"
#       } ],
#       "locations" : [ "1:9651702" ],
#       "author" : "Vuckovic D",
#       "publicationDate" : "2020-09-01",
#       "accessionId" : "GCST90002381",
#       "riskAlleleSep" : " x ",
#       "pubmedId" : "32888494",
#       "_links" : {
#         "self" : {
#           "href" : "https://www.ebi.ac.uk/gwas/api/v2/publications"
#         }
#       }
#     }, {
#       "riskAllele" : [ {
#         "key" : "rs11806839",
#         "label" : "rs11806839-C"
#       } ],
#       "riskFrequency" : "0.384037",
#       "pValueExponent" : -19,
#       "pValue" : 2,
#       "beta" : "0.020676868 unit decrease",
#       "ci" : "[0.016-0.025]",
#       "mappedGenes" : [ "PIK3CD" ],
#       "traitName" : [ "Eosinophil percentage of white cells" ],
#       "efoTraits" : [ {
#         "key" "EFO_0007991",
#         "label" : "eosinophil percentage of leukocytes"
#       } ],
#       "locations" : [ "1:9651702" ],
#       "author" : "Vuckovic D",
#       "publicationDate" : "2020-09-01",
#       "accessionId" : "GCST90002382",
#       "riskAlleleSep" : " x ",
#       "pubmedId" : "32888494",
#       "_links" : {
#         "self" : {
#           "href" : "https://www.ebi.ac.uk/gwas/api/v2/publications"
#         }
#       }
#     }, {
#       "riskAllele" : [ {
#         "key" : "rs7518602",
#         "label" : "rs7518602-C"
#       } ],
#       "riskFrequency" : "0.481322",
#       "pValueExponent" : -27,
#       "pValue" : 8,
#       "mappedGenes" : [ "PIK3CD" ],
#       "traitName" : [ "Eosinophil counts" ],
#       "efoTraits" : [ {
#         "key" : "EFO_0004842",
#         "label" : "eosinophil count"
#       } ],
#       "locations" : [ "1:9651286" ],
#       "author" : "Chen MH",
#       "publicationDate" : "2020-09-01",
#       "accessionId" : "GCST90002302",
#       "riskAlleleSep" : " x ",
#       "pubmedId" : "32888493",
#       "_links" : {
#         "self" : {
#           "href" : "https://www.ebi.ac.uk/gwas/api/v2/publications"
#         }
#       }
#     }, {
#       "riskAllele" : [ {
#         "key" : "rs7516138",
#         "label" : "rs7516138-G"
#       } ],
#       "riskFrequency" : "0.391091",
#       "pValueExponent" : -31,
#       "pValue" : 1,
#       "beta" : "0.022592 SD unit decrease",
#       "ci" : "[0.019-0.026]",
#       "mappedGenes" : [ "PIK3CD" ],
#       "traitName" : [ "Monocyte count" ],
#       "efoTraits" : [ {
#         "key" : "EFO_0005091",
#         "label" : "monocyte count"
#       } ],
#       "locations" : "1:9651584" ], # Note: This was incorrectly a list of strings in the original JSON, now it's a single string for 'locations'
#       "author" : "Chen MH",
#       "publicationDate" : "2020-09-01",
#       "accessionId" : "GCST90002340",
#       "riskAlleleSep" : " x ",
#       "pubmedId" : "32888493",
#       "_links" : {
#         "self" : {
#           "href" : "https://www.ebi.ac.uk/gwas/api/v2/publications"
#         }
#       }
#     } ]
#   },
#   "_links" : {
#     "first" : {
#       "href" : "https://www.ebi.ac.uk/gwas/api/v2/variants?page=0&size=5"
#     },
#     "self" : {
#       "href" : "https://www.ebi.ac.uk/gwas/api/v2/variants"
#     },
#     "next" : {
#       "href" : "https://www.ebi.ac.uk/gwas/api/v2/variants?page=1&size=5"
#     },
#     "last" : {
#       "href" : "https://www.ebi.ac.uk/gwas/api/v2/variants?page=6&size=5"
#     }
#   },
#   "page" : {
#     "size" : 5,
#     "totalElements" : 33,
#     "totalPages" : 7,
#     "number" : 0
#   }
# }
            extracted_associations = []

            # Navigate to the list of associations
            associations = response_json.get("_embedded", {}).get("associations", [])

            for assoc in associations:
                # Extract traitName (it's a list, so join if multiple or take first)
                trait_name = assoc.get("traitName", [])
                if trait_name:
                    trait_name = trait_name[0] # Take the first trait name if multiple
                else:
                    trait_name = "N/A"

                # Extract beta (if present)
                beta = assoc.get("beta")

                # Extract PubMed ID
                pubmed_id = assoc.get("pubmedId")

                # Extract riskAllele (it's a list of dicts, get 'label' or 'key')
                risk_allele_info = assoc.get("riskAllele", [])
                risk_allele = None
                if risk_allele_info and len(risk_allele_info) > 0:
                    risk_allele = risk_allele_info[0].get("label") # or .get("key") for just rsID
                    if not risk_allele: # Fallback to key if label isn't there
                        risk_allele = risk_allele_info[0].get("key")
                if not risk_allele:
                    risk_allele = "N/A"

                # Calculate full pValue from pValue and pValueExponent
                p_value_exponent = assoc.get("pValueExponent")
                p_value_base = assoc.get("pValue")
                
                calculated_p_value = None
                if p_value_exponent is not None and p_value_base is not None:
                    calculated_p_value = f"{p_value_base}e{p_value_exponent}" # Formatted as string like "2e-27"
                    # If you need it as a float: calculated_p_value = float(f"{p_value_base}e{p_value_exponent}")
                else:
                    calculated_p_value = "N/A"
                    
                # Odds Ratio (OR) - checking if it exists, otherwise it will be None
                # GWAS Catalog uses 'orValue' (lowercase) field for odds ratio
                odds_ratio = assoc.get("orValue") 
                if odds_ratio is None: # If 'orValue' field doesn't exist, check for 'oddsRatio' (less common)
                    odds_ratio = assoc.get("oddsRatio")
                if odds_ratio is None:
                    odds_ratio = "N/A" # Set to N/A if neither is found
                    
                if odds_ratio != "N/A":
                    extracted_associations.append({
                        "traitName": trait_name,
                        "beta": beta if beta is not None else "N/A",
                        "pubmedId": pubmed_id if pubmed_id is not None else "N/A",
                        "riskAllele": risk_allele,
                        "pValue": calculated_p_value,
                        "OR": odds_ratio
                    })
            
        print(extracted_associations)
        return extracted_associations

    def append_pubmed_abstracts(self, associated_traits):
        for trait in associated_traits:
            pmid = trait.get("pubmedId")
            if pmid:
                abstract = self.fetch_abstract_from_pubmed_id(pmid)
                trait["abstract"] = abstract

        return associated_traits

    def fetch_abstract_from_pubmed_id(self, pubmed_id):

        response = requests.get(f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}")
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            abstract = soup.find('div', {'class': 'abstract-content'}).get_text(strip=True)
            return abstract
        else:
            return None
            

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
    print("Searching GWAS for VEP variants...")
    associated_traits = rag.search_annotations(annotations_raw)
    print("Finding relevant articles...")
    associated_and_abstracts = rag.append_pubmed_abstracts(associated_traits)
    print("Found articles:")
    print(associated_and_abstracts)

