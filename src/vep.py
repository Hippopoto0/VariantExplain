import requests
import json
import gzip
import sys

# --- Configuration ---
SERVER = "https://rest.ensembl.org"
SPECIES = "human"  # e.g., "human", "mouse", "zebrafish"
VEP_ENDPOINT = f"/vep/{SPECIES}/region"
BATCH_SIZE = 200  # Number of variants to send in each POST request (max ~1000 for Ensembl)

# --- VEP API Parameters (Optional) ---
# You can add VEP options as URL parameters for GET requests
# or as key-value pairs in the JSON body for POST requests.
# For example, to include ClinVar data and SIFT/PolyPhen predictions:
VEP_PARAMS = {
    "ClinVar": 1,
    "sift": 1,
    "polyphen": 1,
    "conservation": 1, # Add conservation scores (e.g., PhyloP, phastCons)
    "canonical": 1,    # Only return consequences for canonical transcripts
    "gene_phenotype": 1, # Add gene-phenotype associations (e.g., OMIM, Orphanet)
    "dbSNP": 1,        # get the rsID
    # "AlphaMissense": 1, # AlphaMissense plugin (requires additional data installation for command-line)
    # "CADD": 1, # CADD plugin (requires additional data installation for command-line)
}

def parse_vcf_line(line):
    """
    Parses a single VCF line and returns a VEP API input string.
    Handles lines starting with '#' as comments/header.
    """
    if line.startswith('#'):
        return None
    
    parts = line.strip().split('\t')
    if len(parts) < 5:
        return None # Not a valid variant line

    chrom = parts[0]
    pos = parts[1]
    _id = parts[2] if parts[2] != '.' else '.' # Use '.' if no ID
    ref = parts[3]
    alt = parts[4]

    # VEP API expects VCF-like strings for POST /region
    # Ensure ID is not empty if it's not present in VCF
    if not _id:
        _id = '.'

    return f"{chrom} {pos} {_id} {ref} {alt}"

def process_vcf_file(input_vcf_path, output_json_path):
    """
    Reads a VCF file, batches variants, and sends them to the VEP REST API.
    Writes the annotated results to a JSON file.
    """
    variant_batch = []
    all_annotations = []
    
    # Open the VCF file (handles .vcf and .vcf.gz)
    open_func = gzip.open if input_vcf_path.endswith('.gz') else open
    
    try:
        with open_func(input_vcf_path, 'rt') as f:
            for line_num, line in enumerate(f, 1):
                vep_input_string = parse_vcf_line(line)
                if vep_input_string:
                    variant_batch.append(vep_input_string)

                    if len(variant_batch) >= BATCH_SIZE:
                        print(f"Processing batch of {len(variant_batch)} variants (line {line_num})...")
                        annotations = send_vep_request(variant_batch)
                        all_annotations.extend(annotations)
                        variant_batch = [] # Reset batch
        
            # Process any remaining variants in the last batch
            if variant_batch:
                print(f"Processing final batch of {len(variant_batch)} variants...")
                annotations = send_vep_request(variant_batch)
                all_annotations.extend(annotations)

        # Write all annotations to the output JSON file
        with open(output_json_path, 'w') as outfile:
            json.dump(all_annotations, outfile, indent=2)
        print(f"Annotation complete. Results saved to {output_json_path}")

    except requests.exceptions.RequestException as e:
        print(f"Error during API request: {e}")
        sys.exit(1)
    except IOError as e:
        print(f"Error reading/writing file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

def send_vep_request(variants):
    """
    Sends a POST request to the VEP API with a batch of variants.
    """
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    
    # Construct the URL with optional parameters
    url = SERVER + VEP_ENDPOINT
    if VEP_PARAMS:
        params_string = '&'.join([f"{k}={v}" for k,v in VEP_PARAMS.items()])
        url = f"{url}?{params_string}"

    data = {"variants": variants}

    try:
        r = requests.post(url, headers=headers, data=json.dumps(data))
        r.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        return r.json()
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
        print(f"Response content: {r.text}")
        raise
    except requests.exceptions.ConnectionError as err:
        print(f"Connection error occurred: {err}")
        raise
    except requests.exceptions.Timeout as err:
        print(f"Timeout error occurred: {err}")
        raise
    except requests.exceptions.RequestException as err:
        print(f"An unknown error occurred: {err}")
        raise

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python vep_vcf_annotator.py <input_vcf_file> <output_json_file>")
        sys.exit(1)

    input_vcf = sys.argv[1]
    output_json = sys.argv[2]

    print(f"Starting VCF annotation for {input_vcf}...")
    process_vcf_file(input_vcf, output_json)
    print("Script finished.")