FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install streamlit fastapi uvicorn requests pandas
CMD ["streamlit", "run", "src/dashboard/tc_dashboard.py", "--server.port=8501"]
