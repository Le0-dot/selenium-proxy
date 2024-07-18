FROM python:3.12.4-alpine3.20

COPY ./src /app
WORKDIR /app

RUN apk add protobuf
RUN pip install .

CMD ["python", "-m", "selenium_proxy"]
