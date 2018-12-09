# TileRoomBot

Requires Python 3 (tested with 3.6, python_twitch_irc library doesn't work with 3.7)

modify tileroombot.py to point to the channels you want to use

copy config.ini.example to cfg/config.ini and put your oauth token that'll be used to connect to Twitch IRC

you can get an oauth token at https://twitchapps.com/tmi/

run "pip3 install -t requirements.txt" to install the required library(s)

you can also just pull the docker container "tcprescott/tileroombot:latest" and use docker-compose to bring up the container

Have fun!

## To do

Clean code up so it actually meets pep8 coding style

## Maybe to do

Leaderboards (if this happens, I want to be more than person x guessed most times correctly)
