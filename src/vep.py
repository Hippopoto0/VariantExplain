import requests
import json
import gzip
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

# --- Configuration ---
SERVER = "https://rest.ensembl.org"
SPECIES = "human"
VEP_ENDPOINT = f"/vep/{SPECIES}/region"
# Increased BATCH_SIZE to 500. Ensembl generally allows up to 1000,
# but 500 is a good balance for testing throughput without hitting issues too fast.
BATCH_SIZE = 200

# --- VEP API Parameters (Optional) ---
VEP_PARAMS = {
    "ClinVar": 1,
    "sift": 1,
    "polyphen": 1,
    "conservation": 1, # Add conservation scores (e.g., PhyloP, phastCons)
    "canonical": 1, # Only return consequences for canonical transcripts
    "gene_phenotype": 1, # Add gene-phenotype
    "dbSNP": 1, # get rsID
}

# --- Function to parse a single VCF line ---
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

    if not _id:
        _id = '.'

    return f"{chrom} {pos} {_id} {ref} {alt}"

# --- Function to send a single batch to VEP ---
def send_vep_batch(variants, batch_index, attempt=1, max_attempts=5):
    """
    Sends a POST request to the VEP API with a batch of variants.
    Includes basic retry logic with exponential backoff and random jitter.
    """
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    
    url = f"{SERVER}{VEP_ENDPOINT}"

    payload = {"variants": variants}
    payload.update(VEP_PARAMS)

    try:
        r = requests.post(url, headers=headers, data=json.dumps(payload))
        r.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        print(f"Batch {batch_index} processed successfully (attempt {attempt}).")
        return r.json()
    except requests.exceptions.HTTPError as err:
        if (r.status_code == 429 or r.status_code >= 500) and attempt < max_attempts: # Too Many Requests or Server Errors
            # Exponential backoff with random jitter
            sleep_time = (2 ** attempt) + random.uniform(0, 1) # Add up to 1 second of random delay
            print(f"Batch {batch_index}: HTTP Error {r.status_code}. Retrying in {sleep_time:.2f} seconds (attempt {attempt})...")
            time.sleep(sleep_time)
            return send_vep_batch(variants, batch_index, attempt + 1, max_attempts)
        print(f"HTTP error for batch {batch_index}: {err}")
        print(f"Response content: {r.text}")
        return None
    except requests.exceptions.ConnectionError as err:
        if attempt < max_attempts:
            sleep_time = (2 ** attempt) + random.uniform(0, 1)
            print(f"Batch {batch_index}: Connection error. Retrying in {sleep_time:.2f} seconds (attempt {attempt})...")
            time.sleep(sleep_time)
            return send_vep_batch(variants, batch_index, attempt + 1, max_attempts)
        print(f"Connection error for batch {batch_index}: {err}")
        return None
    except requests.exceptions.Timeout as err:
        if attempt < max_attempts:
            sleep_time = (2 ** attempt) + random.uniform(0, 1)
            print(f"Batch {batch_index}: Timeout error. Retrying in {sleep_time:.2f} seconds (attempt {attempt})...")
            time.sleep(sleep_time)
            return send_vep_batch(variants, batch_index, attempt + 1, max_attempts)
        print(f"Timeout error for batch {batch_index}: {err}")
        return None
    except requests.exceptions.RequestException as err:
        print(f"An unknown request error occurred for batch {batch_index}: {err}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred for batch {batch_index}: {e}")
        return None

# --- Main parallel processing logic ---
def process_vcf_file_parallel(input_vcf_path, output_json_path, max_workers=10):
    """
    Reads a VCF file, batches variants, and sends them to the VEP REST API in parallel.
    Writes the annotated results to a JSON file.
    """
    all_variants_to_process = []
    
    open_func = gzip.open if input_vcf_path.endswith('.gz') else open
    
    try:
        with open_func(input_vcf_path, 'rt') as f:
            for line in f:
                vep_input_string = parse_vcf_line(line)
                if vep_input_string:
                    all_variants_to_process.append(vep_input_string)
        
        if not all_variants_to_process:
            print("No valid variants found in the VCF file. Exiting.")
            return

        total_variants = len(all_variants_to_process)
        print(f"Found {total_variants} variants to process.")

        batches = [
            all_variants_to_process[i : i + BATCH_SIZE]
            for i in range(0, total_variants, BATCH_SIZE)
        ]
        num_batches = len(batches)
        print(f"Split into {num_batches} batches, using {max_workers} parallel workers.")

        all_annotations = []
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_batch_index = {
                executor.submit(send_vep_batch, batch, i): i
                for i, batch in enumerate(batches)
            }

            for future in as_completed(future_to_batch_index):
                batch_index = future_to_batch_index[future]
                try:
                    data = future.result()
                    if data:
                        all_annotations.extend(data)
                except Exception as exc:
                    print(f"Batch {batch_index} generated an unhandled exception: {exc}")

        end_time = time.time()
        print(f"Total processing time: {end_time - start_time:.2f} seconds")
        print(f"Total VEP results received: {len(all_annotations)}")

        with open(output_json_path, 'w') as outfile:
            json.dump(all_annotations, outfile, indent=2)
        print(f"Annotation complete. Results saved to {output_json_path}")

    except IOError as e:
        print(f"Error reading/writing file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during file processing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python vep_vcf_annotator.py <input_vcf_file> <output_json_file>\n Example: oetry run python src/vep.py data/S1.haplotypecaller.filtered.vcf src/annotation.json")
        sys.exit(1)

    input_vcf = sys.argv[1]
    output_json = sys.argv[2]

    print(f"Starting VCF annotation for {input_vcf}...")
    # You can adjust max_workers here. A value between 10-30 is usually a good starting point.
    process_vcf_file_parallel(input_vcf, output_json, max_workers=20)
    print("Script finished.")