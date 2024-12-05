from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
#import copy
from data_access import models
from database import SessionLocal, engine
from sqlalchemy.orm import Session
from sqlalchemy import text

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Start up
@app.on_event("startup")
def start_up_populate_db():
    db = SessionLocal()
    db.execute(text("PRAGMA foreign_keys = ON"))
    
    num_users = db.query(models.User).count()
    if num_users == 0:
        new_user = models.User(
            id=0,
            username='Grog',
            email='caskOfAle@cr.com',
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        new_watchlist = models.Watchlist(user_id=new_user.id)
        db.add(new_watchlist)
        db.commit()
        db.refresh(new_watchlist)
    
    num_genres = db.query(models.Genre).count()
    if num_genres == 0:
        new_genres = [
        models.Genre(name="Action"),
        models.Genre(name="Adventure"),
        models.Genre(name="Animated"),
        models.Genre(name="Comedy"),
        models.Genre(name="Drama"),
        models.Genre(name="Fantasy"),
        models.Genre(name="Historical"),
        models.Genre(name="Horror"),
        models.Genre(name="Musical"),
        models.Genre(name="Noir"),
        models.Genre(name="Romance"),
        models.Genre(name="Science Fiction"),
        models.Genre(name="Thriller"),
        models.Genre(name="Western")
        ]

        for genre in new_genres:
            db.add(genre)

        db.commit()

    db.close()

# Dependency for current user
def get_current_user(request : Request, db: Session = Depends(get_db)):

    user_id = request.session.get('user_id')
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user

# Main Page
@app.get("/", response_class=HTMLResponse)
async def root(request : Request, db : Session = Depends(get_db)):

    user = db.query(models.User).first()
    genres = db.query(models.Genre).all()

    genre_list = [genre.name for genre in genres]

    return templates.TemplateResponse("index.html", {"request": request, "user" : user, "genres" : genre_list})

# Add movie to watchlist
@app.post("/create_movie")
async def create_movie(movie: dict, db: Session = Depends(get_db)):

    user = db.query(models.User).first()

    try:
        print(f"Received movie data: {movie}")
        
        # Check if the director exists
        director_id = models.Director.encode_id(movie['director_first_name'], movie['director_last_name'])
        director = db.query(models.Director).filter_by(id=director_id).first()
        if not director:
            print(f"Director not found. Creating new director: {director_id} {movie['director_first_name']} {movie['director_last_name']}")
            director = models.Director(
                first_name=movie['director_first_name'],
                last_name=movie['director_last_name']
            )
            db.add(director)
            db.commit()
            db.refresh(director)
        
        # Add new movie
        new_movie = models.Movie(
            title=movie['title'],
            release_year=int(movie['release_year']),
            duration=int(movie['duration']),
            rating=float(movie['rating']) if movie['rating'] else None,
            director_id=director.id,
            genre_name=movie['genre']
        )

        db.add(new_movie)
        db.commit()
        db.refresh(new_movie)


        # Add movie to watchlist
        watchlist = db.query(models.Watchlist).filter_by(user_id=user.id).first()

        watchlist_movies_entry = models.WatchlistMovie(
            watchlist_id=watchlist.id,
            movie_id=new_movie.id
        )
        db.add(watchlist_movies_entry)
        db.commit()
        db.refresh(watchlist_movies_entry)

        return JSONResponse(content={"message": "Movie added successfully!"}, status_code=201)

    except Exception as e:
        return JSONResponse(content={"message": str(e)}, status_code=400)
    
@app.get("/edit_movie/{movie_id}")
def get_movie(movie_id: str, db: Session = Depends(get_db)):
    print(f"Fetching movie with ID: {movie_id}")  # Log the ID for debugging
    movie = db.query(models.Movie).filter(models.Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    
    return {
        "id": movie.id,
        "title": movie.title,
        "release_year": movie.release_year,
        "duration": movie.duration,
        "rating": movie.rating,
        "director_first_name": movie.director.first_name,
        "director_last_name": movie.director.last_name,
        "genre_name": movie.genre_name,
        "status": db.query(models.WatchlistMovie).filter_by(movie_id=movie_id).first().status
    }

@app.patch("/edit_movie/{movie_id}")
async def update_movie(movie_id: str, request: Request, db: Session = Depends(get_db)):
    print(f"PATCH request received for movie_id: {movie_id}")

    try:
        # Extract movie data from the request body
        movie_data = await request.json()
        print(f"Request Body: {movie_data}")

        # Query the movie from the database
        movie = db.query(models.Movie).filter(models.Movie.id == movie_id).first()
        if not movie:
            print("Movie not found.")
            raise HTTPException(status_code=404, detail="Movie not found")
    
        print(f"Movie found: {movie.title}")

        # Only update the fields that are present in the request body
        if 'title' in movie_data:
            movie.title = movie_data['title']
            print(f"Updated title to: {movie.title}")
        if 'release_year' in movie_data:
            movie.release_year = movie_data['release_year']
            print(f"Updated release year to: {movie.release_year}")
        if 'duration' in movie_data:
            movie.duration = movie_data['duration']
            print(f"Updated duration to: {movie.duration}")
        if 'rating' in movie_data:
            movie.rating = movie_data['rating']
            print(f"Updated rating to: {movie.rating}")
        if 'director' in movie_data:
            movie.director_id = movie_data['director']
            print(f"Updated director ID to: {movie.director_id}")
        if 'genre' in movie_data:
            movie.genre_name = movie_data['genre']
            print(f"Updated genre to: {movie.genre_name}")

        # Fetch the associated WatchlistMovie and update status
        watch_movie = db.query(models.WatchlistMovie).filter_by(movie_id=movie_id).first()
        if watch_movie and 'status' in movie_data:
            watch_movie.status = movie_data['status']
            print(f"Updated WatchlistMovie Status to: {watch_movie.status}")

        # Commit the changes to the database
        db.commit()
        print("Movie updated successfully.")

        return {"message": "Movie updated successfully"}
    
    except Exception as e:
        print(f"Error during update: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while updating the movie")


# Delete a movie
@app.delete("/delete_movie/{movie_id}", response_model=None, status_code=204)
async def delete_movie(movie_id: str, db: Session = Depends(get_db)):
    
    user = db.query(models.User).first()
    watchlist = db.query(models.Watchlist).filter_by(user_id=user.id).first()
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found for the user")

    watchlist_movie_entry = db.query(models.WatchlistMovie).filter_by(
        watchlist_id=watchlist.id,
        movie_id=movie_id
    ).first()
    if not watchlist_movie_entry:
        raise HTTPException(status_code=404, detail="Movie not found in the user's watchlist")

    db.delete(watchlist_movie_entry)
    db.commit()
    return None