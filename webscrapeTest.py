import urllib.request
from urllib.error import HTTPError
import datetime
import gzip
import json
import csv
import re
import pandas as pd


class NBAGame:
    def __init__(self, game_id, json_file, seasonal_stats):  # object class used to store information regarding a specific NBA Game
        self.game_id = game_id
        self.json_file = json_file
        self.seasonal_stats = seasonal_stats

        self.home_team_id = None
        self.away_team_id = None
        self.home_team_points = None
        self.away_team_points = None
        self.home_team_players = []
        self.away_team_players = []
        self.home_win = None

        self.__set_team_ids()
        self.__set_points()
        self.__set_seasonal_stats()
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

    # finds player stats in "PlayerStats" and sets the appropriate values ***if KEYERROR occurs add try except where except just continues
    def __set_seasonal_stats(self):
        self.json_file = stats_in_game(self.game_id)  # uses game-specific box score JSON
        for player in self.json_file["resultSets"][0]["rowSet"]:  # increment through all players
            mins_played = player[8]

            if mins_played is None:
                mins_played = 0
            else:
                timestamp = re.match(r"(\d+):(\d+)", mins_played).groups()
                mins_played = (int(timestamp[0]) * 60 + int(timestamp[1])) / 60

            if mins_played > 0:
                seasonal_stats = self.seasonal_stats[str(player[5])]
                if player[1] == self.home_team_id:  # add player to respective team
                    self.home_team_players.append(seasonal_stats)
                else:
                    self.away_team_players.append(seasonal_stats)

    # compares scores and determines which team won
    def __set_result(self):
        if self.home_team_points > self.away_team_points:
            self.home_win = True
        else:
            self.home_win = False

    # prints all variables
    def print_vars(self):
        attrs = vars(self)
        print('\n'.join("%s: %s" % item for item in attrs.items()))

    # inserts seasonal data into an array
    def compile_data(self):
        self.json_file = stats_in_game(self.game_id)
        game_data_array = []  # stores game statistics --> will be a row in the csv file
        stat_indexes = [0, 5, 6, 8, 9, 11, 12, 14, 15, 16, 18, 19, 20, 21, 23, 25, 26]  # indexes of statistics
        edit_stat_indexes [] # indexes of stats to be modified by mins_ratio
        stats_per_player = 17

        game_data_array.append(int(self.home_win))  # adds win result to array
        game_data_array.append(int(self.game_id)) # adds gameID to array

        # loops through all players on the home team and adds relevant data to array
        for i in range(len(self.home_team_players)):
            if i > 12: # break if more than 13 players in list
                break

            mins_played = self.json_file["resultSets"][0]["rowSet"][i][8]
            if mins_played is None:
                mins_played = 0
            else:
                timestamp = re.match(r"(\d+):(\d+)", mins_played).groups()
                mins_played = (int(timestamp[0]) * 60 + int(timestamp[1])) / 60

            mins_ratio = mins_played / (self.home_team_players[i][5])

            for x in range(0, len(self.home_team_players[i])):
                if x not in stat_indexes:
                    continue
                elif x is 5:
                    stat = mins_played
                else:
                    stat = self.home_team_players[i][x]
                    if stat is None:
                        stat = 0

                if x in edit_stat_indexes:
                    game_data_array.append(stat * mins_ratio)
                else:
                    game_data_array.append(stat)

        if len(self.home_team_players) < 13: # fills in 0s if less than 13 players
            missing_players = 13 - len(self.home_team_players)
            for i in range(missing_players * stats_per_player):
                game_data_array.append(0)


        for i in range(len(self.away_team_players)):
            if i > 12:  # break if more than 13 players in list
                break

            mins_played = self.json_file["resultSets"][0]["rowSet"][i][8]
            if mins_played is None:
                mins_played = 0
            else:
                timestamp = re.match(r"(\d+):(\d+)", mins_played).groups()
                mins_played = (int(timestamp[0]) * 60 + int(timestamp[1])) / 60

            mins_ratio = mins_played / (self.away_team_players[i][5])

            for x in range(0, len(self.away_team_players[i])):
                if x not in stat_indexes:
                    continue
                elif x is 5:
                    stat = mins_played
                else:
                    stat = self.away_team_players[i][x]
                    if stat is None:
                        stat = 0

                if x in edit_stat_indexes:
                    game_data_array.append(stat * mins_ratio)
                else:
                    game_data_array.append(stat)

        if len(self.away_team_players) < 13: # fills in 0s if less than 13 players
            missing_players = 13 - len(self.away_team_players)
            for i in range(missing_players * stats_per_player):
                game_data_array.append(0)

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
    gameday_json = json.loads(data)
    return gameday_json


# returns all the games played on a specific day
def get_game_ids(gameday_json):
    game_list = gameday_json["resultSets"][0]["rowSet"]
    game_ids = []
    for game in game_list:
        game_ids.append(game[2])
    return game_ids


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

# gathers advanced stats for all the players in a given season
# def get_advanced_stats(season):
# #     jiebin can you write this method
# #     just get all the basic advanced stats we will sort out which ones we want later


# gathers seasonal stats for all players during a specified season
def get_seasonal_stats(season):
    param = f"{season}-{season % 100 + 1}"
    season_stats_url = f"https://stats.nba.com/stats/leaguedashplayerstats?College=&Conference=&Country=&DateFrom=&DateTo=&Division=&DraftPick=&DraftYear=&GameScope=&GameSegment=&Height=&LastNGames=0&LeagueID=00&Location=&MeasureType=Base&Month=0&OpponentTeamID=0&Outcome=&PORound=0&PaceAdjust=N&PerMode=PerGame&Period=0&PlayerExperience=&PlayerPosition=&PlusMinus=N&Rank=N&Season={param}&SeasonSegment=&SeasonType=Regular+Season&ShotClockRange=&StarterBench=&TeamID=0&TwoWay=0&VsConference=&VsDivision=&Weight="
    season_stats_headers = {"Host": "stats.nba.com", "Connection": "keep-alive", "Accept": "application/json, text/plain, */*", "x-nba-stats-origin": "stats", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36", "Referer": "https://stats.nba.com/players/traditional/?sort=PTS&dir=-1", "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en;q=0.9"}

    req = urllib.request.Request(url=season_stats_url, headers=season_stats_headers)
    response = urllib.request.urlopen(req)
    data = response.read()
    data = str(gzip.decompress(data), 'utf-8')
    json_file = json.loads(data)

    season_stats = {}
    for player in json_file["resultSets"][0]["rowSet"]:
        player_name = str(player[1])
        del player[0: 4]
        season_stats[player_name] = player

    return season_stats


# converts data into a csv file
def export_data(game_day_matrix, filename):
    with open(filename, 'a', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)  # creating a csv writer object
        csv_writer.writerows(game_day_matrix)  # writing the data rows


def collect_data(date_range, filename):
    start_month = date_range[0].month
    start_year = date_range[0].year

    if start_month > 9:
        season = start_year
        seasonal_stats = get_seasonal_stats(season)
    else:
        season = start_year - 1
        seasonal_stats = get_seasonal_stats(season)

    for date in date_range:
        year = date.year
        month = date.month
        day = date.day

        if month in range(5, 10):
            continue

        changed_season = False
        if month == 10 and changed_season is False:
            season += 1
            seasonal_stats = get_seasonal_stats(season)
            changed_season = True
        elif month != 10:
            changed_season = False

        try:
            games = games_on_date(str(month).zfill(2), str(day).zfill(2), year)
            game_id_list = get_game_ids(games)
            game_day_matrix = []
            games_skipped = 0

            for game_id in game_id_list:
                if str(game_id)[2] is not "2":
                    games_skipped += 1
                    continue
                target_game = NBAGame(game_id, games, seasonal_stats)
                game_data = target_game.compile_data()
                game_day_matrix.append(game_data)

            time = datetime.datetime.now().strftime("%I:%M:%S %p")
            games_added = len(game_id_list) - games_skipped

            export_data(game_day_matrix, filename)
            print(str(month).zfill(2), str(day).zfill(2), year, f": {games_added} games added\t({time})")

        except HTTPError as ex:
            if ex.code == 400:
                break
            else:
                raise


csv_filename = "11-12_data.csv"
start_date = datetime.datetime(2011, 12, 25)
end_date = datetime.datetime(2012, 4, 30)
date_list = pd.date_range(start_date, end_date)
collect_data(date_list, csv_filename)