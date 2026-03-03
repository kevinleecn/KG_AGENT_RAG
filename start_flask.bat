@echo off
echo Starting Knowledge Graph QA Demo...
echo.
echo NOTE: Configure Neo4j password via /settings page or set NEO4J_PASSWORD environment variable
echo.

rem Set Neo4j environment variables (default: password, change via /settings page)
set NEO4J_URI=bolt://localhost:7687
set NEO4J_USER=neo4j
if "%NEO4J_PASSWORD%"=="" set NEO4J_PASSWORD=password

rem Set Flask environment
set FLASK_ENV=development

rem Print configuration
echo Neo4j URI: %NEO4J_URI%
echo Neo4j User: %NEO4J_USER%
echo Neo4j Password: ********
echo Flask Environment: %FLASK_ENV%
echo.

rem Run Flask application
echo Starting Flask application...
python app.py

pause