__author__ = 'Anantha'

import media
import fresh_tomatoes

# creation of multiple instances of class Movie

toy_story = media.Movie("Toy Story",
                        "A story about toys and dilemma. Very Good Movie for kids and family",
                        "https://upload.wikimedia.org/wikipedia/en/1/13/Toy_Story.jpg",
                        "https://www.youtube.com/watch?v=vwyZH85NQC4",
                        "G", "81 mins", "1995")

avatar = media.Movie("Avatar",
                     "A story about human evading alien world",
                     "http://upload.wikimedia.org/wikipedia/id/b/b0/Avatar-Teaser-Poster.jpg",
                     "https://www.youtube.com/watch?v=5PSNL1qE6VY",
                     "PG - 13", "162 mins", "2009")

shutter_island = media.Movie("Shutter Island",
                             "A thriller story about mentally ill patient",
                             "https://upload.wikimedia.org/wikipedia/en/7/76/Shutterislandposter.jpg",
                             "https://www.youtube.com/watch?v=qdPw9x9h5CY",
                             "R", "138 mins", "2010")

inception = media.Movie("Inception",
                        "A story about dreams",
                        "https://upload.wikimedia.org/wikipedia/en/7/7f/Inception_ver3.jpg",
                        "https://www.youtube.com/watch?v=d3A3-zSOBT4",
                        "PG - 13", "148 mins", "2010")

wolf_of_wall_street = media.Movie("Wolf of Wall Street",
                                  "A story about debauchery and penny stocks",
                                  "https://upload.wikimedia.org/wikipedia/en/1/1f/WallStreet2013poster.jpg",
                                  "https://www.youtube.com/watch?v=iszwuX1AK6A",
                                  "R", "180 mins", "2013")

blood_diamond = media.Movie("Blood Diamond",
                            "A story about blood diamond",
                            "https://upload.wikimedia.org/wikipedia/en/5/5a/Blooddiamondposter.jpg",
                            "https://www.youtube.com/watch?v=qmXkCXd0QL8",
                            "R", "143 mins", "2006")


# creating a collection of class Movie instances to pass to the static web page method in fresh_tomatoes.py
movies = [toy_story, avatar, inception, shutter_island, wolf_of_wall_street, blood_diamond]

# calling open_movies_page method to create the static movie trailer web page
fresh_tomatoes.open_movies_page(movies)
