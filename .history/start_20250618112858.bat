@echo off
setlocal enabledelayedexpansion

echo 🚀 Starting Professional Web App Monitoring Stack
echo ==================================================

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker and try again.
    pause
    exit /b 1
)

REM Check if Docker Compose is available
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose is not installed. Please install Docker Compose and try again.
    pause
    exit /b 1
)

echo ✅ Docker and Docker Compose are available

REM Create .env file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file with default configuration...
    echo PROMETHEUS_HEX=default_monitoring_key_%RANDOM% > .env
    echo ✅ Created .env file
)

REM Build and start services
echo 🏗️  Building and starting services...
docker-compose up -d --build

echo ⏳ Waiting for services to start...
timeout /t 10 /nobreak >nul

REM Check service health
echo 🔍 Checking service health...
docker-compose ps

echo.
echo 🎉 Monitoring stack is ready!
echo ==================================================
echo.
echo 📊 Access your monitoring tools:
echo    • Grafana Dashboard: http://localhost:3000 (admin/admin)
echo    • Prometheus:        http://localhost:9090
echo    • Alertmanager:      http://localhost:9093
echo    • Web Application:   http://localhost:5001
echo    • Node Exporter:     http://localhost:9100
echo    • cAdvisor:          http://localhost:8080
echo.
echo 🧪 Test the setup:
echo    curl http://localhost:5001/
echo    curl http://localhost:5001/api/health
echo    curl http://localhost:5001/metrics
echo.
echo 📋 Useful commands:
echo    • View logs:         docker-compose logs
echo    • Stop services:     docker-compose down
echo    • Restart services:  docker-compose restart
echo.
echo 📚 For more information, check the README.md file
echo.
pause 