import json
import ticketpy
from urllib.parse import quote
from flaskext.mysql import MySQL


import requests
from flask import Flask, redirect, url_for, session, request, render_template
from flask_oauthlib.client import OAuth, OAuthException

app = Flask(__name__)


mysql = MySQL()
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'put your password here'
app.config['MYSQL_DATABASE_DB'] = 'name of database'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)
conn = mysql.connect()
cursor = conn.cursor()


SPOTIFY_APP_ID = 'put your app_id here'
SPOTIFY_APP_SECRET = 'put your secret here'


app.debug = True
app.secret_key = 'your secret key'
oauth = OAuth(app)

spotify = oauth.remote_app(
    'spotify',
    consumer_key=SPOTIFY_APP_ID,
    consumer_secret=SPOTIFY_APP_SECRET,
    # Change the scope to match whatever it us you need
    # list of scopes can be found in the url below
    # https://developer.spotify.com/web-api/using-scopes/
    request_token_params={'scope': 'user-top-read'},
    base_url='https://accounts.spotify.com',
    request_token_url=None,
    access_token_url='/api/token',
    authorize_url='https://accounts.spotify.com/authorize'
)


@app.route('/')
def index():
    return redirect(url_for('login1'))


@app.route('/login', methods=['GET'])
def login1():
    return render_template('index.html')


@app.route('/login/spotify')
def login():
    #print("in login")
    callback = url_for(
        'spotify_authorized',
       # next=request.args.get('next') or request.referrer or None,
        _external=True
    )
    #print("callback :", callback)
    #print("request.referrer", request.referrer)
    #print("request.args.get", request.args.get('next'))
    return spotify.authorize(callback=callback)


@app.route('/login/spotify/authorized')
def spotify_authorized():
    resp = spotify.authorized_response()
    if resp is None:
        return 'Access denied: reason={0} error={1}'.format(
            request.args['error_reason'],
            request.args['error_description']
        )
    if isinstance(resp, OAuthException):
        return 'Access denied: {0}'.format(resp.message)

    session['oauth_token'] = (resp['access_token'], '')
    # Get profile data

    access_token = resp['access_token']
    #print("access token = ", resp['access_token'])

    s = requests.Session()
    authorization_header = {"Authorization": "Bearer {}".format(resp['access_token'])}
    user_profile_api_endpoint = "https://api.spotify.com/v1/me"
    profile_response = s.get(user_profile_api_endpoint, headers=authorization_header)
    profile_data = json.loads(profile_response.text)
    #print("profile data: ", profile_data)


    if str(profile_data['images']) == "[]":
        #print("should go here")
        profile_photo = "no photo"

    else:
        profile_photo = profile_data['images'][0]['url']


    userID = profile_data['id']
    userName = profile_data['display_name']
    #print("username ", userName)
    #print("userId", userID)
    #print("profile photo", profile_photo)

    # gets list of eventbrite events
    topArtist_api_endpoint = "https://api.spotify.com/v1/me/top/artists?limit=1"
    #print("topArtist_api_endpoint = ", topArtist_api_endpoint)
    topArtist_response = s.get(topArtist_api_endpoint, headers=authorization_header)
    #print("authorization_header = ", authorization_header)
    #print("topArtist_response = ", topArtist_response)
    topArtist_data = json.loads(topArtist_response.text)
    #print("topArtist data: ", topArtist_data)


    genres = []
    for x in topArtist_data['items']:
        genres += [x["genres"]]

    #print("Genres = ", genres)

    genres = [val for sublist in genres for val in sublist]
    genres = list(set(genres))
    #print("genres after = ", genres)
    event_names = []
    for x in range(len(genres)):
        request_link = "https://www.eventbriteapi.com/v3/events/search/?token=(your token here)=" + quote(genres[x], safe='') + "&sort_by=date&categories=103&start_date.keyword=this_week"
        response = s.get(
            request_link, verify=True,  # Verify SSL certificate
        )
        data = response.json()
        #print("request link eventbrite = ", request_link)

        print("DATA: ", data)

        for i in data['events']:
            #print("i ", i)

            city_request_link = "https://www.eventbriteapi.com/v3/venues/" + i['venue_id'] + "/?token=(your token here)"
            #print("city_request_link:", city_request_link)
            response = s.get(
            city_request_link, verify=True,
            )
            data1 = response.json()
            #print("city:", data1['address'])
            #print("city1:", data1['address']['city'])
            city = data1['address']['city']
            #print("city: ", city)

            if str(city) == "None":
                #print("here: " + str(city))
                event_names += [str(i['name']['text']) + ", " + str(i['start']['utc'])]

            else:
                event_names += [str(i['name']['text']) + ", " + str(i['start']['utc']) + ", City: " + str(city)]

        #print("request link eventbrite = ", request_link)
    #print(event_names)

    # gets names of user's top 5 artists and image urls
    topFiveArtist_api_endpoint = "https://api.spotify.com/v1/me/top/artists?limit=5"
    topFiveArtist_response = s.get(topFiveArtist_api_endpoint, headers=authorization_header)
    topFiveArtist_data = json.loads(topFiveArtist_response.text)

    names = []
    image_urls = []
    for y in topFiveArtist_data['items']:
        names += [y['name']]
        image_urls += [y['images'][0]['url']]

    #print("names = ", names)
    #print("image url = ", image_urls)

    tm_client = ticketpy.ApiClient('put your api client id here')

    ticketMasterData = []
    for w in range(len(names)):
        pages = tm_client.events.find(
            keyword=names[w]
        )
        #print("keyword: ", names[w])

        for page in pages:
            for event in page:
                ticketMasterData += [event.name + " " + event.local_start_date + ", Status: " + event.status + ", City: " + event.venues[0].city]
    #print(ticketMasterData)
    cursor = conn.cursor()

    # if user not in table then insert them otherwise don't do anything

    checkQuery = ("SELECT user_id FROM USERS WHERE user_id = '%s'"%userID)

    if cursor.execute(checkQuery):
        #print("not re-entering existing value into database")
        answer = 5
    else:
        cursor.execute("INSERT INTO USERS (user_id, display_name, image, spotify_token) VALUES (%s, %s, %s, %s)", (userID, userName, profile_photo, access_token))
    conn.commit()

    #print("artist photos", image_urls)

    s.cookies.clear()
    return render_template('login.html', topArtists=names, artistPhotos=image_urls, eventbriteResponse=event_names, profilePhoto=profile_photo, ticketmasterResponse=ticketMasterData, name=userName)
    #print(artistPhotos)

@spotify.tokengetter
def get_spotify_oauth_token():
    return session.get('oauth_token')


if __name__ == '__main__':
    app.run(port=5000, debug=True)
