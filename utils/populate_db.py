"""
Script to manually populate the ChromaDB with course data.
Run this before starting the Flask app.
"""
from .pdf_ingester import process_all_pdfs, write_to_csv
from .chunker_retriever import collection

def process_data():
    print("Starting database population...")
    
    # Process PDFs and add to ChromaDB
    courses_data = process_all_pdfs()
    
    # Write to CSV
    write_to_csv(courses_data)
    
    # Verify the data was added
    count = collection.count()
    print(f"\n✓ Database populated successfully!")
    print(f"✓ Total documents in collection: {count}")
    print(f"✓ CSV file created with {len(courses_data)} courses")
    
    if count == 0:
        print("\n⚠ WARNING: No documents were added to the collection!")
        print("Check if PDFs exist in the 'courses' folder")
