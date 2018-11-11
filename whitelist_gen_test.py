import requests
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

def get_sg_schedule_today(slug):
    sched_resp = requests.get(
        url=config['DEFAULT']['SPEEDGAMING_API_PATH'] + '/schedule?event=' + slug,
    )
    return(sched_resp.json())

def get_whitelist_users(slug):
    schedule = get_sg_schedule_today(slug)
    whitelist = []
    for e in schedule:
        if e['event']['slug'] == slug:
            if any(channel.get('slug', None) in ['alttpr','alttpr2','alttpr3','alttpr4','alttpr5','alttpr6'] for channel in e['channels']):
                print('found match ' + str(e['match1']['id']))
                whitelist.extend(get_approved_crew(e['broadcasters']))
                whitelist.extend(get_approved_crew(e['commentators']))
                whitelist.extend(get_approved_crew(e['trackers']))

    return(whitelist)

def get_approved_crew(d):
    approved_crew = []
    for crew in d:
        if crew['approved'] == True:
            if crew['publicStream'] == "" or crew['publicStream'] == None:
                approved_crew.append(crew['displayName'].lower())
            else:
                approved_crew.append(crew['publicStream'].lower())
    return(approved_crew)

print(get_whitelist_users('alttpr'))
