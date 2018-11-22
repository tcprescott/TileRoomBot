FROM python:3.6-alpine

WORKDIR /usr/src/app
COPY requirements.txt ./

ENV TZ=America/New_York

RUN mkdir cfg
RUN mkdir logs
RUN mkdir data
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "./tileroombot.py" ]
