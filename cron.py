import os
from datetime import datetime 
from dateutil import tz
from time import time, mktime
from model import session as modelsession
from model import User, Show, Service, Favorite, CachedService, CachedListing, CachedSearch
from app import get_listings
from twilio.rest import TwilioRestClient 

ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']
TWILIO_PHONE = os.environ['TWILIO_PHONE']

CLIENT = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN) 

NOW = datetime.utcnow()
CURRENT_TIMESTAMP = mktime(NOW.timetuple())

TWELVE_HOURS = 43200

def send_notification():
	users = modelsession.query(User).filter(User.phone == 7086926162, User.get_texts == True)

	for user in users:
		listings = get_listings(user.id)
		## want to return just results list not whole template
		if listings:
			for each in listings:
				for item in each:
					if item[1][0]['AiringType'] == 'New':
						# change unicode item['AiringTime'] to python datetime object
						air_time = datetime.strptime(item[1][0]['AiringTime'], '%Y-%m-%dT%H:%M:%SZ')

						## get unix timestamp for air_time
						air_time_stamp = mktime(air_time.timetuple())

						## if air time is within next 12 hours, 
						# assuming we run this script at 1 p.m. every day:

							from_zone = tz.gettz('UTC')
							to_zone = tz.gettz(user.timezone)

							# Tell the datetime object it's in UTC time zone
							air_time = air_time.replace(tzinfo=from_zone)

							# convert to user's timezone
							air_time = air_time.astimezone(to_zone)

							## format for text message
							friendly_time = air_time.strftime("%I:%M %p, %A, %b %d")
							title = item[1][0]['Title']

							text_message = 'A new episode of "%s" is on at %s' % (title, friendly_time)

							user_phone = "+1" + user.phone

							CLIENT.messages.create(
								to=user_phone, 
								from_=TWILIO_PHONE, 
								body=text_message,  
							)

send_notification()