from app.services.stremio_service import StremioService
from app.services.tmdb_service import TMDBService

import asyncio
from .tmdb.genre import MOVIE_GENRE_TO_ID_MAP, SERIES_GENRE_TO_ID_MAP
from collections import Counter


class DynamicCatalogService:

    def __init__(self, stremio_service: StremioService):
        self.stremio_service = stremio_service
        self.tmdb_service = TMDBService()

    @staticmethod
    def normalize_type(type_):
        return "series" if type_ == "tv" else type_

    def build_catalog_entry(self, item, label):
        return {
            "type": self.normalize_type(item.get("type")),
            "id": item.get("_id"),
            "name": f"Because you {label} {item.get('name')}",
            "extra": [],
        }

    def process_items(self, items, seen_items, seed, label):
        entries = []
        for item in items:
            type_ = self.normalize_type(item.get("type"))
            if item.get("_id") in seen_items or seed[type_]:
                continue
            seen_items.add(item.get("_id"))
            seed[type_] = True
            entries.append(self.build_catalog_entry(item, label))
        return entries

    async def get_watched_loved_catalogs(self, library_items: list[dict]):
        seen_items = set()
        catalogs = []

        seed = {
            "watched": {
                "movie": False,
                "series": False,
            },
            "loved": {
                "movie": False,
                "series": False,
            },
        }

        loved_items = library_items.get("loved", [])
        watched_items = library_items.get("watched", [])

        catalogs += self.process_items(loved_items, seen_items, seed["loved"], "Loved")
        catalogs += self.process_items(watched_items, seen_items, seed["watched"], "Watched")

        return catalogs

    async def get_genre_based_catalogs(self, library_items: list[dict]):
        # get separate movies and series lists from loved items
        loved_movies = [item for item in library_items.get("loved", []) if item.get("type") == "movie"]
        loved_series = [item for item in library_items.get("loved", []) if item.get("type") == "series"]

        # only take last 5 results from loved movies and series
        loved_movies = loved_movies[:5]
        loved_series = loved_series[:5]

        # fetch details:: genre details from tmdb addon
        movie_tasks = [self.tmdb_service.get_addon_meta("movie", {item.get('_id')}) for item in loved_movies]
        series_tasks = [self.tmdb_service.get_addon_meta("series", {item.get('_id')}) for item in loved_series]
        movie_details = await asyncio.gather(*movie_tasks)
        series_details = await asyncio.gather(*series_tasks)

        # now fetch all genres for moviees and series and sort them by their occurance
        movie_genres = [detail.get("genres", []) for detail in movie_details]
        series_genres = [detail.get("genres", []) for detail in series_details]

        # now flatten list and count the occurance of each genre for both movies and series separately
        movie_genre_counts = Counter([genre for sublist in movie_genres for genre in sublist])
        series_genre_counts = Counter([genre for sublist in series_genres for genre in sublist])
        sorted_movie_genres = sorted(movie_genre_counts.items(), key=lambda x: x[1], reverse=True)
        sorted_series_genres = sorted(series_genre_counts.items(), key=lambda x: x[1], reverse=True)

        # now get the top 5 genres for movies and series
        top_5_movie_genres = sorted_movie_genres[:5]
        top_5_series_genres = sorted_series_genres[:5]

        # convert id to name
        top_5_movie_genres_names = [MOVIE_GENRE_TO_ID_MAP[genre_id] for genre_id, _ in top_5_movie_genres]
        top_5_series_genres_names = [SERIES_GENRE_TO_ID_MAP[genre_id] for genre_id, _ in top_5_series_genres]

        # Refactored and added exception handling for genre-based catalog generation

        catalogs = []

        try:
            # Helper function to generate catalog entry
            def build_catalog(media_type, genre_indexes, genre_ids, genre_names):
                # Defensive check: ensure enough genres to access required indices
                try:
                    ids = []
                    for idx in genre_indexes:
                        ids.append(str(genre_ids[idx][0]))
                    names = []
                    for idx in genre_indexes:
                        names.append(str(genre_names[idx]))
                    return {
                        "type": media_type,
                        "id": f"watchly.genre." + ("-".join(ids) if len(ids) == 2 else "_".join(ids)),
                        "name": "-".join(names),
                        "extra": [],
                    }
                except (IndexError, KeyError, TypeError) as e:
                    # Not enough genres? Return None, will be filtered
                    return None

            # Prepare catalogs for movies
            if len(top_5_movie_genres) >= 5:
                c1 = build_catalog("movie", [0, 1], top_5_movie_genres, top_5_movie_genres_names)
                c2 = build_catalog("movie", [2, 3, 4], top_5_movie_genres, top_5_movie_genres_names)
                if c1:
                    catalogs.append(c1)
                if c2:
                    catalogs.append(c2)
            else:
                # Fallback if not enough genres
                for i in range(0, len(top_5_movie_genres), 2):
                    c = build_catalog(
                        "movie",
                        list(range(i, min(i + 2, len(top_5_movie_genres)))),
                        top_5_movie_genres,
                        top_5_movie_genres_names,
                    )
                    if c:
                        catalogs.append(c)

            # Prepare catalogs for series
            if len(top_5_series_genres) >= 5:
                c3 = build_catalog("series", [0, 1], top_5_series_genres, top_5_series_genres_names)
                c4 = build_catalog("series", [2, 3, 4], top_5_series_genres, top_5_series_genres_names)
                if c3:
                    catalogs.append(c3)
                if c4:
                    catalogs.append(c4)
            else:
                for i in range(0, len(top_5_series_genres), 2):
                    c = build_catalog(
                        "series",
                        list(range(i, min(i + 2, len(top_5_series_genres)))),
                        top_5_series_genres,
                        top_5_series_genres_names,
                    )
                    if c:
                        catalogs.append(c)
        except Exception as e:
            # Log exception if logger available, else print
            try:
                from loguru import logger

                logger.error(f"Exception building genre-based catalogs: {e}")
            except ImportError:
                print(f"Exception building genre-based catalogs: {e}")

        return catalogs
