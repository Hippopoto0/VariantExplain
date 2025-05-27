from pydantic import BaseModel, Field
from typing import Optional, List, Any

class TraitSummary(BaseModel):
    trait_title: str
    increase_decrease: str
    details: str
    good_or_bad: str
    image_url: Optional[str] = None

class GwasAssociation(BaseModel):
    gene_symbol: str
    rsid: str
    vep_risk_allele: str
    trait_title: Optional[str] = None
    pValue: Optional[float] = None
    abstract: Optional[str] = None
    pubmedId: Optional[str] = None
    details: Optional[str] = None
    increase_decrease: Optional[str] = None
    good_or_bad: Optional[str] = None

class VepVariant(BaseModel):
    id: Optional[str]
    input: Optional[str]
    gene_symbol: Optional[str]
    allele: Optional[str]
    impact: Optional[str]
    sift_prediction: Optional[str]
    polyphen_prediction: Optional[str]
    # Add more fields as needed based on actual VEP annotation structure

class VcfParseResult(BaseModel):
    vcf_path: str
    vcf_file: Any
    annotation: Any
