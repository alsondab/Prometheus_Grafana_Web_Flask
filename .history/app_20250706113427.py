from flask import Flask, request, abort, jsonify, render_template_string
from prometheus_client import Counter, Histogram, generate_latest, Gauge, Summary, Info
from dotenv import load_dotenv
import os
import time
import requests
import random
import threading
import logging
from datetime import datetime, timedelta
from functools import wraps

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
SHARED_KEY = os.getenv('PROMETHEUS_HEX', 'default_key')

# ===== PROMETHEUS METRICS =====

# Counters
endpoint_clicks = Counter('endpoint_clicks', 'Total clicks per endpoint', ['endpoint', 'method'])
error_counter = Counter('endpoint_errors', 'Total errors per endpoint and status code', ['endpoint', 'status_code'])
user_signups = Counter('user_signups', 'Total user signups')
api_calls = Counter('api_calls', 'Total API calls', ['endpoint', 'method'])
database_operations = Counter('database_operations', 'Database operations', ['operation', 'table'])

# Histograms
endpoint_latency = Histogram('endpoint_latency_seconds', 'Endpoint response time', ['endpoint', 'method'])
request_size = Histogram('request_size_bytes', 'Request size in bytes', ['endpoint'])
response_size = Histogram('response_size_bytes', 'Response size in bytes', ['endpoint'])
db_query_time = Histogram('db_query_time_seconds', 'Database query time', ['operation'])

# Gauges
active_requests = Gauge('active_requests', 'Number of active requests')
active_users = Gauge('active_users', 'Number of active users')
memory_usage = Gauge('memory_usage_bytes', 'Memory usage in bytes')
cpu_usage = Gauge('cpu_usage_percent', 'CPU usage percentage')
database_connections = Gauge('database_connections', 'Number of database connections')

# Summaries
request_duration = Summary('request_duration_seconds', 'Request duration in seconds', ['endpoint'])

# Info
app_info = Info('app_info', 'Application information')
app_info.info({'version': '2.0.0', 'environment': 'production'})

# ===== SIMULATED METRICS =====

def simulate_system_metrics():
    """Simulate system metrics for demonstration"""
    while True:
        # Simulate memory usage (100MB to 500MB)
        memory_usage.set(random.randint(100000000, 500000000))
        
        # Simulate CPU usage (10% to 80%)
        cpu_usage.set(random.uniform(10.0, 80.0))
        
        # Simulate database connections (5 to 20)
        database_connections.set(random.randint(5, 20))
        
        # Simulate active users (10 to 100)
        active_users.set(random.randint(10, 100))
        
        time.sleep(30)  # Update every 30 seconds

# Start system metrics simulation
metrics_thread = threading.Thread(target=simulate_system_metrics, daemon=True)
metrics_thread.start()

def get_location(ip):
    """Get location from IP address"""
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        data = response.json()
        if data['status'] == 'success':
            return [data['lat'], data['lon']]
        else:
            return [0.0, 0.0]
    except Exception as e:
        logger.warning(f"Failed to get location for IP {ip}: {e}")
        return [0.0, 0.0]  

def simulate_database_operation(operation, table):
    """Simulate database operations with random latency"""
    database_operations.labels(operation=operation, table=table).inc()
    
    # Simulate database query time
    query_time = random.uniform(0.01, 0.5)
    db_query_time.labels(operation=operation).observe(query_time)
    
    time.sleep(query_time)  # Simulate actual database operation
    return True

@app.before_request
def start_timer():
    """Start timer for request duration tracking"""
    request.start_time = time.time()
    active_requests.inc()

@app.after_request
def track_metrics(response):
    """Track various metrics after each request"""
    if request.path != '/favicon.ico' and request.path != '/metrics':
        # Track endpoint clicks
        endpoint_clicks.labels(endpoint=request.path, method=request.method).inc()
        
        # Track API calls
        api_calls.labels(endpoint=request.path, method=request.method).inc()
        
        # Track request duration
        request_latency = time.time() - request.start_time
        endpoint_latency.labels(endpoint=request.path, method=request.method).observe(request_latency)
        request_duration.labels(endpoint=request.path).observe(request_latency)
        
        # Track request/response sizes
        request_size.labels(endpoint=request.path).observe(len(request.data))
        response_size.labels(endpoint=request.path).observe(len(response.data))
        
        logger.info(f"{request.method} {request.path} - {response.status_code} - {request_latency:.3f}s")
    
    active_requests.dec()
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle general exceptions"""
    error_counter.labels(endpoint=request.path, status_code="500").inc()
    active_requests.dec()
    logger.error(f"Unhandled exception: {e}")
    return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    error_counter.labels(endpoint=request.path, status_code="404").inc()
    active_requests.dec()
    return jsonify({"error": "Not Found", "message": "The requested resource was not found"}), 404

@app.errorhandler(403)
def forbidden(e):
    """Handle 403 errors"""
    error_counter.labels(endpoint=request.path, status_code="403").inc()
    active_requests.dec()
    return jsonify({"error": "Forbidden", "message": "Access denied"}), 403

@app.route('/metrics')
def metrics():
    """Expose Prometheus metrics"""
    try:
        return generate_latest(), 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        abort(500)

@app.route('/')
def home():
    """Home page with dashboard-like interface"""
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Web App Monitoring Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px; }
            .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .metric-value { font-size: 2em; font-weight: bold; color: #3498db; }
            .metric-label { color: #7f8c8d; margin-top: 5px; }
            .nav-links { margin-top: 20px; }
            .nav-links a { color: #3498db; text-decoration: none; margin-right: 20px; }
            .nav-links a:hover { text-decoration: underline; }
            .status { padding: 10px; border-radius: 4px; margin: 10px 0; }
            .status.ok { background: #d4edda; color: #155724; }
            .status.warning { background: #fff3cd; color: #856404; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Web App Monitoring Dashboard</h1>
                <p>Professional monitoring setup with Prometheus and Grafana</p>
            </div>
            
            <div class="status ok">
                ✅ System Status: All services running normally
            </div>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">📊</div>
                    <div class="metric-label">Prometheus Metrics</div>
                    <p>Real-time metrics collection and monitoring</p>
                </div>
                <div class="metric-card">
                    <div class="metric-value">📈</div>
                    <div class="metric-label">Grafana Dashboards</div>
                    <p>Beautiful visualizations and analytics</p>
                </div>
                <div class="metric-card">
                    <div class="metric-value">🔍</div>
                    <div class="metric-label">Performance Tracking</div>
                    <p>Response times, error rates, and system health</p>
                </div>
                <div class="metric-card">
                    <div class="metric-value">⚡</div>
                    <div class="metric-label">Real-time Alerts</div>
                    <p>Proactive monitoring and alerting</p>
                </div>
            </div>
            
            <div class="nav-links">
                <a href="/api/health">Health Check</a>
                <a href="/api/users">Users API</a>
                <a href="/api/products">Products API</a>
                <a href="/api/orders">Orders API</a>
                <a href="/metrics">Raw Metrics</a>
            </div>
            
            <div style="margin-top: 30px; padding: 20px; background: white; border-radius: 8px;">
                <h3>Quick Links:</h3>
                <ul>
                    <li><strong>Grafana Dashboard:</strong> <a href="http://localhost:3000" target="_blank">http://localhost:3000</a> (admin/admin)</li>
                    <li><strong>Prometheus:</strong> <a href="http://localhost:9090" target="_blank">http://localhost:9090</a></li>
                    <li><strong>Node Exporter:</strong> <a href="http://localhost:9100" target="_blank">http://localhost:9100</a></li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template)

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    health_data = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "services": {
            "web_server": "running",
            "database": "connected",
            "cache": "available"
        }
    }
    return jsonify(health_data)

@app.route('/api/users')
def get_users():
    """Simulate user data API"""
    simulate_database_operation("SELECT", "users")
    
    # Simulate some random errors
    if random.random() < 0.05:  # 5% error rate
        raise Exception("Database connection timeout")
    
    users = [
        {"id": 1, "name": "John Doe", "email": "john@example.com"},
        {"id": 2, "name": "Jane Smith", "email": "jane@example.com"},
        {"id": 3, "name": "Bob Johnson", "email": "bob@example.com"}
    ]
    return jsonify({"users": users, "count": len(users)})

@app.route('/api/products')
def get_products():
    """Simulate products API"""
    simulate_database_operation("SELECT", "products")
    
    products = [
        {"id": 1, "name": "Laptop", "price": 999.99, "category": "Electronics"},
        {"id": 2, "name": "Mouse", "price": 29.99, "category": "Electronics"},
        {"id": 3, "name": "Keyboard", "price": 79.99, "category": "Electronics"}
    ]
    return jsonify({"products": products, "count": len(products)})

@app.route('/api/orders')
def get_orders():
    """Simulate orders API with potential errors"""
    simulate_database_operation("SELECT", "orders")
    
    # Simulate higher error rate for orders
    if random.random() < 0.1:  # 10% error rate
        raise Exception("Orders service temporarily unavailable")
    
    orders = [
        {"id": 1, "user_id": 1, "total": 1029.98, "status": "completed"},
        {"id": 2, "user_id": 2, "total": 79.99, "status": "pending"}
    ]
    return jsonify({"orders": orders, "count": len(orders)})

@app.route('/api/users', methods=['POST'])
def create_user():
    """Create user endpoint"""
    simulate_database_operation("INSERT", "users")
    user_signups.inc()
    
    user_data = request.get_json()
    return jsonify({
        "message": "User created successfully",
        "user_id": random.randint(1000, 9999),
        "user": user_data
    }), 201

@app.route('/slow')
def slow_endpoint():
    """Simulate slow endpoint for testing"""
    time.sleep(random.uniform(1, 5))
    return jsonify({"message": "This was a slow request"})

@app.route('/error')
def error_endpoint():
    """Simulate error endpoint"""
    raise Exception("This is a simulated error for testing")

@app.route('/about')
def about():
    """About page"""
    return jsonify({
        "name": "Professional Web App Monitor",
        "description": "A comprehensive monitoring solution using Prometheus and Grafana",
        "features": [
            "Real-time metrics collection",
            "Performance monitoring",
            "Error tracking",
            "System health monitoring",
            "Beautiful dashboards"
        ]
    })

if __name__ == '__main__': 
    logger.info("Starting Web App Monitor on port 5001...")
    app.run(host='0.0.0.0', port=5001, debug=False)