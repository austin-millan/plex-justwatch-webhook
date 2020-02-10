from plexapi.server import PlexServer
from justwatch import JustWatch
import copy
import os

MAX_MEDIA_COUNT = 5
MAX_JW_QUERIES = 5
MOVIE_KEY = "Movies"
SHOW_KEY = "Shows"
PROVIDER_NAME_URL_MAP = {
    "Netflix": "netflix.com",
    "HBO": "hbo.com",
    "HBO Go": "play.hbogo.com",
    "Vudu": "vudu.com",
    "Hulu": "hulu.com",
    "Google Play": "play.google.com",
    "YouTube": "youtube.com",
    "Hulu": "hulu.com",
    "Microsoft": "microsoft.com",
    "iTunes": "itunes.apple.com",
    "Amazon": "amazon.com",
    "DirectTV": "directv.com"
}
jw = JustWatch(country='US')


def getPlexProviderCoverageStats(results, key):
    def buildProviderMap(provider_map):
        provider_table = {}
        provider_table["Providers"] = {}
        if provider_map:
            for provider, _ in provider_map.items():
                provider_table["Providers"][provider] = 0
        return provider_table
    if not results or key not in results:
        return {}

    total_movie_count = len(results.get(key))
    provider_count_table = buildProviderMap(PROVIDER_NAME_URL_MAP)
    output = {}
    for movie, providers in results.get(key).items():
        for provider in provider_count_table.get('Providers').keys():
            if providers["Providers"][provider]:
                provider_count_table["Providers"][provider] += 1
    for provider, count in provider_count_table.get("Providers").items():
        rate = int((count/total_movie_count)*100)
        output[provider] = {"count": count, "rate": rate}
    return output


def printPlexCoverageStats(stats):
    if not stats:
        return None
    for provider, stat in stats.items():
        print(f"{stat.get('count')} ({stat.get('rate')}%) on {provider}")

def providerHasMedia(title, providerURL, searchResults):
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

def getProvidersForMedia(title):
    def buildProviderMap(provider_map):
        provider_table = {}
        if provider_map:
            for provider, _ in provider_map.items():
                provider_table[provider] = False
        return provider_table

    provider_map = buildProviderMap(PROVIDER_NAME_URL_MAP)
    if not title or title == "":
        print("Title missing...")
        return False
    results = None
    attempts = 0
    while (results == None and attempts < MAX_JW_QUERIES):
        try:
            results = jw.search_for_item(query=title)
        except Exception as e:
            print(f"Error getting results from JustWatch API... Retrying {MAX_JW_QUERIES-attempts} times.")
        attempts += 1
    for provider_name, provider_url in PROVIDER_NAME_URL_MAP.items():
        if providerHasMedia(title=title, providerURL=provider_url, searchResults=results):
            provider_map[provider_name] = True
    return {"Providers": provider_map}

def addProviderLabelsToMedia(media):
    if media is None:
        print("Media list missing.")
        return False
    results = None
    for media_item in media:
        attempts = 0
        while (results == None and attempts < MAX_JW_QUERIES):
            try:
                results = jw.search_for_item(query=media_item.title)
            except Exception as e:
                print(f"Error getting results from JustWatch API... Retrying {MAX_JW_QUERIES-attempts} times.")
            attempts += 1
        for provider_name, provider_url in PROVIDER_NAME_URL_MAP.items():
            if providerHasMedia(title=media_item.title, providerURL=provider_url, searchResults=results):
                if provider_name not in media_item.labels:
                    # add new label
                    media_item.addLabel(provider_name)
            else:
                if provider_name in media_item.labels:
                    # remove existing label
                    media_item.removeLabel(provider_name)
    return True

def main():
    # Check env variables
    if "PLEX_BASE_URL" not in os.environ or "PLEX_TOKEN" not in os.environ:
        print("Set environment variables")
        exit(1)    
    plex = PlexServer(os.environ["PLEX_BASE_URL"], os.environ["PLEX_TOKEN"])
    # List all movies
    movies = plex.library.section('Movies')
    all_movies = movies.search(unwatched=True)
    all_movies = all_movies[:MAX_MEDIA_COUNT]
    movie_map = {MOVIE_KEY: {}}
    # List all shows
    addProviderLabelsToMedia(all_movies)
    # shows = plex.library.section('TV Shows')
    # all_shows = shows.search(unwatched=True)
    # all_shows = all_shows[:MAX_MEDIA_COUNT]
    # show_map = {SHOW_KEY: {}}
    # for i, item in enumerate(all_movies):
    #     res = getProvidersForMedia(item.title)
    #     movie_map[MOVIE_KEY][item.title] = res
    # for i, item in enumerate(all_shows):
    #     res = getProvidersForMedia(item.title)
    #     show_map[SHOW_KEY][item.title] = res
    # print("MOVIE STATS")
    # movie_stats = getPlexProviderCoverageStats(movie_map, MOVIE_KEY)
    # printPlexCoverageStats(movie_stats)
    # print("SHOW STATS")
    # show_stats = getPlexProviderCoverageStats(show_map, SHOW_KEY)
    # printPlexCoverageStats(show_stats)


if __name__ == '__main__':
    main()
