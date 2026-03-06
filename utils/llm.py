"""
LLM Integration Module
======================
Handles all interactions with the Language Model (LLM) via OpenRouter API.
Provides functions for generating responses and optimizing search queries.
"""

import os
from dotenv import load_dotenv
from openai import OpenAI


# Load environment variables from .env file
load_dotenv()

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
LLM_MODEL = "google/gemini-2.5-flash"  # Using Google's Gemini model via OpenRouter

# Initialize OpenAI client configured for OpenRouter
client = OpenAI(
    base_url = "https://openrouter.ai/api/v1",
    api_key = OPENROUTER_API_KEY
)


def call_llm(user_prompt, chat_history=None, is_rewriting=False):
    """
    Call the Language Model to generate a response.
    
    This function handles two modes:
    1. Normal mode: Answers user questions about courses using provided context
    2. Rewriting mode: Optimizes search queries by incorporating conversation history
    
    Args:
        user_prompt (str): The user's question or the prompt to send to the LLM
        chat_history (list, optional): List of previous conversation messages in format:
            [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        is_rewriting (bool): If True, optimizes the query for search. If False, generates
            a conversational response. Defaults to False.
    
    Returns:
        str: The LLM's generated response text
    
    Example:
        >>> answer = call_llm("What courses are in York?", chat_history=[])
        >>> optimized = call_llm("What about there?", chat_history=history, is_rewriting=True)
    """
    # Set system prompt based on mode
    if is_rewriting:
        # Query optimization mode: Create standalone search terms
        system_content = (
            "You are a search optimizer. Extract the search intent, any specific location, and course type mentioned. "
            "Also determine if the user wants courses IN a specific location (exact match) or NEAR a location (within range). "
            "IMPORTANT: Maintain context from previous messages. If the user previously specified a course type or location "
            "and doesn't explicitly change it in the current query, keep using the previous filter. "
            "Return ONLY a valid JSON object (no markdown, no code blocks) with this exact format: "
            '{"search_query": "standalone query", "location": "city or address or null", "search_type": "in or near", "course_type": "type or null"}. '
            "If no location is mentioned AND no previous location exists, use null for location and null for search_type. "
            "If no specific course type is mentioned AND no previous type exists, use null for course_type. "
            'Use "in" for queries like "courses in Cambridge", "classes in York". '
            'Use "near" for queries like "courses near Leeds", "around Manchester", "close to Birmingham". '
            'For course_type, map user terms to these categories: '
            '"Culinary Arts" (cooking, baking, food, culinary, pastry, marmalade, biscuit), '
            '"Fiber Arts" (knitting, crochet, weaving, yarn, wool, textile, felting), '
            '"Nature Crafts" (leaf, moss, cloud, nature, botanical), '
            '"Traditional Skills" (spoon carving, blacksmithing, woodworking, medieval), '
            '"Wellness" (yoga, meditation, mindfulness, zen, laughter), '
            '"Creative Arts" (painting, drawing, art, sculpting, pottery), '
            '"Heritage Crafts" (Victorian, historical, traditional), '
            '"Outdoor Skills" (foraging, outdoor, wilderness), '
            '"Seasonal Activities" (pumpkin, autumn, seasonal), '
            '"Mindfulness" (meditation, mindful, zen, calm). '
            'Examples: '
            'User previously asked about "cooking classes near Cambridge", now asks "what about the one in Norfolk?" '
            '→ {"search_query": "cooking classes in Norfolk", "location": "Norfolk", "search_type": "in", "course_type": "Culinary Arts"} '
            'User previously asked about "knitting courses", now asks "any in York?" '
            '→ {"search_query": "knitting courses in York", "location": "York", "search_type": "in", "course_type": "Fiber Arts"} '
            'User asks "show me something different" after asking about cooking '
            '→ {"search_query": "courses", "location": null, "search_type": null, "course_type": null}'
        )
    else:
        # Conversational mode: Answer questions about courses
        system_content = (
            "You are a helpful assistant for the School of Dandori. You are very human-like, and "
            "your job is to recommend courses based on their questions. "
            "IMPORTANT: When the context includes courses 'within X miles' or 'near' a location, these are "
            "courses available in that area. Treat them as valid options for that location. "
            "For example, if asked about Leeds and given courses within 50 miles of Leeds, recommend those courses. "
            "When a user asks about courses in a location, provide a brief overview of what's available "
            "(e.g., 'Yes! We have 31 courses near Leeds including culinary arts, fiber arts, etc.') "
            "and mention 2-3 specific examples with instructor names. Then ask what they're interested in. "
            "You do not need to include the course code for any courses you recommend. "
            "Use ONLY the provided context to answer. If the context doesn't contain any courses, "
            "state that clearly. Do not make up information."
        )

    # Build message list starting with system prompt
    messages = [
        {"role": "system", "content": system_content}
    ]

    # Add conversation history if provided
    if chat_history:
        # For rewriting, only use last 3 messages for context
        # For normal chat, use full history
        messages.extend(chat_history[-3:] if is_rewriting else chat_history)
    
    # Add current user prompt
    messages.append({"role": "user", "content": user_prompt})
    
    # Call the LLM API
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=0.1,  # Low temperature for more consistent, factual responses
    )
    
    return response.choices[0].message.content


def get_optimized_query(query, chat_history):
    """
    Optimize a user query for better search results.
    
    Takes a potentially ambiguous query (e.g., "What about there?") and rewrites it
    into a standalone search term by incorporating context from the conversation history.
    Also extracts location information if mentioned.
    
    This is crucial for RAG (Retrieval-Augmented Generation) systems where the search
    query needs to be self-contained to retrieve relevant documents.
    
    Args:
        query (str): The user's original query, which may reference previous context
        chat_history (list): Previous conversation messages for context
    
    Returns:
        str: JSON string with format: {"search_query": "...", "location": "..." or null}
    
    Example:
        User: "What courses are in York?"
        Assistant: "We have waffle weaving in York..."
        User: "What about Harrogate?"
        
        >>> get_optimized_query("What about Harrogate?", history)
        '{"search_query": "courses in Harrogate", "location": "Harrogate"}'
    """
    # Use LLM to rewrite query with context and extract location
    return call_llm(f"Rewrite this query: {query}", chat_history=chat_history, is_rewriting=True)