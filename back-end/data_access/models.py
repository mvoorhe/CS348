import uuid
from sqlalchemy import Index, Table, Column, ForeignKey, String, Integer, Float, DateTime, Enum as SQLAlchemyEnum
from sqlalchemy.orm import declarative_base, relationship
from enum import Enum
import datetime
import hashlib

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class watched_status(Enum):
    WATCHED = 1
    NOT_WATCHED = 0

class WatchlistMovie(Base):
    __tablename__ = 'watchlist_movies'
    
    watchlist_id = Column(String, ForeignKey("watchlist.id"), primary_key=True)
    movie_id = Column(String, ForeignKey("movie.id"), primary_key=True)
    date_added = Column(DateTime, default=datetime.datetime.now)
    status = Column(SQLAlchemyEnum(watched_status), default=watched_status.NOT_WATCHED)

    watchlist = relationship("Watchlist", back_populates="watchlist_movies")
    movie = relationship("Movie", back_populates="watchlist_movies")

class User(Base):
    __tablename__ = "user"

    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, nullable=False)
    email = Column(String, nullable=False)
    created = Column(DateTime, default=datetime.datetime.now())

    watchlist = relationship("Watchlist", back_populates="user", uselist=False)

    def dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "created": self.created,
            "watchlist": self.watchlist.dict() if self.watchlist else None
        }


class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("user.id"))

    user = relationship("User", back_populates="watchlist")
    watchlist_movies = relationship("WatchlistMovie", back_populates="watchlist")

    def dict(self):
        return {
            "id": self.id,
            "movies": self.movies
        }


class Director(Base):
    __tablename__ = "director"

    id = Column(String, primary_key=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)

    movie = relationship("Movie", back_populates="director")

    def __init__(self, first_name, last_name):

        self.first_name = first_name
        self.last_name = last_name
        
        # Automatically set the ID when a new Director is created
        self.id = Director.encode_id(first_name, last_name)

    def encode_id(first_name, last_name):
        full_name = f"{first_name.lower()}_{last_name.lower()}"
        # Use a hash function to generate a unique ID
        return hashlib.md5(full_name.encode()).hexdigest()
    

    def dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name" : self.last_name
        }


class Genre(Base):
    __tablename__ = "genre"

    name = Column(String, primary_key=True)

    movies = relationship("Movie", back_populates="genre")

    def dict(self):
        return {
            "name": self.name
        }

class Movie(Base):
    __tablename__ = "movie"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    release_year = Column(Integer, nullable=False)
    duration = Column(Integer, nullable=False)
    rating = Column(Float, nullable=True)
    director_id = Column(String, ForeignKey("director.id"))
    genre_name = Column(String, ForeignKey("genre.name"))

    director = relationship("Director", back_populates="movie")
    genre = relationship("Genre", back_populates="movies")
    watchlist_movies = relationship("WatchlistMovie", back_populates="movie")

    __table_args__ = (
        Index('idx_title', 'title'),
        Index('idx_release_year', 'release_year'),
    )

    def __init__(self, title, release_year, duration, rating, director_id, genre_name):

        self.title = title
        self.release_year = release_year
        self.duration = duration
        self.rating = rating
        self.director_id = director_id
        self.genre_name = genre_name
        
        # Automatically set the ID when a new Director is created
        self.id = Movie.encode_id(title, release_year, director_id)

    def encode_id(title, release_year, director_id):
        print("encode")
        full_code = f"{title.lower()}_{release_year}_{director_id}"
        # Use a hash function to generate a unique ID
        return hashlib.md5(full_code.encode()).hexdigest()

    def dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "release_year": self.release_year,
            "duration": self.duration,
            "rating": self.rating,
            "director": self.director.dict(),
            "genre": self.genre.dict()
        }
