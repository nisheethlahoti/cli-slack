#!/usr/bin/python3 -i

import requests
import sys
import time
from slackclient import SlackClient
from threading import Thread

slack = SlackClient(sys.argv[1])
locations = {}
files = []
ignore_types = {
    'hello', 'user_typing', 'desktop_notification', 'update_thread_state', 'im_marked',
    'mpim_marked', 'group_marked', 'channel_marked', 'pref_change', 'file_created'
}


class PostLocation:
    def __init__(self, data, kind):
        self.data = data
        self.id = data['id']
        self.name = data['name']
        self.kind = kind

    def message(self, msg):
        slack.api_call("chat.postMessage", channel=self.id, as_user=True, text=msg)

    def write_message(self):
        self.message("".join(sys.stdin.readlines())[:-1])

    def upload(self, fname):
        with open(fname) as msgfile:
            slack.api_call("files.upload", channels=self.id, file=msgfile)


def receive():
    global users
    while True:
        time.sleep(1)
        for messages in iter(slack.rtm_read, []):
            for json in messages:
                if json['type'] == 'message' and 'user' in json:
                    uname = users[json['user']].name
                    if uname != slack.server.username:
                        if json['channel'] in locations:
                            uname += " in " + locations[json['channel']].name
                        print('\n' + (uname + ':\n' + json['text']).replace('\n', '\n| '))
                elif json['type'] == 'file_shared' and 'file_id' in json:
                    lfile = slack.api_call('files.info', file=json['file_id'])['file']
                    print(f"\nFile #{len(files)} uploaded: {lfile['name']}\
                           \n  Size: {lfile['size']}\n  User: {lfile['user']}")
                    files.append(lfile)
                elif json['type'] not in ignore_types:
                    print(f'\nUnknown notification: {json}')


def download(fnum, name=''):
    url = files[fnum]['url_private_download']
    with requests.get(url, headers={'Authorization': 'Bearer ' + slack.token}) as fle:
        with open(name or files[fnum]['name'], 'wb') as outf:
            outf.write(fle.content)


def connect():
    print('Establishing real-time messaging connection...')
    slack.rtm_connect(auto_reconnect=True)
    Thread(target=receive, daemon=True).start()


def populate(kind, getter, invalidator):
    globals()[kind] = {}
    for data in slack.api_call(kind + ".list")[getter]:
        if not data[invalidator]:
            loc = PostLocation(data, kind)
            globals()[kind][loc.id] = loc
            globals()[loc.name.replace('-', '_')] = loc
    locations.update(globals()[kind])
    print(f'Identified {kind} {", ".join(x.name for x in globals()[kind].values())}')


populate('users', 'members', 'deleted')
populate('groups', 'groups', 'is_archived')
populate('channels', 'channels', 'is_archived')
connect()
