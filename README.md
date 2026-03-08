# School of Dandori

A Flask-based web application featuring an AI-powered course catalog with intelligent search, location-based filtering, and a chatbot assistant for course recommendations.

## Features

- Course catalog with filtering by type, location (postcode + distance), and cost
- AI chatbot powered by OpenRouter for natural language course queries
- RAG (Retrieval-Augmented Generation) using ChromaDB vector database
- Location-based search with distance calculations
- PDF course data ingestion and processing
- Docker support for easy deployment

## Prerequisites

- Python 3.11+
- OpenRouter API key ([Get one here](https://openrouter.ai/keys))
- Course PDF files in the `courses/` folder

## Quick Start

### 1. Clone and Setup Environment

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your OpenRouter API key
# OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### 3. Prepare Course Data

Place your course PDF files in the `courses/` folder, then run:

```bash
python setup_database.py
```

This will:
- Process all PDF files in the `courses/` folder
- Create a ChromaDB vector database in `chroma_db/`
- Generate `courses_data.csv` with course information

### 4. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Docker Deployment

### Development

```bash
# Build and run with docker-compose
docker-compose up --build
```

### Production

```bash
# Use production configuration
docker-compose -f docker-compose.prod.yml up -d
```

Or use the convenience scripts:
- Windows: `docker-start.bat`
- Linux/Mac: `./docker-start.sh`

## Project Structure

```
.
├── app.py                      # Main Flask application
├── setup_database.py           # Database setup script
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
├── Dockerfile                 # Docker configuration
├── docker-compose.yml         # Docker Compose (development)
├── docker-compose.prod.yml    # Docker Compose (production)
├── courses/                   # PDF course files (add your PDFs here)
├── chroma_db/                 # ChromaDB vector database (auto-generated)
├── courses_data.csv           # Course catalog CSV (auto-generated)
├── static/                    # CSS, JS, images
│   ├── style.css
│   ├── script.js
│   └── logo.png
├── templates/                 # HTML templates
│   └── index.html
└── utils/                     # Utility modules
    ├── chunker_retriever.py   # Vector database operations
    ├── haversine.py          # Distance calculations
    ├── llm.py                # LLM integration
    ├── pdf_ingester.py       # PDF processing
    └── populate_db.py        # Database population
```

## API Endpoints

### GET `/`
Main homepage with course catalog interface

### GET `/api/courses`
Get filtered courses

Query Parameters:
- `type`: Course type filter (e.g., 'Culinary Arts', 'Fiber Arts')
- `postcode`: User's postcode for distance-based filtering
- `distance`: Maximum distance in miles (e.g., '10', '25', '50')
- `maxCost`: Maximum cost in pounds (e.g., '50', '80', '100')

Example:
```
GET /api/courses?type=Culinary%20Arts&postcode=YO1%207HH&distance=25&maxCost=80
```

### GET `/api/filters`
Get available filter options (course types)

### POST `/chat`
AI chatbot endpoint

Request Body:
```json
{
  "query": "What cooking courses are available near York?"
}
```

Response:
```json
{
  "query": "What cooking courses are available near York?",
  "answer": "Based on the available courses..."
}
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | Your OpenRouter API key |
| `FLASK_ENV` | No | Flask environment (development/production) |
| `PORT` | No | Server port (default: 5000) |

## Course PDF Format

Course PDFs should follow this structure:

```
Course Name
Instructor: [Name]
Location: [City]
Course Type: [Type]
Cost: £[Amount]
Learning Objectives
[Objectives text]
Provided Materials
[Materials list]
Skills Developed
[Skills text]
Course Description
[Description text]
Class ID: [ID]
```

## Troubleshooting

### Database is empty
Run `python setup_database.py` to populate the database from PDF files.

### No courses showing
Ensure `courses_data.csv` exists and contains data. Check that PDF files are in the `courses/` folder.

### Geocoding errors
The application uses Nominatim for geocoding. If you encounter rate limiting, the script includes delays to respect API limits.

### Docker port conflicts
If port 5000 is in use, modify the port mapping in `docker-compose.yml`:
```yaml
ports:
  - "8080:5000"  # Change 8080 to your preferred port
```

## Development

### Adding New Features

The application uses a modular structure:
- `app.py`: Main Flask routes and logic
- `utils/llm.py`: LLM integration and query optimization
- `utils/chunker_retriever.py`: Vector database operations
- `utils/pdf_ingester.py`: PDF processing and data extraction

### Running Tests

```bash
# Install development dependencies
pip install pytest pytest-flask

# Run tests (if test suite exists)
pytest
```

## License

[Add your license information here]

## Support

[Add support contact information here]
