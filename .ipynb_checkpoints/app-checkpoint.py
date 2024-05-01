from flask import Flask, jsonify
from pymongo import MongoClient
from bson import ObjectId  # Import ObjectId from bson

import datetime

app = Flask(__name__)

# Connect to MongoDB
client = MongoClient('mongodb+srv://admin:lutadmin@lutcluster.hudxy73.mongodb.net/?retryWrites=true&w=majority')
db = client.get_database('test')
teams_collection = db['teams']
results_collection = db['results']
matches_collection = db['matches']

def collect_match_results():
    # Initialize dictionaries for historical and upcoming matches
    historical_matches = {}
    upcoming_matches = {}

    # Get today's date
    today_date = datetime.datetime.utcnow()

    # Retrieve all match results
    all_matches = results_collection.find()

    for result in all_matches:
        # Fetch match details
        match_id = result['match']
        match = matches_collection.find_one({'_id': match_id})

        if match:
            match_date = match.get('date')  # Assuming match date is stored in 'date' field

            # Compare match date with today's date
            if match_date and match_date < today_date:
                # Match is historical
                team1_id = match['team1']
                team2_id = match['team2']
                team1 = teams_collection.find_one({'_id': team1_id})
                team2 = teams_collection.find_one({'_id': team2_id})

                if team1 and team2:
                    team1_name = team1['name']
                    team2_name = team2['name']
                    team1_goals = result.get('team1Goals', [0])
                    team2_goals = result.get('team2Goals', [0])
                    team1_red_cards = result.get('team1Red', 0)
                    team2_red_cards = result.get('team2Red', 0)
                    team1_yellow_cards = result.get('team1Yellow', 0)
                    team2_yellow_cards = result.get('team2Yellow', 0)

                    # Update team statistics dictionary
                    if team1_name not in historical_matches:
                        historical_matches[team1_name] = {'goals_scored': 0, 'goals_conceded': 0}
                    if team2_name not in historical_matches:
                        historical_matches[team2_name] = {'goals_scored': 0, 'goals_conceded': 0}

                    historical_matches[team1_name]['goals_scored'] += team1_goals[0]
                    historical_matches[team1_name]['goals_conceded'] += team2_goals[0]
                    historical_matches[team2_name]['goals_scored'] += team2_goals[0]
                    historical_matches[team2_name]['goals_conceded'] += team1_goals[0]
            else:
                # Match is upcoming
                team1_id = match['team1']
                team2_id = match['team2']
                team1 = teams_collection.find_one({'_id': team1_id})
                team2 = teams_collection.find_one({'_id': team2_id})

                if team1 and team2:
                    upcoming_matches[match_id] = {
                        'team1_name': team1['name'],
                        'team2_name': team2['name'],
                        'match_date': match_date
                        # Add other relevant information for upcoming matches
                    }

    return historical_matches, upcoming_matches

def predict_match_winner(team1_name, team2_name, historical_matches):
    # Retrieve historical data for both teams
    team1_stats = historical_matches.get(team1_name, {'goals_scored': 0, 'goals_conceded': 0})
    team2_stats = historical_matches.get(team2_name, {'goals_scored': 0, 'goals_conceded': 0})

    # Simple prediction based on goals scored and conceded
    team1_score = team1_stats['goals_scored'] - team1_stats['goals_conceded']
    team2_score = team2_stats['goals_scored'] - team2_stats['goals_conceded']

    if team1_score > team2_score:
        return team1_name
    elif team2_score > team1_score:
        return team2_name
    else:
        return "Draw"  # For simplicity, you can handle a draw scenario

@app.route("/")
def home():
    # Call the function collect_match_results()
    historical_matches, upcoming_matches = collect_match_results()

    # Generate predictions for upcoming matches
    upcoming_predictions = []
    for match_id, details in upcoming_matches.items():
        predicted_winner = predict_match_winner(details['team1_name'], details['team2_name'], historical_matches)
        upcoming_predictions.append({
            'match_id': str(match_id),  # Convert ObjectId to string
            'team1_name': details['team1_name'],
            'team2_name': details['team2_name'],
            'match_date': details['match_date'],
            'predicted_winner': predicted_winner
        })

    # Return predictions in JSON format
    return jsonify(upcoming_predictions)

if __name__ == "__main__":
    app.run(debug=True)
