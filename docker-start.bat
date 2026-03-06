@echo off
REM School of Dandori - Docker Quick Start Script (Windows)

echo.
echo 🎓 School of Dandori - Docker Deployment
echo ========================================
echo.

REM Check if .env file exists
if not exist .env (
    echo ⚠️  .env file not found!
    echo Creating .env file...
    echo OPENROUTER_API_KEY=your-api-key-here > .env
    echo ✓ Created .env file
    echo ⚠️  Please edit .env and add your OpenRouter API key
    echo.
    pause
)

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo ✓ Docker is running
echo.

REM Build and start
echo Building and starting container...
docker-compose up -d --build

if %errorlevel% equ 0 (
    echo.
    echo ✓ Container started successfully!
    echo.
    echo 📍 Application URL: http://localhost:5000
    echo.
    echo Useful commands:
    echo   View logs:    docker-compose logs -f
    echo   Stop:         docker-compose down
    echo   Restart:      docker-compose restart
    echo.
    echo Waiting for application to be ready...
    timeout /t 5 /nobreak >nul
    
    echo ✓ Application should be ready!
    echo 🌐 Opening browser...
    start http://localhost:5000
) else (
    echo ❌ Failed to start container. Check the logs with: docker-compose logs
    pause
    exit /b 1
)

echo.
pause
