import requests
import flask
import json
from flask import Flask, render_template, jsonify, request


app = Flask(__name__)


@app.route('/')
def get_form():
    return render_template('results.html')


@app.route('/', methods=['POST', 'GET'])
def get_query():
    try:
        event_type = request.form.get('event_type')
        print(event_type)

    except:
        print("no search terms added")
        return flask.redirect(flask.url_for('get_query'))

    request_link = "" + event_type
    response = requests.get(https://www.eventbriteapi.com/v3/events/search/?token=(put your token here)&q=
        request_link, verify=True,  # Verify SSL certificate
    )
    data = response.json()

    event_names = []
    for i in data['events']:
        event_names += [str(i['name']['text'])]
    print(event_names)

    return render_template('eventInfo.html', response=event_names)


if __name__ == '__main__':
    app.run()

