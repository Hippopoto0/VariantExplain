from google import genai

import dotenv
import os

dotenv.load_dotenv()

EMBEDDING_MODEL = "text-embedding-004"

class Embedder:
    def __init__(self):
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel('gemini-pro')

    def embed(self, text):
        response = self.model.generate_content(
            text,
            generation_config=genai.GenerativeModel.GenerativeConfig(
                embedding=True
            )
        )
        return response.embedding
    
if __name__ == "__main__":
    embedder = Embedder()
    response = embedder.embed("Explain how AI works in a few words")
    print(response)
    # embedder = Embedder()
    # print(embedder.embed("Hello, how are you?"))