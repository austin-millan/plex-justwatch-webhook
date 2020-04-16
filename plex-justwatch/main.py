from plexapi.server import PlexServer
from justwatch import JustWatch
import copy
import os
import pprint
import time
import math

MAX_MEDIA_COUNT = 75
MAX_JW_QUERIES = 5
MOVIE_KEY = "Movies"
SHOW_KEY = "Shows"
PROVIDER_NAME_URL_MAP = {
    "Netflix": {
        "url": "netflix.com",
        "matched_movies": []
    },
    "HBO Go": {
        "url": "play.hbogo.com",
        "matched_movies": []
    },
    "Vudu": {
        "url": "vudu.com",
        "matched_movies": []
    },
    "Hulu": {
        "url": "hulu.com",
        "matched_movies": []
    },
    "Google Play": {
        "url": "play.google.com",
        "matched_movies": []
    },
    "YouTube": {
        "url": "youtube.com",
        "matched_movies": []
    },
    "Hulu": {
        "url": "hulu.com",
        "matched_movies": []
    },
    "Microsoft": {
        "url": "microsoft.com",
        "matched_movies": []
    },
    "iTunes": {
        "url": "itunes.apple.com",
        "matched_movies": []
    },
    "Amazon": {
        "url": "amazon.com",
        "matched_movies": []
    },
    "DirectTV": {
        "url": "directv.com",
        "matched_movies": []
    }
}
UNMATCHED = []
STOP_ON_MOVIE = ["Alice in Wonderland", "Aladdin", "Afflicted", "Ad Astra", "Abominable", "300", "12 Years a Slave", "8 Mile"]

jw = JustWatch(country='US')
pp = pprint.PrettyPrinter(indent=4)

def plexCoverage(all_movies, provider_map):
    total_movie_count = len(all_movies)
    for provider_name, provider_data in provider_map.items():
        provider_coverage = 0
        provider_count = len(provider_data.get("matched_movies"))
        if provider_count != 0:
            provider_coverage = math.floor((provider_count / total_movie_count)*100)
        print(f"{provider_name} has {provider_coverage}% movies on Plex.")


def providerHasMedia(title, providerURL, searchResults):
    # if title in STOP_ON_MOVIE:
    #     print(title)
    if not title or title == "":
        print("Title missing...")
        return False
    if not providerURL or providerURL == "":
        print("Provider URL missing...")
        return False
    if not searchResults:
        print("Search results missing...")
        return False
    for item in searchResults.get("items"):
        if "offers" not in item:
            continue
        for offer in item.get("offers"):
            if "urls" not in offer:
                continue
            if "standard_web" not in offer.get("urls"):
                continue
            if providerURL.lower() in offer.get("urls").get("standard_web"):
                return True
    return False


def findMediaProviders(media):
    if media is None:
        print("Media list missing.")
        return False
    jw = JustWatch(country='US')
    for media_item in media:
        attempts = 0
        results = None
        while ( (results == None or len(results.get("items")) == 0 ) and attempts < MAX_JW_QUERIES ):
            try:
                results = jw.search_for_item(query=media_item.title)
                attempts += 1
            except Exception as e:
                print(f"Got exception getting results: {e}")
        unmatched = True
        if len(results.get("items")) == 0:
            UNMATCHED.append(media_item.title)
            time.sleep(.500)
            continue
        for provider_name, provider_data in PROVIDER_NAME_URL_MAP.items():
            hasMedia = providerHasMedia(title=media_item.title, providerURL=provider_data.get("url"), searchResults=results)
            if hasMedia:
                PROVIDER_NAME_URL_MAP[provider_name]["matched_movies"].append(media_item.title)
                unmatched = False
            else:
                # print(f"Can't find {media_item.title} on provider {provider_name}")
                pass
        if unmatched:
            UNMATCHED.append(media_item.title)
    return True


if __name__ == '__main__':
    # Check env variables
    if "PLEX_BASE_URL" not in os.environ or "PLEX_TOKEN" not in os.environ:
        print("Set environment variables")
        exit(1)
    plex = PlexServer(os.environ["PLEX_BASE_URL"], os.environ["PLEX_TOKEN"])
    # List all movies
    movies = plex.library.section('Movies')
    all_movies = movies.search(unwatched=True)
    # all_movies = all_movies[:MAX_MEDIA_COUNT]
    findMediaProviders(all_movies)
    plexCoverage(all_movies, PROVIDER_NAME_URL_MAP)
    print("Done.")