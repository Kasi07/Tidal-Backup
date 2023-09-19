#!/usr/bin/env python3

import argparse
from configparser import ConfigParser
import json
import sys
from pathlib import Path
import requests

import tidalapi


def backup(session, filename, backup_dir = Path().cwd() / 'backup'):
    # Create backup directory if it doesn't exist
    backup_dir.mkdir(parents=True, exist_ok=True)
    tidal_favorites = dict(albums=[], artists=[], tracks=[], playlists=[])
    artists = session.user.favorites.artists()
    for e in artists:
        tidal_favorites['artists'].append(dict(name=e.name, id=e.id))

    tracks = session.user.favorites.tracks()
    for e in tracks:
        tidal_favorites['tracks'].append(dict(name=e.name, id=e.id))

    albums = session.user.favorites.albums()
    for e in albums:
        tidal_favorites['albums'].append(dict(name=e.name, id=e.id))

    playlists = session.user.favorites.playlists()
    for e in playlists:
        playlist_data = dict()
        playlist_data['name'] = e.name
        playlist_data['id'] = e.id
        playlist_data['owned'] = e.creator.name == "me"
        playlist_data['public'] = True if e.public else False
        if playlist_data['owned']:
            playlist_data['description'] = e.description
            if e.picture:
                url = e.image(dimensions=1080)
                r = requests.get(url)
                if r.status_code == 200:
                    with open(backup_dir / f'{e.id}.jpg', 'wb') as f:
                        f.write(r.content)
            if e.square_picture:
                url = e.wide_image()
                r = requests.get(url)
                if r.status_code == 200:
                    with open(backup_dir / f'{e.id}_wide.jpg', 'wb') as f:
                        f.write(r.content)
            if e.num_tracks + e.num_videos > 0:
                playlist_data['items'] = []
                for i in range(0, e.num_tracks + e.num_videos, 100):
                    playlist_data['items'] += [dict(name=item.name, id=item.id) for item in e.items(offset = i+1 if i else 0)]
                        
        tidal_favorites['playlists'].append(playlist_data)

    with open(backup_dir / filename, 'w') as outfile:
        json.dump(tidal_favorites, outfile, indent=4)
    print(tidal_favorites)


def restore(session, filename):
    with open(filename) as json_file:
        tidal_favorites = json.load(json_file)
        for a in tidal_favorites['artists']:
            try:
                session.user.favorites.add_artist(a['id'])
                print(f'Artist {a["name"]} added as favorite')
            except:
                pass
        for a in tidal_favorites['tracks']:
            try:
                session.user.favorites.add_track(a['id'])
                print(f'Track {a["name"]} added as favorite')
            except:
                pass
        for a in tidal_favorites['albums']:
            try:
                session.user.favorites.add_album(a['id'])
                print(f'Album {a["name"]} added as favorite')
            except:
                pass
        #for a in tidal_favorites['playlists']:
        #     session.user.favorites.add_playlist(a['id'])


def parse_args(args):
    """
    Parse command line parameters

    :param args: command line parameters as list of strings
    :return: command line parameters as :obj:`argparse.Namespace`
    """
    parser = argparse.ArgumentParser(description="Backup/Restore Tidal tracks/albums/artist favorites")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--backup', '-b', action='store_true', help='Backup favorites')
    group.add_argument('--restore', '-c', action='store_true', help='Restore favorites')

    parser.add_argument('--ini', '-i', dest='ini')
    parser.add_argument('--filename', '-o', dest='filename', default=None)

    return parser.parse_args(args)


def main(args):
    args_parsed = parse_args(args)

    session = tidalapi.Session()

    if args_parsed.ini is not None:
        config = ConfigParser()
        config.read([args_parsed.ini])
        try:
            session.load_oauth_session(
                config['session']['token_type'],
                config['session']['access_token'],
                config['session'].get('refresh_token', None),
                config['session'].get('expiry_time', None)
            )
        except KeyError:
            print('supplied configuration to restore session is incomplete')
        else:
            if not session.check_login():
                print('loaded session appears to be not authenticated')

    if not session.check_login():
        print('authenticating new session')
        session.login_oauth_simple()

        print('To load the session next time you run this program, '
              'supply the following information via an INI file:')
        print()
        print(f'[session]')
        print(f'token_type = {session.token_type}')
        print(f'access_token = {session.access_token}')
        print(f'refresh_token = {session.refresh_token}')
        print(f'expiry_time = {session.expiry_time}')
        print()


    if args_parsed.backup:
        backup(session, args_parsed.filename or 'tidal_favorites.json')
    if args_parsed.restore:
        restore(session, args_parsed.filename or 'tidal_favorites.json')


if __name__ == '__main__':
    main(sys.argv[1:])
