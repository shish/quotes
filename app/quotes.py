#!/usr/bin/python

import web
web.config.debug = False

import cgi
import logging
import logging.handlers
import hashlib

from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import func
from models import *

urls = (
    '/?', 'quotes',
    '/quotes', 'quotes',
    '/quotes/(\d+)', 'quote',
    '/(favicon.ico)', 'static',
)
site = "http://quotes.shishnet.org"


def load_sqla(handler):
    web.ctx.orm = scoped_session(sessionmaker(bind=engine))
    try:
        return handler()
    except web.HTTPError:
        web.ctx.orm.commit()
        raise
    except:
        web.ctx.orm.rollback()
        raise
    finally:
        web.ctx.orm.commit()
        # If the above alone doesn't work, uncomment
        # the following line:
        #web.ctx.orm.expunge_all()

def override_method(handler):
    web.ctx.method = web.input().get("_method", web.ctx.method)
    return handler()


#render = web.template.render("../templates/")
class render_mako:
    """copied from web.contrib.templates, with t.render_unicode"""
    def __init__(self, *a, **kwargs):
        from mako.lookup import TemplateLookup
        self._lookup = TemplateLookup(*a, **kwargs)

    def __getattr__(self, name):
        # Assuming all templates are html
        path = name + ".html"
        t = self._lookup.get_template(path)
        return t.render_unicode

render = render_mako(
    directories=["../templates/"],
    input_encoding='utf-8',
    output_encoding='utf-8',
    default_filters=['unicode', 'h'],
)
app = web.application(urls, globals())
app.add_processor(load_sqla)
app.add_processor(override_method)

import rediswebpy
session = web.session.Session(
    app, rediswebpy.RedisStore(prefix='session:quotes:'),
    initializer={'username': None})


# {{{ utility functions
class QuoteError(Exception):
    def __init__(self, title, message):
        self.title = title
        self.message = message

def log_info(text):
    if session.username:
        logging.info("%s: %s" % (session.username, text))
    else:
        logging.info("<anon>: %s" % text)

def if_logged_in(func):
    def splitter(*args):
        if session.username:
            return func(*args)
        else:
            web.seeother("/")
    return splitter

def handle_exceptions(func):
    def logger(*args):
        try:
            return func(*args)
        except QuoteError, e:
            return render.standard("Error", e.title, "", e.message)
        except Exception, e:
            logging.exception("Unhandled exception:")
            #return render.standard("Error", str(e), "", str(e))
            raise
    return logger

# }}}

class static:
    @handle_exceptions
    def GET(self, filename):
        try:
            return file("static/"+filename).read()
        except:
            return "not found"


def get_tag(name):
    tag = web.ctx.orm.query(Tag).filter(Tag.name==name).first()
    if tag:
        return tag
    else:
        return Tag(name.lower())

def tagcloud():
    return web.ctx.orm.execute("SELECT greatest(0.1, log(count(quote_id))) AS tagcount, name FROM map_tag_to_quote JOIN tag ON map_tag_to_quote.tag_id=tag.id GROUP BY name")


class quotes:
    @handle_exceptions
    def GET(self):
        form = web.input(search=u"", page="")
        title = "More UKC Quotes"
        try:
            page = int(form.page)
        except ValueError:
            page = 1

        quotes = web.ctx.orm.query(Quote)
        if form.search:
            search_tag = web.ctx.orm.query(Tag).filter(Tag.name==form.search).first()
            if search_tag:
                quotes = quotes.join(Quote.tags)
                quotes = quotes.filter(Tag.id == search_tag.id)
            else:
                quotes = quotes.filter("""
                    to_tsvector('english', regexp_replace(text, '[^a-zA-Z0-9]', ' ', 'g')) @@
                    plainto_tsquery(:text)
                """).params(text=form.search)
        quotes = quotes.order_by(Quote.id.desc())
        quotes = quotes[(page-1)*10:page*10]
        body = "<hr>".join([render.quote(quote, web.net.urlquote, web.net.htmlquote) for quote in quotes])
        nav  = render.navigation(page, web.http.changequery, tagcloud())
        return render.standard(title, title, nav, body)

    @handle_exceptions
    def POST(self, id=None):
        form = web.input(text="", tags="")
        all_tags = [get_tag(tag) for tag in form.tags.split(" ")]
        uni_tags = list(set(all_tags))
        quote = Quote(form.text, uni_tags)
        web.ctx.orm.add(quote)
        web.ctx.orm.commit()
        log_info("added Quote #%d" % quote.id)
        web.seeother(site+"/")


class quote:
    @handle_exceptions
    def GET(self, id):
        form = web.input(edit="no")
        title = "UKC Quotes #%d" % int(id)
        quote = web.ctx.orm.query(Quote).filter(Quote.id==id).first()
        if quote:
            if form.edit == "no":
                body = render.quote(quote, web.net.urlquote, web.net.htmlquote)
            else:
                body = render.quote_edit(quote)
            snip = (" -- ".join(quote.text.split("\n")[:5])+" -- Read the rest &rarr;").replace("<", "[").replace(">", "]")
            return render.standard(title, title, render.navigation(1, web.http.changequery, tagcloud()), body, description=snip)
        else:
            return "Quote not found"

    @handle_exceptions
    def PUT(self, id):
        quote = web.ctx.orm.query(Quote).filter(Quote.id==id).first()
        if quote:
            form = web.input(text="", tags="")
            all_tags = [get_tag(tag) for tag in form.tags.split(" ")]
            uni_tags = list(set(all_tags))
            quote.text = form.text
            quote.tags = uni_tags
            web.ctx.orm.commit()
            log_info("updated Quote #%d" % quote.id)
        web.seeother(site+"/")

    @handle_exceptions
    @if_logged_in
    def DELETE(self, id=None):
        form = web.input()
        pass


class users:
    @handle_exceptions
    def POST(self):
        form = web.input()
        username = form.username
        password1 = form.password1
        password2 = form.password2
        if len(form.email) > 0:
            email = form.email
        else:
            email = None

        user = db.users.find_one(user_name=username)
        if user == None:
            if password1 == password2:
                user = rav.User.NewUser(username, password1, email)
                db.users.add(user)

                session.username = username
                log_info("User created")
                web.seeother("user")
            else:
                raise QuoteError("Password Error", "The password and confirmation password don't match D:")
        else:
            raise QuoteError("Name Taken", "That username has already been taken, sorry D:")


if __name__ == "__main__":
    logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)-8s %(message)s',
            filename="../logs/app.log")
    smtp = logging.handlers.SMTPHandler(
            "localhost", "noreply@shishnet.org",
            ["shish+quotes@shishnet.org", ], "quotes error report")
    smtp.setLevel(logging.WARNING)
    logging.getLogger('').addHandler(smtp)

    logging.info("App starts...")
    app.run()
