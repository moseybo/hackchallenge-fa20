import json
import csv
from threading import Thread
from time import sleep
import unittest

from userapp_jiayi import app
import requests

# URL pointing to your local dev host
LOCAL_URL = "http://localhost:5000"

# Grab game data and insert into Python objects
category_title_set = set()
games_list = []

with open('data.csv') as csv_file:
    game_reader = csv.reader(csv_file, delimiter=",")
    for index, row in enumerate(game_reader):
        if index > 0:
            games_list.append(
                {
                    "title": row[0],
                    "platform": row[1],
                    "publisher": row[4],
                    "release_date": row[2],
                    "category_id": row[3],
                }
            )
            category_title_set.add(row[3])

category_set = [{"title": category} for category in category_title_set]



# Request endpoint generators
def gen_categories_path(category_id=None):
    base_path = f"{LOCAL_URL}/api/categories"
    return (
        base_path + "/" if category_id is None else f"{base_path}/{str(category_id)}/"
    )

def gen_games_path(game_id=None):
    base_path = f"{LOCAL_URL}/api/games"
    return (
        base_path + "/"
        if game_id is None
        else f"{base_path}/{str(course_id)}/"
    )

# Response handler for unwrapping jsons, provides more useful error messages
def unwrap_response(response, body={}):
    try:
        return response.json()
    except Exception as e:
        req = response.request
        raise Exception(
            f"""
            Error encountered on the following request:

            request path: {req.url}
            request method: {req.method}
            request body: {str(body)}
            exception: {str(e)}

            There is an uncaught-exception being thrown in your
            method handler for this route!
            """
        )

category_dict = {}

class TestRoutes(unittest.TestCase):        
    def test_create_game(self):
        for category in category_set:
            res = requests.post(gen_categories_path(), data=json.dumps(category)) 
            body = unwrap_response(res)
            category = body["data"]   
            id = category["id"]
            title = category["title"]
            category_dict[title] = id
        for game in games_list:
            game["category_id"] = category_dict.get(game["category_id"])
            res = requests.post(gen_games_path(), data=json.dumps(game)) 
            body = unwrap_response(res)

def run_requests():
    sleep(1.5)
    unittest.main()

if __name__ == "__main__":
    thread = Thread(target=run_requests)
    thread.start()
    app.run(host="localhost", port=5000, debug=False)
    
