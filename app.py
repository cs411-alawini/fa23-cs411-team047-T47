from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
import requests

app = Flask(__name__)

# Assuming you have set up Cloud SQL with a public IP and have whitelisted your server's IP to access it.
# Replace the placeholders with your actual credentials.
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:cs411t47db@34.28.132.25/cs411'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database model for stops
class BusStop(db.Model):
    __tablename__ = 'bus_stops'  # Ensure this matches your actual table name in MySQL
    stop_id = db.Column(db.Integer, primary_key=True)
    stop_name = db.Column(db.String(256), nullable=False)
    stop_desc = db.Column(db.String(256), nullable=True)
    stop_lat = db.Column(db.Float, nullable=False)
    stop_lon = db.Column(db.Float, nullable=False)

# Geocoding API setup
GEOCODING_API_URL = 'https://maps.googleapis.com/maps/api/geocode/json'
GEOCODING_API_KEY = 'AIzaSyBS-S37L58YssF52HQocELjBEI4s1-NSiM'

@app.route('/geocode', methods=['POST'])
def geocode_address():
    data = request.get_json()
    address = data.get('address')

    # Geocode the address using the Google Geocoding API
    response = requests.get(GEOCODING_API_URL, params={
        'address': address,
        'key': GEOCODING_API_KEY
    })

    if response.status_code != 200:
        return jsonify({'error': 'Geocoding API error'}), response.status_code

    geocoding_data = response.json()
    if geocoding_data['status'] != 'OK':
        return jsonify({'error': 'Invalid address'}), 400

    # Extract latitude and longitude
    location = geocoding_data['results'][0]['geometry']['location']
    latitude = location['lat']
    longitude = location['lng']

    # At this point, you can send back the latitude and longitude to the frontend
    # or if you need to save this in the database, you can do so here.

    return jsonify({
        'latitude': latitude,
        'longitude': longitude
    })

@app.route('/')
def index():
    return render_template('index.html')


# testing database connection
@app.route('/test_db')
def test_db():
    try:
        # Try fetching the first record from the BusStop table
        bus_stop = BusStop.query.first()
        if bus_stop:
            return jsonify({'message': f"Connected! First bus stop is: {bus_stop.stop_name}"})
        else:
            return jsonify({'message': "Connected! But no data in the bus_stops table."})
    except Exception as e:
        return jsonify({'error': f"Database connection failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
