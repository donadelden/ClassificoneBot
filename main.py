#!/usr/bin/env python

import logging
import json

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re
import pygsheets
import pandas as pd

DEBUG = False

# Authenticate with Spotify and Telegram
with open(".credentials", "r") as f:
    credentials = json.load(f)
    ALLOWED_CHAT_IDS = credentials["chat_id"].strip().split(",")
    CLASSIFICONE_URL = credentials["google_sheet_url"]
    PLAYLIST_URI = credentials["playlist_uri"]

# Spotify authentication
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=credentials["sp_id"],
                                            client_secret=credentials["sp_secret"],
                                            redirect_uri="https://localhost:1234/",
                                            scope="user-library-read playlist-modify-public"))
# telegram authentication
tg_app = Application.builder().token(credentials["tg_token"]).build()

# Authenticate with Google Sheets
gc = pygsheets.authorize(service_file='.google-creds.json')


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("log/main.log", mode="a"),
        logging.StreamHandler()
    ]
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

async def parse_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parse the message and extract the Spotify URI. 
    Then, add the best track to the playlist and the album to the Google"""

    chat_id = update.message.chat_id    
    #await update.message.reply_text(f"[!] chat_id: {chat_id}")
    if str(chat_id) in ALLOWED_CHAT_IDS:
        message_text = update.message.text
        if "open.spotify.com" in message_text:
            url_pattern = re.compile(r"https?://open\.spotify\.com/[^\s]+")
            match = url_pattern.search(message_text)
            clean_message = re.sub(url_pattern, "", message_text)

            if match:
                spotify_url = match.group(0)
                id = spotify_url.split("/")[-1].split("?")[0]
                type = spotify_url.split("/")[-2]
                uri = f"spotify:{type}:{id}"

                msg = ""

                if not add_best_song_to_playlist(uri):
                    #await update.message.reply_text("[!] Best track already in playlist.")
                    msg += "[!] Best track already in playlist.\n"
                
                if not add_to_google_sheet_by_uri(uri, comment=clean_message.strip()):
                    #await update.message.reply_text("[!] Album already in Google Sheet or not released in this year.")  
                    msg += "[!] Album already in Google Sheet or not released in this year.\n"
                
                if msg:
                    await update.message.reply_text(msg.strip())
                else:
                    await update.message.reply_text(f"Added to the playlist and in the list! :)")
            else:
                pass #await update.message.reply_text("No Spotify URL found (second check).")
        else:
            pass #await update.message.reply_text("No Spotify URL found.")
    else:
        logger.warning(f"[x] Unauthorized chat_id: {chat_id}.")
        await update.message.reply_text(f"[x] Unauthorized chat_id: {chat_id}.")


def main() -> None:
    """Start the bot."""

    # on non command i.e message
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, parse_message))

    # Run the bot until the user presses Ctrl-C
    tg_app.run_polling(allowed_updates=Update.ALL_TYPES)


def get_album_tracks_by_popularity(album_uri: str) -> list:
        """Get the tracks of an album sorted by popularity."""

        results = sp.album_tracks(album_uri)
        tracks = results["items"]

        track_popularity = []

        for track in tracks:
            track_uri = track["uri"]
            track_info = sp.track(track_uri)
            track_popularity.append((track["name"], track_info["popularity"], track_uri))

        track_popularity.sort(key=lambda x: x[1], reverse=True)
        return track_popularity


def get_album_info(album_uri: str) -> list: 
    """Get the artist, title, type and year of an album."""

    album = sp.album(album_uri)
    return {"artist": album["artists"][0]["name"], 
            "title": album["name"],
            "type": album["album_type"],
            "year": album["release_date"].split("-")[0]}


def add_best_song_to_playlist(album_uri: str, allow_duplicates: bool = False) -> bool:
    """Add the best song of an album to the playlist.
    If allow_duplicates is True, the song will be added even if it is already in the playlist."""

    # get best song from album
    popular_tracks = get_album_tracks_by_popularity(album_uri)
    selected_track = popular_tracks[0]

    # Check if the track is already in the playlist
    playlist_tracks = sp.playlist_tracks(PLAYLIST_URI)
    track_uris = [item["track"]["uri"] for item in playlist_tracks["items"]]

    if allow_duplicates or selected_track[2] not in track_uris:
        sp.playlist_add_items(PLAYLIST_URI, [popular_tracks[0][2]])
        return True
    else:
        logger.info(f"[!] Track {selected_track[0]} is already in the playlist.")
        return False



def add_to_google_sheet_by_uri(album_uri: str, comment: str = "") -> None:
    """Update the Google Sheet with the new entry."""
    
    album_info = get_album_info(album_uri) # TODO: need to extract also the other stuffs
    return add_to_google_sheet_by_info(album_info["artist"], album_info["title"], support=album_info["type"], comment=comment, year=album_info["year"])


def add_to_google_sheet_by_info(artist: str, title: str, cat: str = "", support: str = "", genre: str = "", comment: str = "", year: str = str(pd.Timestamp.now().year)) -> None:
    """Update the Google Sheet with the new entry."""

    if DEBUG: 
        year = "test"
    elif year != "2025":
        return False

    sh = gc.open_by_url(CLASSIFICONE_URL)
    # Select the sheet named "2025"
    wks = sh.worksheet_by_title(year) # TODO: check that year is correct for the disk in question before entering in this function

    # Read all data from the worksheet into a pandas dataframe
    df_existing = wks.get_as_df()

    # Pretty print the dataframe
    if DEBUG: print(df_existing.head())

    # Add a new row to the existing dataframe
    new_row = {'Artista': artist, 'Titolo': title, 'CAT': cat, 'Supporto': support, "Genere": genre, "Commento": comment}

    if not df_existing[(df_existing['Artista'] == artist) & (df_existing['Titolo'] == title)].empty:
        logger.info(f"[!] Album '{title}' by '{artist}' is already in the Google Sheet.")
        return False

    df_existing.loc[len(df_existing)] = new_row

    #update the first sheet with df, starting at cell B2. 
    wks.set_dataframe(df_existing,(1,1))

    return True


if __name__ == "__main__":

    main()


    # Example usage
    # album_uri = "spotify:album:5r2lUKLgKTNqbsloCwB9X5"

    # print(get_album_info(album_uri))

    # popular_tracks = get_album_tracks_by_popularity(album_uri)
    # for track in popular_tracks:
    #     print(f"{track[0]}: {track[1]}")
