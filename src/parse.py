"""
VCFParser module for parsing and annotating VCF files.
"""
import os
import json
import logging
from typing import Optional, Any
import vcfpy
from vep import process_vcf_file

class VCFParser:
    """
    VCFParser loads and annotates VCF or RData files.
    """
    def __init__(self, vcf_path: str) -> None:
        """
        Initialize the parser and fetch VEP annotation.
        Args:
            vcf_path (str): Path to VCF or RData file.
        """
        self.vcf_path = vcf_path
        self.vcf_file: Optional[Any] = self.load()
        self.annotation: Optional[Any] = None
        self.fetch_vep_annotation()

    def fetch_vep_annotation(self) -> None:
        """
        Run VEP annotation and store the result in self.annotation.
        """
        try:
            output_path = 'src/annotation.json'
            process_vcf_file(self.vcf_path, output_path)
            if not os.path.exists(output_path):
                raise FileNotFoundError(f"Annotation file not found at {output_path}")
            with open(output_path, 'r') as f:
                self.annotation = json.load(f)
                logging.info(f"Successfully loaded {len(self.annotation)} annotations")
        except Exception as e:
            logging.error(f"Error fetching VEP annotation: {str(e)}")
            self.annotation = []
            raise

    def load(self) -> Optional[Any]:
        """
        Load the VCF or RData file.
        Returns:
            File content or object.
        """
        if not self.vcf_path:
            raise ValueError("vcf_path is not set")
        if self.vcf_path.endswith('.vcf'):
            with open(self.vcf_path, 'r') as f:
                return f.read()
        elif self.vcf_path.endswith('.rdata'):
            return self.parse_rdata()
        else:
            raise ValueError("vcf_path must end with .vcf or .rdata")

    def parse_rdata(self) -> Any:
        """
        Parse an RData file using rpy2 and return the loaded object.
        Returns:
            Loaded R object.
        """
        import rpy2.robjects as robjects
        import rpy2.robjects.packages as rpackages
        import rpy2.robjects.numpy2ri as numpy2ri
        numpy2ri.activate()
        base = rpackages.importr('base')
        r = robjects.r
        r['load'](self.vcf_path)
        return r['vcf']

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    parser = VCFParser('data/truncated.vcf')
    print(parser.vcf_file)