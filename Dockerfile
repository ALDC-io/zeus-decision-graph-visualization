FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/api_server.py .

# Copy pre-computed data (clustering + layout)
COPY data/clustering_results.json ./data/
COPY data/layout_results.json ./data/

# Copy static visualization
COPY output/html/zeus_decision_graph.html ./static/

# Expose port (Container Apps handles TLS)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Run with gunicorn for production
# 2 workers to balance cold start vs throughput
CMD ["gunicorn", "api_server:app", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8080", "--timeout", "120", "--access-logfile", "-"]
