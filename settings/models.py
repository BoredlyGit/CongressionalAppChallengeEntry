from sqlalchemy import orm, create_engine, Table, Column, Integer, String, Sequence, ForeignKey, DateTime
from project_sqlalchemy_globals import Session, Base, engine


class Setting(Base):
    __tablename__ = "settings"
    name = Column(String, primary_key=True)
    category = Column(String)
    value = Column(String)

    def set_value(self, value):
        self.value = value
        self.save()

    @classmethod
    def get_or_create(cls, name, value=None):
        a = Session.query(cls).filter(cls.name == name).one_or_none()
        if a is None:
            a = cls(name=name, value=value)
            Session.add(a)
            Session.commit()
        return a

    @classmethod
    def get(cls, name):
        return Session.query(cls).filter(cls.name == name).one_or_none()

    def save(self):
        Session.add(self)
        Session.commit()

