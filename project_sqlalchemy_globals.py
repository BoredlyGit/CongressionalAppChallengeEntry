from sqlalchemy import orm, create_engine

Base = orm.declarative_base()
engine = create_engine('sqlite:///db.sqlite3', echo=False)
Session = orm.sessionmaker(bind=engine)()
Session.expire_on_commit = False
