import sys
import time
from slackclient import SlackClient

slack_client = SlackClient(sys.argv[1])

class User:
    def __init__(self, data):
        self.id = data['id']
        self.name = data['name']

    def message(self):
        slack_client.api_call("chat.postMessage", channel=self.id, as_user=True,
                              text="".join(sys.stdin.readlines())[:-1])
        idle_loop()

    def upload(self, fname):
        with open(fname) as msgfile:
            slack_client.api_call("files.upload", channels=self.id, file=msgfile)
        idle_loop()


ignore_types = {'hello', 'user_typing', 'desktop_notification', 'im_marked', 'update_thread_state'}
def receive():
    for messages in iter(slack_client.rtm_read, []):
        for json in messages:
            if json['type'] == 'message' and 'user' in json:
                uname = users[json['user']].name
                if uname != slack_client.server.username:
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


users = {}
for user_data in slack_client.api_call("users.list")['members']:
    if not user_data['deleted']:
        user = User(user_data)
        users[user.id] = user
        globals()[user.name] = user

slack_client.rtm_connect()
idle_loop()
