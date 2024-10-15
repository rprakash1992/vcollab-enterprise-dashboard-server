FROM python:3.12

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app/

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY main.py .

COPY keys.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
