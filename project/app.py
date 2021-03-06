from flask import Flask, render_template, session, redirect, request, url_for,g
from twitter_utils import get_request_token, get_oauth_verifier_url, get_access_token
from user import User
from database import Database
import requests

app = Flask(__name__)
app.secret_key = '1234'
# this is necessary so that the cookies can be encrypted and secured

Database.initialize(user='postgres', password='1234', host='localhost', database='Learning')
# Don't forget this!

@app.before_request
def load_user():
    if 'screen_name' in session: # if screen name key exists in the session
        g.user = User.load_from_db_by_screen_name(session['screen_name'])
        # g is a global Flask variable. Available throughout the entire request
        # so we have the access to the user object all the time

@app.route('/') # means http://127.0.0.1:4995
# decorator. means when meet / - return the contents of the method below
def homepage():
    return render_template('home.html')

# app route can have smth like /users. So when they are at the user endpoint
# then the method below will be executed and a certain page will be displayed

@app.route('/login/twitter')
def twitter_login():

    # if the user logged in, show the profile page. If the app is already authorized
    if 'screen_name' in session:
        return redirect(url_for('profile'))

    request_token = get_request_token()
    # this var is inside the method and will disappear after leaving the func
    # but we need this var later. The way to use it - sessions and cookies
    session['request_token'] = request_token
    # session is persistent between the requests
    # we store the request token in a session

    # cookie gets stored in the browser of the user. Flask will now that this cookie is related to a certain session
    # session is stored on a hard-drive. And it contains the request token

    return redirect(get_oauth_verifier_url(request_token))
    # redirecting the user to twitter


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('homepage'))


@app.route('/auth/twitter') # we are at the end point 127.0.0.1:4995/auth/twitter?oauth_verifier=some number
def twitter_auth():
    oauth_verifier = request.args.get('oauth_verifier') # gets what goes after oauth_verifier in a string above
    access_token = get_access_token(session['request_token'], oauth_verifier)

    user = User.load_from_db_by_screen_name(access_token['screen_name'])
    if not user: # if new user
        user = User(access_token['screen_name'], access_token['oauth_token'], access_token['oauth_token_secret'], None)
        user.save_to_db()
    # save sn to the session so that we know who is it when they come back
    session['screen_name'] = user.screen_name

    return redirect(url_for('profile')) # profile is a method (the one below)! Not the end point


@app.route('/profile')
def profile():
    return render_template('profile.html', user=g.user) # pass in an arugment


@app.route('/search') #127.0.0.1:4995/search?q=cars+filter:images
def search():

    query = request.args.get('q')

    tweets = g.user.twitter_request('https://api.twitter.com/1.1/search/tweets.json?q={}'.format(query))
    tweet_texts = [{'tweet': tweet['text'], 'label':'neutral'} for tweet in tweets['statuses']]
    # list comprehension
    # get text for each tweet in tweets statuses
    # each tweet is a dict now with its text and sentiment. Neutral by default

    # Sentiment analysis
    for tweet in tweet_texts:
        r = requests.post('http://text-processing.com/api/sentiment/', data={'text':tweet['tweet']})
        # using requests library (not Flask part)
        json_response = r.json()
        label = json_response['label']
        # http://text-processing.com/docs/sentiment.html instructions are here
        tweet['label'] = label
        # change the tweet label to positive or negative or leave neutral

    return render_template('search.html', content = tweet_texts)

app.run(port=4995, debug=True)

