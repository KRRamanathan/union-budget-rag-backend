# Union Budget RAG Backend

A production-ready RAG (Retrieval-Augmented Generation) system for document-based question answering with history-aware retrieval and multi-language support.

## 🌐 Live Demo

**Hosted Backend API**: [https://hcl-test.onrender.com](https://hcl-test.onrender.com)

- Health Check: [https://hcl-test.onrender.com/api/health](https://hcl-test.onrender.com/api/health)
- API Base URL: `https://hcl-test.onrender.com/api`


## Architecture

### System Overview

```
Client (Frontend)
    ↓ HTTP/REST
Flask API Server
    ├── Auth Routes (JWT)
    ├── Chat Routes (RAG Pipeline)
    └── Ingest Routes (Document Processing)
    ↓
PostgreSQL (Users, Chats, Messages) + Pinecone (Vector Store)
```

### RAG Pipeline Flow

```
1. User Message
   ↓
2. Language Detection → Translate to English (if needed)
   ↓
3. Load Chat History (last 8 messages from PostgreSQL)
   ↓
4. History-Aware Query Rewriting
   - Uses LLM to contextualize ambiguous queries
   - Example: "What about infrastructure?" → "What is the infrastructure budget in Union Budget 2026-27?"
   ↓
5. Vector Similarity Search (Pinecone)
   - Generate query embedding (HuggingFace)
   - Retrieve top-K documents (default: 6)
   ↓
6. Response Generation (Gemini LLM)
   - Context: Retrieved documents + Chat history
   - Language: Original user language
   ↓
7. Persist Messages (PostgreSQL)
   - Save user message
   - Save assistant response with sources
   ↓
8. Return Response
```

### High-level Architecture
![Architecture](./hld.jpeg)

### History-Aware Retrieval

**Problem**: Follow-up questions are ambiguous without context.

**Solution**: Query rewriting using chat history.

- **Input**: Chat history + Current query
- **Process**: LLM rewrites query to be standalone and contextual
- **Output**: Improved retrieval accuracy

**Example**:
- Q1: "What is the healthcare budget?"
- A1: "The healthcare budget is $50 billion..."
- Q2: "What about infrastructure?" 
- **Rewritten**: "What is the infrastructure budget allocation in the Union Budget 2026-27?"

### Document Ingestion Flow

```
PDF File
  ↓
Text Extraction (PyMuPDF, page-by-page)
  ↓
Text Chunking (400 chars, 80 overlap)
  ↓
Embedding Generation (HuggingFace all-MiniLM-L6-v2, 384-dim)
  ↓
Vector Storage (Pinecone with metadata)
```

### Component Architecture

**Core Components**:
- `app/rag/retriever.py` - Vector similarity search
- `app/rag/history_aware.py` - Contextual query rewriting
- `app/rag/generator.py` - LLM response generation
- `app/services/language_service.py` - Multi-language detection & translation
- `app/services/embeddings.py` - HuggingFace embeddings
- `app/services/pinecone_client.py` - Vector database operations

**Data Flow**:
- **PostgreSQL**: User authentication, chat sessions, message history
- **Pinecone**: Document embeddings with metadata (doc_name, page_number, chunk_index)
- **Gemini LLM**: Query rewriting, response generation, translation

## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL (Neon recommended)
- Pinecone account
- Google AI Studio API key

### Installation

1. **Install dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Configure environment** (create `.env`):
   ```bash
   DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
   PINECONE_API_KEY=your-pinecone-api-key
   PINECONE_INDEX_NAME=union-budget-rag
   GOOGLE_API_KEY=your-gemini-api-key
   JWT_SECRET=your-super-secret-key-min-32-chars
   JWT_EXPIRY_DAYS=7
   RAG_TOP_K=6
   CHAT_HISTORY_LIMIT=8
   PDF_SOURCE_DIR=./docs
   FLASK_PORT=4000
   ```

3. **Run database migrations**:
   ```bash
   python migrate.py
   ```

4. **Ingest documents**:
   ```bash
   # Add PDFs to docs/ folder
   python ingest.py
   ```

5. **Start server**:
   ```bash
   python run.py
   ```

Server runs at `http://localhost:4000`

## 🌐 Production Deployment

The backend is deployed on **Render**:
- **Live API**: [https://hcl-test.onrender.com](https://hcl-test.onrender.com)
- **Health Check**: [https://hcl-test.onrender.com/api/health](https://hcl-test.onrender.com/api/health)

## Tech Stack

- **Framework**: Flask
- **Database**: PostgreSQL (Neon) + SQLAlchemy ORM
- **Vector DB**: Pinecone
- **RAG Framework**: LangChain
- **Embeddings**: HuggingFace (all-MiniLM-L6-v2, 384-dim)
- **LLM**: Google Gemini 2.0 Flash
- **Auth**: JWT + bcrypt
- **PDF Parsing**: PyMuPDF

## Project Structure

```
backend/
├── app/
│   ├── app.py                 # Flask application
│   ├── config.py              # Configuration
│   ├── routes/                 # API endpoints
│   ├── rag/                    # RAG pipeline components
│   ├── models/                 # Database models
│   ├── services/               # Business logic (PDF, embeddings, etc.)
│   ├── auth/                   # JWT & password handling
│   └── db/                     # Database session & migrations
├── docs/                       # PDF upload directory
├── ingest.py                   # CLI ingestion script
├── migrate.py                  # Database migration script
└── run.py                      # Run API server
```

## Key Features

- **History-Aware Retrieval**: Contextualizes queries using chat history
- **Multi-Language Support**: Detects and responds in 13+ Indian languages
- **Document Ingestion**: Automatic PDF processing with idempotency
- **JWT Authentication**: Secure user authentication
- **Chat Persistence**: PostgreSQL-based chat history
