# results [{'trait_title': 'Early-onset schizophrenia', 'increase_decrease': '34.6% increase in the odds of developing early-onset schizophrenia', 'details': "Early-onset schizophrenia (EOS) is a rare form of schizophrenia that begins before the age of 18. This association study found that the 'A' allele of the rs1801133 variant is associated with an increased risk of EOS in Han Chinese populations. The study involved a two-stage genome-wide association study (GWAS) with over 2,159 EOS cases and 6,561 controls. The identified risk loci may provide potential targets for therapeutics and diagnostics.", 'good_or_bad': 'Bad - Schizophrenia is a severe mental disorder.', 'image_url': 'https://tse4.mm.bing.net/th/id/OIP.6-VgYes6T0EYLl9UaW4dUAHaHa?w=159&h=180&c=7&r=0&o=5&pid=1.7'}, 

from typing import Literal, Optional
from pydantic import BaseModel


class TraitSummary(BaseModel):
    trait_title: str
    increase_decrease: float
    details: str
    good_or_bad: Literal['good', 'bad']
    image_url: Optional[str] = None

def parse_trait_summary(trait_dict: dict) -> TraitSummary:
    """
    Maps a summarised trait dict (from LLM output) to a TraitSummary object.
    Handles type conversion and normalization.
    """
    # Extract and normalize trait_title
    trait_title = trait_dict.get('trait_title') or trait_dict.get('traitName') or ''

    # Extract and parse increase_decrease as float (e.g. '34.6% increase in the odds...')
    inc_dec_raw = trait_dict.get('increase_decrease') or ''
    import re
    match = re.search(r'([-+]?\d*\.?\d+)', str(inc_dec_raw))
    increase_decrease = float(match.group(1)) if match else 0.0
    if 'decrease' in str(inc_dec_raw).lower():
        increase_decrease = -abs(increase_decrease)

    # Extract details
    details = trait_dict.get('details') or trait_dict.get('abstract') or ''

    # Normalize good_or_bad
    good_or_bad_raw = trait_dict.get('good_or_bad', '').lower()
    if 'good' in good_or_bad_raw:
        good_or_bad = 'good'
    else:
        good_or_bad = 'bad'

    # Image URL
    image_url = trait_dict.get('image_url')

    return TraitSummary(
        trait_title=trait_title,
        increase_decrease=increase_decrease,
        details=details,
        good_or_bad=good_or_bad,  # type: ignore
        image_url=image_url
    )
    