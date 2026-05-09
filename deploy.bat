@echo off
color 0b
echo ===================================================
echo      Heta AI - Free Cloud Backend Setup
echo ===================================================
echo.
echo Please ensure you have GEMINI_API_KEY set in your environment
echo or in a .env file to use the free cloud AI processing.
echo.
echo Building backend image...
echo This might take a few minutes on the first run.
echo.

docker-compose up -d --build

echo.
echo ===================================================
echo             BACKEND DEPLOYMENT SUCCESSFUL!
echo ===================================================
echo.
echo Your API service is now running:
echo.
echo   [FastAPI Backend] http://localhost:8000
echo   [AI Engine]       Using Gemini Free Cloud API
echo.
echo The Flutter mobile app will automatically connect to this local backend
echo for development, and can be deployed to Render/Railway for production.
echo.
echo To view live server logs, type: docker-compose logs -f
echo To shut down the servers, type: docker-compose down
echo.
pause
