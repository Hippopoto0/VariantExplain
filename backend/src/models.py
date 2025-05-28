# results [{'trait_title': 'Early-onset schizophrenia', 'increase_decrease': '34.6% increase in the odds of developing early-onset schizophrenia', 'details': "Early-onset schizophrenia (EOS) is a rare form of schizophrenia that begins before the age of 18. This association study found that the 'A' allele of the rs1801133 variant is associated with an increased risk of EOS in Han Chinese populations. The study involved a two-stage genome-wide association study (GWAS) with over 2,159 EOS cases and 6,561 controls. The identified risk loci may provide potential targets for therapeutics and diagnostics.", 'good_or_bad': 'Bad - Schizophrenia is a severe mental disorder.', 'image_url': 'https://tse4.mm.bing.net/th/id/OIP.6-VgYes6T0EYLl9UaW4dUAHaHa?w=159&h=180&c=7&r=0&o=5&pid=1.7'}, 

from typing import Literal, Optional


class TraitSummary(BaseModel):
    trait_title: str
    increase_decrease: float
    details: str
    good_or_bad: Literal['good', 'bad']
    image_url: Optional[str] = None
    