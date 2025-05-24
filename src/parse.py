#!/usr/bin/env python3
# parse and load the vcf data
import vcfpy
from vep import process_vcf_file
import json
import os

class VCFParser:
    def __init__(self, vcf_path):
        self.vcf_path = vcf_path
        self.vcf_file = self.load()
        self.annotation = None
        self.fetch_vep_annotation()

    def fetch_vep_annotation(self):
        try:
            # Process VCF file and create annotation
            output_path = 'src/annotation.json'
            process_vcf_file(self.vcf_path, output_path)
            
            # Check if file exists and load it
            if not os.path.exists(output_path):
                raise FileNotFoundError(f"Annotation file not found at {output_path}")
                
            with open(output_path, 'r') as f:
                self.annotation = json.load(f)
                print(f"Successfully loaded {len(self.annotation)} annotations")
                
        except Exception as e:
            print(f"Error fetching VEP annotation: {str(e)}")
            self.annotation = []  # Set to empty list on error
            raise

    def load(self):
        if self.vcf_path is None:
            raise ValueError("vcf_path is not set")
        
        if self.vcf_path.endswith('.vcf'):
            with open(self.vcf_path, 'r') as f:
                self.vcf_file = f.read()
        
        elif self.vcf_path.endswith('.rdata'):
            self.vcf_file = self.parse_rdata()

        else:
            raise ValueError("vcf_path must end with .vcf or .rdata")

        return self.vcf_file

    def parse_rdata(self):
        import rpy2.robjects as robjects
        import rpy2.robjects.packages as rpackages
        import rpy2.robjects.numpy2ri as numpy2ri
        numpy2ri.activate()
        
        base = rpackages.importr('base')
        
        r = robjects.r
        r['load'](self.vcf_path)
        
        return r['vcf']

if __name__ == '__main__':
    parser = VCFParser('src/test.vcf')
    print(parser.vcf_file)