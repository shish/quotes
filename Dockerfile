FROM python:2.7-slim-stretch
EXPOSE 8000
RUN apt update && apt install -y curl
HEALTHCHECK --interval=5m --timeout=3s CMD curl --fail http://127.0.0.1:8000/ || exit 1
ENV DB_DSN=postgres://foo:bar@172.17.0.1/mydatabase

ENV PYTHONUNBUFFERED 1
RUN /usr/local/bin/pip install --upgrade pip setuptools wheel
RUN /usr/local/bin/pip install web.py mako sqlalchemy bcrypt psycopg2-binary

COPY . /app
WORKDIR /app
CMD ["/usr/local/bin/python", "quotes.py", "0.0.0.0:8000"]

