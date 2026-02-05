# Union Budget RAG - Complete Setup Guide

## Overview

Union Budget RAG is a full RAG (Retrieval-Augmented Generation) system with:

**Phase 1 - Document Ingestion:**
- PDF text extraction and chunking
- Embeddings via HuggingFace (free)
- Vector storage in Pinecone

**Phase 2 - RAG Chat API:**
- User authentication (JWT)
- Chat sessions with history
- History-aware retrieval (LangChain)
- LLM responses via Gemini 2.5 Flash
- PostgreSQL persistence (Neon)

---

## Required API Keys

| Service | Required | Free Tier | Where to Get |
|---------|----------|-----------|--------------|
| Pinecone | Yes | Yes | [pinecone.io](https://www.pinecone.io/) |
| Google AI (Gemini) | Yes | Yes | [aistudio.google.com](https://aistudio.google.com/apikey) |
| Neon PostgreSQL | Yes | Yes | [neon.tech](https://console.neon.tech/) |
| HuggingFace | No | N/A | Model downloads automatically |

---

## Environment Variables

Create a `.env` file with:

```bash
# ===========================================
# REQUIRED
# ===========================================

# Neon PostgreSQL (from https://console.neon.tech/)
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require

# Pinecone (from https://app.pinecone.io/)
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX_NAME=union-budget-rag

# Gemini (from https://aistudio.google.com/apikey)
GOOGLE_API_KEY=your-gemini-api-key

# JWT Secret (generate a random string)
JWT_SECRET=your-super-secret-key-min-32-chars

# ===========================================
# OPTIONAL (have defaults)
# ===========================================

# LLM Model
LLM_MODEL=gemini-2.0-flash-exp

# JWT expiry
JWT_EXPIRY_DAYS=7

# RAG settings
RAG_TOP_K=6
CHAT_HISTORY_LIMIT=8

# PDF source directory
PDF_SOURCE_DIR=./docs

# Flask settings
FLASK_PORT=4000
FLASK_DEBUG=1
```

---

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Run Database Migrations

```bash
# Check connection
python migrate.py --check

# Run migrations
python migrate.py
```

### 4. Ingest Documents

```bash
# Add PDFs to docs/ folder
cp your-documents/*.pdf ./docs/

# Run ingestion
python ingest.py
```

### 5. Start the API Server

```bash
python run.py
```

Server runs at: `http://localhost:4000`

---

## API Endpoints

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | Register new user |
| `/api/auth/login` | POST | Login and get JWT |
| `/api/auth/me` | GET | Get current user (requires JWT) |

### Chat (requires JWT)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chats` | POST | Create new chat session |
| `/api/chats` | GET | List all user's chats |
| `/api/chats/{id}` | GET | Get chat with messages |
| `/api/chats/{id}` | DELETE | Delete chat |
| `/api/chats/{id}/message` | POST | Send message & get RAG response |

### Document Ingestion

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ingest` | POST | Upload and ingest PDF |
| `/api/ingest/all` | POST | Ingest all PDFs in docs/ |
| `/api/stats` | GET | Get Pinecone index stats |
| `/api/health` | GET | Health check |

---

## API Usage Examples

### Register User

```bash
curl -X POST http://localhost:4000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "password": "password123"
  }'
```

### Login

```bash
curl -X POST http://localhost:4000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "password123"
  }'
```

Response:
```json
{
  "access_token": "eyJ...",
  "user": {"id": "...", "name": "John Doe", "email": "john@example.com"}
}
```

### Create Chat Session

```bash
curl -X POST http://localhost:4000/api/chats \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Send Message (RAG Query)

```bash
curl -X POST http://localhost:4000/api/chats/{chat_id}/message \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the key points in the document?"
  }'
```

Response:
```json
{
  "answer": "Based on the documents...",
  "sources": [
    {"doc_name": "document.pdf", "page_number": 5}
  ]
}
```

---

## Project Structure

```
backend/
├── docs/                      # PDF upload directory
├── app/
│   ├── app.py                 # Flask application
│   ├── config.py              # Configuration
│   ├── ingest_runner.py       # Ingestion orchestrator
│   ├── routes/
│   │   ├── auth.py            # Auth endpoints
│   │   ├── chats.py           # Chat endpoints
│   │   └── ingest.py          # Ingestion endpoints
│   ├── rag/
│   │   ├── retriever.py       # Vector retrieval
│   │   ├── history_aware.py   # History-aware retriever
│   │   └── generator.py       # LLM response generation
│   ├── models/
│   │   ├── user.py            # User model
│   │   ├── chat_session.py    # Chat session model
│   │   └── chat_message.py    # Chat message model
│   ├── services/
│   │   ├── pdf_loader.py      # PDF extraction
│   │   ├── chunker.py         # Text chunking
│   │   ├── embeddings.py      # HuggingFace embeddings
│   │   └── pinecone_client.py # Pinecone operations
│   ├── auth/
│   │   ├── jwt.py             # JWT handling
│   │   └── password.py        # Password hashing
│   ├── db/
│   │   ├── session.py         # Database connection
│   │   └── migrations.sql     # SQL migrations
│   └── utils/
│       ├── file_scanner.py    # Directory scanning
│       └── id_generator.py    # ID generation
├── ingest.py                  # CLI ingestion script
├── migrate.py                 # Database migration script
├── run.py                     # Run API server
├── requirements.txt           # Dependencies
├── .env.example               # Environment template
└── SETUP.md                   # This file
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | Flask |
| Database | PostgreSQL (Neon) |
| ORM | SQLAlchemy |
| Vector DB | Pinecone |
| RAG Framework | LangChain |
| Embeddings | HuggingFace (all-MiniLM-L6-v2) |
| LLM | Google Gemini 2.5 Flash |
| Auth | JWT + bcrypt |
| PDF Parsing | PyMuPDF |

---

## Frontend Integration

The API has CORS enabled for all origins. To integrate with React:

```javascript
// Example: Login
const response = await fetch('http://localhost:4000/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email, password })
});
const { access_token } = await response.json();

// Example: Send message
const response = await fetch(`http://localhost:4000/api/chats/${chatId}/message`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${access_token}`
  },
  body: JSON.stringify({ message: 'Your question here' })
});
const { answer, sources } = await response.json();
```

---

## Troubleshooting

### "DATABASE_URL is not configured"
- Ensure `.env` file exists with valid Neon connection string

### "GOOGLE_API_KEY is required"
- Get API key from [aistudio.google.com](https://aistudio.google.com/apikey)

### "Index does not exist"
- Run `python ingest.py` to auto-create the Pinecone index

### JWT errors
- Ensure `JWT_SECRET` is set in `.env`
- Check token hasn't expired (default: 7 days)

### CORS errors
- API allows all origins by default
- Check your frontend is sending proper headers
