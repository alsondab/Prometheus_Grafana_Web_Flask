#!/usr/bin/env python3
"""
Load Testing Script for Web App Monitoring
This script generates traffic to test the monitoring setup
"""

import requests
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor
import argparse

class LoadTester:
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url
        self.endpoints = [
            "/",
            "/api/health",
            "/api/users",
            "/api/products", 
            "/api/orders",
            "/about"
        ]
        self.error_endpoints = [
            "/error",
            "/slow"
        ]
        
    def make_request(self, endpoint):
        """Make a single request to an endpoint"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, timeout=10)
            return {
                'endpoint': endpoint,
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds(),
                'success': True
            }
        except Exception as e:
            return {
                'endpoint': endpoint,
                'status_code': 0,
                'response_time': 0,
                'success': False,
                'error': str(e)
            }
    
    def worker(self, duration, requests_per_second):
        """Worker function for generating load"""
        end_time = time.time() + duration
        interval = 1.0 / requests_per_second
        
        while time.time() < end_time:
            # 90% normal requests, 10% error requests
            if random.random() < 0.9:
                endpoint = random.choice(self.endpoints)
            else:
                endpoint = random.choice(self.error_endpoints)
            
            result = self.make_request(endpoint)
            
            if result['success']:
                print(f"✅ {endpoint} - {result['status_code']} - {result['response_time']:.3f}s")
            else:
                print(f"❌ {endpoint} - Error: {result.get('error', 'Unknown')}")
            
            time.sleep(interval)
    
    def run_load_test(self, duration=60, requests_per_second=10, num_threads=4):
        """Run the load test"""
        print(f"🚀 Starting load test for {duration} seconds")
        print(f"📊 Target: {requests_per_second} requests/second across {num_threads} threads")
        print(f"🎯 Total expected requests: {duration * requests_per_second}")
        print("=" * 60)
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for _ in range(num_threads):
                future = executor.submit(self.worker, duration, requests_per_second / num_threads)
                futures.append(future)
            
            # Wait for all threads to complete
            for future in futures:
                future.result()
        
        end_time = time.time()
        actual_duration = end_time - start_time
        
        print("=" * 60)
        print(f"✅ Load test completed in {actual_duration:.2f} seconds")
        print(f"📈 Average RPS: {duration * requests_per_second / actual_duration:.2f}")

def main():
    parser = argparse.ArgumentParser(description='Load testing script for web app monitoring')
    parser.add_argument('--url', default='http://localhost:5001', help='Base URL of the application')
    parser.add_argument('--duration', type=int, default=60, help='Duration of the test in seconds')
    parser.add_argument('--rps', type=int, default=10, help='Requests per second')
    parser.add_argument('--threads', type=int, default=4, help='Number of threads')
    
    args = parser.parse_args()
    
    # Test if the application is accessible
    try:
        response = requests.get(f"{args.url}/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Application is accessible")
        else:
            print(f"⚠️  Application returned status code: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to application: {e}")
        print("Make sure the application is running on the specified URL")
        return
    
    # Run the load test
    tester = LoadTester(args.url)
    tester.run_load_test(args.duration, args.rps, args.threads)

if __name__ == "__main__":
    main() 