
import hashlib
import Image
import StringIO

from sqlalchemy import create_engine, func
from sqlalchemy import Column, Integer, String, Unicode, Boolean, DateTime
from sqlalchemy import ForeignKey, Table
from sqlalchemy.orm import relationship, backref

import ConfigParser
config = ConfigParser.SafeConfigParser()
config.read("../app/quotes.cfg")
host = config.get("database", "hostname")
user = config.get("database", "username")
password = config.get("database", "password")
database = config.get("database", "database")
engine = create_engine("postgres://%s:%s@%s/%s" % (user, password, host, database), echo=False)


from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "user"

    id       = Column(Integer, primary_key=True)
    username = Column(Unicode,    nullable=False, index=True)
    password = Column(String(32), nullable=False)
    email    = Column(Unicode, default=u"")
    message  = Column(Unicode, default=u"")

    def __init__(self, username, password, email):
        self.username = username
        self.password = hashlib.md5("lolsalt"+username.lower()+password).hexdigest()
        self.email = email

    def __repr__(self):
        return "<User('%s')>" % (self.name, )


map_ttq = Table('map_tag_to_quote', Base.metadata,
    Column('quote_id', Integer, ForeignKey('quote.id')),
    Column('tag_id', Integer, ForeignKey('tag.id'))
)


class Quote(Base):
    __tablename__ = "quote"

    id       = Column(Integer,    primary_key=True)
    owner_id = Column(Integer,    ForeignKey('user.id'), nullable=True, index=True)
    text     = Column(Unicode,    nullable=False)
    date     = Column(DateTime,   nullable=False, default=func.now())

    owner = relationship(
       "User",
        backref=backref('quotes', order_by=[id.desc(), ])
    )
    tags = relationship(
        "Tag",
        secondary=map_ttq,
        backref=backref("quotes"),
        order_by=["tag.name", ]
    )

    def __init__(self, text, tags=[]):
        self.text = text
        self.tags = tags

    def __repr__(self):
        return "<Quote('%s')>" % (self.text, )


class Tag(Base):
    __tablename__ = "tag"

    id       = Column(Integer, primary_key=True)
    name     = Column(Unicode, index=True, nullable=False)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<Tag('%s')>" % (self.name, )


metadata = Base.metadata

if __name__ == "__main__":
    metadata.create_all(engine)
