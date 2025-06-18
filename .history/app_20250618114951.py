from flask import Flask, request, abort, jsonify, render_template_string
from prometheus_client import (
    Counter, Histogram, generate_latest, Gauge, Summary, Info, 
    CollectorRegistry, multiprocess, generate_latest
)
from dotenv import load_dotenv
import os
import time
import requests
import random
import threading
import logging
import psutil
import json
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.exceptions import HTTPException
import uuid

# Load environment variables
load_dotenv()

# Application configuration
class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    PROMETHEUS_HEX = os.getenv('PROMETHEUS_HEX', 'default-key')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    MONITORING_INTERVAL = int(os.getenv('MONITORING_INTERVAL', '30'))

# Initialize Flask app with better configuration
app = Flask(__name__)
app.config.from_object(Config)

# Enhanced logging configuration
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===== ENHANCED PROMETHEUS METRICS =====

# Application metrics
http_requests_total = Counter(
    'http_requests_total', 
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

http_request_size_bytes = Histogram(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint']
)

http_response_size_bytes = Histogram(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint']
)

# Business metrics
user_registrations_total = Counter('user_registrations_total', 'Total user registrations')
api_calls_total = Counter('api_calls_total', 'Total API calls', ['endpoint', 'method'])
database_operations_total = Counter(
    'database_operations_total', 
    'Database operations counter',
    ['operation', 'table', 'status']
)

# System metrics
system_cpu_usage_percent = Gauge('system_cpu_usage_percent', 'System CPU usage percentage')
system_memory_usage_bytes = Gauge('system_memory_usage_bytes', 'System memory usage in bytes')
system_memory_available_bytes = Gauge('system_memory_available_bytes', 'System available memory in bytes')
system_disk_usage_percent = Gauge('system_disk_usage_percent', 'System disk usage percentage')
active_connections = Gauge('active_connections', 'Number of active connections')
database_connection_pool_size = Gauge('database_connection_pool_size', 'Database connection pool size')

# Application health metrics
app_uptime_seconds = Gauge('app_uptime_seconds', 'Application uptime in seconds')
app_health_score = Gauge('app_health_score', 'Application health score (0-100)')

# Performance metrics
database_query_duration_seconds = Histogram(
    'database_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'table']
)

external_api_duration_seconds = Histogram(
    'external_api_duration_seconds',
    'External API call duration in seconds',
    ['service', 'endpoint']
)

# Error tracking
error_rate = Gauge('error_rate_percent', 'Error rate percentage')
last_error_timestamp = Gauge('last_error_timestamp', 'Timestamp of last error')

# Application info
app_info = Info('app_info', 'Application information')
app_info.info({
    'version': '3.0.0',
    'environment': os.getenv('ENVIRONMENT', 'production'),
    'build_date': datetime.now().isoformat(),
    'python_version': f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}",
    'hostname': os.uname().nodename if hasattr(os, 'uname') else 'unknown'
})

# ===== SYSTEM MONITORING =====

class SystemMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.error_count = 0
        self.total_requests = 0
        
    def collect_system_metrics(self):
        """Collect comprehensive system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            system_cpu_usage_percent.set(cpu_percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            system_memory_usage_bytes.set(memory.used)
            system_memory_available_bytes.set(memory.available)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            system_disk_usage_percent.set(disk_usage_percent)
            
            # Application uptime
            uptime = time.time() - self.start_time
            app_uptime_seconds.set(uptime)
            
            # Calculate health score
            health_score = self.calculate_health_score(cpu_percent, memory.percent, disk_usage_percent)
            app_health_score.set(health_score)
            
            # Database connection simulation
            database_connection_pool_size.set(random.randint(5, 25))
            
            # Network connections
            active_connections.set(len(psutil.net_connections()))
            
            logger.debug(f"System metrics updated - CPU: {cpu_percent}%, Memory: {memory.percent}%, Health: {health_score}")
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def calculate_health_score(self, cpu_percent, memory_percent, disk_percent):
        """Calculate application health score based on system metrics"""
        score = 100
        
        # Penalize high resource usage
        if cpu_percent > 80:
            score -= 30
        elif cpu_percent > 60:
            score -= 15
        
        if memory_percent > 90:
            score -= 25
        elif memory_percent > 70:
            score -= 10
        
        if disk_percent > 95:
            score -= 20
        elif disk_percent > 85:
            score -= 10
        
        # Factor in error rate
        if self.total_requests > 0:
            current_error_rate = (self.error_count / self.total_requests) * 100
            if current_error_rate > 10:
                score -= 20
            elif current_error_rate > 5:
                score -= 10
        
        return max(0, score)
    
    def increment_error(self):
        self.error_count += 1
        last_error_timestamp.set(time.time())
        if self.total_requests > 0:
            error_rate.set((self.error_count / self.total_requests) * 100)
    
    def increment_request(self):
        self.total_requests += 1
        if self.total_requests > 0:
            error_rate.set((self.error_count / self.total_requests) * 100)

# Initialize system monitor
system_monitor = SystemMonitor()

def start_system_monitoring():
    """Start system monitoring in background thread"""
    def monitor_loop():
        while True:
            system_monitor.collect_system_metrics()
            time.sleep(Config.MONITORING_INTERVAL)
    
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    logger.info("System monitoring started")

# ===== MIDDLEWARE AND DECORATORS =====

def require_api_key(f):
    """Decorator to require API key for sensitive endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key != Config.PROMETHEUS_HEX:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def before_request():
    """Enhanced request preprocessing"""
    request.start_time = time.time()
    request.request_id = str(uuid.uuid4())
    
    # Skip metrics for static files and health checks
    if request.path not in ['/favicon.ico', '/health', '/metrics']:
        system_monitor.increment_request()

@app.after_request
def after_request(response):
    """Enhanced request postprocessing with comprehensive metrics"""
    if hasattr(request, 'start_time') and request.path not in ['/favicon.ico', '/metrics']:
        duration = time.time() - request.start_time
        
        # Record metrics
        http_requests_total.labels(
            method=request.method,
            endpoint=request.path,
            status_code=response.status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.path
        ).observe(duration)
        
        # Request/Response size metrics
        request_size = len(request.get_data())
        response_size = len(response.get_data())
        
        http_request_size_bytes.labels(
            method=request.method,
            endpoint=request.path
        ).observe(request_size)
        
        http_response_size_bytes.labels(
            method=request.method,
            endpoint=request.path
        ).observe(response_size)
        
        # Log request details
        logger.info(
            f"Request {request.request_id} - {request.method} {request.path} - "
            f"{response.status_code} - {duration:.3f}s - {request_size}B/{response_size}B"
        )
    
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    """Enhanced error handling with detailed logging"""
    system_monitor.increment_error()
    
    error_details = {
        'error_id': str(uuid.uuid4()),
        'timestamp': datetime.now().isoformat(),
        'path': request.path,
        'method': request.method,
        'error_type': type(e).__name__,
        'error_message': str(e),
        'request_id': getattr(request, 'request_id', 'unknown')
    }
    
    if isinstance(e, HTTPException):
        status_code = e.code
        message = e.description
    else:
        status_code = 500
        message = "Internal Server Error"
    
    logger.error(f"Error {error_details['error_id']}: {error_details}")
    
    return jsonify({
        'error': message,
        'error_id': error_details['error_id'],
        'timestamp': error_details['timestamp']
    }), status_code

# ===== DATABASE SIMULATION =====

class DatabaseSimulator:
    def __init__(self):
        self.connection_pool = random.randint(5, 15)
    
    def execute_query(self, operation, table, simulate_slow=False):
        """Simulate database operations with realistic timing"""
        start_time = time.time()
        
        try:
            # Simulate different operation speeds
            if simulate_slow or random.random() < 0.1:  # 10% slow queries
                delay = random.uniform(0.5, 2.0)
            else:
                delay = random.uniform(0.01, 0.1)
            
            time.sleep(delay)
            
            # Simulate occasional failures
            if random.random() < 0.02:  # 2% failure rate
                raise Exception(f"Database operation failed: {operation} on {table}")
            
            duration = time.time() - start_time
            
            database_query_duration_seconds.labels(
                operation=operation,
                table=table
            ).observe(duration)
            
            database_operations_total.labels(
                operation=operation,
                table=table,
                status='success'
            ).inc()
            
            logger.debug(f"Database {operation} on {table} completed in {duration:.3f}s")
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            database_operations_total.labels(
                operation=operation,
                table=table,
                status='error'
            ).inc()
            logger.error(f"Database operation failed: {e}")
            raise

db = DatabaseSimulator()

# ===== PROFESSIONAL DASHBOARD =====

@app.route('/')
def dashboard():
    """Professional monitoring dashboard"""
    dashboard_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Enterprise Monitoring Dashboard</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }
        ]
        
        # Apply status filter
        if status_filter:
            orders = [o for o in orders if o['status'].lower() == status_filter.lower()]
        
        # Calculate analytics
        total_value = sum(order['total'] for order in orders)
        status_counts = {}
        for order in orders:
            status = order['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        api_calls_total.labels(endpoint='/api/orders', method='GET').inc()
        
        return jsonify({
            "orders": orders,
            "analytics": {
                "total_orders": len(orders),
                "total_value": round(total_value, 2),
                "average_order_value": round(total_value / len(orders) if orders else 0, 2),
                "status_breakdown": status_counts
            },
            "filters": {
                "status": status_filter
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "query_time_ms": int((time.time() - request.start_time) * 1000)
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        raise

@app.route('/api/analytics')
def get_analytics():
    """Advanced analytics endpoint"""
    try:
        db.execute_query("SELECT", "analytics")
        
        # Generate comprehensive analytics
        current_time = datetime.now()
        
        analytics_data = {
            "system_performance": {
                "uptime_hours": round((time.time() - system_monitor.start_time) / 3600, 2),
                "total_requests": system_monitor.total_requests,
                "error_rate_percent": round((system_monitor.error_count / max(system_monitor.total_requests, 1)) * 100, 2),
                "avg_response_time_ms": random.uniform(50, 200),  # Simulated
                "requests_per_minute": random.randint(50, 200)
            },
            "resource_usage": {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": round(psutil.disk_usage('/').percent, 2),
                "network_connections": len(psutil.net_connections())
            },
            "business_metrics": {
                "active_users": random.randint(150, 300),
                "daily_signups": random.randint(10, 50),
                "revenue_today": round(random.uniform(1000, 5000), 2),
                "conversion_rate": round(random.uniform(2.5, 8.5), 2)
            },
            "api_usage": {
                "most_called_endpoint": "/api/users",
                "least_called_endpoint": "/api/orders",
                "peak_hour": f"{random.randint(9, 17)}:00",
                "api_health_score": random.randint(85, 99)
            },
            "timestamp": current_time.isoformat(),
            "generated_in_ms": int((time.time() - request.start_time) * 1000)
        }
        
        return jsonify(analytics_data)
        
    except Exception as e:
        logger.error(f"Error generating analytics: {e}")
        raise

@app.route('/api/users', methods=['POST'])
@require_api_key
def create_user():
    """Create user endpoint with validation"""
    try:
        db.execute_query("INSERT", "users")
        user_registrations_total.inc()
        
        user_data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'name']
        if not user_data or not all(field in user_data for field in required_fields):
            return jsonify({
                "error": "Missing required fields",
                "required": required_fields
            }), 400
        
        # Simulate user creation
        new_user = {
            "id": random.randint(10000, 99999),
            "name": user_data['name'],
            "email": user_data['email'],
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "profile_completed": False
        }
        
        return jsonify({
            "message": "User created successfully",
            "user": new_user,
            "links": {
                "self": f"/api/users/{new_user['id']}",
                "profile": f"/api/users/{new_user['id']}/profile"
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise

@app.route('/api/stress')
def stress_test():
    """Endpoint for stress testing metrics"""
    try:
        # Simulate heavy operations
        iterations = request.args.get('iterations', 100, type=int)
        
        start_time = time.time()
        
        for i in range(iterations):
            # Simulate database operations
            db.execute_query("SELECT", "stress_test")
            
            # Simulate CPU intensive task
            time.sleep(0.001)
        
        duration = time.time() - start_time
        
        return jsonify({
            "message": f"Stress test completed with {iterations} iterations",
            "duration_seconds": round(duration, 3),
            "operations_per_second": round(iterations / duration, 2),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Stress test failed: {e}")
        raise

@app.route('/api/simulate-error')
def simulate_error():
    """Endpoint to simulate different types of errors for testing"""
    error_type = request.args.get('type', '500')
    
    if error_type == '404':
        abort(404)
    elif error_type == '403':
        abort(403)
    elif error_type == '429':
        abort(429)
    elif error_type == 'timeout':
        time.sleep(10)  # Simulate timeout
        return jsonify({"message": "This should have timed out"})
    elif error_type == 'db':
        raise Exception("Simulated database connection error")
    else:
        raise Exception(f"Simulated {error_type} error for testing monitoring")

@app.route('/metrics')
def metrics():
    """Expose Prometheus metrics with enhanced metadata"""
    try:
        metrics_data = generate_latest()
        
        # Add custom headers for monitoring tools
        response_headers = {
            'Content-Type': 'text/plain; version=0.0.4; charset=utf-8',
            'X-Metrics-Version': '3.0.0',
            'X-Generated-At': datetime.now().isoformat(),
            'X-Metrics-Count': str(len(metrics_data.decode().split('\n')))
        }
        
        return metrics_data, 200, response_headers
        
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        abort(500)

@app.route('/api/config')
@require_api_key
def get_config():
    """Get current application configuration"""
    config_data = {
        "application": {
            "name": "Enterprise Monitoring System",
            "version": "3.0.0",
            "environment": os.getenv('ENVIRONMENT', 'production'),
            "debug_mode": Config.DEBUG,
            "log_level": Config.LOG_LEVEL
        },
        "monitoring": {
            "interval_seconds": Config.MONITORING_INTERVAL,
            "metrics_enabled": True,
            "health_checks_enabled": True,
            "error_tracking_enabled": True
        },
        "system": {
            "hostname": os.uname().nodename if hasattr(os, 'uname') else 'unknown',
            "python_version": f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}.{psutil.sys.version_info.micro}",
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2)
        },
        "timestamp": datetime.now().isoformat()
    }
    
    return jsonify(config_data)

# ===== APPLICATION STARTUP =====

def initialize_application():
    """Initialize application components"""
    logger.info("Initializing Enterprise Monitoring System v3.0.0")
    
    # Start system monitoring
    start_system_monitoring()
    
    # Log startup information
    logger.info(f"Application started at: {datetime.now().isoformat()}")
    logger.info(f"Python version: {psutil.sys.version}")
    logger.info(f"CPU cores: {psutil.cpu_count()}")
    logger.info(f"Total memory: {round(psutil.virtual_memory().total / (1024**3), 2)} GB")
    logger.info("System monitoring thread started")
    logger.info("Prometheus metrics initialized")
    
    # Set initial system info
    app_info.info({
        'version': '3.0.0',
        'environment': os.getenv('ENVIRONMENT', 'production'),
        'startup_time': datetime.now().isoformat(),
        'python_version': f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}",
        'hostname': os.uname().nodename if hasattr(os, 'uname') else 'unknown',
        'cpu_cores': str(psutil.cpu_count()),
        'memory_gb': str(round(psutil.virtual_memory().total / (1024**3), 2))
    })

if __name__ == '__main__':
    try:
        initialize_application()
        
        logger.info("Starting Enterprise Monitoring System on port 5001...")
        logger.info("Dashboard available at: http://localhost:5001")
        logger.info("Metrics endpoint: http://localhost:5001/metrics")
        logger.info("Health check: http://localhost:5001/api/health")
        
        app.run(
            host='0.0.0.0', 
            port=5001, 
            debug=Config.DEBUG,
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
            
            .container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
            }
            
            .header {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 30px;
                margin-bottom: 30px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            .header h1 {
                font-size: 2.5em;
                font-weight: 700;
                background: linear-gradient(45deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 10px;
            }
            
            .header p {
                color: #666;
                font-size: 1.1em;
                margin-bottom: 20px;
            }
            
            .status-bar {
                display: flex;
                gap: 15px;
                flex-wrap: wrap;
            }
            
            .status-badge {
                padding: 8px 16px;
                border-radius: 25px;
                font-weight: 600;
                font-size: 0.9em;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .status-success {
                background: linear-gradient(45deg, #4CAF50, #45a049);
                color: white;
            }
            
            .status-warning {
                background: linear-gradient(45deg, #ff9800, #f57c00);
                color: white;
            }
            
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 25px;
                margin-bottom: 30px;
            }
            
            .metric-card {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 25px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }
            
            .metric-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
            }
            
            .metric-header {
                display: flex;
                align-items: center;
                gap: 15px;
                margin-bottom: 15px;
            }
            
            .metric-icon {
                font-size: 2.5em;
                width: 60px;
                height: 60px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 15px;
                background: linear-gradient(45deg, #667eea, #764ba2);
            }
            
            .metric-title {
                font-size: 1.2em;
                font-weight: 600;
                color: #333;
            }
            
            .metric-value {
                font-size: 2.2em;
                font-weight: 700;
                color: #2c3e50;
                margin-bottom: 10px;
            }
            
            .metric-description {
                color: #666;
                line-height: 1.5;
            }
            
            .nav-section {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 30px;
                margin-bottom: 30px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            .nav-title {
                font-size: 1.5em;
                font-weight: 600;
                color: #333;
                margin-bottom: 20px;
            }
            
            .nav-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
            }
            
            .nav-link {
                display: block;
                padding: 15px 20px;
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                text-decoration: none;
                border-radius: 12px;
                text-align: center;
                font-weight: 600;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            }
            
            .nav-link:hover {
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
            }
            
            .external-links {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            .external-links h3 {
                color: #333;
                margin-bottom: 20px;
                font-size: 1.3em;
            }
            
            .external-links ul {
                list-style: none;
            }
            
            .external-links li {
                margin-bottom: 12px;
                padding: 12px;
                background: rgba(102, 126, 234, 0.1);
                border-radius: 8px;
                border-left: 4px solid #667eea;
            }
            
            .external-links a {
                color: #667eea;
                text-decoration: none;
                font-weight: 600;
            }
            
            .external-links a:hover {
                color: #764ba2;
            }
            
            @media (max-width: 768px) {
                .container { padding: 15px; }
                .header h1 { font-size: 2em; }
                .metrics-grid { grid-template-columns: 1fr; }
                .nav-grid { grid-template-columns: 1fr; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Enterprise Monitoring Dashboard</h1>
                <p>Professional-grade application monitoring with real-time metrics and analytics</p>
                <div class="status-bar">
                    <div class="status-badge status-success">
                        <span>✓</span> System Operational
                    </div>
                    <div class="status-badge status-success">
                        <span>✓</span> All Services Running
                    </div>
                    <div class="status-badge status-warning">
                        <span>⚡</span> High Performance Mode
                    </div>
                </div>
            </div>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-header">
                        <div class="metric-icon">📊</div>
                        <div class="metric-title">Real-time Metrics</div>
                    </div>
                    <div class="metric-value">15+</div>
                    <div class="metric-description">
                        Comprehensive metrics collection including HTTP requests, system resources, 
                        database operations, and custom business metrics.
                    </div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-header">
                        <div class="metric-icon">📈</div>
                        <div class="metric-title">Performance Analytics</div>
                    </div>
                    <div class="metric-value">99.9%</div>
                    <div class="metric-description">
                        Advanced performance tracking with response times, error rates, 
                        throughput analysis, and health scoring.
                    </div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-header">
                        <div class="metric-icon">🔍</div>
                        <div class="metric-title">System Monitoring</div>
                    </div>
                    <div class="metric-value">24/7</div>
                    <div class="metric-description">
                        Continuous monitoring of CPU, memory, disk usage, network connections, 
                        and application uptime with intelligent alerting.
                    </div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-header">
                        <div class="metric-icon">🛡️</div>
                        <div class="metric-title">Error Tracking</div>
                    </div>
                    <div class="metric-value">&lt;0.1%</div>
                    <div class="metric-description">
                        Comprehensive error tracking with detailed logging, 
                        unique error IDs, and automated alerting for quick resolution.
                    </div>
                </div>
            </div>
            
            <div class="nav-section">
                <div class="nav-title">API Endpoints</div>
                <div class="nav-grid">
                    <a href="/api/health" class="nav-link">Health Check</a>
                    <a href="/api/users" class="nav-link">Users API</a>
                    <a href="/api/products" class="nav-link">Products API</a>
                    <a href="/api/orders" class="nav-link">Orders API</a>
                    <a href="/api/analytics" class="nav-link">Analytics</a>
                    <a href="/metrics" class="nav-link">Raw Metrics</a>
                </div>
            </div>
            
            <div class="external-links">
                <h3>🔗 Monitoring Tools</h3>
                <ul>
                    <li>
                        <strong>Grafana Dashboard:</strong> 
                        <a href="http://localhost:3000" target="_blank">http://localhost:3000</a> 
                        (admin/admin) - Advanced visualizations and alerting
                    </li>
                    <li>
                        <strong>Prometheus:</strong> 
                        <a href="http://localhost:9090" target="_blank">http://localhost:9090</a> 
                        - Metrics collection and querying
                    </li>
                    <li>
                        <strong>Node Exporter:</strong> 
                        <a href="http://localhost:9100" target="_blank">http://localhost:9100</a> 
                        - System metrics collection
                    </li>
                    <li>
                        <strong>Application Logs:</strong> 
                        <code>tail -f app.log</code> - Real-time application logging
                    </li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(dashboard_html)

# ===== ENHANCED API ENDPOINTS =====

@app.route('/api/health')
def health_check():
    """Comprehensive health check endpoint"""
    try:
        # Perform system checks
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "3.0.0",
            "uptime_seconds": int(time.time() - system_monitor.start_time),
            "system": {
                "cpu_usage_percent": round(cpu_percent, 2),
                "memory_usage_percent": round(memory.percent, 2),
                "disk_usage_percent": round((disk.used / disk.total) * 100, 2),
                "available_memory_gb": round(memory.available / (1024**3), 2)
            },
            "services": {
                "web_server": "operational",
                "database": "connected",
                "monitoring": "active",
                "logging": "operational"
            },
            "metrics": {
                "total_requests": system_monitor.total_requests,
                "error_count": system_monitor.error_count,
                "error_rate_percent": round((system_monitor.error_count / max(system_monitor.total_requests, 1)) * 100, 2),
                "health_score": int(system_monitor.calculate_health_score(cpu_percent, memory.percent, (disk.used / disk.total) * 100))
            }
        }
        
        return jsonify(health_data)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 503

@app.route('/api/users')
def get_users():
    """Enhanced users API with pagination and filtering"""
    try:
        db.execute_query("SELECT", "users")
        
        # Simulate pagination
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        
        # Mock user data
        all_users = [
            {"id": i, "name": f"User {i}", "email": f"user{i}@company.com", 
             "created_at": (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat(),
             "status": random.choice(["active", "inactive", "pending"])}
            for i in range(1, 101)
        ]
        
        start = (page - 1) * limit
        end = start + limit
        users = all_users[start:end]
        
        api_calls_total.labels(endpoint='/api/users', method='GET').inc()
        
        return jsonify({
            "users": users,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": len(all_users),
                "pages": (len(all_users) + limit - 1) // limit
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "response_time_ms": int((time.time() - request.start_time) * 1000)
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise

@app.route('/api/products')
def get_products():
    """Enhanced products API with categories and search"""
    try:
        db.execute_query("SELECT", "products")
        
        category = request.args.get('category')
        search = request.args.get('search', '').lower()
        
        products = [
            {"id": 1, "name": "Professional Laptop", "price": 1299.99, "category": "Electronics", "stock": 45},
            {"id": 2, "name": "Wireless Mouse", "price": 79.99, "category": "Electronics", "stock": 120},
            {"id": 3, "name": "Mechanical Keyboard", "price": 149.99, "category": "Electronics", "stock": 67},
            {"id": 4, "name": "Monitor Stand", "price": 89.99, "category": "Accessories", "stock": 34},
            {"id": 5, "name": "USB Hub", "price": 39.99, "category": "Accessories", "stock": 89}
        ]
        
        # Apply filters
        if category:
            products = [p for p in products if p['category'].lower() == category.lower()]
        if search:
            products = [p for p in products if search in p['name'].lower()]
        
        api_calls_total.labels(endpoint='/api/products', method='GET').inc()
        
        return jsonify({
            "products": products,
            "filters": {
                "category": category,
                "search": search
            },
            "count": len(products),
            "categories": ["Electronics", "Accessories"],
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "cached": False
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching products: {e}")
        raise

@app.route('/api/orders')
def get_orders():
    """Enhanced orders API with status filtering"""
    try:
        db.execute_query("SELECT", "orders", simulate_slow=True)
        
        # Simulate higher complexity
        status_filter = request.args.get('status')
        
        orders = [
            {
                "id": 1001, "user_id": 1, "total": 1459.98, "status": "completed",
                "created_at": "2024-12-15T10:30:00Z", "items": 3,
                "shipping_address": "123 Main St, City, State"
            },
            {
                "id": 1002, "user_id": 2, "total": 89.97, "status": "pending",
                "created_at": "2024-12-18T14:22:00Z", "items": 1,
                "shipping_address": "456 Oak Ave, City, State"
            },
            {
                "id": 1003, "user_id": 3, "total": 299.99, "status": "shipped",
                "created_at": "2024-12-17T09:15:00Z", "items": 2,
                "shipping_address": "789 Pine St, City, State"
            },
            {
                "id": 1004, "user_id": 1, "total": 45.50, "status": "cancelled",
                "created_at": "2024-12-16T16:45:00Z", "items": 1,
                "shipping_address": "123 Main St, City, State"
            }