from flask import Flask, jsonify
from pymongo import MongoClient
import datetime
import statistics
from bson import ObjectId
from flask_cors import CORS 


app = Flask(__name__)
CORS(app) 
# MongoDB client setup
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
        match = matches_collection.find_one({'_id': ObjectId(match_id)})  # Convert match_id to ObjectId

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

                    # Update goals scored and conceded
                    if team1_name not in historical_matches:
                        historical_matches[team1_name] = {'goals_scored': [], 'goals_conceded': [], 'wins': []}
                    if team2_name not in historical_matches:
                        historical_matches[team2_name] = {'goals_scored': [], 'goals_conceded': [], 'wins': []}

                    historical_matches[team1_name]['goals_scored'].append(team1_goals[0])
                    historical_matches[team1_name]['goals_conceded'].append(team2_goals[0])
                    historical_matches[team2_name]['goals_scored'].append(team2_goals[0])
                    historical_matches[team2_name]['goals_conceded'].append(team1_goals[0])

                    # Determine winning team and update wins count
                    if team1_goals[0] > team2_goals[0]:
                        winning_team = team1_name
                    elif team2_goals[0] > team1_goals[0]:
                        winning_team = team2_name
                    else:
                        winning_team = None  # It's a draw

                    if winning_team:
                        historical_matches[winning_team]['wins'].append(1)

            else:
                # Match is upcoming
                team1_id = match['team1']
                team2_id = match['team2']
                team1 = teams_collection.find_one({'_id': team1_id})
                team2 = teams_collection.find_one({'_id': team2_id})

                if team1 and team2:
                    team1_name = team1['name']
                    team2_name = team2['name']
                    team1_stats = historical_matches.get(team1_name, {'goals_scored': [0], 'goals_conceded': [0], 'wins': [0]})
                    team2_stats = historical_matches.get(team2_name, {'goals_scored': [0], 'goals_conceded': [0], 'wins': [0]})

                    # Predict winning team based on historical statistics
                    team1_avg_goals_scored = statistics.mean(team1_stats['goals_scored']) if team1_stats['goals_scored'] else 0
                    team1_avg_goals_conceded = statistics.mean(team1_stats['goals_conceded']) if team1_stats['goals_conceded'] else 0
                    team1_avg_wins = statistics.mean(team1_stats['wins']) if team1_stats['wins'] else 0

                    team2_avg_goals_scored = statistics.mean(team2_stats['goals_scored']) if team2_stats['goals_scored'] else 0
                    team2_avg_goals_conceded = statistics.mean(team2_stats['goals_conceded']) if team2_stats['goals_conceded'] else 0
                    team2_avg_wins = statistics.mean(team2_stats['wins']) if team2_stats['wins'] else 0

                    # Calculate percentage chance of winning based on historical statistics
                    if team1_avg_wins + team2_avg_wins > 0:
                        percentage_team1_win = (team1_avg_wins / (team1_avg_wins + team2_avg_wins)) * 100
                        percentage_team2_win = (team2_avg_wins / (team1_avg_wins + team2_avg_wins)) * 100
                    else:
                        percentage_team1_win = 50  # Default to 50% if no historical data
                        percentage_team2_win = 50

                    # Simple prediction based on averages
                    if (team1_avg_goals_scored - team1_avg_goals_conceded) > (team2_avg_goals_scored - team2_avg_goals_conceded):
                        predicted_winner = team1_name
                    elif (team2_avg_goals_scored - team2_avg_goals_conceded) > (team1_avg_goals_scored - team1_avg_goals_conceded):
                        predicted_winner = team2_name
                    else:
                        predicted_winner = "Draw"

                    # Predict probable goals for upcoming match
                    if team1_avg_goals_scored > 0 and team2_avg_goals_conceded > 0:
                        predicted_goals_team1 = int(team1_avg_goals_scored * (team2_avg_goals_conceded / team1_avg_goals_scored))
                    else:
                        predicted_goals_team1 = 0

                    if team2_avg_goals_scored > 0 and team1_avg_goals_conceded > 0:
                        predicted_goals_team2 = int(team2_avg_goals_scored * (team1_avg_goals_conceded / team2_avg_goals_scored))
                    else:
                        predicted_goals_team2 = 0

                    # Store upcoming match details with percentage chances
                    upcoming_matches[str(match_id)] = {
                        'team1_name': team1_name,
                        'team2_name': team2_name,
                        'match_date': match_date,
                        'predicted_winner': predicted_winner,
                        'predicted_goals_team1': predicted_goals_team1,
                        'predicted_goals_team2': predicted_goals_team2,
                        'percentage_team1_win': percentage_team1_win,
                        'percentage_team2_win': percentage_team2_win
                        # Add other relevant information for upcoming matches
                    }

    return historical_matches, upcoming_matches

@app.route('/')
def index():
    return "Welcome to Match Prediction System"

@app.route('/historical')
def get_historical_matches():
    historical_matches, _ = collect_match_results()
    return jsonify(historical_matches)

@app.route('/upcoming')
def get_upcoming_matches():
    _, upcoming_matches = collect_match_results()
    return jsonify(upcoming_matches)

if __name__ == '__main__':
    app.run(debug=False,host='0.0.0.0')
