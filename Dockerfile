FROM python:alpine

WORKDIR /app

COPY requirements.txt /app/
RUN pip install wheel && pip3 install -r /app/requirements.txt
COPY . /app/

CMD ["python3", "src/main.py"]