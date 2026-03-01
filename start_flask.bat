@echo off
echo Starting Knowledge Graph QA Demo with Neo4j authentication...

rem Set Neo4j environment variables
set NEO4J_URI=bolt://localhost:7687
set NEO4J_USER=neo4j
set NEO4J_PASSWORD=neo4j168

rem Set Flask environment
set FLASK_ENV=development

rem Print configuration
echo Neo4j URI: %NEO4J_URI%
echo Neo4j User: %NEO4J_USER%
echo Flask Environment: %FLASK_ENV%

rem Run Flask application
echo Starting Flask application...
python app.py

pause