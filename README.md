# PDF Research Assistant

A powerful RAG (Retrieval-Augmented Generation) system that allows you to chat with your PDF documents using AI. Upload PDFs, ask questions, and get intelligent answers based on the document content.

## 🚀 Features

- **PDF Upload & Processing**: Upload multiple PDF files with automatic text extraction and chunking
- **Intelligent Q&A**: Ask questions about your documents using natural language
- **Semantic Search**: Find relevant information using advanced vector similarity search
- **Multiple Vector Databases**: Support for FAISS and ChromaDB
- **Beautiful UI**: Clean, intuitive Streamlit interface
- **Multi-Document Support**: Query across multiple documents simultaneously
- **Source Attribution**: See exactly which parts of your documents were used to generate answers

## 🛠 Tech Stack

- **Framework**: Streamlit
- **LLM Integration**: LangChain + OpenAI GPT-4
- **PDF Processing**: PyPDF2, pdfplumber, PyMuPDF
- **Vector Databases**: FAISS, ChromaDB
- **Embeddings**: OpenAI text-embedding-ada-002
- **Language**: Python 3.8+

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/justineyoo1/PDFResearchAssistant.git
   cd PDFResearchAssistant
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

5. **Run the application**
   ```bash
   streamlit run app.py
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional (with defaults)
OPENAI_MODEL=gpt-4
EMBEDDING_MODEL=text-embedding-ada-002
VECTOR_DB_TYPE=faiss
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RESULTS=5
```

### Vector Database Options

- **FAISS** (default): Fast, in-memory vector search
- **ChromaDB**: Persistent vector database with metadata support

## 🏗 Project Structure

```
pdf-research-assistant/
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── README.md                      # This file
├── .env.example                   # Environment variables template
├── pdf_assistant/                 # Main package
│   ├── core/                      # Core components
│   │   ├── __init__.py
│   │   ├── base.py               # Abstract base classes
│   │   └── errors/               # Custom exceptions
│   │       ├── __init__.py
│   │       └── pdf_errors.py
│   ├── config/                   # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── ingestion/               # PDF processing components
│   ├── indexing/                # Vector database components  
│   ├── retrieval/               # Search and retrieval
│   ├── generation/              # LLM response generation
│   └── ui/                      # UI components
├── data/                        # Data storage (created automatically)
│   ├── uploads/                 # Uploaded PDFs
│   ├── vector_db/              # Vector database files
│   └── logs/                   # Application logs
└── tests/                      # Unit tests
```

## 🎯 Usage

1. **Start the application**: Run `streamlit run app.py`
2. **Configure API Key**: Enter your OpenAI API key in the sidebar
3. **Upload PDFs**: Use the "Upload & Process" tab to add your documents
4. **Ask Questions**: Switch to "Ask Questions" tab and start chatting with your PDFs
5. **Manage Documents**: View and manage your document library

## 🔄 Development Roadmap

### Stage 1: Core Infrastructure ✅
- [x] Project structure setup
- [x] Base classes and interfaces
- [x] Configuration management
- [x] Error handling framework

### Stage 2: PDF Processing (In Progress)
- [ ] PDF upload and validation
- [ ] Text extraction with multiple libraries
- [ ] Intelligent text chunking
- [ ] Metadata extraction

### Stage 3: Vector Storage & Indexing
- [ ] FAISS integration
- [ ] ChromaDB integration
- [ ] Embedding generation
- [ ] Index management

### Stage 4: Retrieval & Search
- [ ] Similarity search implementation
- [ ] Context assembly
- [ ] Multi-document search
- [ ] Search result ranking

### Stage 5: LLM Integration
- [ ] OpenAI GPT-4 integration
- [ ] Prompt engineering
- [ ] Response generation
- [ ] Source attribution

### Stage 6: UI/UX Enhancement
- [ ] Advanced Streamlit interface
- [ ] Real-time processing indicators
- [ ] Chat history
- [ ] Document management interface

### Stage 7: Advanced Features
- [ ] Multi-PDF support
- [ ] Session persistence
- [ ] Document classification
- [ ] Performance optimization

## 🧪 Testing

Run the test suite:

```bash
pytest tests/
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LangChain](https://langchain.com/) for the RAG framework
- [Streamlit](https://streamlit.io/) for the web interface
- [OpenAI](https://openai.com/) for GPT-4 and embeddings
- [FAISS](https://github.com/facebookresearch/faiss) for vector search

## 📞 Support

If you have any questions or run into issues, please:

1. Check the [Issues](https://github.com/justineyoo1/PDFResearchAssistant/issues) page
2. Create a new issue with detailed information
3. Join our [Discussions](https://github.com/justineyoo1/PDFResearchAssistant/discussions) for community support 