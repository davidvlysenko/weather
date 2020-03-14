#Import libraries
from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup

from random import getrandbits
import re
import os
import inspect
import csv



#Stores all information about a given head-to-head matchup  
class game_info():
    
    #Initialize everything as empty string (instead of 0) since some stats are missing or not tracked before certain year 
    def __init__(self, game_year, game_week):      
        self.game_id = getrandbits(32)
        self.year = game_year
        self.week = game_week
        self.away = ""
        self.home = ""
        self.away_score = ""
        self.home_score = ""
        self.temp = ""
        self.forecast = ""
        self.is_dome = False
        self.wind_speed = ""
        self.wind_direct = ""

    
    def add_scores(self, score_string):
        try:
            score_info = score_string.split()[-2:]
            self.away_score = int(score_info[0])
            self.home_score = int(score_info[1])

        except:
            pass


    def add_forecast(self, forecast_string):
        forecast_info = forecast_string.strip().split("f ")
        
        if forecast_info == ["DOME"]:
            self.is_dome = True
            self.temp = 72
            self.forecast = "DOME"
            
        else:
            self.temp = int(forecast_info[0][-2:])
            self.forecast = forecast_info[1]


    def add_wind(self, wind_string):
        wind_info = wind_string.strip().split("m ")
        self.wind_speed = int(wind_info[0][-2:])
        self.wind_direct = wind_info[1]
        
        
        
class Weather_Data():
    
    def __init__(self, year_start, year_end, week_start, week_end):
        self.year_start = year_start
        self.year_end = year_end
        self.week_start = week_start
        self.week_end = week_end
        self.master_list = []
        
        #wind substrings always contain a number followed by an m
        #forecast substrings always contain a number followed by an f
        self.wind_format = [str(integer) + "m " for integer in range(10)] 
        self.forecast_format = [str(integer) + "f " for integer in range(10)] 
        
        #Import from list of all 32 NFL teams from same folder as Python file
        self.data_folder = str(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))) 
        self.team_list = [y for x in list(csv.reader(open(self.data_folder + "\\NFL Team List.csv", "rt", encoding = "utf-8")))
                          for y in x if x != []]
        self.headers = ["game_id", "year", "week", "away", "home", "away_score", "home_score", "temp", "forecast", "is_dome",
                        "wind_speed", "wind_direct"]

        
    #Get text from given url
    def simple_get(self, url):
        try:
            with closing(get(url, stream=True)) as resp:
                if self.is_good_response(resp):
                    return resp.content
                else:
                    return None
    
        except RequestException as e:
            print("Error during requests to {0} : {1}".format(url, str(e)))
            return None
        
    
    #Check whether response is in HTML format
    def is_good_response(self, resp):
        content_type = resp.headers["Content-Type"].lower()
        return (resp.status_code == 200 and content_type is not None and content_type.find("html") > -1)
    
    
    #List of scraped text
    def get_html_text(self, year, week):
        #Go to page
        try:
            html = BeautifulSoup(self.simple_get("http://www.nflweather.com/en/week/%s/week-%s/" %(year, week)), "html.parser")
            
        except:
            
            try:
                #Different url format for some weeks
                html = BeautifulSoup(self.simple_get("http://www.nflweather.com/en/week/%s/week-%s-2/" %(year, week)), "html.parser")
            except:
                print("Error opening %s %s" %(year, week))
    
        return [re.sub(r'[\W_]+', ' ', info.text) for info in html.select("td")] #Clean up
           
    
    #Parse information and add to appropriate instance variable for the head-to-head matchup
    def parse_page(self, year, week, text_list):
        
        home_away_counter = 0
        matchup_list = []
        current_game = game_info(year, week)
        
        #Some matchups are missing scores, wind data, or forecast data,
        #We only know that all matchups start with two teams followed by data
        #Therefore, we need to reverse the list and add data to the class instance until we reach a second team name
        for element in reversed(text_list):
        
            #Check if element contains one of the the 32 NFL teams
            if element.strip() in self.team_list:
                
                #Home team
                if home_away_counter == 0:
                    current_game.home = element.strip()          
                
                #Away team
                else:
                    current_game.away = element.strip()
                    matchup_list.append([info for key, info in vars(current_game).items()])  
                    current_game = game_info(year, week)
                    
                home_away_counter = 1 - home_away_counter     
            
            #Records final score of game
            elif "Final" in element or "Q4" in element:
                current_game.add_scores(element)
                       
            #Split forecast string into temperature and weather, and indicate whether game was held in dome
            elif any(substring in element for substring in self.forecast_format) or "DOME" in element:
                current_game.add_forecast(element)
              
            #Split wind string into wind speed and wind direction
            elif any(substring in element for substring in self.wind_format):
                current_game.add_wind(element)
                
        self.master_list += reversed(matchup_list)
    
    
    #Write CSV file
    def csv_writer(self, data, path):
        with open(path,"wt") as csv_file:
            writer = csv.writer(csv_file, delimiter=",")
            for line in data:
                writer.writerow(line)
        csv_file.close()


    #Run program
    def run(self):
        for year in range(self.year_start, self.year_end):
            for week in range(self.week_start, self.week_end):
                
                print(year, week)
                html_text_list = self.get_html_text(year, week)
                self.parse_page(year, week, html_text_list)
        
        self.csv_writer([self.headers] + self.master_list, self.data_folder + "\\NFL Weather Data.csv")



#Run program - year start, year end, week start, week end - Max (2009, 2019, 1, 18)
data = Weather_Data(2009, 2019, 1, 18)
data.run()
