import logging
from gmusicapi import Mobileclient
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
import argparse
try:
    register_namespace = ET.register_namespace
except AttributeError:
    def register_namespace(prefix, uri):
        ET._namespace_map[uri] = prefix

DEFAULT_PLAYLIST_NAME = "Imported XSPF"
XSPF_NAMESPACE_URL = "http://xspf.org/ns/0/"

def setup_parser():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--username', '-u', dest='username', help='Your Google Music username', required=True)
    parser.add_argument('--password', '-p', dest='password',
                        help='Your Google Music password (create an application specific password if you use two-factor '
                             'authentication)', required=True)
    parser.add_argument('--xspf-playlist', '-x', dest='xspf_file', help='The filename of the XSPF playlist', required=True)
    parser.add_argument('--playlist', dest='playlist_name', default=DEFAULT_PLAYLIST_NAME,
                        help='The playlist to add the songs to, will be created if it does not exist')
    return parser

def find_playlist_id(playlist_name):
    playlist_id = None

    playlists = api.get_all_playlists()
    for playlist in playlists:
        if playlist["name"] == playlist_name:
            playlist_id = playlist["id"]
            logging.debug("Found existing playlist, will use that")

            break

    if playlist_id is None:
        playlist_id = api.create_playlist(playlist_name)
        logging.info("Created new playlist for import")

    return playlist_id

def get_playlist_song_ids(playlist_id):
    song_ids = None

    playlists = api.get_all_user_playlist_contents()

    for playlist in playlists:
        if playlist["id"] == playlist_id:
            song_ids = []
            for track in playlist['tracks']:
                song_ids.append(track['trackId'])

    if song_ids is None:
        raise 'Playlist ' + playlist_id + ' not found'

    return song_ids

def add_song_to_playlist(result):
    """
    Add a song from the search results to the playlist. If the playlist already contains the song it will not be added
    again
    :param result:
    """

    result_track = result["track"]
    result_score = result["score"]
    result_string = result_track["artist"] + " - " + result_track["title"] + " with score " + (
        "%.2f" % result_score)
    logging.info(result_string)
    song_id = result_track["nid"]
    if song_id not in playlist_song_ids:
        api.add_songs_to_playlist(playlist_id, song_id)
        playlist_song_ids.append(song_id)
        logging.debug("Successfully added song")
        stats['songs_added'] += 1
    else:
        logging.debug("Playlist already contains song, skipping")
        stats['songs_skipped'] += 1

parser = setup_parser()
args = parser.parse_args()

api = Mobileclient(debug_logging=False)
api.login(args.username, args.password)

playlist_id = find_playlist_id(args.playlist_name)
playlist_song_ids = get_playlist_song_ids(playlist_id)

stats = {
    'songs_added': 0,
    'songs_skipped': 0,
    'songs_not_found': 0,
}

xml = ET.parse(args.xspf_file)
root = xml.getroot()

for track in xml.iter():

    # TODO: Figure out how to properly iterate over the <track> instead of filtering all tags
    if track.tag != "{" + XSPF_NAMESPACE_URL + "}track":
        continue

    creator = track.find("{" + XSPF_NAMESPACE_URL + "}creator")
    title = track.find("{" + XSPF_NAMESPACE_URL + "}title")
    query = creator.text + " - " + title.text

    logging.info("Looking for " + query)

    results = api.search_all_access(query)
    if len(results["song_hits"]) > 0:

        # The results are sorted by score descending so just pick the first one
        result = results["song_hits"][0]

        add_song_to_playlist(result)

    else:
        logging.warn("No matches for " + query)
        stats['songs_not_found'] += 1

print stats
