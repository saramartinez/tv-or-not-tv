from flask import Flask, render_template, redirect, request, session, flash, url_for, jsonify
from model import session as modelsession
from model import User, Show, Service, Favorite
from string import ascii_lowercase
import sys
import os
import requests
import json
import hashlib
from time import time, strftime
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'comingsoon'
ROVI_LISTINGS_API_KEY = os.environ['ROVI_TV_LISTINGS_API_KEY']
ROVI_SEARCH_API_KEY = os.environ['ROVI_METADATA_SEARCH_API_KEY']
ROVI_SEARCH_SECRET_KEY = os.environ['ROVI_METADATA_SHARED_SECRET']

unix_time = int(time())
sig = hashlib.md5(ROVI_SEARCH_API_KEY + ROVI_SEARCH_SECRET_KEY + str(unix_time)).hexdigest()

@app.route("/")
def index():
    """Shows the index."""
    return render_template("index.html")

@app.route("/signup", methods=['GET'])
def show_signup():
    """Display registration form"""
    return render_template("signup.html")

@app.route("/signup", methods=['GET', 'POST'])
def process_signup():
    """
    Get user information from signup.html on form submit
    and add as new user in database, then redirect to
    index. If user already exists, redirect to login
    page. Adds session cookies for logged_in = True and
    id = user.id.
    """
    new_email = request.form.get("email")
    new_password = request.form.get("password")

    name = request.form.get("username")
    zipcode = request.form.get("zipcode")
    service_id = request.form.get("service-provider")
    timezone = request.form.get("timezone")

    existing_user = modelsession.query(User).filter(User.email==new_email).first()
    
    if existing_user == None:
        new_user = User(name=name, email=new_email, password=new_password, zipcode=zipcode, service_id=service_id, timezone=timezone)
        modelsession.add(new_user)
        modelsession.commit()
        session['logged_in'] = True
        session['id'] = new_user.id
        flash("Successfully created account. Add your favorite shows to get personalized listings!")
        return redirect("/")
    else:
        flash("Your email address is already associated with an account. Please log in.")
        return redirect("/login")

@app.route("/find-provider", methods=['GET'])
def find_provider():
    """
    AJAX request sends user zipcode from signup.html to
    query Rovi TV Listings API for possible service 
    providers during user signup and add provider to
    database if not already there; then and return to
    signup.html.
    """
    zipcode = str(request.args.get("zipcode"))

    ## look for zip param in table, if req relatively fresh, return cached json from table; otherwise below

    listings_request = "http://api.rovicorp.com/TVlistings/v9/listings/services/postalcode/%s/info?locale=en-US&countrycode=US&format=json&apikey=%s" % (zipcode, ROVI_LISTINGS_API_KEY)

    listings_results = requests.get(listings_request)

    if listings_results.status_code == 200:
        providers = listings_results.json()

        services = providers['ServicesResult']['Services']['Service']
        
        for each in services:
            existing_service = modelsession.query(Service).filter(Service.id == each['ServiceId']).first()
            if existing_service == None:
                new_service = Service(name=each['Name'], id=each['ServiceId'])
                modelsession.add(new_service)
                modelsession.commit()
    else:
        services = None
        flash("There was an issue getting listings. Please reload the page.")

    return jsonify({'services': services})

@app.route("/login", methods=['GET'])
def show_login():
    """Show login form only if user not logged in"""
    if "logged_in" not in session:
        return render_template("login.html")
    else:
        flash("You're already logged in!")
        return redirect('/') 

@app.route("/login", methods=['POST'])
def process_login():
    """
    Checks to see if user exists in database and either
    logs them in or redirects to signup page.
    Adds session cookies for logged_in = True and
    id = user.id.
    """
    new_email = request.form.get('email')
    new_password = request.form.get('password')

    existing_user = modelsession.query(User).filter(User.email==new_email).first()

    if existing_user == None:
        flash("No user with that email exists. Please sign up!")
        return render_template("signup.html")
    else:
        if new_password != existing_user.password:
            flash("Incorrect password. Please try again.")
            return render_template("login.html")
        else:
            session['logged_in'] = True
            session['id'] = existing_user.id
            flash("Successfully logged in.")
            return redirect("/")

@app.route("/logout")
def logout():
    """Remove user.id and logged_in from session"""
    session.pop('logged_in', None)
    session.pop('id', None)
    flash("You were logged out.")
    return redirect("/")

@app.route("/settings/<int:id>")
def user_settings(id):
    user_profile = modelsession.query(User).filter(User.id == id).one()
    return render_template("settings.html", id=id, user=user_profile)

@app.route("/settings/<int:id>/edit")
def edit_settings(id):
    user_profile = modelsession.query(User).filter(User.id == id).one()
    return render_template("edit-settings.html", id=id, user=user_profile)

@app.route("/settings/<int:id>/update", methods=["POST"])
def update_settings(id):
    user_profile = modelsession.query(User).filter(User.id == id).one()

    old_password = request.form.get("old-password")
    new_email = request.form.get("email", None)
    new_password = request.form.get("new-password", None)
    new_name = request.form.get("username", None)
    new_zipcode = request.form.get("zipcode", None)
    new_service_id = request.form.get("service-provider", None)

    if old_password == user_profile.password:
        if new_email:
            user_profile.email = new_email
        if new_password:
            user_profile.password = new_password
        if new_name:
            user_profile.name = new_name
        if new_zipcode:
            user_profile.zipcode = new_zipcode
        if new_service_id:
            user_profile.service_id = new_service_id

        modelsession.commit()
        modelsession.refresh(user_profile)
        
        flash("Profile updated successfully.")

    else:
        flash("Incorrect password, please try again.")

    return redirect("/settings/" + str(id))

@app.route("/search")
def search():
    return render_template("search.html")

@app.route("/search", methods=["POST"])
def search_results():
    query = request.form.get('query')
    # db_results = modelsession.query(Show).filter(Show.title.like("%" + query + "%")).limit(10).all()

## if query exists in cache and timestamp is sort of recent, return results right here

    api_request = "http://api.rovicorp.com/search/v2.1/video/search?entitytype=tvseries&query=" + query + "&rep=1&include=synopsis%2Cimages&size=5&offset=0&language=en&country=US&format=json&apikey=" + ROVI_SEARCH_API_KEY + "&sig=" + sig

    rovi_results = requests.get(api_request)

    print requests.get(api_request)
## if 403, wait a second and try again?    

    if rovi_results.status_code == 200:
        json_results = rovi_results.json()

        ## if none fixx it
        results = json_results['searchResponse']['results']
        for each in results:
            result_title = each['video']['masterTitle']
            result_id = each['video']['ids']['cosmoId']
            
            if each['video']['synopsis']:
                result_synopsis = each['video']['synopsis']['synopsis']
            else:
                result_synopsis = None

            if each['video']['images']:
                result_img = each['video']['images'][0]['url']
            else:
                result_img = None

            existing_show = modelsession.query(Show).filter(Show.cosmoid == result_id).first()
            if existing_show == None:
                new_show = Show(title=result_title, cosmoid=result_id, synopsis=result_synopsis, img=result_img)
                modelsession.add(new_show)
                modelsession.commit()

        ## save result to new table

    else:
        results = None
        flash("There was an issue getting results. Please search again or reload the page.")
    
    return render_template("search.html", results=results)
    # return render_template("tv_list.html", db_shows=db_results, rovi_shows=rovi_results)

@app.route("/favorites", methods=['POST'])
def add_to_favorites():
    """
    Saves new database entry in favorites table with
    user's ID and show ID (foreign keys bridge users
    table and shows table).
    """
    shows = request.form.getlist("show")
    for show in shows:
        existing_favorite = modelsession.query(Favorite).filter(Favorite.show_id == show, Favorite.user_id == session['id']).first()
        if existing_favorite == None:
            new_favorite = Favorite(user_id=session['id'], show_id=show)
            modelsession.add(new_favorite)
            modelsession.commit()

    return redirect("/")

@app.route("/favorites/<int:id>")
def show_favorites(id):
    """
    Queries favorites table with user's ID to determine
    which shows are saved as favorites, then passes
    to HTMl to display all.
    """
    favorites = modelsession.query(Favorite).filter(Favorite.user_id==id).all()
    favorite = favorites.sort()
    return render_template("favorites.html", id=id, favorites=favorites)

@app.route("/schedule/<int:id>")
def show_schedule(id):
    """
    Gets user's first five favorites from database, then
    determine's user's service_id, current datetime and
    5 days from now to build API query. Results with
    broadcast times append to list to be returned to HTML. 
    """
    favorites = modelsession.query(Favorite).filter(Favorite.user_id==id).limit(5)
    favorites = sorted(favorites)
    
    serviceid = modelsession.query(User.service_id).filter(User.id==id).first()[0]

    now = datetime.utcnow()
    # start = now.strftime("%Y%m%d%H%M%S")
    # end = (now + timedelta(days=5)).strftime("%Y%m%d%H%M%S")
    start = now.strftime("%Y-%m-%dT%H%%3A%M%%3A%S.%fZ")

    results_list = []

    for favorite in favorites:
        cosmoid = favorite.show_id


        ##sted api req check FRESHNESS OF STUFF

        ## if now within 24 h of timestamp in table, then send back cached data; if not then update w/ following request


        api_request = "http://api.rovicorp.com/TVlistings/v9/listings/programdetails/%s/%s/info?locale=en-US&copytextformat=PlainText&include=Program&imagecount=5&duration=10080&inprogress=true&startdate=%s&pagesize=6&format=json&apikey=%s" % (serviceid, cosmoid, start, ROVI_LISTINGS_API_KEY)

        rovi_results = requests.get(api_request)

        if rovi_results.status_code == 200:

            request_results = rovi_results.json()
            results = request_results['ProgramDetailsResult']['Schedule']['Airings']

            results = sorted(results, key=lambda results: results['AiringTime'])

            results_list.append(results)
        else:
            flash("The request timed out. Please refresh the page.")
            results_list = None


    return render_template("schedule.html", schedule=results_list, favorites=favorites)


if __name__ == "__main__":
    app.run(debug = True)