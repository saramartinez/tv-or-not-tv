from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, BLOB, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, backref, scoped_session

ENGINE = create_engine("sqlite:///tv.db", echo=False)
session = scoped_session(sessionmaker(bind=ENGINE,
                                      autocommit=False,
                                      autoflush=False))

Base = declarative_base()
Base.query = session.query_property()


# To create database run:
# python -i model.py
# ENGINE = create_engine("sqlite:///tv.db", echo=True)
# Base.metadata.create_all(ENGINE)


### Class declarations

## defines User class; instantiated through signup
class User(Base):
    """
    Class for User in users table. This class is instantiated
    when a user signs up via the /signup route.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(64), nullable=True)
    password = Column(String(64), nullable=True)
    name = Column(String(64), nullable=True)
    phone = Column(String(15), nullable=True)
    get_texts = Column(Boolean)
    zipcode = Column(String(15), nullable=True)
    timezone = Column(String(64), nullable=True)
    service_id = Column(Integer, ForeignKey('services.id')) # ServiceId in rovi

    service = relationship("Service", backref=backref("services", order_by=id))

    def __repr__(self):
        return "<User: name=%s, email=%s, zipcode=%s, timezone=%s,\
        service_id=%s" % (self.name, self.email, self.zipcode, self.timezone, self.service_id)

## defines Show class, created from search results. Stores
## basic data from initial query returning show information.
class Show(Base):
    """
    Show class created by adding show information and IDs to
    database from search results. Basic data to be reused on
    individual show information pages.
    """
    __tablename__ = "shows"

    id = Column(Integer, primary_key=True)
    cosmoid = Column(Integer, nullable=True) # rovi
    tvdb_id = Column(Integer, nullable=True) # for future use
    title = Column(String(64)) # title or video if in rovi search
    synopsis = Column(Text, nullable=True)
    img = Column(String(400), nullable=True)

    def __repr__(self):
        return "<TV Show: id=%d, title=%s, cosmoid=%s, synopsis=%s,\
         img=%s>" % (self.id, self.title, self.cosmoid, self.synopsis, self.img)

## defines Service class, storing TV provider's name and
## serviceID as it is specified in API.
class Service(Base):
    """
    Table keeps track of TV service provider IDs and names;
    stored when user searches zip codes during signup or while
    editing settings.
    """
    __tablename__ = "services"
    id = Column(Integer, primary_key=True)
    name = Column(String(144), nullable=True)

    def __repr__(self):
        return "<Service: id=%d, name=%s>" % (self.id, self.name)

## defines Favorite class with relationships back to User
## and Show tables. A user can save many shows as favorites.
class Favorite(Base):
    """
    Favorites table connects user table to TV show table with
    relationship/backref storing user's ID and show's ID.
    A user can save many shows as favorites.
    """
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    show_id = Column(Integer, ForeignKey('shows.cosmoid'))

    user = relationship("User", backref=backref("users", order_by=id))
    show = relationship("Show", backref=backref("shows"))

    def __repr__(self):
        return "<Favorite: id=%d, user_id=%d, show_id=%d>" % (self.id, self.user_id, self.show_id)

## table for cached results based on zip code API call
## to get service providers.
class CachedService(Base):
    """
    Table stores JSON object and timestamp from API query
    for TV service providers.
    """
    __tablename__ = "cached_services"
    id = Column(Integer, primary_key=True)
    zipcode_parameter = Column(String(15), nullable=True)
    timestamp = Column(DateTime, nullable=True)
    results = Column(Text, nullable=True)

    def __repr__(self):
        return "<CachedService: id=%d, zipcode_parameter=%d, timestamp=%r, results=%r>" % (id, zipcode_parameter, timestamp, results)


## table for cached results based on search for TV Listings
## with params: service_id, show_id
class CachedListing(Base):
    """
    Table stores JSON object and timestamp from API query
    for TV listings based on specific show ID and service ID
    as defined by User.
    """
    __tablename__ = "cached_listings"
    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, nullable=True)
    show_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime)
    results = Column(BLOB, nullable=True)

    def __repr__(self):
        return "<CachedListing: id=%d, service_id=%d, show_id=%d, timestamp=%r, results=%r>" % (id, service_id, show_id, timestamp, results)


## table for caching search results based on query sent to API
class CachedSearch(Base):
    """
    Table stores JSON object and timestamp with search results
    based on text query sent to API via search function.
    """
    __tablename__ = "cached_searches"
    id = Column(Integer, primary_key=True)
    query = Column(String(155), nullable=True)
    timestamp = Column(DateTime, nullable=True)
    results = Column(Text, nullable=True)

    def __repr__(self):
        return "<CachedSearch: id=%d, query=%s, timestamp=%r, results=%r>" % (id, query, timestamp, results)

### End class declarations


def main():
    """Because I might need this"""
    pass

if __name__ == "__main__":
    main()
