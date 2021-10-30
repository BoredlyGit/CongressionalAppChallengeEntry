import json

import sqlalchemy.exc
from sqlalchemy import orm, create_engine, Table, Column, Integer, String, Sequence, ForeignKey, DateTime
from project_sqlalchemy_globals import Session, Base, engine
import typing


class CoolerModel:
    def save(self):
        Session.add(self)
        Session.commit()


class TodoListModel(Base):
    __tablename__ = "todo_lists"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    cards = orm.relationship("TodoCardModel", back_populates="list")  # one-to-many

    def __init__(self, title):
        self.title = title
        self.save()

    @orm.reconstructor
    def db_init(self):
        pass

    def add_card(self, card: "TodoCardModel"):
        print(f"ADDING to {self.title}: ", card.title, [a.title for a in self.cards])
        self.cards.append(card)
        self.save()

    def remove_card(self, card):
        if isinstance(card, int):
            card = Session.query(TodoCardModel).filter(TodoCardModel.id == card).first()
        print(f"REMOVING from {self.title}: ", card.title, [a.title for a in self.cards])
        self.cards.remove(card)
        print(card)
        print(self.cards)
        try:
            self.save()
        except sqlalchemy.exc.InvalidRequestError:
            # IF the card is being removed from here as part of a delete process, it's database entry was probably
            # already deleted, so no more action is needed
            pass  # tbh idk why there is no need to save but whatever

    def save(self):
        print(f"SAVING {self.title}", [c.title for c in self.cards])
        Session.add(self)
        Session.commit()


card_labels_m2m = Table("todo_card_labels_m2m", Base.metadata,
                        Column("card_id", ForeignKey("todo_cards.id"), primary_key=True),
                        Column("label_id", ForeignKey("todo_labels.id"), primary_key=True)
                        )


class TodoLabelModel(Base):
    __tablename__ = "todo_labels"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    color = Column(String)
    cards = orm.relationship("TodoCardModel", secondary=card_labels_m2m, back_populates="labels")  # many-to-many

    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.save()

    @classmethod
    def get_or_create(cls, name, color=None):
        a = Session.query(cls).filter(cls.name == name).one_or_none()
        if a is None:
            a = cls(name=name, color=color)
            Session.add(a)
            Session.commit()
        return a

    def save(self):
        Session.add(self)
        Session.commit()


class TodoCardModel(Base):
    __tablename__ = "todo_cards"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(String)
    due_date = Column(DateTime)
    position = Column(Integer)
    list_id = Column(Integer, ForeignKey("todo_lists.id"))  # both this and the one below are necessary
    list = orm.relationship("TodoListModel")  # many-to-one
    labels = orm.relationship(TodoLabelModel, secondary=card_labels_m2m, back_populates="cards")  # many-to-many

    def __init__(self, parent_list, title, description, due_date, position=None, labels=None,):
        self.list = parent_list
        self.title = title
        self.description = description
        self.due_date = due_date
        self.position = position if position is not None else 0
        self.labels = [] if labels is None else labels

        self.save()

    @orm.reconstructor
    def from_db_init(self):
        pass

    def save(self):
        Session.add(self)
        Session.commit()


