import urllib.request
import gzip
import json
import numpy as np
from pandas import *
import csv
import re


class NBAGame:
    def __init__(self, game_id, json_file):  # object class used to store information regarding a specific NBA Game
        self.game_id = game_id
        self.json_file = json_file

        self.home_team_id = None
        self.away_team_id = None
        self.home_team_points = None
        self.away_team_points = None
        self.home_team_players = []
        self.away_team_players = []
        self.home_win = None

        self.__set_team_ids()
        self.__set_points()
        self.__set_player_stats()
        self.__set_result()

    # finds the match lineup in "Series Standings" and sets the appropriate values
    def __set_team_ids(self):
        for i in range(len(self.json_file["resultSets"][2]["rowSet"])):  # increment through all games
            if self.json_file["resultSets"][2]["rowSet"][i][0] == self.game_id:  # find matching game
                self.home_team_id = self.json_file["resultSets"][2]["rowSet"][i][1]
                self.away_team_id = self.json_file["resultSets"][2]["rowSet"][i][2]
                return

    # finds the points for each team in "Line Score" and sets the appropriate values
    def __set_points(self):
        for i in range(len(self.json_file["resultSets"][1]["rowSet"])):  # increment through all teams
            if self.json_file["resultSets"][1]["rowSet"][i][3] == self.home_team_id:  # match home id
                self.home_team_points = self.json_file["resultSets"][1]["rowSet"][i][22]
            if self.json_file["resultSets"][1]["rowSet"][i][3] == self.away_team_id:  # match away id
                self.away_team_points = self.json_file["resultSets"][1]["rowSet"][i][22]
            if self.home_team_points is not None and self.away_team_points is not None:  # stops when both are filled
                return

    # finds player stats in "PlayerStats" and sets the appropriate values
    def __set_player_stats(self):
        self.json_file = stats_in_game(self.game_id)  # uses game-specific box score JSON
        for player in self.json_file["resultSets"][0]["rowSet"]:  # increment through all players
            if player[1] == self.home_team_id:  # add player to respective team
                self.home_team_players.append(player)
            else:
                self.away_team_players.append(player)

    # compares scores and determines which team won
    def __set_result(self):
        if self.home_team_points > self.away_team_points:
            self.home_win = True
        else:
            self.home_win = False

    # prints all variables
    def print(self):
        attrs = vars(self)
        print('\n'.join("%s: %s" % item for item in attrs.items()))

    # inserts all data into a one-dimension array
    def compile_data(self):
        game_data_array = []  # stores game statistics --> will be a row in the machine learning training file
        omit_stat_indexes = [10, 13, 16, 20]  # indexes of statistics to omit (FGM, FTM, 3PM, REB)
        stats_per_player = 16

        # loops through all players on the home team and adds relevant data to array
        for i in range(len(self.home_team_players)):
            for x in range(8, len(self.home_team_players[i])):
                if x in omit_stat_indexes:
                    continue
                stat = self.home_team_players[i][x]
                if stat is None:
                    stat = 0
                elif x == 8:  # modify timestamp into seconds
                    timestamp = re.match(r"(\d+):(\d+)", stat).groups()
                    stat = int(timestamp[0])*60 + int(timestamp[1])
                game_data_array.append(stat)

        # fills in 0s if less than 13 players
        if len(self.home_team_players) < 13:
            missing_players = 13 - len(self.home_team_players)
            for i in range(missing_players * stats_per_player):
                game_data_array.append(0)

        # loops through all players on the away team and adds relevant data to array
        for i in range(len(self.away_team_players)):
            for x in range(8, len(self.away_team_players[i])):
                if x in omit_stat_indexes:
                    continue
                stat = self.away_team_players[i][x]
                if stat is None:
                    stat = 0
                elif x == 8:  # modify timestamp into seconds
                    timestamp = re.match(r"(\d+):(\d+)", stat).groups()
                    stat = int(timestamp[0])*60 + int(timestamp[1])
                game_data_array.append(stat)

        # fills in 0s if less than 13 players
        if len(self.away_team_players) < 13:
            missing_players = 13 - len(self.away_team_players)
            for i in range(missing_players * stats_per_player):
                game_data_array.append(0)

        game_data_array.append(int(self.home_win))  # adds win result to array
        return game_data_array


# finds all games on a specific day and returns a JSON containing info of all games on that day
def games_on_date(month, day, year):
    day = f"{month}%2F{day}%2F{year}"
    game_id_url = f"https://stats.nba.com/stats/scoreboardV2?DayOffset=0&LeagueID=00&gameDate={day}"
    game_id_headers = {"Host": "stats.nba.com", "Connection": "keep-alive", "Accept": "application/json, text/plain, */*", "x-nba-stats-origin": "stats", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36", "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en;q=0.9"}

    req = urllib.request.Request(url=game_id_url, headers=game_id_headers)
    response = urllib.request.urlopen(req)
    data = response.read()
    data = str(gzip.decompress(data), 'utf-8')
    json_file = json.loads(data)
    return json_file


# finds box score information of a specific game and a JSON containing detailed stats of players in the game
def stats_in_game(game_id):
    game_stats_url = f"https://stats.nba.com/stats/boxscoretraditionalv2?EndPeriod=10&EndRange=28800&GameID={game_id}&RangeType=0&StartPeriod=1&StartRange=0"
    game_stats_headers = {"Host": "stats.nba.com", "Connection": "keep-alive", "Accept": "application/json, text/plain, */*", "x-nba-stats-origin": "stats", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36", "Referer": f"https://stats.nba.com/game/{game_id}/", "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en;q=0.9"}

    req = urllib.request.Request(url=game_stats_url, headers=game_stats_headers)
    response = urllib.request.urlopen(req)
    data = response.read()
    data = str(gzip.decompress(data), 'utf-8')
    json_file = json.loads(data)
    return json_file


# returns all the games played on a specific day
def get_game_ids(json_file):
    game_list = json_file["resultSets"][0]["rowSet"]
    game_ids = []
    for game in game_list:
        game_ids.append(game[2])
    return game_ids


# converts data into a csv file
def export_data(game_day_matrix):
    filename = "original_training_data.csv"
    with open(filename, 'a', newline='') as csv_file:

        # creating a csv writer object
        csv_writer = csv.writer(csv_file)

        # writing the data rows
        csv_writer.writerows(game_day_matrix)


def export_range(begin_month, begin_day, begin_year, end_month, end_day, end_year):
    for year in range(begin_year, end_year+1):
        s_month = 1
        e_month = 12
        if year == begin_year:
            s_month = begin_month
        if year == end_year:
            e_month = end_month
        for month in range(s_month, e_month+1):
            s_day = 1
            e_day = 31
            if month == begin_month and year == begin_year:
                s_day = begin_day
            if month == end_month and year == end_year:
                e_day = end_day
            for day in range(s_day, e_day+1):
                try:
                    games = games_on_date(str(month).zfill(2), str(day).zfill(2), year)
                    game_id_list = get_game_ids(games)

                    game_day_matrix = []
                    game_data = []

                    for game_id in game_id_list:
                        target_game = NBAGame(game_id, games)
                        game_data = target_game.compile_data()
                        game_day_matrix.append(game_data)

                    print(str(month).zfill(2), str(day).zfill(2), year)

                    export_data(game_day_matrix)
                except:
                    continue


export_range(1, 1, 2020, 1, 3, 2020)

# print(game_info.away_team_players[i])

# print(json.dumps(games, indent=4))
# print(json.dumps(game_info.home_team_players, indent=4))
#
# for game_id in get_game_ids(games):
#     stats = stats_in_game(game_id)
#     print(json.dumps(stats, indent=4))

# print(json.dumps(games_on_date("11", "01", "2001"), indent=4))
# print(json.dumps(stats_in_game("0020100019"), indent=4))
