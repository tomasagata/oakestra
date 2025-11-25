docker run -d -p 5000:5000 ghcr.io/mlflow/mlflow:v3.6.0 \
  mlflow server \
    --backend-store-uri sqlite:///mlflow.db \
    --host 0.0.0.0 \
    --port 5000