"""
Chat routes for RAG-based conversation.
"""
import logging
from flask import Blueprint, request, jsonify, g

from app.db.session import get_db_session
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage
from app.auth.jwt import jwt_required, get_current_user_id
from app.rag.history_aware import retrieve_with_history, format_chat_history
from app.rag.retriever import format_sources
from app.rag.generator import generate_response, generate_chat_title
from app.services.language_service import process_user_query
from app.config import Config

logger = logging.getLogger(__name__)

chats_bp = Blueprint('chats', __name__)


@chats_bp.route('', methods=['POST'])
@jwt_required
def create_chat():
    """
    Create a new chat session.

    Returns:
        {
            "chat_id": "uuid"
        }
    """
    user_id = get_current_user_id()

    db = get_db_session()
    try:
        chat_session = ChatSession(
            user_id=user_id,
            title=None  # Will be set after first message
        )
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)

        logger.info(f"Chat session created: {chat_session.id}")

        return jsonify({
            "chat_id": str(chat_session.id)
        }), 201

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating chat: {str(e)}")
        return jsonify({"error": "Failed to create chat"}), 500
    finally:
        db.close()


@chats_bp.route('', methods=['GET'])
@jwt_required
def list_chats():
    """
    List all chat sessions for the current user.

    Returns:
        List of chat sessions
    """
    user_id = get_current_user_id()

    db = get_db_session()
    try:
        chats = db.query(ChatSession).filter(
            ChatSession.user_id == user_id
        ).order_by(ChatSession.created_at.desc()).all()

        return jsonify({
            "chats": [chat.to_dict() for chat in chats]
        }), 200

    except Exception as e:
        logger.error(f"Error listing chats: {str(e)}")
        return jsonify({"error": "Failed to list chats"}), 500
    finally:
        db.close()


@chats_bp.route('/<chat_id>', methods=['GET'])
@jwt_required
def get_chat(chat_id):
    """
    Get a chat session with its messages.

    Returns:
        Chat session with messages
    """
    user_id = get_current_user_id()

    db = get_db_session()
    try:
        chat = db.query(ChatSession).filter(
            ChatSession.id == chat_id,
            ChatSession.user_id == user_id
        ).first()

        if not chat:
            return jsonify({"error": "Chat not found"}), 404

        return jsonify(chat.to_dict(include_messages=True)), 200

    except Exception as e:
        logger.error(f"Error getting chat: {str(e)}")
        return jsonify({"error": "Failed to get chat"}), 500
    finally:
        db.close()


@chats_bp.route('/<chat_id>', methods=['DELETE'])
@jwt_required
def delete_chat(chat_id):
    """
    Delete a chat session.
    """
    user_id = get_current_user_id()

    db = get_db_session()
    try:
        chat = db.query(ChatSession).filter(
            ChatSession.id == chat_id,
            ChatSession.user_id == user_id
        ).first()

        if not chat:
            return jsonify({"error": "Chat not found"}), 404

        db.delete(chat)
        db.commit()

        logger.info(f"Chat deleted: {chat_id}")

        return jsonify({"message": "Chat deleted"}), 200

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting chat: {str(e)}")
        return jsonify({"error": "Failed to delete chat"}), 500
    finally:
        db.close()


@chats_bp.route('/<chat_id>/message', methods=['POST'])
@jwt_required
def send_message(chat_id):
    """
    Send a message and get RAG-based response.

    Request body:
        {
            "message": "User's question"
        }

    Returns:
        {
            "answer": "Assistant's response",
            "sources": [{"doc_name": "...", "page_number": ...}]
        }
    """
    user_id = get_current_user_id()
    data = request.get_json()

    if not data or not data.get("message"):
        return jsonify({"error": "Message is required"}), 400

    user_message = data["message"].strip()

    db = get_db_session()
    try:
        # Verify chat belongs to user
        chat = db.query(ChatSession).filter(
            ChatSession.id == chat_id,
            ChatSession.user_id == user_id
        ).first()

        if not chat:
            return jsonify({"error": "Chat not found"}), 404

        # Detect language and translate to English for processing
        english_query, original_language = process_user_query(user_message)
        logger.info(f"Original language: {original_language}, English query: {english_query}")

        # Load existing chat history first (before adding new message)
        # This ensures we get proper pairs of user/assistant messages
        existing_messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == chat_id
        ).order_by(ChatMessage.created_at.asc()).all()

        # Get last N messages (in chronological order) for context
        # We want pairs, so we take the last Config.CHAT_HISTORY_LIMIT messages
        history_messages = existing_messages[-Config.CHAT_HISTORY_LIMIT:] if len(existing_messages) > Config.CHAT_HISTORY_LIMIT else existing_messages

        # Format history for retrieval and generation
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in history_messages
        ]

        # Save user message (save original, not translated)
        user_msg = ChatMessage(
            session_id=chat_id,
            role="user",
            content=user_message
        )
        db.add(user_msg)
        db.commit()

        # Perform history-aware retrieval using English query
        documents, _ = retrieve_with_history(english_query, history)

        # Format history for LLM
        formatted_history = format_chat_history(history)

        # Generate response in the original language
        answer = generate_response(english_query, documents, formatted_history, response_language=original_language)

        # Format sources
        sources = format_sources(documents)

        # Save assistant message
        assistant_msg = ChatMessage(
            session_id=chat_id,
            role="assistant",
            content=answer,
            sources=sources
        )
        db.add(assistant_msg)

        # Update chat title if this is the first message (use English query for title generation)
        if not chat.title:
            chat.title = generate_chat_title(english_query)

        db.commit()

        logger.info(f"Message processed in chat {chat_id}")

        return jsonify({
            "answer": answer,
            "sources": sources,
            "message_id": str(assistant_msg.id)
        }), 200

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        return jsonify({"error": f"Failed to process message: {str(e)}"}), 500
    finally:
        db.close()
