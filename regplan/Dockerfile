FROM python:3.10-slim
WORKDIR /app
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e . && \
    adduser --disabled-password --gecos "" regplan && \
    chown -R regplan:regplan /app
USER regplan
CMD ["regplan", "--help"]
