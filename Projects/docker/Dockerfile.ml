FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/models /app/logs /app/data/picks

EXPOSE 8000

CMD ["python", "engine/train_with_shap.py", "--data", "data/historical.csv", "--model", "models/probability_model.joblib"]
