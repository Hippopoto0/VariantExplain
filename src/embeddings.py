from google import genai
from google.genai import types

if __name__ == "__main__":
    genai.configure(api_key="YOUR_API_KEY")
    model = genai.Client().models.get("gemini-2.0-flash")
    response = model.generate("Hello, how are you?")
    print(response.text)