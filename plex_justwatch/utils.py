from plexapi.server import PlexServer
# from plexapi.myplex import MyPlex
import plexapi.myplex
import plexapi.playlist
from plexapi.myplex import MyPlexAccount
from justwatch import JustWatch
import copy
import os
import pprint
import time
import math
import logging
import sched
import time
import datetime
from functools import wraps
from threading import Thread
from pylogrus import PyLogrus, TextFormatter, JsonFormatter
import ast

MAX_MEDIA_COUNT = 75
MAX_JW_QUERIES = 5
MOVIE_KEY = "Movies"
SHOW_KEY = "Shows"
PERIODIC_SCAN_INTERVAL = 10000
UNMATCHED = []
PROVIDER_NAME_URL_MAP = {
  "Providers": {
    "Netflix": {
      "url": "netflix.com",
      "matched_movies": [],
      "poster": "https://cdn.vox-cdn.com/thumbor/AwKSiDyDnwy_qoVdLPyoRPUPo00=/39x0:3111x2048/1400x1400/filters:focal(39x0:3111x2048):format(png)/cdn.vox-cdn.com/uploads/chorus_image/image/49901753/netflixlogo.0.0.png",
    },
    "HBO Go": {
      "url": "play.hbogo.com",
      "matched_movies": [],
      "poster": "https://lh3.googleusercontent.com/9UwtRXMngCerXAh2Kvg_4WVNCOxRsXiHd1xntaGNPAQ_4_Xj3eH6v_agpy_D9bHUJgfZ"
    },
    "Vudu": {
      "url": "vudu.com",
      "matched_movies": [],
      "poster": "https://www.logolynx.com/images/logolynx/s_f8/f8a3591773c92589eb6b1efd2e886515.png"
    },
    "Hulu": {
      "url": "hulu.com",
      "matched_movies": [],
      "poster": "https://cdn1.iconfinder.com/data/icons/metro-ui-dock-icon-set--icons-by-dakirby/512/Hulu.png"
    },
    "Google Play": {
      "url": "play.google.com",
      "matched_movies": [],
      "poster": "https://img.talkandroid.com/uploads/2013/07/google_play_logo_text_and_graphic_2016.png"
    },
    "YouTube": {
      "url": "youtube.com",
      "matched_movies": [],
      "poster": "https://cdn1.iconfinder.com/data/icons/logotypes/32/youtube-512.png"
    },
    "Microsoft": {
      "url": "microsoft.com",
      "matched_movies": [],
      "poster": "https://cdn4.iconfinder.com/data/icons/flat-brand-logo-2/512/microsoft-512.png"
    },
    "iTunes": {
      "url": "itunes.apple.com",
      "matched_movies": [],
      "poster": "https://i1.pngguru.com/preview/215/624/1011/clay-os-6-a-macos-icon-itunes-pink-music-note-illustration-png-clipart.jpg"
    },
    "Amazon": {
      "url": "amazon.com",
      "matched_movies": [],
      "poster": "https://cdn2.iconfinder.com/data/icons/social-icons-33/128/Amazon-512.png"
    },
    "DirectTV": {
      "url": "directv.com",
      "matched_movies": [],
      "poster": "https://apprecs.org/gp/images/app-icons/300/ec/com.directv.promo.shade.jpg"
    },
    "Hoopla": {
      "url": "hoopladigital.com",
      "matched_movies": [],
      "poster": "https://d33enj3lw2yaz0.cloudfront.net/logo/google-search-logo-smaller.png"
    },
    "FandangoNOW": {
      "url": "fandangonow.com",
      "matched_movies": [],
      "poster": "https://cdn.crowdtwist.com/img/v2/c8eca3fa44889552826a60ccff31a59919e565bc/w/h/0/image.png"
    }
  }
}


def getProviderURL(provider_name):
    return PROVIDER_NAME_URL_MAP.get('Providers', {}).get(provider_name, {}).get("url")


def getProviderPosterURL(provider_name):
    return PROVIDER_NAME_URL_MAP.get('Providers', {}).get(provider_name, {}).get("poster")


def getAllProviderNames():
    return list(PROVIDER_NAME_URL_MAP.get('Providers', {}).keys())


BLACKLISTED_PLAYLISTS = ['Pandemic Time!']

class PlexJustWatchPlaylistManager:
    def __init__(self):
        # Init locals
        self.logger = None
        self.justwatch = None
        self.plex = None
        self.myplex = None
        self.ignored_users = []
        self.movie_library_name = ""
        self.show_library_name = ""
        self.update_user_playlists = False
        self.supported_media_types = ['Movie', 'Movies', 'Show','Shows']
        # Init client
        self._setup_logging()
        self._setup_justwatch_client()
        self._setup_plex_client()
        if 'BLACKLISTED_USERS' in os.environ:
            try:
                # first try list
                parsed = ast.literal_eval(os.environ.get('BLACKLISTED_USERS'))
                self.ignored_users = parsed
            except Exception as e:
                # sercond try string
                self.ignored_users.append(os.environ.get('BLACKLISTED_USERS'))
        if os.environ.get('UPDATE_USER_PLAYLISTS', 'n') == 'y':
            self.update_user_playlists = True
        self.movie_library_name = os.environ.get('MOVIES_LIBRARY', 'Movies')
        self.show_library_name = os.environ.get('SHOWS_LIBRARY', 'TV Shows')
        if os.environ.get('UPDATE_USER_PLAYLISTS', 'n') == 'y':
            self.update_user_playlists = True
            self.copy_provider_playlists_to_users()
        if os.environ.get('PRE_CLEAR_PLAYLISTS', 'n') == 'y':
            self.clear_playlists()
        if os.environ.get('SYNC_EXISTING_LIBRARIES', 'n') == 'y':
            self.logger.info("Syncing existing libraries. This is a blocking process.")
            self.sync_all()
        
    def format_provider_playlist_name(self, mediaType, providerName):
        if mediaType not in self.supported_media_types:
            self.logger.error(f"Unknown media type: {mediaType}")
            return f"On {providerName}"
        if providerName != None:
            return f"{mediaType} On {providerName}"
        return None

    def format_provider_name_from_playlist_name(self, playlistName):
        formattedPlaylistName = ""
        if playlistName != None:
            split = playlistName.split(" ")
            for idx, item in enumerate(split):
                if not item.startswith("Movies") and not item.startswith("Shows") and not item.startswith("On"):
                    formattedPlaylistName = ' '.join(split[idx:])
                    break
            return formattedPlaylistName
        return None

    def clear_playlists(self):
        for playlist in self.plex.playlists():
            if playlist.title not in BLACKLISTED_PLAYLISTS:
                playlist.delete()

    def _setup_logging(self):
        try:
            logging.setLoggerClass(PyLogrus)
            logger = logging.getLogger(__name__)
            logger.setLevel(logging.DEBUG)
            formatter = TextFormatter(datefmt='Z', colorize=True)
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            ch.setFormatter(formatter)
            logger.addHandler(ch)
            self.logger = logger
        except Exception as e:
            raise ValueError(f"Error getting logger: {e}")

    def _setup_justwatch_client(self):
        try:
            self.justwatch = JustWatch(country='US')
        except Exception as e:
            err = f"Unable to configure justwatch client due to error: {e}"
            self.logger.error(err)
            raise ValueError(err)
        
    def _setup_plex_client(self):
        if "PLEX_BASE_URL" not in os.environ or "PLEX_TOKEN" not in os.environ:
            self.logger.error("Unable to initialize Plex server.")
            raise ValueError("Unable to configure Plex Client, missing environment variables")
        else:
            self.plex = PlexServer(os.environ["PLEX_BASE_URL"], os.environ["PLEX_TOKEN"])
        if "PLEX_ACCOUNT_USER" not in os.environ or "PLEX_TOKEN" not in os.environ:
            self.logger.error("Unable to initialize MyPlexAccount.")
            raise ValueError("Unable to initialize MyPlexAccount, missing environment variables")
        else:
            self.myplex = MyPlexAccount(username=os.environ["PLEX_ACCOUNT_USER"], token=os.environ["PLEX_TOKEN"])

    def provider_has_title(self, title, providerURL, searchResults):
        if not title or title == "":
            self.logger.error("Title missing...")
            return False
        if not providerURL or providerURL == "":
            self.logger.error("Provider URL missing...")
            return False
        if not searchResults:
            self.logger.error("Search results missing...")
            return False
        for item in searchResults.get("items"):
            if "offers" not in item:
                continue
            for offer in item.get("offers"):
                if "urls" not in offer:
                    continue
                if "standard_web" not in offer.get("urls"):
                    continue
                if providerURL.lower() in offer.get("urls", {}).get("standard_web"):
                    if title.lower() == item.get('title', '').lower():
                        return True
        return False

    def sync_all(self):
        self.sync_library(self.movie_library_name)
        self.sync_library(self.show_library_name)
        if self.update_user_playlists:
            self.copy_provider_playlists_to_users()

    def sync_library(self, library=''):
        if not library:
            self.logger.error("Must provide library name to sync.")
            return
        for media_item in self.plex.library.section(library).search():
            providers = self.get_current_justwatcH_providers_for_title(media_item.title)
            if providers:
                self.logger.info(f"Found providers for {media_item.title}: {providers}")
                for provider in providers:
                    self.update_title_in_playlist(provider, media_item.title, library=library)
            else:
                self.logger.info(f"No provider found for title \"{media_item.title}\"")

    def get_current_justwatcH_providers_for_title(self, title):
        if title == "":
            self.logger.info("Missing title, returning early.")
            return
        self.logger.info(f"Querying JustWatch for title: \"{title}\"")
        matched_providers = []
        attempts = 0
        results = None
        while ( (results == None or len(results.get("items")) == 0 ) and attempts < MAX_JW_QUERIES ):
            try:
                results = self.justwatch.search_for_item(query=title)
                attempts += 1
            except Exception as e:
                self.logger.error(f"Got exception getting results: {e}")
        for provider_name in getAllProviderNames():
            provider_url = getProviderURL(provider_name)
            hasMedia = self.provider_has_title(title=title, providerURL=provider_url, searchResults=results)
            if hasMedia:
                matched_providers.append(provider_name)
            else:
                pass
        return matched_providers

    def process_event(self, payload):
        if not payload:
            self.logger.error("Empty payload. Early return.")
            return
        event_type = payload.get('event')
        if not event_type or event_type == '':
            self.logger.error("No event type")
            return
        if event_type == "library.new":
            self.logger.info("Processing library.new event")
            title = payload.get("Metadata", {}).get("title", "")
            mediaType = payload.get("Metadata", {}).get("type", "")
            library = ""
            if mediaType == 'movie':
                library = self.movie_library_name
            else:
                library = self.show_library_name
            if title == "":
                self.logger.error("Unable to get title from event.")
                return
            self.logger.info(f"Movie \"{title}\" added to library \"{library}\"")
            providers = self.get_current_justwatcH_providers_for_title(title)
            if providers:
                self.logger.info(f"Found providers for movie \"{title}\": {providers}")
                for provider in providers:
                    self.update_title_in_playlist(provider, title, library)
            else:
                self.logger.info(f"No providers found for title: \"{title}\"")
            self.prune_title_from_playlists(title)
            if self.update_user_playlists:
                self.copy_provider_playlists_to_users()

    def get_provider_playlist(self, mediaType, providerName):
        if providerName == "" or providerName == None:
            self.logger.error("Cannot add item to empty playlist.")
            return
        playlists = self.plex.playlists()
        provider_playlist = None
        formattedPlaylistName = self.format_provider_playlist_name(mediaType, providerName)
        for playlist in playlists:
            if playlist.title == formattedPlaylistName:
                return playlist
        return None

    def prune_title_from_playlists(self, title):
        # Prunes item from Plex playlists if it's no longer supported by provider.
        plexPlaylists = self.get_current_plex_provider_playlists()
        currentProviders = self.get_current_justwatcH_providers_for_title(title)
        for playlist in plexPlaylists:
            formattedName = self.format_provider_name_from_playlist_name(playlist.title)
            if formattedName not in currentProviders:
                self.logger.info(f"Pruning title \"{title}\" from playlist: \"{playlist.title}\"")
                items = self.plex.library.section(self.movie_library_name).search(title)
                for item in items:
                    try:
                        result = playlist.removeItem(item)
                        self.logger.info(f"Successfully pruned title: \"{title}\"")
                    except Exception as e:
                        self.logger.error(f"Error pruning {title} from playlist: \"{playlist.title}\" due to error: {e} ")

    def update_title_in_playlist(self, providerName, title, library='Movies'):
        if providerName == "" or providerName == None:
            self.logger.error("Cannot add item to empty provider.")
            return
        if title == "" or title == None:
            self.logger.error(f"Cannot add empty item to playlist \"{providerName}\".")
            return
        items = self.plex.library.section(library).search(title)
        for item in items:
            mediaType = 'Movies'
            if item.type == 'show':
                mediaType = 'Shows'
            if item.type == 'movie':
                mediaType == 'Movies'
            formattedPlaylistName = self.format_provider_playlist_name(mediaType, providerName)
            provider_playlist = self.get_provider_playlist(mediaType, providerName)
            if provider_playlist == None:
                self.logger.info(f"Creating playlist \"{formattedPlaylistName}\"")
                provider_playlist = self.plex.createPlaylist(formattedPlaylistName, item)
                provider_playlist.edit(title=formattedPlaylistName, summary=f"A playlist containing {mediaType} found on {providerName}")
                provider_playlist.uploadPoster(url=getProviderPosterURL(providerName))
            else:
                # self.logger.info(f"Adding to playlist \"{formattedPlaylistName}\"")
                provider_playlist.addItems(item)
            
    def update_media_item_in_playlist(self, providerName, media_item):
        if providerName == "" or providerName == None:
            self.logger.error("Cannot add item to empty provider.")
            return
        if media_item == None:
            self.logger.error(f"Cannot add empty item to playlist {providerName}.")
            return
        item = None
        media_type = 'Movie'
        if media_item.type == 'movie':
            media_type = 'Movies'
            item = self.plex.library.section(self.movie_library_name).search(media_item.title)
        if media_item.type == 'show':
            media_type = 'Shows'
            item = self.plex.library.section(self.show_library_name).search(media_item.title)
        formattedPlaylistName = self.format_provider_playlist_name(media_type, providerName)
        provider_playlist = self.get_provider_playlist(media_type, providerName)
        if provider_playlist == None:
            self.logger.info(f"Creating playlist \"{formattedPlaylistName}\"")
            provider_playlist = self.plex.createPlaylist(formattedPlaylistName, item)
            provider_playlist.edit(title=formattedPlaylistName, summary=f"A playlist containing movies found on {providerName}")
            provider_playlist.uploadPoster(url=getProviderPosterURL(providerName))
        else:
            self.logger.info(f"Adding to playlist \"{formattedPlaylistName}\"")
            provider_playlist.addItems(item)

    def copy_provider_playlists_to_users(self):
        users = self.myplex.users()
        for user in users:
            if user.username in self.ignored_users:
                self.logger.info(f"Skipping copying playlist to user {user.username}")
                continue
            if not user.username:
                self.logger.info("Skipping empty user, probably just an invited user.")
                continue
            self.logger.info(f"Copying playlists to user: {user.username}")
            for playlist in self.get_current_plex_provider_playlists():
                try:
                    playlist.copyToUser(user.username)
                except Exception as e:
                    self.logger.error(f"Unable to copy playists to user {user.username} due to error: {e}")

    def get_current_plex_provider_playlists(self):
        all_playlists = self.plex.playlists()
        playlists = []
        for playlist in all_playlists:
            for provider in getAllProviderNames():
                for mediaType in ['Movies', 'Shows']:
                    formattedTitle = self.format_provider_playlist_name(mediaType, provider)
                    if playlist.title == formattedTitle:
                        playlists.append(playlist)
        return playlists


if __name__ == '__main__':
    NEW_CONTENT_PAYLOAD = {'event': 'library.new', 'user': True, 'owner': True, 'Account': {'id': 1, 'thumb': 'https://plex.tv/users/071db0d4a79a4d18/avatar?c=1582404481', 'title': 'CreaterOfAccounts'}, 'Server': {'title': 'Clunky', 'uuid': 'd97cb25be6ceeccb2e5b3d1fbef06bf59ffcd5fc'}, 'Metadata': {'librarySectionType': 'movie', 'ratingKey': '13386', 'key': '/library/metadata/13386', 'guid': 'com.plexapp.agents.imdb://tt0071203?lang=en', 'studio': 'Nippon Herald Films', 'type': 'movie', 'title': "Taxi Driver", 'originalTitle': '哀しみのベラドンナ', 'contentRating': 'Unrated', 'summary': 'A peasant woman is banished from her village and makes a deal with the devil to gain magical powers.', 'rating': 8.9, 'audienceRating': 7.6, 'year': 1973, 'thumb': '/library/metadata/13386/thumb/1587594379', 'art': '/library/metadata/13386/art/1587594379', 'duration': 5340000, 'originallyAvailableAt': '1973-06-30', 'addedAt': 1587594362, 'updatedAt': 1587594379, 'audienceRatingImage': 'rottentomatoes://image.rating.upright', 'chapterSource': 'media', 'primaryExtraKey': '/library/metadata/13387', 'ratingImage': 'rottentomatoes://image.rating.ripe', 'Genre': [{'id': 27, 'filter': 'genre=27', 'tag': 'Animation', 'count': 159}, {'id': 163, 'filter': 'genre=163', 'tag': 'Drama', 'count': 423}, {'id': 422, 'filter': 'genre=422', 'tag': 'Fantasy', 'count': 193}, {'id': 1175, 'filter': 'genre=1175', 'tag': 'Horror', 'count': 173}], 'Director': [{'id': 25960, 'filter': 'director=25960', 'tag': 'Eiichi Yamamoto'}], 'Writer': [{'id': 25961, 'filter': 'writer=25961', 'tag': 'Yoshiyuki Fukuda'}, {'id': 25962, 'filter': 'writer=25962', 'tag': 'Eiichi Yamamoto'}], 'Producer': [{'id': 25969, 'filter': 'producer=25969', 'tag': 'Osamu Tezuka'}], 'Country': [{'id': 6281, 'filter': 'country=6281', 'tag': 'Japan', 'count': 40}], 'Role': [{'id': 25963, 'filter': 'actor=25963', 'tag': 'Aiko Nagayama', 'role': 'Jeanne / Belladonna'}, {'id': 21562, 'filter': 'actor=21562', 'tag': 'Tatsuya Nakadai', 'count': 4, 'role': 'The Devil', 'thumb': 'http://image.tmdb.org/t/p/original/3P6rX9NCFAwfKjAOj1fh1lk7I0H.jpg'}, {'id': 25964, 'filter': 'actor=25964', 'tag': 'Katsuyuki Itô', 'role': 'Jean'}, {'id': 25965, 'filter': 'actor=25965', 'tag': 'Masaya Takahashi', 'role': 'The Lord', 'thumb': 'http://image.tmdb.org/t/p/original/q0f7lBJxUUmWoJlh0DsT51E6Vlu.jpg'}, {'id': 25966, 'filter': 'actor=25966', 'tag': 'Shigako Shimegi', 'role': "The Lord's Mistress"}, {'id': 25967, 'filter': 'actor=25967', 'tag': 'Natsuka Yashiro', 'role': 'The Witch'}, {'id': 25968, 'filter': 'actor=25968', 'tag': 'Masakane Yonekura', 'role': 'The Priest', 'thumb': 'http://image.tmdb.org/t/p/original/mxjvLuceLhjCtCwMEkhBwBglHlo.jpg'}], 'Similar': [{'id': 37791, 'filter': 'similar=37791', 'tag': "All Tomorrow's Parties"}, {'id': 25977, 'filter': 'similar=25977', 'tag': 'Hard Contract'}, {'id': 25985, 'filter': 'similar=25985', 'tag': 'The Gates of Paris'}, {'id': 37793, 'filter': 'similar=37793', 'tag': 'The Dreamed Path'}, {'id': 37792, 'filter': 'similar=37792', 'tag': 'Naked Bullet'}, {'id': 40442, 'filter': 'similar=40442', 'tag': 'Privilege'}, {'id': 37799, 'filter': 'similar=37799', 'tag': 'Petulia'}, {'id': 25980, 'filter': 'similar=25980', 'tag': 'Golden Salamander'}, {'id': 37798, 'filter': 'similar=37798', 'tag': 'Sylvia and the Ghost'}, {'id': 37797, 'filter': 'similar=37797', 'tag': 'Escape from Crime'}, {'id': 25979, 'filter': 'similar=25979', 'tag': 'Counter-Espionage'}, {'id': 25983, 'filter': 'similar=25983', 'tag': "Dr. Kildare's Strange Case"}, {'id': 37794, 'filter': 'similar=37794', 'tag': 'Everyday Life in a Syrian Village'}, {'id': 37795, 'filter': 'similar=37795', 'tag': 'The Great Man Votes'}, {'id': 25982, 'filter': 'similar=25982', 'tag': 'Danger Lights'}, {'id': 25984, 'filter': 'similar=25984', 'tag': 'West Of Shanghai'}, {'id': 25981, 'filter': 'similar=25981', 'tag': 'The Squaw Man'}, {'id': 37796, 'filter': 'similar=37796', 'tag': 'Captured!'}, {'id': 25978, 'filter': 'similar=25978', 'tag': 'The Texas Rangers'}, {'id': 25989, 'filter': 'similar=25989', 'tag': 'Born in Flames'}]}}
    manager = PlexJustWatchPlaylistManager()
    manager.process_event(NEW_CONTENT_PAYLOAD)
    # manager.get_current_plex_provider_playlists()
