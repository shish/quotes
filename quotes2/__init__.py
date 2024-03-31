import os
import click
import math
import datetime
from typing import List, Tuple
import sqlalchemy

from werkzeug.wrappers.response import Response
from flask import (
    Flask,
    render_template,
    session,
    redirect,
    url_for,
    request,
    abort,
    send_from_directory,
    jsonify,
    g,
)
from .models import db, Quote, Tag


def get_tag(name: str) -> Tag:
    """Get an existing tag or create a new one."""
    return Tag.query.filter(Tag.name == name).first() or Tag(name.lower())


def tag_cloud() -> List[Tuple[str, float]]:
    """Return a list of all tags and their logaritmic count."""
    return db.session.execute(
        db.text(
            """
                SELECT greatest(0.1, log(count(quote_id))) AS tagcount, name
                FROM map_tag_to_quote
                JOIN tag ON map_tag_to_quote.tag_id=tag.id
                GROUP BY name
                """
        )
    ).all()


def create_app(test_config=None):
    ###################################################################
    # Load config

    app = Flask(__name__, instance_path=os.path.abspath("./data"))
    with open("./data/secret.txt", "rb") as fp:
        secret_key = fp.read()
    app.config.from_mapping(
        SECRET_KEY=secret_key,
        SQLALCHEMY_DATABASE_URI="sqlite:///quotes.sqlite",
    )
    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    ###################################################################
    # Load database

    db.init_app(app)

    @click.command("init-db")
    def init_db_command():  # pragma: no cover
        """Clear the existing data and create new tables."""
        with app.app_context():
            db.create_all()
        click.echo("Initialized the database.")

    app.cli.add_command(init_db_command)

    with app.app_context():

        @sqlalchemy.event.listens_for(db.engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            dbapi_connection.create_function("greatest", 2, lambda a, b: max(a, b))
            dbapi_connection.create_function("log", 1, lambda a: math.log(a, 10))

    ###################################################################
    # Public routes

    @app.route("/favicon.ico")
    def favicon() -> Response:
        return send_from_directory(
            os.path.join(app.root_path, "static"),
            "favicon.ico",
            mimetype="image/vnd.microsoft.icon",
        )

    @app.route("/")
    @app.route("/quotes", methods=["GET"])
    def quotes() -> str:
        """Show a page of quotes, optionally filtered by search text and tags."""
        search = request.args.get("search", "")
        page = int(request.args.get("page", 1))
        q = db.select(Quote)
        if search:
            search_tag = (
                db.session.execute(db.select(Tag).filter(Tag.name == search))
                .scalars()
                .first()
            )
            if search_tag:
                q = q.join(Quote.tags).filter(Tag.id == search_tag.id)
            else:
                q = q.filter(Quote.text.contains(search))
        q = q.order_by(Quote.id.desc()).limit(10).offset((page - 1) * 10)
        quotes = db.session.execute(q).scalars().all()
        return render_template(
            "quotes.html",
            title="More UKC Quotes",
            quotes=quotes,
            search=search,
            page=page,
            tag_cloud=tag_cloud(),
        )

    @app.route("/quotes", methods=["POST"])
    def quotes_post() -> Response:
        """Create a new quote"""
        text = request.form["text"]
        tags = list(set(get_tag(tag) for tag in request.form["tags"].split()))
        if (
            "[url=" in text
            or "<a href=" in text
            or request.form["captcha"] != str(datetime.date.today().day)
        ):
            abort(400, "Spam detected")
        quote = Quote(text, tags)
        db.session.add(quote)
        db.session.commit()
        app.logger.info(f"Quote #{quote.id} created")
        return redirect(url_for("quote_get", id=quote.id))

    @app.route("/quote/<id>", methods=["GET"])
    def quote_get(id: int) -> str:
        """Show a single quote"""
        quote = db.first_or_404(db.select(Quote).filter(Quote.id == id))
        return render_template(
            "quote.html",
            title="Quote #%d" % quote.id,
            edit=request.args.get("edit", False),
            quote=quote,
        )

    @app.route("/quote/<id>", methods=["POST"])
    def quote_post(id: int) -> Response:
        """Update a single quote"""
        quote = db.first_or_404(db.select(Quote).filter(Quote.id == id))
        if request.form["text"]:
            quote.text = request.form["text"]
            quote.tags = list(set(get_tag(tag) for tag in request.form["tags"].split()))
            db.session.commit()
            app.logger.info(f"Quote #{quote.id} updated")
            return redirect(url_for("quote_get", id=id))
        else:
            db.session.delete(quote)
            db.session.commit()
            app.logger.info(f"Quote #{quote.id} deleted")
            return redirect(url_for("quotes"))

    return app
