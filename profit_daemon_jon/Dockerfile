FROM python:3.12-slim
WORKDIR /app
COPY profit_daemon_jon/requirements.txt /app/profit_daemon_jon/requirements.txt
RUN pip install --no-cache-dir -r /app/profit_daemon_jon/requirements.txt
COPY . /app
ENV PYTHONUNBUFFERED=1 PROFIT_DAEMON_JON=1
EXPOSE 9108 8787
CMD ["python", "profit_daemon_jon/run.py", "--profile", "paper"]
