# TV listings app
for Hackbright final project

"TV...or Not TV" is a utility app that creates personalized TV listings based on a user's preferences and favorites. After selecting a TV service provider, users build a list of "favorite" shows which are organized into a listings schedule. The personalized schedule provides information on upcoming episodes including a synopsis, when to watch, channel information and if the episodes are new or in HD. Users can sign up to receive a text message notification to alert them when one of their favorites has a new episode that night.

## Technology

### Project Technology Stack:
Python, Flask, Jinja, SQLAlchemy, Javascript, jQuery, AJAX, [Moment.js](http://momentjs.com/), HTML5, CSS3, [Bootstrap](http://getbootstrap.com/), [PyLint](http://www.pylint.org/)

### APIs:
[ROVI Cloud Services API](http://developer.rovicorp.com/docs), [Twilio API](https://www.twilio.com/)

## Features
#####User login/favorites
Users can create and log into an account to save favorites and create a personalized TV schedule.
##### Personalized Listings
Users search for TV shows and, if logged in, can save favorites to display on the home page and in a personalized listings grid.
![Personalized listings screenshot](http://s27.postimg.org/68y2xhftv/Screen_Shot_2015_03_17_at_7_58_43_PM.png)
##### Preview new episodes
On the home screen, users will always find an image and summary of each of their favorite TV shows along with a details and a preview of the upcoming new episode. If no new episodes are airing this week, only the TV show image and description will appear on the home page. The listings tab will have all listings of repeat episodes.
![Homepage screenshot](http://s14.postimg.org/l3t8tmtyp/Screen_Shot_2015_03_17_at_7_58_23_PM.png)
##### Daily text message for new episodes
If users provide a phone number and opt in for text messaging, TV or Not TV makes use of the Twilio API and a continuous cron job to send text messages to the user every day at 2:30 p.m. if there is a new episode that night.
##### Caching
To improve speed and usability, every query made to the Rovi API is cached for future use. Regular search queries and zip code queries for a TV service provider and all complementary results are stored in the database for 7 days before hitting the API to refresh results. Personalized TV listings queries have two parameters -- service ID and TV series ID -- and are subject to change more frequently, so those results are only cached for 6 hours before re-querying the API.

### Version 2.0
#### What's next for TV or Not TV?

##Structure
###Backend
####app.py
Flask app to run things on the server side
####model.py
Defines database classes:
- User
- Show
- Favorite (backref relationships connect User class to Show class; a user can have many favorite shows)
- CachedService (param: zipcode)
- CachedListing (params: TV provider/service ID, TV series/show ID)
- CachedSearch (param: search terms)

####cron.py
Cron job runs on service once a day at 2:30 p.m.: Finds all users in database who have a valid phone number and who have opted in to receive text notifications, then looks through each user's favorites and retrieves listings for those favorites (if not cached within 6 hours, re-queries for refreshed listings. If an episode's type is marked "new" and it occurs within 12 hours of the query (between 2:30 p.m. today and 2:30 a.m. tomorrow), then send a text message to the user's phone number to alert the user that a new episode of that show is on tonight.
###Front-end
Uses Jinja templating and manipulates time/adjusts to local time zones with moment.js library.
