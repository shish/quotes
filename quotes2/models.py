import datetime
from typing import List

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

map_ttq = db.Table(
    "map_tag_to_quote",
    db.Column("quote_id", db.Integer, db.ForeignKey("quote.id")),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id")),
)


class Quote(db.Model):  # type: ignore
    __tablename__ = "quote"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(nullable=False)
    date: Mapped[datetime.datetime] = mapped_column(
        nullable=False, default=db.func.now()
    )

    tags: Mapped[List["Tag"]] = relationship(secondary=map_ttq, back_populates="quotes")

    def __init__(self, text: str, tags: List["Tag"] = []):
        self.text = text
        self.tags = tags

    @property
    def tag_str(self) -> str:
        return " ".join(tag.name for tag in self.tags)


class Tag(db.Model):  # type: ignore
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(index=True, nullable=False)

    quotes: Mapped[List[Quote]] = relationship(secondary=map_ttq, back_populates="tags")

    def __init__(self, name: str):
        self.name = name
