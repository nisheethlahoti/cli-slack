import sys
import time
from slackclient import SlackClient

slack_client = SlackClient(sys.argv[1])

class PostLocation:
    def __init__(self, data, kind):
        self.id = data['id']
        self.name = data['name']
        self.kind = kind

    def message(self, msg):
        slack_client.api_call("chat.postMessage", channel=self.id, as_user=True, text=msg)
        idle_loop()

    def write_message(self):
        self.message("".join(sys.stdin.readlines())[:-1])

    def upload(self, fname):
        with open(fname) as msgfile:
            slack_client.api_call("files.upload", channels=self.id, file=msgfile)
        idle_loop()


ignore_types = {'hello', 'user_typing', 'desktop_notification', 'update_thread_state',
                'im_marked', 'mpim_marked', 'group_marked', 'channel_marked'}
def receive():
    for messages in iter(slack_client.rtm_read, []):
        for json in messages:
            if json['type'] == 'message' and 'user' in json:
                uname = users[json['user']].name
                if uname != slack_client.server.username:
                    if json['channel'] in locations:
                        uname += " in " + locations[json['channel']].name
                    print( (uname + ':\n' + json['text']).replace('\n', '\n| ') + '\n')
            elif json['type'] not in ignore_types:
                print(json)
                print()


def idle_loop():
    print("[Idling about]")
    while True:
        try:
            receive()
            time.sleep(1)
        except Exception:
            print("Disconnected")
            if not slack_client.rtm_connect():
                break
            print("Reconnected")


def populate(kind, getter, invalidator):
    globals()[kind] = {}
    for data in slack_client.api_call(kind + ".list")[getter]:
        if not data[invalidator]:
            loc = PostLocation(data, kind)
            globals()[kind][loc.id] = loc
            globals()[loc.name.replace('-','_')] = loc
    locations.update(globals()[kind])


locations = {}
populate('users', 'members', 'deleted')
populate('groups', 'groups', 'is_archived')
populate('channels', 'channels', 'is_archived')
slack_client.rtm_connect()
idle_loop()
