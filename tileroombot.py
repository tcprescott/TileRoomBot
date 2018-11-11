from python_twitch_irc import TwitchIrc
import configparser
import time

config = configparser.ConfigParser()
config.read('config.ini')

#a temporary whitelist of users, this is temporary until I implement checking of SG schedule
#!gtbkwhitelist can be used by an authorized user to update the list without restarting


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
        #check if its a command, and it is an channel moderator or owner
        # if message.startswith('!') and (tags['mod'] == '1' or channel == ('#' + user) or user.lower() in (for name.lower() in whitelist):
        if message.startswith('!'):
            whitelist = config['DEFAULT']['WHITELIST'].split(',')
            if user.lower() in (name.lower() for name in whitelist) or tags['mod'] == '1' or channel.lower() == ('#' + user.lower()):
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
                elif cmd[0] == '!bigkey':
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
                    config.read('config.ini')
                    whitelist = config['DEFAULT']['WHITELIST'].split(',')
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
        gtbk_game_guesses[channel][user] = int(message)
        print('recording guess by ' + user + ' as ' + message)

def findwinner(keyloc, channel):
    if keyloc.isdigit():
        target = int(keyloc)
        #this was shamelessly stolen from stack exchange becuase I'm bad at things
        key, value = min(gtbk_game_guesses[channel].items(), key=lambda kv : abs(kv[1] - target))
        return [key, value]
    else:
        return False

client = TileRoomBot('TileRoomBot', config['DEFAULT']['TWITCH_OAUTH_TOKEN']).start()
client.handle_forever()
