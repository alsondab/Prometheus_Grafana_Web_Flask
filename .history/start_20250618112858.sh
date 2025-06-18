#!/bin/bash

# Professional Web App Monitoring Setup Script
# This script helps you start the monitoring stack with proper checks

set -e

echo "🚀 Starting Professional Web App Monitoring Stack"
echo "=================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Check if ports are available
check_port() {
    local port=$1
    local service=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Port $port is already in use. Please stop the service using port $port and try again."
        return 1
    fi
    return 0
}

echo "🔍 Checking port availability..."
ports=(3000 5001 8080 9090 9093 9100)
for port in "${ports[@]}"; do
    if ! check_port $port; then
        exit 1
    fi
done

echo "✅ All ports are available"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file with default configuration..."
    cat > .env << EOF
PROMETHEUS_HEX=default_monitoring_key_$(date +%s)
EOF
    echo "✅ Created .env file"
fi

# Build and start services
echo "🏗️  Building and starting services..."
docker-compose up -d --build

echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🔍 Checking service health..."
services=("flask-app" "prometheus" "grafana" "alertmanager" "node_exporter" "cadvisor")
for service in "${services[@]}"; do
    if docker-compose ps | grep -q "$service.*Up"; then
        echo "✅ $service is running"
    else
        echo "❌ $service is not running properly"
    fi
done

echo ""
echo "🎉 Monitoring stack is ready!"
echo "=================================================="
echo ""
echo "📊 Access your monitoring tools:"
echo "   • Grafana Dashboard: http://localhost:3000 (admin/admin)"
echo "   • Prometheus:        http://localhost:9090"
echo "   • Alertmanager:      http://localhost:9093"
echo "   • Web Application:   http://localhost:5001"
echo "   • Node Exporter:     http://localhost:9100"
echo "   • cAdvisor:          http://localhost:8080"
echo ""
echo "🧪 Test the setup:"
echo "   curl http://localhost:5001/"
echo "   curl http://localhost:5001/api/health"
echo "   curl http://localhost:5001/metrics"
echo ""
echo "📋 Useful commands:"
echo "   • View logs:         docker-compose logs"
echo "   • Stop services:     docker-compose down"
echo "   • Restart services:  docker-compose restart"
echo ""
echo "📚 For more information, check the README.md file"
echo "" 