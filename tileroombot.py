from python_twitch_irc import TwitchIrc
import requests
import configparser
import datetime
import time
import schedule
import math
from datetime import timedelta
import logging
import logging.handlers as handlers
import sqlite3

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('tileroombot')
logger.setLevel(logging.DEBUG)
logHandler = handlers.TimedRotatingFileHandler('logs/tileroombot.log', when='D', interval=1, backupCount=7)
logHandler.setLevel(logging.DEBUG)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

#open up our database connection

def main():
    global config
    config = configparser.ConfigParser()
    config.read('cfg/config.ini')

    global channels
    channels = config['DEFAULT']['CHANNELS'].split(',')

    # initialize the dictionaries used to keep game start
    # this is all in memory, so if the bot crashes ¯\_(ツ)_/¯

    global gtbk_game_status
    global gtbk_game_guesses

    gtbk_game_status = {}
    gtbk_game_guesses = {}

    for channel in channels:
        #game's default state is finished
        gtbk_game_status[channel] = {'finished'}
        #no guesses
        gtbk_game_guesses[channel] = {}

    global dbconn
    dbconn = create_connection('data/tileroombot.db')
    init_database(dbconn)

    update_whitelist()
    schedule.every(20).minutes.do(update_whitelist)

    client = TileRoomBot('TileRoomBot', config['DEFAULT']['TWITCH_OAUTH_TOKEN']).start()
    client.handle_forever()


# initialize
class TileRoomBot(TwitchIrc):
    def on_connect(self):
        for channel in channels:
            logger.info('Joining channel ' + channel)
            self.join(channel)
        logger.info('Finished joining channels.')

    # Override from base class
    def on_message(self, timestamp, tags, channel, user, message):

        #run any pending scheduled jobs (currently just the whitelist)
        schedule.run_pending()

        if message.startswith('!'):
            cmd = message.split()
            if cmd[0] == '!start':
                if is_authorized(user,tags,channel):
                    if gtbk_game_status[channel] == 'started':
                        msg = 'Game already started!  Use !forcestop to force the previous game to end if this is in error.'
                        self.message(channel,msg)
                    else:
                        gtbk_game_guesses[channel].clear()
                        msg = 'Get your GTBK guesses in!  The first viewer who guesses closest to the actual key location gets a place on the leaderboard!  Points are scored based on the number of participants in the game.  Only your last guess counts.'
                        self.message(channel,msg)
                        gtbk_game_status[channel] = "started"
                        logger.info(user + ' started GTBK game on ' + channel)
            elif cmd[0] == '!stop':
                if is_authorized(user,tags,channel):
                    if gtbk_game_status[channel] != 'started':
                        msg = 'Game already stopped or finished!'
                        self.message(channel,msg)
                    else:
                        if len(gtbk_game_guesses[channel]) == 0:
                            msg = 'No guesses were entered prior to !stop being issued.  Finishing the GTBK game.'
                            self.message(channel,msg)
                            gtbk_game_status[channel] = "finished"
                            logger.info(user + ' finished GTBK game on ' + channel)
                            logger.info(gtbk_game_guesses[channel])
                        else:
                            msg = 'Guesses have now closed. {points} points will be awarded to the winner. Good luck!'.format(
                                points = calculate_score(gtbk_game_guesses[channel]),
                            )
                            self.message(channel,msg)
                            gtbk_game_status[channel] = "stopped"
                            logger.info(user + ' stopped GTBK game on ' + channel)
            elif cmd[0] == '!forcestop':
                if is_authorized(user,tags,channel):
                    msg = 'Setting GTBK game to finished.'
                    self.message(channel,msg)
                    gtbk_game_status[channel] = "finished"
                    logger.info(user + ' forced finish GTBK game on ' + channel)
                    logger.debug(gtbk_game_guesses[channel])
            elif cmd[0] == '!bigkey' or cmd[0] == '!key':
                if is_authorized(user,tags,channel):
                    winner = findwinner(cmd[1],channel)
                    if winner:
                        gtbk_game_status[channel] = "finished"
                        logger.info('GTBK winner found. ' + winner[0] + ' ' + str(winner[1]) + ' ' + cmd[1])
                        score = calculate_score(gtbk_game_guesses[channel])
                        logger.info('GTBK score calculated. ' + winner[0] + ' wins ' + str(score) + ' points')
                        logger.debug(gtbk_game_guesses[channel])
                        msg = '{winnername} was the winner of the Ganon\'s Tower Big Key guessing game. {winnername} guessed {winnerguess} and the big key was {keyloc} and has thus scored {points} point(s) on the ALTTPR GTBK leaderboard!'.format(
                            winnername = winner[0],
                            winnerguess = str(winner[1]),
                            keyloc = cmd[1],
                            points = score,
                        )
                        runners_up = get_exact_guesses(gtbk_game_guesses[channel],winner[0],int(cmd[1]))
                        print(runners_up)
                        if len(runners_up) > 0:
                            msg += '  The player(s) {runnerup} also guessed exactly correct and score 5 bonus points each.'.format(
                                runnerup = ', '.join(runners_up),
                            )
                        msg += '  Congratulations! (use !leaderboard to see current leaderboard)'
                        self.message(channel,msg)
                        logger.info('Logging results')
                        insert_score(winner[0],channel,score)
                        for runnerup in runners_up:
                            insert_score(runnerup,channel,5)
                        # msg = get_leaderboard_msg()
                        # self.message(channel,msg)
                    else:
                        msg = 'There was an issue while finding the winner.  Please make sure you entered a postiive number.'
                        self.message(channel,msg)
            elif cmd[0] == '!save':
                if is_authorized(user,tags,channel):
                    msg = 'The !save command is not required on ALTTPR channels.'
                    self.message(channel,msg)
            elif cmd[0] == '!whitelist':
                if is_mod(user,tags,channel):
                    try:
                        arg = cmd[1]
                    except IndexError:
                        arg = 'list'

                    if arg == 'add':
                        whitelist_add(cmd[2],user)
                    elif arg == 'del':
                        whitelist_del(cmd[2],user)
                    elif arg == 'update':
                        update_whitelist()
                    elif arg == 'list':
                        self.message(channel,'Here is a comma-separated list of currently whitelisted users for TileRoomBot: ' + ','.join(whitelist))
                    else:
                        self.message(channel,'Unknown whitelist command.')
            elif cmd[0] == '!populateguesses':
                if is_mod(user,tags,channel):
                    recordguess(channel, 'testuser1', '8')
                    recordguess(channel, 'testuser2', '18')
                    recordguess(channel, 'testuser3', '12')
                    recordguess(channel, 'testuser4', '1')
                    recordguess(channel, 'testuser5', '-1')
                    recordguess(channel, 'testuser6', '2000')
                    recordguess(channel, 'testuser7', '23')
                    recordguess(channel, 'testuser8', '10')
                    recordguess(channel, 'testuser9', '19')
                    recordguess(channel, 'testuser10', '15')
                    recordguess(channel, 'testuser11', '14')
                    recordguess(channel, 'testuser12', '2')
                    recordguess(channel, 'testuser13', '2000')
                    recordguess(channel, 'testuser14', '17')
                    recordguess(channel, 'spam1', '2')
                    recordguess(channel, 'spam2', '2')
                    recordguess(channel, 'spam3', '2')
                    recordguess(channel, 'spam4', '2')
                    recordguess(channel, 'spam5', '2')
                    recordguess(channel, 'spam6', '2')
                    recordguess(channel, 'spam7', '2')
                    recordguess(channel, 'spam8', '2')
                    recordguess(channel, 'spam9', '2')
                    recordguess(channel, 'spam10', '2')
                    recordguess(channel, 'spam11', '2')
                    logger.info(gtbk_game_guesses[channel])
            elif cmd[0] == '!addguess':
                if is_mod(user,tags,channel):
                    recordguess(channel, cmd[1], cmd[2])
            #our unprivledged commands
            elif cmd[0] == '!leaderboard':
                msg = get_leaderboard_msg()
                self.message(channel,msg)
            elif cmd[0] == '!score':
                try:
                    arg = cmd[1]
                except IndexError:
                    arg = user
                userscore = get_user_score(arg)
                if userscore:
                    msg = "Score for {user} is {points}".format(
                        user = arg,
                        points = userscore,
                    )
                else:
                    msg = "No score found for {user}".format(
                        user = arg,
                    )
                self.message(channel,msg)
            elif cmd[0] == '!tileroombot':
                msg = ("TileRoomBot, the official GTBK guessing game bot of the ALTTPR channels, written by Synack."
                    "Licensed under the Apache License, Version 2.0.")
                self.message(channel,msg)
            elif cmd[0] == '!gtbk':
                msg = "This bot records your guesses as to where the Ganon\'s Tower Big Key is located.  The first viewer who guesses closest to the actual key location gets a place on the leaderboard!  Points are scored based on the number of participants in the game."
                self.message(channel,msg)
        else:
            recordguess(channel, user, message)

def recordguess(channel, user, message):
    if gtbk_game_status[channel] == 'started' and message.isdigit():
        gtbk_game_guesses[channel].pop(user, None)
        # in case the user tries to send something strange
        try:
            gtbk_game_guesses[channel][user] = int(message)
            logger.info('recording guess on channel ' + channel + ' by ' + user + ' as ' + message)
        except ValueError:
            pass

def findwinner(keyloc, channel):
    if keyloc.isdigit():
        target = int(keyloc)
        key, value = min(gtbk_game_guesses[channel].items(), key=lambda kv : abs(kv[1] - target))
        return [key, value]
    else:
        return False
def get_sg_schedule_today(slug):
    now = datetime.datetime.now()
    sched_from = now - timedelta(hours=12)
    sched_to = now + timedelta(hours=6)

    if config.has_option('DEFAULT','SPEEDGAMING_API_PATH'):
        url=config['DEFAULT']['SPEEDGAMING_API_PATH'] + '/schedule'

        params = {
            'event': slug,
            'from': sched_from.isoformat(),
            'to': sched_to.isoformat()
        }
        sched_resp = requests.get(
            url=url,
            params=params
        )
        logger.info(sched_resp.url)
        return(sched_resp.json())
    else:
        return None

def get_whitelist_users(sluglist):
    whitelist = []
    for slug in sluglist:
        schedule = get_sg_schedule_today(slug)
        if schedule:
            for e in schedule:
                if any(channel.get('slug', None) in ['alttpr','alttpr2','alttpr3','alttpr4','alttpr5','alttpr6'] for channel in e['channels']):
                    whitelist.extend(get_approved_crew(e['broadcasters']))
                    whitelist.extend(get_approved_crew(e['commentators']))
                    whitelist.extend(get_approved_crew(e['trackers']))



    sql = ''' SELECT whitelisted_twitch_user FROM whitelist; '''
    cur = dbconn.cursor()
    cur.execute(sql)

    rows = cur.fetchall()
    for row in rows:
        whitelist.append(row[0])

    return(list(set(whitelist)))

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
    whitelist = get_whitelist_users(['alttpr','owg'])

    logger.info('ran whitelist update')
    logger.info('new whitelist is ' + ','.join(whitelist))

def init_database(conn):
    qry = open('dbscripts/create_inital.sql', 'r').read()
    conn.executescript(qry)
    dbconn.commit()

def create_connection(db_file):
    conn = sqlite3.connect(db_file)
    return conn

def calculate_score(guessdict):
    cnt = len(guessdict)
    if cnt <= 25:
        score = math.ceil((cnt - 1)/2) + 5
    else:
        score = math.ceil(17 + ((cnt-26) / 25) * 10)

    return score

def get_exact_guesses(guessdict,winner,loc):
    runners_up = []
    for user, guess in guessdict.items():
        if guess == loc and not user == winner:
            print(user)
            print(winner)
            runners_up.append(user)
    return runners_up


def insert_score(winner, channel, score):
    sql = ''' INSERT INTO scores(twitch_username,channel,ts,score) VALUES(?,?,?,?) '''
    score_record = [winner,channel,int(time.time()),score]
    dbconn.cursor().execute(sql, score_record)
    dbconn.commit()

def get_leaderboard_msg():
    sql = ''' SELECT twitch_username,SUM(score) as "points" FROM scores GROUP BY twitch_username ORDER BY points desc LIMIT 10; '''
    cur = dbconn.cursor()
    cur.execute(sql)

    rows = cur.fetchall()

    msg = 'Current GTBK game leaderboard for ALTTPR channels: '
    for row in rows:
        msg += '{name} has {points} point(s), '.format(
            name = row[0],
            points = str(row[1])
        )

    return msg

def get_user_score(user):
    sql = ''' SELECT SUM(score) as "points" FROM scores WHERE twitch_username = ?; '''
    cur = dbconn.cursor()
    cur.execute(sql,[user])

    return cur.fetchone()[0]

def is_authorized(user,tags,channel):
    if user.lower() in whitelist or tags['mod'] == '1' or channel.lower() == ('#' + user.lower()):
        return True
    else:
        return False

def is_mod(user,tags,channel):
    if tags['mod'] == '1' or channel.lower() == ('#' + user.lower()):
        return True
    else:
        return False

def whitelist_add(whitelisted_twitch_user,user):
    sql = ''' INSERT INTO whitelist(whitelisted_twitch_user, whitelisted_by) SELECT ?, ? WHERE NOT EXISTS(SELECT 1 FROM whitelist WHERE whitelisted_twitch_user=?);'''
    whitelist_record = [whitelisted_twitch_user,user,whitelisted_twitch_user]
    dbconn.cursor().execute(sql, whitelist_record)
    dbconn.commit()
    update_whitelist()

def whitelist_del(whitelisted_twitch_user,user):
    sql = ''' DELETE FROM whitelist WHERE whitelisted_twitch_user=?;'''
    whitelist_record = [whitelisted_twitch_user]
    dbconn.cursor().execute(sql, whitelist_record)
    dbconn.commit()
    update_whitelist()

main()
