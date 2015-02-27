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
    if 'logged_in' in session:
        favorites = modelsession.query(Favorite).filter(Favorite.user_id==session['id']).all()
        return render_template("favorites.html", favorites=favorites, id=session['id'])

    return render_template("index.html")

@app.route("/signup", methods=['GET'])
def show_signup():
    """Display registration form"""
    return render_template("signup.html")

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

    listings_request = "http://api.rovicorp.com/TVlistings/v9/listings/services/postalcode/%s/info?locale=en-US&countrycode=US&format=json&apikey=%s" % (zipcode, ROVI_LISTINGS_API_KEY)

    providers = requests.get(listings_request).json() 
    
    services = providers['ServicesResult']['Services']['Service']
    
    for each in services:
        existing_service = modelsession.query(Service).filter(Service.id == each['ServiceId']).first()
        if existing_service == None:
            new_service = Service(name=each['Name'], id=each['ServiceId'])
            modelsession.add(new_service)
            modelsession.commit()
    return jsonify({'services': services})


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

@app.route("/login", methods=['GET'])
def show_login():
    """Show login form only if user not logged in"""
    if "user" not in session:
        return render_template("login.html")
    else:
        flash("You're already logged in!")
        return redirect('/') 

# Allow existing users to log in
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

@app.route("/search")
def search():
    return render_template("search.html")

@app.route("/search", methods=["POST"])
def search_results():
    query = request.form.get('query')
    # db_results = modelsession.query(Show).filter(Show.title.like("%" + query + "%")).limit(10).all()


    api_request = "http://api.rovicorp.com/search/v2.1/video/search?entitytype=tvseries&query=" + query + "&rep=1&include=synopsis%2Cimages&size=5&offset=0&language=en&country=US&format=json&apikey=" + ROVI_SEARCH_API_KEY + "&sig=" + sig

    # try except for value error if no results returned

    rovi_results = requests.get(api_request).json()


    results = rovi_results['searchResponse']['results']
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
        # save to user's db

    return redirect("/")

@app.route("/favorites/<int:id>")
def show_favorites(id):
    # favorites = modelsession.query(Favorite).filter(Favorite.user_id==id).all()
    # return render_template("favorites.html", id=id, favorites=favorites)

# @app.route("/schedule")
# def show_schedule():
    favorites = modelsession.query(Favorite).filter(Favorite.user_id==id).limit(5)
    
    serviceid = modelsession.query(User.service_id).filter(User.id==id).first()[0]
    
    start = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    end = (datetime.utcnow() + timedelta(days=5)).strftime("%Y%m%d%H%M%S")

    results_list = []

    for favorite in favorites:
        cosmoid = favorite.show_id

        api_request = "http://api.rovicorp.com/TVlistings/v9/listings/programdetails/%s/%s/info?locale=en-US&copytextformat=PlainText&include=Program&imagecount=5&duration=10080&inprogress=true&pagesize=0&format=json&apikey=%s" % (serviceid, cosmoid, ROVI_LISTINGS_API_KEY)

        request_results = requests.get(api_request).json()
        results = request_results['ProgramDetailsResult']['Schedule']['Airings']
        results_list.append(results)

    return render_template("schedule.html", schedule=results_list, favorites=favorites)

@app.route("/settings/<int:id>")
def user_settings(id):
    user_profile = modelsession.query(User).filter(User.id == id).one()
    return render_template("settings.html", id=id, user=user_profile)


if __name__ == "__main__":
    app.run(debug = True)