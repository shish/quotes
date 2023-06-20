from flask.testing import FlaskClient


def test_favicon(client: FlaskClient):
    response = client.get("/favicon.ico")
    assert response.status_code == 200


def test_index(client: FlaskClient):
    response = client.get("/")
    assert response.status_code == 200


def test_quotes_get(client: FlaskClient):
    response = client.get("/quotes")
    assert response.status_code == 200

    response = client.get("/quotes?page=2")
    assert response.status_code == 200

    response = client.get("/quotes?search=irc")
    assert response.status_code == 200

    response = client.get("/quotes?search=text")
    assert response.status_code == 200


def test_quotes_post(client: FlaskClient):
    response = client.post(
        "/quotes",
        data={"text": "test", "tags": "test tag", "captcha": "6"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 302

    response = client.post(
        "/quotes",
        data={"text": "test", "tags": "test", "captcha": "0"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


def test_quote_get(client: FlaskClient):
    response = client.get("/quote/1")
    assert response.status_code == 200

    response = client.get("/quote/1?edit=on")
    assert response.status_code == 200

    response = client.get("/quote/999")
    assert response.status_code == 404


def test_quote__post__missing(client: FlaskClient):
    response = client.post("/quote/999")
    assert response.status_code == 404


def test_quote__post__update(client: FlaskClient):
    response = client.post(
        "/quote/1",
        data={"text": "test updated", "tags": "test new"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 302

    response = client.get("/quote/1")
    assert b"test updated" in response.data


def test_quote__post__delete(client: FlaskClient):
    response = client.post(
        "/quote/1",
        data={"text": "", "tags": ""},
        content_type="multipart/form-data",
    )
    assert response.status_code == 302

    response = client.get("/quote/1")
    assert response.status_code == 404
