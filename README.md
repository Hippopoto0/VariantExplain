# Variant Explain

A web application that helps users understand the meaning and implications of genetic variants in their genome sequences using RAG (Retrieval-Augmented Generation) technology.

## Features

- Upload and parse VCF files containing genetic variants
- Search GWAS catalog for associated traits
- Generate detailed explanations of trait associations using AI
- Display relevant medical images and visualizations
- Color-coded percentage indicators showing trait likelihood changes
- Interactive Streamlit interface for easy exploration

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/variantexplain.git
cd variantexplain
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Create a `.env` file from the example:
```bash
cp .env.example .env
```

4. Add your API keys to the `.env` file:
```
GOOGLE_API_KEY=your_google_api_key
```

## Usage

1. Start the application:
```bash
poetry run streamlit run src/main.py
```

2. Open your web browser and navigate to the displayed URL (typically http://localhost:8501)

3. Upload your VCF file through the interface
4. The application will:
   - Parse your genetic variants
   - Search for associated traits
   - Generate detailed explanations
   - Display relevant information in an organized format

## Project Structure

```
variantexplain/
├── src/
│   ├── main.py          # Main Streamlit application
│   ├── agent.py         # AI agent for trait summarization
│   ├── embeddings.py    # Embedding generation
│   ├── parse.py         # VCF file parsing
│   ├── vep.py           # Variant Effect Predictor integration
│   └── rag.py           # RAG implementation
├── data/               # Project data directory
├── testing_data/       # Test data directory
└── vcfR_example.rdata  # Example R data file
```

## Dependencies

- Streamlit: For the web interface
- vcfpy: For VCF file parsing
- BeautifulSoup4: For web scraping
- Pydantic: For data validation
- Google Generative AI: For AI-powered explanations
- dotenv: For environment variable management

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Uses Google's Generative AI for trait explanations
- Built with Streamlit for the web interface
- Thanks to the open-source community for all the great libraries used in this project
