"""
Standalone script to populate ChromaDB and generate courses_data.csv
Run this once before deploying the application.

Usage:
    python setup_database.py
"""
import sys
import warnings
from utils.populate_db import process_data
from utils.chunker_retriever import collection

if __name__ == '__main__':
    # Suppress Windows socket shutdown warnings
    if sys.platform == 'win32':
        warnings.filterwarnings('ignore', category=ResourceWarning)
    
    print("=" * 60)
    print("School of Dandori - Database Setup")
    print("=" * 60)
    print("\nThis will process all PDF files and create:")
    print("  1. ChromaDB vector database (chroma_db/)")
    print("  2. Course catalog CSV (courses_data.csv)")
    print("\nStarting...\n")
    
    # Process PDFs and populate database
    process_data()
    
    # Verify the data was added
    count = collection.count()
    
    print("\n" + "=" * 60)
    if count > 0:
        print("✓ Setup completed successfully!")
        print(f"✓ Database contains {count} documents")
        print("✓ CSV file created")
        print("\nYou can now run the Flask app with: python app.py")
    else:
        print("⚠ WARNING: Setup completed but database is empty!")
        print("Check if PDF files exist in the 'courses' folder")
    print("=" * 60)
