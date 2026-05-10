# SKT-AI-LABS ADK Deployment Guide

## Local Development

```bash
# Clone repository
git clone https://github.com/skt-ai-labs/skt-ai-labs-adk.git
cd skt-ai-labs-adk

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Install Playwright browsers
playwright install

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run CLI
skt-adk status

# Run API server
make serve
# or
uvicorn skt_ai_labs.api.server:app --reload --host 0.0.0.0 --port 8000
```

## Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e ".[all]"
RUN playwright install chromium

EXPOSE 8000
CMD ["uvicorn", "skt_ai_labs.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t skt-ai-labs-adk .
docker run -p 8000:8000 --env-file .env skt-ai-labs-adk
```

## Cloud Deployment

### Railway/Render
1. Connect GitHub repo
2. Set environment variables
3. Deploy

### AWS/GCP/Azure
- Use containerized deployment
- Configure managed PostgreSQL with pgvector
- Set up Redis for caching
- Use load balancer for API

## Scaling

### Horizontal Scaling
- Stateless API design
- Shared vector database
- Redis for session management

### Vertical Scaling
- GPU instances for embeddings
- High-memory instances for large context

## Monitoring

```python
# Structured logging is built-in
# Integrate with:
# - Datadog
# - Grafana + Loki
# - CloudWatch
```

## Security Checklist

- [ ] All API keys in environment variables
- [ ] Database SSL enabled
- [ ] Rate limiting configured
- [ ] CORS origins restricted
- [ ] Input validation on all endpoints
- [ ] Audit logging enabled
