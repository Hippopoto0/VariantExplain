from google import genai

import dotenv
import os

dotenv.load_dotenv()

EMBEDDING_MODEL = "text-embedding-004"

class Embedder:
    def __init__(self):
        pass
        # embeddings will be useful when we need to create vector search for further queries, especially if the data is large.
        # for now, it's overkill

    def embed(self, text):
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        response = client.models.embed_content(
            model= EMBEDDING_MODEL,
            contents=text,
        )
        return response.embeddings
    
if __name__ == "__main__":
    embedder = Embedder()
    response = embedder.embed("Explain how AI works in a few words")
    print(response)
    # embedder = Embedder()
    # print(embedder.embed("Hello, how are you?"))