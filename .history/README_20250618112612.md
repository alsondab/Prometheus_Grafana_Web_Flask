# 🚀 Professional Web App Monitoring with Prometheus & Grafana

A comprehensive monitoring solution for web applications using Prometheus and Grafana. This setup provides real-time metrics collection, beautiful dashboards, and proactive alerting for production-ready applications.

![Monitoring Stack](grafana.png)

## 🎯 Features

- **Real-time Metrics Collection**: Comprehensive application and system metrics
- **Beautiful Dashboards**: Pre-configured Grafana dashboards with key performance indicators
- **Proactive Alerting**: Configurable alerts for error rates, response times, and system health
- **Container Monitoring**: Full Docker container metrics with cAdvisor
- **System Metrics**: Node Exporter for host system monitoring
- **Production Ready**: Optimized for production environments with proper logging and error handling

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Flask App     │    │   Prometheus    │    │     Grafana     │
│   (Port 5001)   │───▶│   (Port 9090)   │───▶│   (Port 3000)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         │              │  Alertmanager   │              │
         │              │   (Port 9093)   │              │
         │              └─────────────────┘              │
         │                       │
         │              ┌─────────────────┐
         │              │  Node Exporter  │
         │              │   (Port 9100)   │
         │              └─────────────────┘
         │
         │              ┌─────────────────┐
         └─────────────▶│    cAdvisor     │
                        │   (Port 8080)   │
                        └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- At least 2GB of available RAM
- Ports 3000, 5001, 8080, 9090, 9093, 9100 available

### 1. Clone and Setup

```bash
git clone https://github.com/Vishakha-Sawra/Grafana-Prometheus-Dashboard
cd Grafana-Prometheus-Dashboard
```

### 2. Start the Monitoring Stack

```bash
docker-compose up -d
```

### 3. Access the Services

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| **Grafana Dashboard** | http://localhost:3000 | admin/admin |
| **Prometheus** | http://localhost:9090 | - |
| **Alertmanager** | http://localhost:9093 | - |
| **Web Application** | http://localhost:5001 | - |
| **Node Exporter** | http://localhost:9100 | - |
| **cAdvisor** | http://localhost:8080 | - |

## 📊 Available Metrics

### Application Metrics
- **Request Rate**: Requests per second per endpoint
- **Response Time**: 50th and 95th percentile response times
- **Error Rate**: Error counts by endpoint and status code
- **Active Requests**: Current number of active requests
- **API Calls**: Total API calls by endpoint and method
- **Database Operations**: Database query counts and timing
- **User Signups**: Business metric tracking

### System Metrics
- **Memory Usage**: Application memory consumption
- **CPU Usage**: CPU utilization percentage
- **Database Connections**: Active database connections
- **Container Metrics**: Docker container resource usage

## 🎨 Grafana Dashboards

### Web Application Dashboard
- **Request Rate Graph**: Real-time request rate visualization
- **Response Time Analysis**: 95th and 50th percentile response times
- **Error Rate Monitoring**: Error rates by endpoint and status code
- **System Health Stats**: Memory, CPU, and connection metrics
- **Database Operations**: Database query performance
- **Business Metrics**: User signup tracking

## ⚠️ Alerting Rules

The system includes pre-configured alerts for:

- **High Error Rate**: > 0.1 errors/second for 2 minutes
- **High Response Time**: > 2 seconds 95th percentile for 2 minutes
- **Service Down**: Application unavailable for 1 minute
- **High Memory Usage**: > 400MB for 5 minutes
- **High CPU Usage**: > 80% for 5 minutes
- **Database Issues**: < 5 connections for 2 minutes
- **High Request Rate**: > 100 requests/second for 2 minutes

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
PROMETHEUS_HEX=your_secret_key_here
```

### Customizing Alerts

Edit `prometheus-rules.yml` to modify alert thresholds and conditions.

### Adding New Metrics

1. Add new Prometheus metrics in `app.py`
2. Update the Grafana dashboard in `dashboards/web-app-dashboard.json`
3. Restart the services: `docker-compose restart`

## 🧪 Testing the Setup

### Generate Load

```bash
# Test the web application endpoints
curl http://localhost:5001/
curl http://localhost:5001/api/health
curl http://localhost:5001/api/users
curl http://localhost:5001/api/products
curl http://localhost:5001/api/orders

# Test error endpoints
curl http://localhost:5001/error
curl http://localhost:5001/slow
```

### View Raw Metrics

```bash
curl http://localhost:5001/metrics
```

## 📈 Production Considerations

### Security
- Change default Grafana credentials
- Use HTTPS in production
- Implement proper authentication
- Secure Prometheus endpoints

### Performance
- Adjust scrape intervals based on load
- Configure proper retention policies
- Monitor Prometheus storage usage
- Use persistent volumes for data

### Scaling
- Consider Prometheus federation for multiple instances
- Use service discovery for dynamic targets
- Implement proper backup strategies

## 🛠️ Troubleshooting

### Common Issues

1. **Port Conflicts**: Ensure all required ports are available
2. **Memory Issues**: Increase Docker memory allocation
3. **Permission Errors**: Check file permissions on mounted volumes
4. **Network Issues**: Verify Docker network connectivity

### Logs

```bash
# View all service logs
docker-compose logs

# View specific service logs
docker-compose logs flask-app
docker-compose logs prometheus
docker-compose logs grafana
```

### Health Checks

```bash
# Check service status
docker-compose ps

# Restart services
docker-compose restart

# Rebuild and restart
docker-compose up -d --build
```

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Alertmanager Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [Node Exporter Documentation](https://prometheus.io/docs/guides/node-exporter/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Original project by [Vishakha Sawra](https://github.com/Vishakha-Sawra)
- Prometheus and Grafana communities
- Docker and container ecosystem

---

**Happy Monitoring! 🎉**
