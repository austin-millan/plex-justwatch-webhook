from plexapi.server import PlexServer
from justwatch import JustWatch
import copy
import os

baseurl = os.environ["PLEX_BASE_URL"]
token = os.environ["PLEX_TOKEN"]
plex = PlexServer(baseurl, token)
movie_limit = 75
curr_movie_i = 0

# Example 1: List all unwatched movies.
movies = plex.library.section('Movies')
just_watch = JustWatch(country='US')
all_movies = movies.search(unwatched=True)

movie_table = dict()
provider_table = {
    'Netflix': False,
    'DisneyPlus': False,
    'HBO': False,
}
provider_counts = {
    'Netflix': 0,
    'DisneyPlus': 0,
    'HBO': 0,
}
for movie in all_movies:
    movie_table[movie.title] = copy.copy(provider_table)


for video in all_movies:
    curr_movie_i += 1
    results = just_watch.search_for_item(query=video.title)
    for item in results.get("items"):
        if "offers" not in item:
            continue
        for offer in item.get("offers"):
            for provider, _ in provider_table.items():
                if "urls" not in offer:
                    continue
                if "standard_web" not in offer.get("urls"):
                    continue
                if provider.lower() in offer.get("urls").get("standard_web"):
                    movie_table[video.title][provider] = True
                    # provider_counts[provider] += 1
    # if curr_movie_i > movie_limit:
    #     break

# Do counts
for movie, providers in movie_table.items():
    for provider in provider_table.keys():
        if providers[provider]:
            provider_counts[provider] += 1


# print(movie_table)
for provider, count in provider_counts.items():
    res = int((count/len(all_movies))*100)
    print(f"{count} movies ({res}%) on {provider}")

missing_movies = 0
for movie, providers in movie_table.items():
    found = False
    for key, val in providers.items():
        if val:
            found = True
            break
    if found == False:
        missing_movies += 1

print("Movies not found elsewhere ", missing_movies)
        