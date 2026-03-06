"""
School of Dandori - Flask Web Application
==========================================
Main application file for the School of Dandori course catalog and chatbot.
Provides API endpoints for course filtering and an AI-powered chat assistant.
"""

from flask import Flask, render_template, jsonify, request
import csv
import json
from pathlib import Path
from utils.llm import call_llm, get_optimized_query
from utils.chunker_retriever import retrieve_chunks, collection
from utils.haversine import calculate_haversine
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import time

# Initialize Flask application
app = Flask(__name__)

# Global variable to store chat conversation history
global chat_history
chat_history = []

# Initialize geocoder for postcode lookups
geolocator = Nominatim(user_agent="school_of_dandori")


def get_coordinates_from_postcode(postcode):
    """
    Convert a UK postcode to latitude/longitude coordinates.
    
    Uses the Nominatim geocoding service to look up postcode coordinates.
    Includes rate limiting to respect API usage policies.
    
    Args:
        postcode (str): UK postcode (e.g., "SW1A 1AA")
    
    Returns:
        tuple: (latitude, longitude) or None if postcode not found
    
    Example:
        >>> coords = get_coordinates_from_postcode("YO1 7HH")
        >>> coords
        (53.9591, -1.0815)
    """
    try:
        # Add UK country bias for better results
        location = geolocator.geocode(f"{postcode}, UK")
        if location:
            return (location.latitude, location.longitude)
        return None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None



def calculate_distance(coord1, coord2):
    """
    Calculate distance between two geographic coordinates.
    
    Uses the geodesic distance calculation (accounts for Earth's curvature)
    to find the distance between two points.
    
    Args:
        coord1 (tuple): (latitude, longitude) of first point
        coord2 (tuple): (latitude, longitude) of second point
    
    Returns:
        float: Distance in miles, rounded to 1 decimal place
    
    Example:
        >>> york = (53.9591, -1.0815)
        >>> harrogate = (53.9921, -1.5418)
        >>> calculate_distance(york, harrogate)
        23.4
    """
    return round(geodesic(coord1, coord2).miles, 1)


def load_courses_from_csv():
    """
    Load course data from CSV file.
    
    Reads the courses_data.csv file and returns a list of course dictionaries.
    Each course contains information like name, instructor, location, type, etc.
    
    Returns:
        list: List of course dictionaries, or empty list if file doesn't exist
    """
    csv_path = Path('courses_data.csv')
    if not csv_path.exists():
        return []
    
    courses = []
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            courses.append(row)
    return courses


@app.route('/')
def index():
    """
    Render the main homepage.
    
    Returns:
        HTML: The index.html template with course catalog interface
    """
    return render_template('index.html')



@app.route('/api/courses')
def get_courses():
    """
    API endpoint to get filtered courses.
    
    Accepts query parameters for filtering by type, location (postcode + distance), and cost.
    If postcode and distance are provided, calculates distances and filters accordingly.
    
    Query Parameters:
        type (str): Course type filter (e.g., 'Culinary Arts', 'Fiber Arts')
        postcode (str): User's postcode for distance-based filtering
        distance (str): Maximum distance in miles (e.g., '10', '25', '50')
        maxCost (str): Maximum cost in pounds (e.g., '50', '80', '100')
    
    Returns:
        JSON: List of filtered course objects, with 'distance' field added if
              postcode filtering is used
    
    Example:
        GET /api/courses?type=Culinary%20Arts&postcode=YO1%207HH&distance=25&maxCost=80
    """
    courses = load_courses_from_csv()
    type_filter = request.args.get('type', 'All')
    postcode = request.args.get('postcode', '').strip()
    max_distance = request.args.get('distance', 'All')
    max_cost = request.args.get('maxCost', 'All')
    
    # Filter by course type
    filtered = courses
    if type_filter != 'All':
        filtered = [c for c in filtered if c['course_type'] == type_filter]
    
    # Filter by cost
    if max_cost != 'All':
        try:
            max_cost_value = float(max_cost)
            filtered = [c for c in filtered 
                       if float(c.get('course_cost', '£0').replace('£', '').replace(',', '')) <= max_cost_value]
        except (ValueError, AttributeError):
            pass  # Skip cost filtering if there's an error
    
    # Filter by distance if postcode provided
    if postcode and max_distance != 'All':
        try:
            # Get coordinates for user's postcode
            user_coords = get_coordinates_from_postcode(postcode)
            
            if user_coords:
                max_dist = float(max_distance)
                courses_with_distance = []
                
                for course in filtered:
                    # Get course coordinates
                    try:
                        course_lat = float(course.get('course_latitude', 0))
                        course_lon = float(course.get('course_longitude', 0))
                        
                        if course_lat and course_lon:
                            course_coords = (course_lat, course_lon)
                            distance = calculate_distance(user_coords, course_coords)
                            
                            # Only include if within max distance
                            if distance <= max_dist:
                                course['distance'] = distance
                                courses_with_distance.append(course)
                    except (ValueError, TypeError):
                        # Skip courses with invalid coordinates
                        continue
                
                # Sort by distance (closest first)
                filtered = sorted(courses_with_distance, key=lambda x: x.get('distance', float('inf')))
            else:
                # Invalid postcode - return empty list
                filtered = []
        except Exception as e:
            print(f"Distance filtering error: {e}")
            # On error, return unfiltered results
    
    return jsonify(filtered)


@app.route('/api/filters')
def get_filters():
    """
    API endpoint to get available filter options.
    
    Extracts unique course types from all courses to populate the type filter dropdown.
    Location filtering is now handled by postcode + distance, so no location list needed.
    
    Returns:
        JSON: Object containing:
            - types: List of unique course types (with 'All' prepended)
    """
    courses = load_courses_from_csv()
    types = list(set(c['course_type'] for c in courses if c.get('course_type')))
    return jsonify({
        'types': ['All'] + sorted(types)
    })



@app.route('/chat', methods=["POST"])
def chat():
    """
    API endpoint for AI chatbot interactions.
    
    Processes user queries about courses using RAG (Retrieval-Augmented Generation).
    Steps:
    1. Optimizes the user query for better search results and detects location mentions
    2. If location detected, filters courses within 50 miles
    3. Retrieves relevant course information from ChromaDB (filtered by location if applicable)
    4. Sends context + query to LLM for answer generation
    5. Maintains conversation history for context-aware responses
    
    Request Body (JSON):
        query (str): User's question about courses
    
    Returns:
        JSON: Object containing:
            - query: The original user query
            - answer: AI-generated response with course information
    
    Error Responses:
        400: If query is empty
    """
    global chat_history
    
    if request.method == "GET":
        return render_template('chat.html')
    
    # Extract query from request
    data = request.json
    query = data.get("query", "")
    if not query:
        return jsonify({'error': 'Query is empty'}), 400
    
    # Optimize query for better retrieval using conversation history
    # This also extracts location and course type information if mentioned
    try:
        raw_llm_output = get_optimized_query(query, chat_history)
        print(f"[DEBUG] Raw LLM output: {raw_llm_output}")
        
        # Clean up the response - remove markdown code blocks if present
        cleaned_output = raw_llm_output.strip()
        if cleaned_output.startswith('```'):
            # Remove markdown code block formatting
            lines = cleaned_output.split('\n')
            cleaned_output = '\n'.join(lines[1:-1]) if len(lines) > 2 else cleaned_output
        
        extracted = json.loads(cleaned_output)
        search_term = extracted.get("search_query", query)
        location_name = extracted.get("location")
        search_type = extracted.get("search_type", "near")  # Default to "near" for backward compatibility
        course_type = extracted.get("course_type")  # Extract course type filter
        
        print(f"[DEBUG] Search term: {search_term}")
        print(f"[DEBUG] Location detected: {location_name}")
        print(f"[DEBUG] Search type: {search_type}")
        print(f"[DEBUG] Course type detected: {course_type}")
        
    except (json.JSONDecodeError, Exception) as e:
        # If JSON parsing fails, use the original query
        print(f"[ERROR] Query optimization error: {e}")
        print(f"[ERROR] Raw output: {raw_llm_output if 'raw_llm_output' in locals() else 'No output'}")
        search_term = query
        location_name = None
        search_type = "near"
        course_type = None

    # Initialize location-based filtering
    results = []
    course_id_filter = None  # No filtering by default
    
    # Load all courses from CSV for filtering
    database_courses = load_courses_from_csv()
    
    # Apply course type filter if specified
    if course_type and course_type.lower() != 'null':
        print(f"[DEBUG] Filtering by course type: {course_type}")
        database_courses = [
            course for course in database_courses 
            if course.get('course_type', '').strip() == course_type
        ]
        print(f"[DEBUG] Found {len(database_courses)} courses of type '{course_type}'")
    
    # If a location is detected in the query, filter courses by proximity
    # Check for both None and string "null" from JSON
    if location_name and location_name.lower() != 'null':
        print(f"[DEBUG] Processing location: {location_name} (search type: {search_type})")
        
        # Geocode with UK country bias to prioritize UK locations
        # This ensures "York" returns York, UK instead of York, USA
        loc = geolocator.geocode(f"{location_name}, UK", addressdetails=True)
        
        # If no UK result, try without country restriction as fallback
        if not loc:
            print(f"[DEBUG] No UK location found, trying global search")
            loc = geolocator.geocode(location_name)
        
        if loc:
            print(f"[DEBUG] Geocoded '{location_name}' to: {loc.latitude}, {loc.longitude}")
            if hasattr(loc, 'address'):
                print(f"[DEBUG] Full address: {loc.address}")
            
            user_lat, user_lon = loc.latitude, loc.longitude
            
            # Handle "in" vs "near" search types differently
            if search_type == "in":
                # "IN" search: Only exact location matches
                print(f"[DEBUG] Searching for courses IN {location_name} (exact match)")
                for course in database_courses:
                    course_location = course.get('course_location', '').strip()
                    # Case-insensitive exact match
                    if course_location.lower() == location_name.lower():
                        course['distance'] = 0  # Exact match
                        course['course_id'] = course.get('course_id', '')
                        results.append(course)
            else:
                # "NEAR" search: Within 50 miles + exact location matches
                print(f"[DEBUG] Searching for courses NEAR {location_name} (within 50 miles + in location)")
                
                # First, add exact location matches with distance 0
                for course in database_courses:
                    course_location = course.get('course_location', '').strip()
                    if course_location.lower() == location_name.lower():
                        course['distance'] = 0  # Exact match
                        course['course_id'] = course.get('course_id', '')
                        results.append(course)
                
                # Then, add courses within 50 miles (excluding duplicates)
                added_ids = {course['course_id'] for course in results}
                for course in database_courses:
                    course_id = course.get('course_id', '')
                    if course_id in added_ids:
                        continue  # Skip if already added as exact match
                    
                    try:
                        course_lat = float(course.get('course_latitude', 0))
                        course_lon = float(course.get('course_longitude', 0))
                        
                        if course_lat and course_lon:
                            dist = calculate_haversine(user_lat, user_lon, course_lat, course_lon)
                            if dist < 50:
                                course['distance'] = round(dist, 1)
                                course['course_id'] = course.get('course_id', '')
                                course['lat'] = course_lat
                                course['lon'] = course_lon
                                results.append(course)
                    except (ValueError, TypeError):
                        # Skip courses with invalid coordinates
                        continue
            
            # Sort by distance (closest first)
            results = sorted(results, key=lambda x: x.get('distance', 0))
            
            # Extract course IDs to filter ChromaDB search
            # This ensures the chatbot only considers the filtered courses
            course_id_filter = [course['course_id'] for course in results]
            
            if search_type == "in":
                type_info = f" of type '{course_type}'" if course_type and course_type.lower() != 'null' else ""
                print(f"[DEBUG] Found {len(results)} courses{type_info} IN {location_name} (exact match)")
            else:
                # Count exact matches vs nearby
                exact_matches = sum(1 for r in results if r.get('distance', 0) == 0)
                nearby_matches = len(results) - exact_matches
                type_info = f" of type '{course_type}'" if course_type and course_type.lower() != 'null' else ""
                print(f"[DEBUG] Found {len(results)} courses{type_info} NEAR {location_name} ({exact_matches} in location, {nearby_matches} within 50 miles)")
            
            if course_id_filter:
                print(f"[DEBUG] First 3 course IDs: {course_id_filter[:3]}")
        else:
            print(f"[DEBUG] Could not geocode location: {location_name}")
    elif course_type and course_type.lower() != 'null':
        # Course type specified but no location - filter by type only
        print(f"[DEBUG] Filtering by course type only: {course_type}")
        results = database_courses  # Already filtered by type above
        course_id_filter = [course['course_id'] for course in results]
        print(f"[DEBUG] Found {len(results)} courses of type '{course_type}'")
    else:
        print(f"[DEBUG] No location to filter (location_name={location_name})")

    # Retrieve relevant course information from vector database
    # If location or course type was detected, only search within filtered courses
    print(f"[DEBUG] Retrieving chunks with filter: {course_id_filter is not None}")
    context = retrieve_chunks(search_term, course_id_filter=course_id_filter)
    print(f"[DEBUG] Context length: {len(context)} characters")

    # Construct prompt with context and question
    # Add filtering context if applied
    if course_id_filter and len(results) > 0:
        # Build context message based on what filters were applied
        type_mention = f" {course_type}" if course_type and course_type.lower() != 'null' else ""
        
        if location_name and location_name.lower() != 'null':
            # Location filtering was applied
            if search_type == "in":
                location_context = (
                    f"The user asked about{type_mention} courses IN {location_name} (exact location match). "
                    f"The following {len(results)} courses are located specifically in {location_name}:\n\n"
                )
            else:
                # Count exact matches vs nearby for better context
                exact_matches = sum(1 for r in results if r.get('distance', 0) == 0)
                nearby_matches = len(results) - exact_matches
                
                if exact_matches > 0 and nearby_matches > 0:
                    location_context = (
                        f"The user asked about{type_mention} courses NEAR {location_name}. "
                        f"The following {len(results)} courses include {exact_matches} in {location_name} "
                        f"and {nearby_matches} within 50 miles, sorted by distance (closest first):\n\n"
                    )
                elif exact_matches > 0:
                    location_context = (
                        f"The user asked about{type_mention} courses NEAR {location_name}. "
                        f"The following {len(results)} courses are all located in {location_name}:\n\n"
                    )
                else:
                    location_context = (
                        f"The user asked about{type_mention} courses NEAR {location_name}. "
                        f"The following {len(results)} courses are all within 50 miles of {location_name}, "
                        f"sorted by distance (closest first):\n\n"
                    )
        else:
            # Only course type filtering (no location)
            location_context = (
                f"The user asked about {course_type} courses. "
                f"The following {len(results)} courses match this category:\n\n"
            )
        current_prompt = f"{location_context}Context:\n{context}\n\nQuestion: {query}"
    else:
        current_prompt = f"Context:\n{context}\n\nQuestion: {query}"
    
    # Generate answer using LLM with conversation history
    answer = call_llm(current_prompt, chat_history=chat_history)
    
    # Update conversation history
    chat_history.append({"role": "user", "content": query})
    chat_history.append({"role": "assistant", "content": answer})
    
    return jsonify({'query': query, 'answer': answer})



if __name__ == '__main__':
    """
    Application entry point.
    
    Starts the Flask development server.
    
    NOTE: Database and CSV must be pre-generated using setup_database.py
    """
    import sys
    import warnings
    import os
    
    # Suppress Windows socket shutdown warnings
    if sys.platform == 'win32':
        warnings.filterwarnings('ignore', category=ResourceWarning)
    
    # Check if database is populated
    count = collection.count()
    if count == 0:
        print("\n⚠ Database is empty. Checking for CSV to populate...")
        csv_path = Path('courses_data.csv')
        if csv_path.exists():
            print("✓ CSV found. Populating database from CSV...")
            # Import here to avoid circular dependency
            from utils.populate_db import process_data
            process_data()
            count = collection.count()
            if count > 0:
                print(f"✓ Database populated with {count} documents\n")
            else:
                print("⚠ Database population failed\n")
        else:
            print("⚠ No CSV file found. Run 'python setup_database.py' locally first.\n")
    else:
        print(f"\n✓ Database ready with {count} documents\n")
    
    # Verify CSV exists
    csv_path = Path('courses_data.csv')
    if not csv_path.exists():
        print("⚠ WARNING: courses_data.csv not found!")
        print("Course catalog will be empty.\n")
    
    # Start Flask development server
    try:
        # Use 0.0.0.0 to allow external connections (important for Docker)
        # Read PORT from environment variable (Cloud Run sets this to 8080)
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=True, use_reloader=True)
    except (KeyboardInterrupt, SystemExit):
        print("\n\n✓ Server stopped gracefully")
        sys.exit(0)
