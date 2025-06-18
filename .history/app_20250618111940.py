from flask import Flask, request, abort
from prometheus_client import Counter, Histogram, generate_latest, Gauge
from dotenv import load_dotenv
import os
import time
import requests

load_dotenv()
app = Flask(__name__)
SHARED_KEY = os.getenv('PROMETHEUS_HEX') # Shared key for Prometheus

# Counter to count endpoint clicks
endpoint_clicks = Counter('endpoint_clicks', 'Total clicks per endpoint', ['endpoint'])

# Histogram to track response times
endpoint_latency = Histogram('endpoint_latency_seconds', 'Endpoint response time', ['endpoint'])

# Counter to track unique user locations
user_locations = Counter('unique_user_locations', 'Unique user locations', ['latitude', 'longitude'])

# Counter to track errors
error_counter = Counter('endpoint_errors', 'Total errors per endpoint and status code', ['endpoint', 'status_code'])

# Histogram to track request sizes
request_size = Histogram('request_size_bytes', 'Request size in bytes', ['endpoint'])

# Histogram to track response sizes
response_size = Histogram('response_size_bytes', 'Response size in bytes', ['endpoint'])

# Gauge to track active requests
active_requests = Gauge('active_requests', 'Number of active requests')

# Histogram to track database query times
db_query_time = Histogram('db_query_time_seconds', 'Database query time')

# Custom business metric example: Counter to track user signups
user_signups = Counter('user_signups', 'Total user signups')

def get_location(ip):
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}')
        data = response.json()
        if data['status'] == 'success':
            return [data['lat'], data['lon']]
        else:
            return [0.0, 0.0]
    except Exception as e:
        return [0.0, 0.0]  

@app.before_request
def start_timer():
    request.start_time = time.time()
    active_requests.inc()

@app.after_request
def track_metrics(response):
    if request.path != '/favicon.ico' and request.path != '/metrics':
        endpoint_clicks.labels(endpoint=request.path).inc()
        request_latency = time.time() - request.start_time
        endpoint_latency.labels(endpoint=request.path).observe(request_latency)
        request_size.labels(endpoint=request.path).observe(len(request.data))
        response_size.labels(endpoint=request.path).observe(len(response.data))
    active_requests.dec()
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    error_counter.labels(endpoint=request.path, status_code="500").inc()
    active_requests.dec()
    return "Internal Server Error", 500

@app.errorhandler(404)
def page_not_found(e):
    error_counter.labels(endpoint=request.path, status_code="404").inc()
    active_requests.dec()
    return "404 Not Found", 404

@app.errorhandler(403)
def page_not_found(e):
    error_counter.labels(endpoint=request.path, status_code="403").inc()
    active_requests.dec()
    return "403 Forbidden", 403

@app.route('/metrics')
def metrics():
    try:
        return generate_latest(), 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        app.logger.error("Error generating metrics: %s", str(e))
        abort(500)  # Internal Server Error

@app.route('/')
def home():
    return "Welcome to the Home Page!"

@app.route('/about') 
def about():
    return "Welcome to the about page!"

@app.route('/contact')
def contact():
    return "Welcome to the contact page!"

@app.route('/error')
def error1():
    raise Exception("Oops got an error")

@app.route('/signup')
def signup():
    user_signups.inc()
    return "User signed up!"

if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=5001, debug=True)