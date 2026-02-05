"""
History-aware retriever for contextual retrieval.
Rewrites queries based on chat history for better retrieval.
"""
import logging
from typing import List, Tuple
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from app.rag.retriever import get_retriever
from app.rag.generator import get_llm

logger = logging.getLogger(__name__)

# Prompt for contextualizing the question based on chat history
CONTEXTUALIZE_PROMPT = """Given a chat history and the latest user question \
which might reference context in the chat history, formulate a standalone question \
which can be understood without the chat history. Do NOT answer the question, \
just reformulate it if needed and otherwise return it as is."""


def get_contextualize_prompt():
    """Get the prompt template for contextualizing questions."""
    return ChatPromptTemplate.from_messages([
        ("system", CONTEXTUALIZE_PROMPT),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}")
    ])


def create_history_aware_rag_retriever():
    """
    Create a history-aware retriever that contextualizes questions.

    Returns:
        History-aware retriever function that returns (docs, contextualized_query)
    """
    llm = get_llm()
    retriever = get_retriever()
    contextualize_prompt = get_contextualize_prompt()

    # Create a chain that contextualizes the query, then retrieves documents
    # Using LCEL (LangChain Expression Language) pattern
    contextualize_chain = contextualize_prompt | llm | StrOutputParser()
    
    def history_aware_retrieve(inputs: dict):
        """Retrieve documents using contextualized query."""
        # If there's no chat history, use the original query
        if not inputs.get("chat_history"):
            contextualized_query = inputs["input"]
        else:
            # Contextualize the query based on chat history
            contextualized_query = contextualize_chain.invoke({
                "input": inputs["input"],
                "chat_history": inputs["chat_history"]
            })
        
        # Retrieve documents using the contextualized query
        docs = retriever.invoke(contextualized_query)
        return docs, contextualized_query
    
    return history_aware_retrieve


def format_chat_history(messages: List[dict]) -> List:
    """
    Format chat messages into LangChain message format.

    Args:
        messages: List of message dicts with 'role' and 'content'

    Returns:
        List of LangChain message objects
    """
    history = []

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")

        if role == "user":
            history.append(HumanMessage(content=content))
        elif role == "assistant":
            history.append(AIMessage(content=content))

    return history


def retrieve_with_history(
    query: str,
    chat_history: List[dict]
) -> Tuple[List, str]:
    """
    Retrieve documents using history-aware retrieval.

    Args:
        query: Current user query
        chat_history: Previous chat messages

    Returns:
        Tuple of (retrieved documents, contextualized query)
    """
    logger.info("Performing history-aware retrieval")

    # Format chat history
    formatted_history = format_chat_history(chat_history)

    # Get history-aware retriever
    history_aware_retriever = create_history_aware_rag_retriever()

    # Retrieve documents
    docs, contextualized_query = history_aware_retriever({
        "input": query,
        "chat_history": formatted_history
    })

    logger.info(f"Retrieved {len(docs)} documents with history context")
    return docs, contextualized_query
