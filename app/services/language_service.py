"""
Language detection and translation service.
Detects user query language and translates to English for processing using Gemini,
then ensures response is in the original language.
"""
import logging
import re
from typing import Tuple, Optional
from langdetect import detect, detect_langs, DetectorFactory
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.config import Config

# Initialize logger first
logger = logging.getLogger(__name__)

# Set seed for consistent language detection
DetectorFactory.seed = 0

# Common English words that help identify English text
COMMON_ENGLISH_WORDS = {
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
    'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
    'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
    'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their',
    'what', 'are', 'tax', 'holidays', 'budget', 'union', 'finance', 'can',
    'how', 'when', 'where', 'why', 'who', 'which', 'about', 'explain'
}

# Global LLM instance for translation
_translation_llm = None

# Supported Indian languages
INDIAN_LANGUAGES = {
    'hi': 'Hindi',
    'te': 'Telugu',
    'ta': 'Tamil',
    'kn': 'Kannada',
    'ml': 'Malayalam',
    'mr': 'Marathi',
    'gu': 'Gujarati',
    'bn': 'Bengali',
    'pa': 'Punjabi',
    'or': 'Odia',
    'ur': 'Urdu',
    'as': 'Assamese',
    'ne': 'Nepali',
}


def is_likely_english(text: str) -> bool:
    """
    Check if text is likely English based on common words.
    
    Args:
        text: Text to check
        
    Returns:
        True if likely English
    """
    if not text or not text.strip():
        return True
    
    # Normalize text: lowercase, remove punctuation
    normalized = re.sub(r'[^\w\s]', ' ', text.lower())
    words = set(normalized.split())
    
    # Count English words
    english_word_count = sum(1 for word in words if word in COMMON_ENGLISH_WORDS)
    total_words = len(words)
    
    # If at least 30% of words are common English words, likely English
    if total_words > 0:
        english_ratio = english_word_count / total_words
        return english_ratio >= 0.3
    
    return False


def detect_language(text: str) -> str:
    """
    Detect the language of the input text with improved reliability.
    
    Args:
        text: Input text to detect language for
        
    Returns:
        Language code (e.g., 'en', 'hi', 'te')
    """
    try:
        if not text or not text.strip():
            return 'en'
        
        # First check: if text looks like English based on common words, default to English
        if is_likely_english(text):
            logger.info(f"Text appears to be English based on word analysis: {text[:50]}...")
            # Still run detection but with lower threshold
            try:
                detected_langs = detect_langs(text)
                if detected_langs:
                    top_lang = detected_langs[0]
                    # Only trust non-English if confidence is very high (>0.9)
                    if top_lang.lang != 'en' and top_lang.prob > 0.9:
                        logger.info(f"High confidence non-English detection: {top_lang.lang} ({top_lang.prob:.2f})")
                        return top_lang.lang
                    else:
                        logger.info(f"Low confidence or English detected, defaulting to English. Top: {top_lang.lang} ({top_lang.prob:.2f})")
                        return 'en'
            except Exception:
                pass
            return 'en'
        
        # For non-English-looking text, use detection with confidence check
        detected_langs = detect_langs(text)
        if detected_langs:
            top_lang = detected_langs[0]
            # Require at least 0.7 confidence for non-English languages
            if top_lang.lang != 'en' and top_lang.prob >= 0.7:
                logger.info(f"Detected language: {top_lang.lang} (confidence: {top_lang.prob:.2f}) for text: {text[:50]}...")
                return top_lang.lang
            else:
                # Low confidence or English detected
                logger.info(f"Low confidence detection or English detected. Top: {top_lang.lang} ({top_lang.prob:.2f}), defaulting to English")
                return 'en'
        
        # Fallback to simple detect
        lang_code = detect(text)
        logger.info(f"Detected language (fallback): {lang_code} for text: {text[:50]}...")
        
        # Double-check: if detected as non-English but text looks English, default to English
        if lang_code != 'en' and is_likely_english(text):
            logger.warning(f"Language detection mismatch: detected {lang_code} but text appears English. Defaulting to English.")
            return 'en'
        
        return lang_code
    except Exception as e:
        logger.warning(f"Language detection failed: {e}, defaulting to English")
        return 'en'


def get_translation_llm():
    """Get or initialize the LLM for translation."""
    global _translation_llm
    if _translation_llm is None:
        _translation_llm = ChatGoogleGenerativeAI(
            model=Config.LLM_MODEL,
            google_api_key=Config.GOOGLE_API_KEY,
            temperature=0.1,  # Low temperature for accurate translation
        )
    return _translation_llm


def translate_to_english(text: str, source_lang: str) -> str:
    """
    Translate text from source language to English using Gemini.
    
    Args:
        text: Text to translate
        source_lang: Source language code
        
    Returns:
        Translated text in English
    """
    if source_lang == 'en' or not source_lang:
        return text
    
    try:
        source_lang_name = get_language_name(source_lang)
        
        # Use Gemini for translation
        llm = get_translation_llm()
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are a professional translator. Translate the following text from {source_lang_name} to English. Return ONLY the translated text, nothing else."),
            ("human", "{text}")
        ])
        
        chain = prompt | llm | StrOutputParser()
        translated = chain.invoke({"text": text})
        
        logger.info(f"Translated from {source_lang} ({source_lang_name}) to English: {text[:50]}... -> {translated[:50]}...")
        return translated.strip()
    except Exception as e:
        logger.error(f"Translation to English failed: {e}")
        # Return original text if translation fails
        return text


def translate_from_english(text: str, target_lang: str) -> str:
    """
    Translate text from English to target language using Gemini.
    
    Args:
        text: Text in English to translate
        target_lang: Target language code
        
    Returns:
        Translated text in target language
    """
    if target_lang == 'en' or not target_lang:
        return text
    
    try:
        target_lang_name = get_language_name(target_lang)
        
        # Use Gemini for translation
        llm = get_translation_llm()
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are a professional translator. Translate the following text from English to {target_lang_name}. Return ONLY the translated text, nothing else."),
            ("human", "{text}")
        ])
        
        chain = prompt | llm | StrOutputParser()
        translated = chain.invoke({"text": text})
        
        logger.info(f"Translated from English to {target_lang} ({target_lang_name}): {text[:50]}... -> {translated[:50]}...")
        return translated.strip()
    except Exception as e:
        logger.error(f"Translation from English failed: {e}")
        # Return original text if translation fails
        return text


def get_language_name(lang_code: str) -> str:
    """
    Get the human-readable name of a language.
    
    Args:
        lang_code: Language code
        
    Returns:
        Language name
    """
    if lang_code in INDIAN_LANGUAGES:
        return INDIAN_LANGUAGES[lang_code]
    # Fallback to capitalized code
    return lang_code.upper()


def process_user_query(text: str) -> Tuple[str, str]:
    """
    Process user query: detect language and translate to English if needed.
    
    Args:
        text: User's query text
        
    Returns:
        Tuple of (translated_text_in_english, original_language_code)
    """
    original_lang = detect_language(text)
    
    if original_lang == 'en':
        return text, original_lang
    
    # Translate to English for processing
    english_text = translate_to_english(text, original_lang)
    return english_text, original_lang
