"""
ChromaDB Vector Database Module
================================
Handles document chunking, embedding, and retrieval for the RAG system.
Uses ChromaDB for vector similarity search to find relevant course information.
"""

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings

# Initialize persistent ChromaDB client
# Data is stored in ./chroma_db directory for persistence across restarts
client = chromadb.PersistentClient(path="./chroma_db")

# Get or create the documents collection
# This collection stores course information as embedded vectors
collection = client.get_or_create_collection(
    name = "documents"
)


def chunker(chunk_id, course_info):
    """
    Convert course information into a searchable text chunk with metadata.
    
    Creates a formatted text representation of a course that will be embedded
    and stored in the vector database. The text is optimized for semantic search
    by repeating key information (name, location, type, instructor) to improve
    retrieval accuracy.
    
    Args:
        chunk_id (str): Unique identifier for this chunk
        course_info (dict): Dictionary containing course details with keys:
            - course_name: Name of the course
            - course_location: Where the course is held
            - course_type: Category (e.g., 'Culinary Arts')
            - course_instructor: Teacher's name
            - course_objectives: Learning goals
            - course_skills: Skills developed
            - course_description: Full description
            - course_cost: Price
            - course_id: Unique course identifier
            - course_latitude: Geographic latitude (optional)
            - course_longitude: Geographic longitude (optional)
    
    Returns:
        dict: Chunk object with structure:
            {
                'id': str,           # Unique chunk identifier
                'text': str,         # Searchable text content
                'metadata': dict     # Structured course metadata
            }
    
    Example:
        >>> course = {'course_name': 'Waffle Weaving', 'course_location': 'York', ...}
        >>> chunk = chunker('1', course)
        >>> chunk['text']
        'Course: Waffle Weaving. Course Location: York...'
    """
    # Create searchable text with repeated key terms for better retrieval
    searchable_text = (
        f"Course: {course_info['course_name']}. "
        f"Course Location: {course_info['course_location']} "
        f"Course Type: {course_info['course_type']} "
        f"Course Instructor: {course_info['course_instructor']} "
        f"Objectives: {course_info['course_objectives']}. "
        f"Skills: {course_info['course_skills']}. "
        f"Description: {course_info['course_description']}. "
        # Repeat key info for emphasis in embeddings
        f"Course: {course_info['course_name']}. "
        f"Course Location: {course_info['course_location']} "
        f"Course Type: {course_info['course_type']} "
        f"Course Instructor: {course_info['course_instructor']}"
    )
    
    # Extract metadata for filtering and display
    metadata = {
        "course_id": str(course_info.get('course_id', '')),
        "course_name": str(course_info.get('course_name', '')),
        "instructor": str(course_info.get('course_instructor', '')),
        "location": str(course_info.get('course_location', '')),
        "latitude": str(course_info.get('course_latitude', '')),
        'longitude': str(course_info.get('course_longitude', '')),
        "cost": str(course_info.get('course_cost', '')),
        "type": str(course_info.get('course_type', ''))
    }
    
    return {
        'id': str(chunk_id),
        'text': searchable_text,
        'metadata': metadata
    }


def add_to_index(chunks):
    """
    Add course chunks to the ChromaDB vector database.
    
    Takes a list of chunk objects and adds them to the collection.
    ChromaDB automatically generates embeddings for the text content
    using its default embedding function.
    
    Args:
        chunks (list): List of chunk dictionaries from chunker() function
    
    Side Effects:
        - Adds documents to ChromaDB collection
        - Prints progress messages to console
    
    Example:
        >>> chunks = [chunker('1', course1), chunker('2', course2)]
        >>> add_to_index(chunks)
        Adding 2 chunks to collection...
        Successfully added chunks. Collection now has 2 documents
    """
    print(f"Adding {len(chunks)} chunks to collection...")
    
    # Add to ChromaDB collection
    collection.add(
        ids = [i.get('id') for i in chunks],
        documents = [i.get('text') for i in chunks],
        metadatas = [i.get('metadata') for i in chunks]
    )
    
    print(f"Successfully added chunks. Collection now has {collection.count()} documents")


def retrieve_chunks(query, n_results=50, course_id_filter=None):
    """
    Retrieve relevant course information using semantic search.
    
    Performs vector similarity search to find courses most relevant to the query.
    Returns formatted text combining course details and metadata for LLM context.
    Can optionally filter results to only include specific course IDs.
    
    The function:
    1. Checks if database has any documents
    2. If course_id_filter provided, retrieves those specific courses directly
    3. Otherwise, performs semantic search using query embeddings
    4. Formats results with metadata for easy LLM consumption
    
    Args:
        query (str): Search query (e.g., "culinary courses in York")
        n_results (int): Maximum number of results to return. Defaults to 50.
        course_id_filter (list, optional): List of course IDs to filter results.
            If provided, only courses with IDs in this list will be returned.
            Useful for location-based filtering. Example: ['CLASS_001', 'CLASS_002']
    
    Returns:
        str: Formatted context string with course information, or error message
            if database is empty. Format:
            ```
            COURSE: [Name]
            ID: [ID] | Cost: [Cost] | Location: [Location] | Lat: [Lat] | Lon: [Lon]
            Details: [Full text]
            ---
            COURSE: [Name]
            ...
            ```
    
    Example:
        >>> context = retrieve_chunks("waffle courses")
        >>> # With location filter
        >>> nearby_ids = ['CLASS_001', 'CLASS_002']
        >>> context = retrieve_chunks("waffle courses", course_id_filter=nearby_ids)
    """
    # Check if database has any documents
    count = collection.count()
    
    if count == 0:
        return "No course information available."
    
    # If we have a course ID filter, retrieve those specific courses directly
    # This ensures we get all nearby courses regardless of semantic similarity
    if course_id_filter is not None and len(course_id_filter) > 0:
        print(f"[DEBUG] Retrieving {len(course_id_filter)} specific courses by ID")
        
        # Get all documents and filter by course ID
        # We need to get enough results to include all filtered courses
        all_results = collection.get(
            limit=count,  # Get all documents
            include=['documents', 'metadatas']
        )
        
        # Filter to only the courses in our filter list
        combined_context = []
        for i in range(len(all_results['documents'])):
            text = all_results['documents'][i]
            meta = all_results['metadatas'][i]
            course_id = meta.get('course_id', '')
            
            if course_id in course_id_filter:
                # Create formatted course entry
                course_entry = (
                    f"COURSE: {meta.get('course_name')}\n"
                    f"ID: {meta.get('course_id')} | Cost: {meta.get('cost')} | "
                    f"Location: {meta.get('location')} | Latitude: {meta.get('latitude')} | "
                    f"Longitude: {meta.get('longitude')}\n"
                    f"Details: {text}\n"
                )
                combined_context.append(course_entry)
        
        # Join all course entries with separator
        final_context = "\n---\n".join(combined_context)
        
        # If no results found, return helpful message
        if not combined_context:
            return "No courses found matching your location criteria."
        
        print(f"[DEBUG] Retrieved {len(combined_context)} courses from filter list")
        return final_context
    
    # No filter - perform normal semantic search
    print(f"[DEBUG] Performing semantic search for: {query}")
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )

    # Format results with metadata
    combined_context = []
    for i in range(len(results['documents'][0])):
        text = results['documents'][0][i]
        meta = results['metadatas'][0][i]

        # Create formatted course entry
        course_entry = (
            f"COURSE: {meta.get('course_name')}\n"
            f"ID: {meta.get('course_id')} | Cost: {meta.get('cost')} | "
            f"Location: {meta.get('location')} | Latitude: {meta.get('latitude')} | "
            f"Longitude: {meta.get('longitude')}\n"
            f"Details: {text}\n"
        )
        combined_context.append(course_entry)
    
    # Join all course entries with separator
    final_context = "\n---\n".join(combined_context)
    
    return final_context