"""
Agent module for summarizing GWAS traits and fetching related images.
"""
from typing import List, Dict, Optional
import os
import json
import requests
from bs4 import BeautifulSoup
from google import genai
import dotenv
import logging

dotenv.load_dotenv()
GEN_MODEL = "gemini-2.0-flash"

class Agent:
    """
    Agent class for summarizing GWAS traits and fetching trait images.
    """
    def __init__(self) -> None:
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not set in environment.")
        try:
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            logging.error(f"Failed to initialize genai client: {e}")
            raise

    def summarise_traits_no_images(self, info: str) -> List[Dict]:
        """
        Summarize GWAS traits using LLM, returning structured data.
        Args:
            info (str): GWAS information string.
        Returns:
            List[Dict]: List of trait summaries.
        """

        print("hrererer")
        prompt = f"""
            You are a medical doctor, part of a program that helps patients understand their genetic variants, along with the GWAS traits they are associated with.
            The GWAS catalog has been searched, and traits that show significance are listed below, along with important details such as the OR value. Each trait should also have an abstract from the study that found the association.

            Give an in depth but comprehensive summary of the GWAS traits, and how they are associated with the variant. 

            The important information is:
            Trait title:
            Increase/decrease of chance as percentage
            Details of the GWAS trait
            Whether having this gene is a good or bad thing

            Data should be given as JSON:
            [
            {{"trait_title": "Trait title", "increase_decrease": "Increase/decrease of chance as percentage", "details": "Details of the GWAS trait", "good_or_bad": "Good or bad"}},
            {{"trait_title": "Trait title", "increase_decrease": "Increase/decrease of chance as percentage", "details": "Details of the GWAS trait", "good_or_bad": "Good or bad"}},
            {{"trait_title": "Trait title", "increase_decrease": "Increase/decrease of chance as percentage", "details": "Details of the GWAS trait", "good_or_bad": "Good or bad"}}
            ]

            {info}
        """
        try:
            # print("prompt", prompt)
            response = self.client.models.generate_content(
                model=GEN_MODEL,
                contents=prompt,
            )
            # print("response", response)
            # Clean up LLM response
            clean_text = response.text.replace("```json", "").replace("```", "")
            return json.loads(clean_text)
        except Exception as e:
            logging.error(f"Error in summarise_traits_no_images: {e}")
            return []

    def find_image(self, trait_title: str) -> Optional[str]:
        """
        Fetch a representative image URL for a given trait title using Bing Images.
        Args:
            trait_title (str): Trait name.
        Returns:
            Optional[str]: Image URL or None if not found.
        """
        try:
            url = (
                f"https://www.bing.com/images/search?q={trait_title}" 
                "+qft=+filterui:aspect-square+filterui:photo-clipart&form=IRFLTR&first=1"
            )
            response = requests.get(url, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            images = soup.find_all('img', {'class': 'mimg'})
            for image_tag in images:
                src = image_tag.get('src', '')
                if src.startswith("http"):
                    return src
        except Exception as e:
            logging.warning(f"Image fetch failed for '{trait_title}': {e}")
        return None

    def summarise_traits(self, traits: str | List[Dict]) -> List[Dict]:
        """
        Summarize traits and fetch images for each trait.
        Args:
            traits (str | List[Dict]): GWAS traits info as either a JSON string or a list of dicts.
        Returns:
            List[Dict]: List of trait summaries with images.
        """
        if isinstance(traits, str):
            traits = traits.replace("```json", "").replace("```", "")
            traits = json.loads(traits)
        print("before", len(traits))
        
        def parse_number(s):
            """Helper to safely parse numbers that might be in scientific notation"""
            try:
                return float(s)
            except (ValueError, TypeError):
                return None

        # Create a new list with only the traits we want to keep
        filtered_traits = []
        for trait in traits:
            # Skip if any required fields are missing
            if (trait.get('traitName') == 'N/A' or 
                trait.get('abstract') is None or
                'pValue' not in trait):
                continue
                
            # Parse p-value (handle scientific notation)
            pval = parse_number(trait['pValue'])
            if pval is None or pval >= 0.01:  # Skip if p-value is missing or >= 0.01
                continue
                
            # Handle OR value
            or_val = trait.get('OR')
            if or_val in ('', 'N/A', None):
                continue
                
            try:
                or_float = float(or_val)
                if abs(or_float - 1) < 0.15:  # Skip if OR is too close to 1.0
                    continue
            except (ValueError, TypeError):
                continue
                
            # If we get here, keep the trait
            filtered_traits.append(trait)
        print("after", len(filtered_traits))
        traits = filtered_traits
        print(filtered_traits[:10])
        
        # Convert traits to a string representation for the LLM
        traits_str = json.dumps(traits, indent=2)
        llm_info = self.summarise_traits_no_images(traits_str)
        
        trait_info_with_images = []
        for trait in llm_info:
            image_url = self.find_image(trait.get('trait_title', ''))
            trait_info_with_images.append({
                'trait_title': trait.get('trait_title'),
                'increase_decrease': trait.get('increase_decrease', 'N/A'),
                'details': trait.get('details', 'No details available'),
                'good_or_bad': trait.get('good_or_bad', 'Neutral'),
                'image_url': image_url
            })
            
        return trait_info_with_images

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    agent = Agent()
    # example_path = "testing_data/example_before_summary.txt"
    example_path = "generated_annotation/final_rag_results_from_rsid_danger.json"
    if os.path.exists(example_path):
        with open(example_path, "r") as f:
            info = f.read()
        trait_info_with_images = agent.summarise_traits(info)
        print(json.dumps(trait_info_with_images, indent=2))
    else:
        logging.error(f"Example file {example_path} not found.")