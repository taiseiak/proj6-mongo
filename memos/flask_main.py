"""
Flask web app connects to Mongo database.
Keep a simple list of dated memoranda.

Representation conventions for dates: 
   - We use Arrow objects when we want to manipulate dates, but for all
     storage in database, in session or g objects, or anything else that
     needs a text representation, we use ISO date strings.  These sort in the
     order as arrow date objects, and they are easy to convert to and from
     arrow date objects.  (For display on screen, we use the 'humanize' filter
     below.) A time zone offset will 
   - User input/output is in local (to the server) time.  
"""

import flask
from flask import request
from flask import url_for
import logging
from bson import ObjectId
# Date handling
import arrow
from pymongo import MongoClient

import config

###
# Globals
###
CONFIG = config.configuration()

app = flask.Flask(__name__)
app.secret_key = CONFIG.SECRET_KEY

# Mongo database
MONGO_CLIENT_URL = "mongodb://{}:{}@{}:{}/{}".format(
    CONFIG.DB_USER,
    CONFIG.DB_USER_PW,
    CONFIG.DB_HOST,
    CONFIG.DB_PORT,
    CONFIG.DB)

dbclient = MongoClient(MONGO_CLIENT_URL)
db = dbclient[str(CONFIG.DB)]
collection = db.dated_memos

app.debug = CONFIG.DEBUG
if CONFIG.DEBUG:
    app.logger.setLevel(logging.DEBUG)

####
# Database connection per server process
###




###
# Pages
###

@app.route("/")
@app.route("/index")
def index():
    app.logger.debug("Main page entry")
    return flask.render_template('index.html')


# Responses
@app.route("/_get_memos")
def send_memos():
    results = get_memos()
    if results:
        return flask.jsonify(results={"memos": results})
    else:
        return flask.jsonify(results={"memos": "none"})


@app.route("/_post_memo", methods=['POST'])
def post_memo():
    data = request.form
    date, memo = data['date'], data['memo']
    try:
        date_valid = arrow.get(date)
        insert_bson = {'date': date, 'memo': memo}
        tr_id = collection.insert_one(insert_bson).inserted_id
    except:
        tr_id = 0
    return flask.jsonify(results={'success': bool(tr_id)})


@app.route("/_delete_memo")
def delete_memo():
    data = request.args['id']
    success = collection.delete_one({'_id': ObjectId(data)}).deleted_count
    return flask.jsonify(result={'success': success})


@app.errorhandler(404)
def page_not_found(error):
    app.logger.debug("Page not found")
    return flask.render_template('page_not_found.html',
                                 badurl=request.base_url,
                                 linkback=url_for("index")), 404


#################
#
# Functions used within the templates
#
#################


def humanize_arrow_date(date):
    """
    Date is internal UTC ISO format string.
    Output should be "today", "yesterday", "in 5 days", etc.
    Arrow will try to humanize down to the minute, so we
    need to catch 'today' as a special case. 
    """

    then = arrow.get(date).to('local')
    now = arrow.utcnow().to('local')
    if then.date() == now.date():
        human = "Today"
    else:
        human = then.humanize(now)
        if human == "in a day":
            human = "Tomorrow"
    return human


#############
#
# Functions available to the page code above
#
##############
def get_memos():
    """
    Returns all memos in the database, in a form that
    can be inserted directly in the 'session' object.
    """
    records = []
    for record in collection.find():
        record["_id"] = str(record["_id"])
        record['human_date'] = humanize_arrow_date(record['date'])
        records.append(record)
    if records:
        return_record = sorted(records, key=lambda k: arrow.get(k['date']))
    else:
        return_record = records
    return return_record


if __name__ == "__main__":
    app.run(port=CONFIG.PORT, host="0.0.0.0")
