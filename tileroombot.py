from python_twitch_irc import TwitchIrc
import requests
import configparser
import datetime
import schedule
from datetime import timedelta

config = configparser.ConfigParser()
config.read('config.ini')

whitelist = []


channels = [
    '#the_synack',
    '#alttprandomizer',
    '#alttprandomizer2',
    '#alttprandomizer3',
    '#alttprandomizer4',
    '#alttprandomizer5',
    '#alttprandomizer6',
]

# initialize the dictionaries used to keep game start
# this is all in memory, so if the bot crashes ¯\_(ツ)_/¯
gtbk_game_status = {}
gtbk_game_guesses = {}

for channel in channels:
    #game's default state is finished
    gtbk_game_status[channel] = {'finished'}
    #no guesses
    gtbk_game_guesses[channel] = {}


# initialize
class TileRoomBot(TwitchIrc):
    def on_connect(self):
        for channel in channels:
            print('Joining channel ' + channel)
            self.join(channel)
        print('Finished joining channels.')

    # Override from base class
    def on_message(self, timestamp, tags, channel, user, message):

        #run any pending scheduled jobs (currently just the whitelist)
        schedule.run_pending()

        if message.startswith('!'):
            if user.lower() in whitelist or tags['mod'] == '1' or channel.lower() == ('#' + user.lower()):
                cmd = message.split()
                if cmd[0] == '!start':
                    if gtbk_game_status[channel] == 'started':
                        self.message(channel,'Game already started!  Use !forcestop to force the previous game to end if this is in error.')
                    else:
                        gtbk_game_guesses[channel].clear()
                        self.message(channel,'Get your GTBK guesses in!  The first viewer who guesses closest to the actual key location gets praise by this bot and potentially the commentators!  Only your last guess counts.')
                        gtbk_game_status[channel] = "started"
                elif cmd[0] == '!stop':
                    if gtbk_game_status[channel] != 'started':
                        self.message(channel,'Game already stopped or finished!')
                    else:
                        if len(gtbk_game_guesses[channel]) == 0:
                            self.message(channel,'No guesses were entered prior to !stop being issued.  Finishing the GTBK game.')
                            gtbk_game_status[channel] = "finished"
                        else:
                            self.message(channel,'Guesses have now closed.  Good luck!')
                            gtbk_game_status[channel] = "stopped"
                elif cmd[0] == '!forcestop':
                    self.message(channel,'Setting GTBK game to finished.')
                    gtbk_game_status[channel] = "finished"
                elif cmd[0] == '!bigkey' or cmd[0] == '!key':
                    winner = findwinner(cmd[1],channel)
                    if winner:
                        self.message(channel,winner[0] + ' was the winner of the Ganon\'s Tower Big Key guessing game. ' + winner[0] + ' guessed ' + str(winner[1]) + ' and the big key was ' + cmd[1] + '. Congratulations!')
                        gtbk_game_status[channel] = "finished"
                    else:
                        self.message(channel,'There was an issue while finding the winner.  Please make sure you entered a postiive number.')
                elif cmd[0] == '!gtbkstatus':
                    print(gtbk_game_status[channel])
                elif cmd[0] == '!gtbkguesses':
                    print(gtbk_game_guesses[channel])
                elif cmd[0] == '!gtbkwhitelist':
                    print(whitelist)
                elif cmd[0] == '!gtbktags':
                    print(tags)
                # elif cmd[0] == '!gtbkpopulate':
                #     recordguess(channel, 'testuser1', '8')
                #     recordguess(channel, 'testuser2', '18')
                #     recordguess(channel, 'testuser3', '12')
                #     recordguess(channel, 'testuser4', '1')
                #     recordguess(channel, 'testuser5', '-1')
                #     recordguess(channel, 'testuser6', '2000')
                #     recordguess(channel, 'testuser7', '23')
                #     print(gtbk_game_guesses[channel])
                # elif cmd[0] == '!addguess':
                #     recordguess(channel, cmd[1], cmd[2])
        else:
            recordguess(channel, user, message)

def recordguess(channel, user, message):
    if gtbk_game_status[channel] == 'started' and message.isdigit():
        gtbk_game_guesses[channel].pop(user, None)
        # in case the user tries to send something strange
        try:
            gtbk_game_guesses[channel][user] = int(message)
            print('recording guess on channel ' + channel + ' by ' + user + ' as ' + message)
        except ValueError:
            pass

def findwinner(keyloc, channel):
    if keyloc.isdigit():
        target = int(keyloc)
        #this was shamelessly stolen from stack exchange becuase I'm bad at things
        key, value = min(gtbk_game_guesses[channel].items(), key=lambda kv : abs(kv[1] - target))
        return [key, value]
    else:
        return False
def get_sg_schedule_today(slug):
    now = datetime.datetime.now()
    sched_from = now - timedelta(hours=6)
    sched_to = now + timedelta(hours=6)
    url=config['DEFAULT']['SPEEDGAMING_API_PATH'] + '/schedule?event=' + slug + '&from=' + sched_from.isoformat() + '&to=' + sched_to.isoformat()
    sched_resp = requests.get(url)
    return(sched_resp.json())

def get_whitelist_users(slug):
    schedule = get_sg_schedule_today(slug)
    list = []
    for e in schedule:
        if e['event']['slug'] == slug:
            if any(channel.get('slug', None) in ['alttpr','alttpr2','alttpr3','alttpr4','alttpr5','alttpr6'] for channel in e['channels']):
                list.extend(get_approved_crew(e['broadcasters']))
                list.extend(get_approved_crew(e['commentators']))
                list.extend(get_approved_crew(e['trackers']))

    return(list)

def get_approved_crew(d):
    approved_crew = []
    for crew in d:
        if crew['approved'] == True:
            if crew['publicStream'] == "" or crew['publicStream'] == None:
                approved_crew.append(crew['displayName'].lower())
            else:
                approved_crew.append(crew['publicStream'].lower())
    return(approved_crew)

def update_whitelist():
    global whitelist
    whitelist = get_whitelist_users('alttpr')
    print('ran whitelist update')

update_whitelist()
schedule.every(20).minutes.do(update_whitelist)

client = TileRoomBot('TileRoomBot', config['DEFAULT']['TWITCH_OAUTH_TOKEN']).start()
client.handle_forever()
