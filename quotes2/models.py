from typing import List
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


map_ttq = db.Table(
    "map_tag_to_quote",
    db.Column("quote_id", db.Integer, db.ForeignKey("quote.id")),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id")),
)


class Quote(db.Model):  # type: ignore
    __tablename__ = "quote"

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Unicode, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=db.func.now())

    tags = db.relationship("Tag", secondary=map_ttq, backref=db.backref("quotes"))

    def __init__(self, text: str, tags: List["Tag"] = []):
        self.text = text
        self.tags = tags

    @property
    def tag_str(self) -> str:
        return " ".join(tag.name for tag in self.tags)


class Tag(db.Model):  # type: ignore
    __tablename__ = "tag"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode, index=True, nullable=False)

    def __init__(self, name: str):
        self.name = name
