import os
from datetime import datetime
from time import time, mktime
from model import session as modelsession
from model import User, Show, Service, Favorite, CachedService, CachedListing, CachedSearch
from app import show_schedule
from twilio.rest import TwilioRestClient 

ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']
TWILIO_PHONE = os.environ['TWILIO_PHONE']
CLIENT = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN) 


NOW = datetime.utcnow()
CURRENT_TIMESTAMP = mktime(NOW.timetuple())

TWELVE_HOURS = 43200

def send_notification():
	users = modelsession.query(User).filter(User.phone != None, User.get_texts == True)

	for user in users:
		listings = show_schedule(user.id)
		## want to return just resulst list not whole template
		for item in listings:
			if item['AiringType'] =='new':
				air_time = mktime(item['AiringTime'].timetuple())
				## if air time is within next 12 hours, 
				## assuming we run this script at 1 p.m. every day:
				if air_time - CURRENT_TIMESTAMP < TWELVE_HOURS:

					from_zone = tz.gettz('UTC')
					to_zone = tz.gettz(user.timezone)

					## change unicode item['AiringTime'] to python datetime object
					air_time = datetime.strptime(item['AiringTime'], '%Y-%m-%dT%H:%M:%SZ')

					# Tell the datetime object it's in UTC time zone
					air_time = air_time.replace(tzinfo=from_zone)

					# convert to user's timezone
					air_time = air_time.astimezone(to_zone)

					## format for text message
					friendly_time = air_time.strftime("%b %d at %I:%M %p")

					CLIENT.messages.create(
						to=user.phone, 
						from_=TWILIO_PHONE, 
						body= "A new episode of " + item['Title'] + " is on at " + friendly_time + " tonight",  
					)
