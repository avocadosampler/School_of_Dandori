import fitz
import csv
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time
from pathlib import Path
from .chunker_retriever import chunker, add_to_index


pdf_DIR = Path("courses")
geolocator = Nominatim(user_agent='my_nature_app')
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

def extract_text_pymupdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_course_info(pdf_path):
    full_text = extract_text_pymupdf(pdf_path)
    separated_text = full_text.split("\n")
    
    course_name = ""
    course_instructor = ""
    course_location = ""
    course_type = ""
    course_cost = ""
    course_objectives = ""
    course_materials = ""
    course_skills = ""
    course_description = ""
    course_id = ""
    
    for i, line in enumerate(separated_text):
        if i == 0:
            course_name = line
        elif line == 'Instructor:':
            course_instructor = separated_text[i+1]
        elif line == 'Location:':
            course_location = separated_text[i+1]
        elif line == 'Course Type:':
            print("Found course type")
            course_type = separated_text[i+1]
        elif line == 'Cost:':
            course_cost = separated_text[i+1]
        elif line == 'Learning Objectives':
            objectives = []
            j = 1
            while i+j < len(separated_text) and separated_text[i+j] != 'Provided Materials':
                objectives.append(separated_text[i+j])
                j += 1
            course_objectives = " ".join(objectives)
        elif line == 'Provided Materials':
            j = 1
            materials = []
            while i+j < len(separated_text) and separated_text[i+j] != '• ':
                materials.append(separated_text[i+j])
                j += 1
            course_materials = "\n".join(materials)
        elif line == 'Skills Developed':
            j = 1
            skills = []
            while i+j < len(separated_text) and separated_text[i+j] != "Course Description":
                skills.append(separated_text[i+j])
                j += 1
            course_skills = " ".join(skills)
        elif line == 'Course Description':
            j = 1
            description = []
            while i+j < len(separated_text) and not separated_text[i+j].startswith("Class ID"):
                description.append(separated_text[i+j])
                j += 1
            course_description = " ".join(description)
        elif line.startswith("Class ID"):
            course_id = line
    if ',' in course_location:
        course_location = course_location.split(',')[0]

    course_coordinates = get_coordinates(course_location)
    course_latitude = course_coordinates[0]
    course_longitude = course_coordinates[1]
    
    return {
        'course_name': course_name,
        'course_instructor': course_instructor,
        'course_location': course_location,
        'course_latitude': course_latitude,
        'course_longitude': course_longitude,
        'course_type': course_type,
        'course_cost': course_cost,
        'course_objectives': course_objectives,
        'course_materials': course_materials,
        'course_skills': course_skills,
        'course_description': course_description,
        'course_id': course_id
    }

def process_all_pdfs():
# Process all PDFs in the courses folder
    pdf_files = list(pdf_DIR.glob("*.pdf"))
    courses_data = []
    chunks = []
    i=0
    for pdf_file in pdf_files:
        print(f"Processing {pdf_file.name}...")
        course_info = extract_course_info(pdf_file)
        chunks.append(chunker(str(i), course_info))  # Convert ID to string
        courses_data.append(course_info)
        i += 1

    if chunks:
        print(f"\nPreparing to add {len(chunks)} chunks to index...")
        add_to_index(chunks)
        print(f"Successfully indexed {len(chunks)} course documents")
    else:
        print("Warning: No chunks created!")
    
    return courses_data

def get_coordinates(location_name):
    try:
        location = geocode(f"{location_name}, UK")
        if location:
            return location.latitude, location.longitude
        return None, None
    except Exception as e:
        print(f"Error finding {location_name}: {e}")
        return None, None

def write_to_csv(courses_data):
    # Write to CSV
    csv_filename = "courses_data.csv"
    fieldnames = ['course_name', 'course_instructor', 'course_location', 'course_latitude', 'course_longitude', 'course_type', 
                'course_cost', 'course_objectives', 'course_materials', 'course_skills', 
                'course_description', 'course_id']

    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(courses_data)

    print(f"\nExtracted data from {len(courses_data)} PDF files and saved to {csv_filename}")