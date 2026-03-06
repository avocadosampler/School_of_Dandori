#!/bin/bash

# School of Dandori - Docker Quick Start Script

echo "🎓 School of Dandori - Docker Deployment"
echo "========================================"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Creating .env file..."
    echo "OPENROUTER_API_KEY=your-api-key-here" > .env
    echo "✓ Created .env file"
    echo "⚠️  Please edit .env and add your OpenRouter API key"
    echo ""
    read -p "Press Enter after updating .env file..."
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "✓ Docker is running"
echo ""

# Build and start
echo "Building and starting container..."
docker-compose up -d --build

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Container started successfully!"
    echo ""
    echo "📍 Application URL: http://localhost:5000"
    echo ""
    echo "Useful commands:"
    echo "  View logs:    docker-compose logs -f"
    echo "  Stop:         docker-compose down"
    echo "  Restart:      docker-compose restart"
    echo ""
    echo "Waiting for application to be ready..."
    sleep 5
    
    # Check if app is responding
    if curl -s http://localhost:5000 > /dev/null; then
        echo "✓ Application is ready!"
        echo "🌐 Opening browser..."
        
        # Open browser (cross-platform)
        if command -v xdg-open > /dev/null; then
            xdg-open http://localhost:5000
        elif command -v open > /dev/null; then
            open http://localhost:5000
        else
            echo "Please open http://localhost:5000 in your browser"
        fi
    else
        echo "⚠️  Application is starting... Check logs with: docker-compose logs -f"
    fi
else
    echo "❌ Failed to start container. Check the logs with: docker-compose logs"
    exit 1
fi
