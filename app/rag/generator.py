"""
LLM-based answer generation for RAG pipeline.
Uses Gemini 2.0 Flash for response generation.
"""
import logging
import re
from typing import List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from app.config import Config

logger = logging.getLogger(__name__)

# Global LLM instance
_llm = None

# System prompt for RAG
RAG_SYSTEM_PROMPT = """You are a helpful AI assistant specialized in answering questions about the Union Budget 2026-27 and general finance topics. You are powered by HCL Tech and provide information based on official budget documents.

ABOUT YOU:
- You are an AI assistant focused on Union Budget 2026-27 information
- You help users understand budget allocations, tax reforms, sector-wise initiatives, and financial policies
- You can answer questions about finance, taxation, infrastructure, healthcare, education, and other budget-related topics
- You are designed to make budget information accessible and easy to understand

IMPORTANT INSTRUCTIONS:
1. For greeting questions (like "hi", "hello", "what can you do", "who are you"), introduce yourself and explain your purpose as a Union Budget 2026-27 assistant.
2. Answer questions based on the provided context documents when available.
3. If the answer is not found in the context, say "I couldn't find information about that in the budget documents."
4. Be concise but thorough in your answers.
5. DO NOT include source citations (like "Document 1, Page 1" or similar references) in your response. The sources are tracked separately and will be displayed automatically.
6. Focus on providing clear, natural answers without mentioning document names or page numbers.
7. If the question is unclear, ask for clarification.
8. Always maintain a helpful and professional tone.

Context from documents:
{context}"""


def get_llm() -> ChatGoogleGenerativeAI:
    """
    Get or initialize the LLM.

    Returns:
        ChatGoogleGenerativeAI instance
    """
    global _llm

    if _llm is None:
        logger.info(f"Initializing LLM: {Config.LLM_MODEL}")
        _llm = ChatGoogleGenerativeAI(
            model=Config.LLM_MODEL,
            google_api_key=Config.GOOGLE_API_KEY,
            temperature=0.3,
        )
        logger.info("LLM initialized successfully")

    return _llm


def clean_source_citations(text: str) -> str:
    """
    Remove source citations from the response text.
    Handles patterns like:
    - "(Document 1, Page 1.0; Document 2, Page 10.0)"
    - "Document 1, Page 1.0"
    - "(Document 1, Page 1.0)"
    """
    # Pattern to match parenthetical citations with multiple documents
    # Matches: (Document 1, Page 1.0; Document 2, Page 10.0; ...)
    parenthetical_citation = r'\([^)]*Document\s+\d+[^)]*Page\s+[\d.]+[^)]*(?:\s*;\s*Document\s+\d+[^)]*Page\s+[\d.]+[^)]*)*\)'
    
    # Pattern for standalone citations (not in parentheses)
    standalone_citation = r'Document\s+\d+[^)]*Page\s+[\d.]+[^)]*(?:\s*;\s*Document\s+\d+[^)]*Page\s+[\d.]+[^)]*)*'
    
    cleaned = text
    
    # Remove parenthetical citations first
    cleaned = re.sub(parenthetical_citation, '', cleaned, flags=re.IGNORECASE)
    
    # Remove standalone citations
    cleaned = re.sub(standalone_citation, '', cleaned, flags=re.IGNORECASE)
    
    # Clean up any leftover punctuation and whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)  # Multiple spaces to single space
    cleaned = re.sub(r'\s*\.\s*\.', '.', cleaned)  # Multiple periods
    cleaned = re.sub(r'\s*,\s*,', ',', cleaned)  # Multiple commas
    cleaned = re.sub(r'\s*\(\s*\)', '', cleaned)  # Empty parentheses
    cleaned = cleaned.strip()
    
    return cleaned


def format_docs(docs: List[Document]) -> str:
    """
    Format documents into a context string.

    Args:
        docs: List of retrieved documents

    Returns:
        Formatted context string
    """
    formatted = []

    for i, doc in enumerate(docs, 1):
        doc_name = doc.metadata.get("doc_name", "Unknown")
        page = doc.metadata.get("page_number", "?")
        content = doc.page_content

        formatted.append(f"[Document {i}: {doc_name}, Page {page}]\n{content}")

    return "\n\n---\n\n".join(formatted)


def get_rag_prompt(response_language: str = 'en'):
    """
    Get the RAG prompt template with language instruction.
    
    Args:
        response_language: Language code for the response
    """
    from app.services.language_service import get_language_name
    
    # Get language-specific system prompt
    system_prompt = RAG_SYSTEM_PROMPT
    
    # Add language instruction if not English
    if response_language != 'en':
        lang_name = get_language_name(response_language)
        language_instruction = f"\n\nCRITICAL: The user asked their question in {lang_name} ({response_language}). You MUST respond in {lang_name} ({response_language}). Do NOT respond in English. All your responses must be in {lang_name}."
        system_prompt = system_prompt + language_instruction
    
    return ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}")
    ])


def generate_response(
    query: str,
    documents: List[Document],
    chat_history: List = None,
    response_language: str = 'en'
) -> str:
    """
    Generate a response using the LLM.

    Args:
        query: User's question (in English)
        documents: Retrieved context documents
        chat_history: Previous chat messages (LangChain format)
        response_language: Language code for the response (e.g., 'en', 'hi', 'te')

    Returns:
        Generated response string in the specified language
    """
    if chat_history is None:
        chat_history = []

    logger.info(f"Generating response for query with {len(documents)} context documents in language: {response_language}")

    llm = get_llm()

    # Format context
    context = format_docs(documents)

    # Create prompt with language instruction
    prompt = get_rag_prompt(response_language)

    # Create chain
    chain = prompt | llm | StrOutputParser()

    # Generate response
    response = chain.invoke({
        "context": context,
        "chat_history": chat_history,
        "input": query
    })

    # Clean up any source citations that might have been included
    response = clean_source_citations(response)

    logger.info("Response generated successfully")
    return response


def generate_chat_title(first_message: str) -> str:
    """
    Generate a title for a chat session based on the first message.

    Args:
        first_message: First user message in the chat

    Returns:
        Generated title (max 50 chars)
    """
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Generate a very short title (3-6 words) for a chat that starts with this message. Return only the title, nothing else."),
        ("human", "{message}")
    ])

    chain = prompt | llm | StrOutputParser()

    try:
        title = chain.invoke({"message": first_message})
        # Truncate to 50 chars
        return title[:50].strip()
    except Exception as e:
        logger.warning(f"Failed to generate title: {e}")
        # Fallback: use first few words of message
        words = first_message.split()[:5]
        return " ".join(words)[:50]
