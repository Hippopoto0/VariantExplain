from google import genai
import os
import dotenv
import json
import requests
from bs4 import BeautifulSoup
dotenv.load_dotenv()

GEN_MODEL = "gemini-2.0-flash"

class Agent:
    def __init__(self):
        pass

    def summarise_traits_no_images(self, info):
        
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        response = client.models.generate_content(
            model= GEN_MODEL,
            contents=f"""
            You are a medical doctor, part of a program that helps patients understand their genetic variants, along with the GWAS traits they are associated with.
            THe GWAS catalog has been searched, and traits that show significance are listed below, along with important details such as the OR value. Each trait should also have an abstract from the study that found the association.

            Give an in depth but comprehensive summary of the GWAS traits, and how they are associated with the variant. 

            The important information is:
            Trait title:
            Increase/decrease of chance as percentage
            Details of the GWAS trait
            Whether having the trait is a good or bad thing

            Data should be given as JSON:
            [
            {'{"trait_title": "Trait title", "increase_decrease": "Increase/decrease of chance as percentage", "details": "Details of the GWAS trait", "good_or_bad": "Good or bad"}'},
            {'{"trait_title": "Trait title", "increase_decrease": "Increase/decrease of chance as percentage", "details": "Details of the GWAS trait", "good_or_bad": "Good or bad"}'},
            {'{"trait_title": "Trait title", "increase_decrease": "Increase/decrease of chance as percentage", "details": "Details of the GWAS trait", "good_or_bad": "Good or bad"}'},
            ]
            

            {info}
            """,
        )
        return json.loads(response.text.replace("```json", "").replace("```", ""))

    def find_image(self, trait_title):
        # fetch from bing images, url example - https://www.bing.com/images/search?q=Allergic+rhinitis&qft=+filterui:aspect-square+filterui:photo-clipart&form=IRFLTR&first=1

        response = requests.get(f"https://www.bing.com/images/search?q={trait_title}&qft=+filterui:aspect-square+filterui:photo-clipart&form=IRFLTR&first=1")
        soup = BeautifulSoup(response.text, 'html.parser')
        images = soup.find_all('img', {'class': 'mimg'})
        image_source = None
        for image_tag in images:
            if image_tag.has_attr('src'):
                if image_tag['src'].startswith("http"):
                    image_source = {"trait_title": trait_title, "image_url": image_tag['src']}
                    break

        return image_source

    def summarise_traits(self, traits):
        llm_info = self.summarise_traits_no_images(traits)
    
        trait_info_with_images = []
        for trait in llm_info:
            image_result = self.find_image(trait['trait_title'])
            trait_info_with_images.append({
                "trait_title": trait['trait_title'],
                "increase_decrease": trait['increase_decrease'],
                "details": trait['details'],
                "good_or_bad": trait['good_or_bad'],
                "image_url": image_result['image_url'] if image_result else None
            })

        return trait_info_with_images

if __name__ == "__main__":
    agent = Agent()
    with open("testing_data/example_before_summary.txt", "r") as f:
        info = f.read()
    
    trait_info_with_images = agent.summarise_traits(info)

    print(trait_info_with_images)