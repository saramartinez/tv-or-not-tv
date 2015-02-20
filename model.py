from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, backref, scoped_session

ENGINE = create_engine("sqlite:///tv.db", echo=True)
session = scoped_session(sessionmaker(bind=ENGINE,
                                      autocommit = False,
                                      autoflush = False))

Base = declarative_base()
Base.query = session.query_property()

### Class declarations go here
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(64), nullable=True)
    password = Column(String(64), nullable=True)
    name = Column(String(64), nullable=True)
    zipcode = Column(String(15), nullable=True) #postalcode in rovi
    timezone = Column(String(64), nullable=True)
    service_id = Column(Integer, ForeignKey('services.id')) # serviceid in rovi

    service = relationship("Service", backref=backref("services", order_by=id))

    def __repr__(self):
        return "<User: name=%s, email=%s, zipcode=%s, timezone=%s, service_id=%s" % (self.name, self.email, self.zipcode, self.timezone, self.service_id)


class Show(Base):
    __tablename__ = "shows"

    id = Column(Integer, primary_key= True) #cosmoid in rovi -- 
    cosmoid = Column(Integer, nullable=True) # rovi
    tvdb_id = Column(Integer, nullable=True) # for future use
    title = Column(String(64)) # title or video if in rovi search

    def __repr__(self):
        return "<TV Show: id=%d, title=%s>" % (self.id, self.title)


class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True)    
    name = Column(String(144), nullable=True)

    def __repr__(self):
        return "<Service: id=%d, name=%s>" % (self.id, self.name)


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    show_id = Column(Integer, ForeignKey('shows.id'))

    user = relationship("User", backref=backref("users", order_by=id))
    show = relationship("Show", backref=backref("shows"))

    def __repr__(self):
        return "<Favorite: id=%d, user_id=%d, show_id=%d>" % (self.id, self.user_id, self.show_id)

### End class declarations

def main():
    """Because I might need this"""
    pass

if __name__ == "__main__":
    main()