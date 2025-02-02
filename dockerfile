FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV TG_TOKEN=${8169183380:AAEp2I0Bb_Ljnzd4n8gMaDbVPLuFCi6BFDk}
ENV YANDEX_API_KEY=${AQVNznkv2cu-WerDTScb2YWsVBcomNIjvkzb9Tmy
}
ENV WEBHOOK_URL=${WEBHOOK_URL}

CMD ["python", "app.py"]
