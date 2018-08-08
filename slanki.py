import json
import requests
import os
import pprint
import random
import shutil
import sys
import tempfile
import urllib.request

import genanki
from dotenv import load_dotenv
load_dotenv()

SLACK_API_TOKEN = os.getenv('SLACK_API_TOKEN')
USERS_LIMIT = int(os.getenv('USERS_LIMIT'))
OUTPUT_FILE = os.getenv('OUTPUT_FILE')
DECK_ID = int(os.getenv('DECK_ID'))
MODEL_ID = int(os.getenv('MODEL_ID'))

def fetch_slack_users(token):
    resp = requests.get(
        'https://slack.com/api/users.list',
        params={
            'token': token,
            'limit': 1000,
        })
    if resp.status_code != 200:
        print("Got status code %s from Slack users.list API", resp.status_code)
        sys.exit(1)
    j = resp.json()
    # we don't want to learn slackbot's name
    ignore_users = set(['slackbot'])
    j['members'] = [m for m in j['members'] if m['name'] not in ignore_users][:USERS_LIMIT]
    return j['members']

def best_image_field(profile):
    # some slack user profiles have a 'image_original' field, some
    # don't.  grab the image_N field with the highest N.
    if 'image_original' in profile:
        return 'image_original'
    image_fields = [f for f in profile if f.startswith('image_')]
    return max(image_fields, key=lambda f: int(f.split('_')[1]))

def generate_anki_deck(output_file, users):
    deck = genanki.Deck(DECK_ID, 'Zapier Team Names')
    model = genanki.Model(
        MODEL_ID,
        'Name model',
        fields=[
            {'name': 'photo_tags'},
            {'name': 'name'},
        ],
        templates=[
            {
                'name': 'card 1',
                'qfmt': '{{photo_tags}}',
                'afmt': '{{name}}',
            }
        ])

    old_working_dir = os.getcwd()
    temp_dir = tempfile.mkdtemp(prefix='slanki')
    os.chdir(temp_dir)
    image_file_names = []

    for i, user in enumerate(users):
        print("User %s [%d/%d]" % (user['profile']['real_name'], i, len(users)))
        image_url = user['profile'][best_image_field(user['profile'])]
        image_file_name = image_url.split('/')[-1]
        urllib.request.urlretrieve(image_url, image_file_name)
        image_file_names.append(image_file_name)

        note = genanki.Note(
            model=model,
            fields=['<img src="%s">' % image_file_name, user['profile']['real_name']]
        )
        deck.add_note(note)

    package = genanki.Package(deck, media_files=image_file_names)
    package.write_to_file(os.path.join(old_working_dir, output_file))

    shutil.rmtree(temp_dir)

if __name__ == '__main__':
    slack_users_json = fetch_slack_users(SLACK_API_TOKEN)
    generate_anki_deck(OUTPUT_FILE, slack_users_json)
    print("Created %s" % OUTPUT_FILE)
