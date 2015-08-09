__author__ = 'Anantha'

import webbrowser

# definition of a class Movie

class Movie():
# definition of init method with class variables initialization
    def __init__(self, title, storyline, poster_url, trailer_url, rating, runtime, release_year):
        self.title = title
        self.storyline = storyline
        self.poster_url = poster_url
        self.trailer_url = trailer_url
        self.rating = rating
        self.runtime = runtime
        self.release_year = release_year

