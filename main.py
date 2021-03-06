from flask import Flask, url_for, render_template, redirect, jsonify, request, flash
from forms import PlayerForm, PlayerSelectionForm
import numpy as np
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, select, and_
from tensorflow import keras

# WebApp configuration and file paths
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ao19s2en1638nsh6msh172kd0s72ksj2'
model = keras.models.load_model('NBA_Game_model.h5')
db = create_engine('sqlite:///NBAPlayers.db', echo=True)
meta = MetaData()

# Table format from database
players = Table('players', meta,
    Column('NAME', String),
    Column('PLAYER_ID', String, primary_key=True),
    Column('YEAR', String, primary_key=True),
    Column('AGE', Integer),
    Column('HEIGHT', Integer),
    Column('WEIGHT', Integer),
    Column('MIN', Integer),
    Column('PTS', Integer),
    Column('FGM', Integer),
    Column('FG_PERCENTAGE', Integer),
    Column('THREE_PM', Integer),
    Column('THREE_P_PERCENTAGE', Integer),
    Column('FTM', Integer),
    Column('FT_PERCENTAGE', Integer),
    Column('OREB', Integer),
    Column('DREB', Integer),
    Column('AST', Integer),
    Column('TOV', Integer),
    Column('STL', Integer),
    Column('BLK', Integer),
    Column('PF', Integer),
    Column('PLUS_MINUS', Integer),
    Column('EFG_PERCENTAGE', Integer),
    Column('TS_PERCENTAGE', Integer)
)


# Returns true if at least 5 players were entered into the form for a team
def player_validation(players):
    players_selected = 0
    for player in players:
        if player["year"] != "Empty" and player["player_name"] != "Empty":
            players_selected += 1

    if players_selected < 9:
        return False
    else:
        return True


# Processes information entered into form - returns an array of stats to be analyzed by our model
def get_stats(home_players, away_players):

    num_home_players = 0
    home_stats = []
    for player in home_players:
        year = player["year"]
        player_id = player["player_name"]
        if year != "Empty" and player_id != "Empty":
            query = select([players]).where(and_(players.c.YEAR == year, players.c.PLAYER_ID == player_id))
            conn = db.connect()
            result = conn.execute(query)

            result = result.fetchone().values()
            del result[0:3]
            home_stats.extend(result)

            num_home_players += 1

    for x in range(num_home_players, 13):
        home_stats.extend(np.zeros(21))

    num_away_players = 0
    away_stats = []
    for player in away_players:
        year = player["year"]
        player_id = player["player_name"]
        if year != "Empty" and player_id != "Empty":
            print("RUN")
            query = select([players]).where(and_(players.c.YEAR == year, players.c.PLAYER_ID == player_id))
            conn = db.connect()
            result = conn.execute(query)

            result = result.fetchone().values()
            del result[0:3]
            away_stats.extend(result)

            num_away_players += 1

    for x in range(num_away_players, 13):
        away_stats.extend(np.zeros(21))

    stats = mod_min_ratio(home_stats, away_stats)

    return np.array(stats)


def mod_min_ratio(home_stats, away_stats):
    edit_stat_indexes = [3, 4, 5, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18]

    home_total_min = sum(home_stats[0:273:21])
    home_min_ratio = 5*48/home_total_min
    for i in range(0, 13):
        for j in edit_stat_indexes:
            home_stats[i*21+j] = round(home_stats[i*21+j] * home_min_ratio, 1)

    away_total_min = sum(away_stats[0:273:21])
    away_min_ratio = 5*48/away_total_min
    for i in range(0, 13):
        for j in edit_stat_indexes:
            away_stats[i*21+j] = round(away_stats[i*21+j] * away_min_ratio, 1)

    return home_stats + away_stats


# Route for webapp homepage - contains form
@app.route('/', methods=('GET', 'POST'))
def homepage():
    form = PlayerSelectionForm()

    player_choices = [("Empty", "Empty")]
    for player in form.home_players:
        player.player_name.choices = player_choices
    for player in form.away_players:
        player.player_name.choices = player_choices

    if request.method == "POST":
        home_players = form.home_players.data
        away_players = form.away_players.data

        if not player_validation(away_players) and not player_validation(home_players):
            flash("Please enter 9 players on both teams.", "error")
        elif not player_validation(home_players):
            flash("Please enter 9 players on the home team.", "error")
        elif not player_validation(away_players):
            flash("Please enter 9 players on the away team.", "error")
        else:
            stats = np.array([get_stats(home_players, away_players)])
            prediction = model.predict(stats)
            message = "The probability that the home team wins is " + str((prediction[0][0] * 100).round(1)) + "%"
            flash(message, "success")

    return render_template('request.html', form=form, title='Home')


# Queries database for list of names given the year - returns a JSON dictionary of objects containing player name and ID
@app.route('/update/<year>')
def update(year):
    query = select([players.c.PLAYER_ID, players.c.NAME]).where(players.c.YEAR == year)
    conn = db.connect()
    result = conn.execute(query)

    player_array = []

    for player in result:
        playerObj = {}
        playerObj["name"] = player.NAME
        playerObj["player_id"] = player.PLAYER_ID
        player_array.append(playerObj)

    return jsonify({"players": player_array})


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
