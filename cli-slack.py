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
    def __init__(self, data):
        self.data = data
        self.id = data['id']
        self.name = data['name']

    def message(self, msg):
        slack.api_call("chat.postMessage", channel=self.id, as_user=True, text=msg)

    def write_message(self):
        self.message("".join(sys.stdin.readlines())[:-1])

    def upload(self, fname):
        with open(fname) as msgfile:
            slack.api_call("files.upload", channels=self.id, file=msgfile)

    def __repr__(self):
        return f'{self.__class__.__name__}(id={self.id}, name={self.name})'


def receive():
    while True:
        time.sleep(1)
        for messages in iter(slack.rtm_read, []):
            for json in messages:
                if json['type'] == 'message' and 'user' in json and json['user'] != uid:
                    uname = users[json['user']].name
                    if json['channel'] in locations:
                        uname += " in " + locations[json['channel']].name
                    print('\n' + (uname + ':\n' + json['text']).replace('\n', '\n| '))
                elif json['type'] == 'file_shared' and 'file_id' in json:
                    lfile = slack.api_call('files.info', file=json['file_id'])['file']
                    print(f"\nFile #{len(files)} uploaded: {lfile['name']}\
                           \n  Size: {lfile['size']}\n  User: {users[lfile['user']].name}")
                    files.append(lfile)
                elif json['type'] not in ignore_types and json.get('user') != uid:
                    print(f'\nUnknown notification: {json}')


def download(fnum, name=''):
    url = files[fnum]['url_private_download']
    with requests.get(url, headers={'Authorization': 'Bearer ' + slack.token}) as fle:
        with open(name or files[fnum]['name'], 'wb') as outf:
            outf.write(fle.content)


def populate(api, getter, skip, first_name, second_name='', splitter=lambda _: True):
    elems = {x['id']: PostLocation(x) for x in slack.api_call(api)[getter] if not x[skip]}
    first = {k: v for k, v in elems.items() if splitter(v)}
    second = {k: v for k, v in elems.items() if k not in first}
    globals().update({x.name.replace('-', '_'): x for x in elems.values()})
    locations.update(elems)
    for vals, name in (first, first_name), (second, second_name):
        if vals:
            print(f'Identified {name} {", ".join(x.name for x in vals.values())}')
    return first, second


def mpdm(*args):
    groups = [x for x in mpdms.values() if set(x.data['members']) == {y.id for y in args} | {uid}]
    assert len(groups) == 1, f'No unique group with these users {[x.name for x in groups]}'
    return groups[0]


try:
    users, _ = populate('users.list', 'members', 'deleted', 'users')
    public_channels, _ = populate('channels.list', 'channels', 'is_archived', 'public channels')
    private_channels, mpdms = populate('groups.list', 'groups', 'is_archived', 'private channels',
                                       'mpdms', lambda x: x.name[:5] != 'mpdm-')
    print('Establishing real-time messaging connection...')
    slack.rtm_connect(auto_reconnect=True)
except requests.exceptions.ConnectionError:
    print('Unable to connect')
    sys.exit(1)

Thread(target=receive, daemon=True).start()
uid = slack.server.login_data['self']['id']
