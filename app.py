from flask import Flask, request, jsonify, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
# from flask_cors import CORS

import requests
import mysql.connector
from ConnectionDB import *
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 't47'  # Set a secret key for secure sessions


# Assuming you have set up Cloud SQL with a public IP and have whitelisted your server's IP to access it.
# Replace the placeholders with your actual credentials.
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:cs411t47db@34.28.132.25/cs411'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)    

# Database model for Bus_stops
class BusStop(db.Model):
    __tablename__ = 'Bus_stops'  # Ensure this matches your actual table name in MySQL
    stop_id = db.Column(db.Integer, primary_key=True)
    stop_name = db.Column(db.String(256), nullable=False)
    stop_desc = db.Column(db.String(256), nullable=True)
    stop_lat = db.Column(db.Float, nullable=False)
    stop_lon = db.Column(db.Float, nullable=False)

# Database model for Shape
class Shape(db.Model):
    __tablename__ = 'Shape'
    shape_id = db.Column(db.Integer, primary_key=True)
    shape_pt_lat = db.Column(db.Float, nullable=False)
    shape_pt_lon = db.Column(db.Float, nullable=False)
    shape_pt_sequence = db.Column(db.Integer, primary_key=True)
    shape_dist_traveled = db.Column(db.Float, nullable=True)

# Database model for trips
class Trips(db.Model):
    __tablename__ = 'Trips'  # This should match the actual table name in your database
    trip_id = db.Column(db.String(256), primary_key=True)
    route_id = db.Column(db.String(256), nullable=False)
    service_id = db.Column(db.String(5), nullable=False)
    trip_headsign = db.Column(db.String(256), nullable=True)
    direction_id = db.Column(db.Integer)
    shape_id = db.Column(db.Integer, nullable=False)
    
# Database model for arrival
class Arrival(db.Model):
    __tablename__ = 'Arrival'
    trip_id = db.Column(db.String(13), db.ForeignKey('Trips.trip_id'), primary_key=True)
    stop_id = db.Column(db.Integer, db.ForeignKey('Bus_stops.stop_id'), primary_key=True)
    arrival_time = db.Column(db.String(10))
    stop_sequence = db.Column(db.Integer)

# favorites modelZ
class Favorites(db.Model):
    __tablename__ = 'Favorites'
    favorites_id = db.Column(db.Integer, primary_key=True)
    favorite_stops = db.Column(db.Text, nullable=True)
    favorite_routes = db.Column(db.Text, nullable=True)

# User model
class User(db.Model):
    __tablename__ = 'User'
    email = db.Column(db.String(42), primary_key=True)
    username = db.Column(db.String(17), nullable=False)
    password = db.Column(db.String(17), nullable=False)
    favorites_id = db.Column(db.Integer, db.ForeignKey('Favorites.favorites_id'), nullable=True)



# Geocoding API setup
GEOCODING_API_URL = 'https://maps.googleapis.com/maps/api/geocode/json'
GEOCODING_API_KEY = 'AIzaSyBS-S37L58YssF52HQocELjBEI4s1-NSiM'


# get the lat and log for the closeby bus stops
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

    # print(latitude, longitude)

    # At this point, you can send back the latitude and longitude to the frontend
    # or if you need to save this in the database, you can do so here.
    # return latitude and longtitude

    return jsonify({
        'latitude': latitude,
        'longitude': longitude
    })

@app.route('/')
def index():
    # if 'user_id' in session:
    #     return render_template('index.html')
    # return render_template('login.html')
    return render_template('index.html')
    # return redirect(url_for('login.html'))

# register function
@app.route('/register', methods=['POST'])
def register():
    print("hello")
    data = request.get_json()
    print(data)
    existing_user = User.query.filter_by(email=data['email']).limit(1).all()
    # write a query to check if the username already exists
    existing_username = User.query.filter_by(username=data['username']).limit(1).all()
          
    if existing_user:
        return jsonify({"error": "Email already in use"}), 400

    new_user = User(email=data['email'], username=data['username'])
    new_user.password = (data['password'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "Registration successful"}), 201

# login function
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and user.password == (data['password']):
        # Login successful
        return jsonify({"message": "Login successful"}), 200
    else:
        # Login failed
        return jsonify({"error": "Invalid username or password"}), 401

# logout function
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# test function to check if the database is connected
@app.route('/test_db')
def test_db():
    try:
        # Connect to the database using mysql.connector
        db = mysql.connector.connect(user='root', password='cs411t47db',
                                     host='34.28.132.25',
                                     database='cs411')
        mycursor = db.cursor(dictionary=True)  # Use dictionary=True to fetch results as dictionaries
        mycursor.execute("SELECT stop_name, stop_lat, stop_lon \
                            FROM Bus_stops \
                            LIMIT 1")
        
        bus_stop = mycursor.fetchone()

        if bus_stop:
            return jsonify({'message': f"Connected! First bus stop is: {bus_stop['stop_name']} with Latitude: {bus_stop['stop_lat']} and Longitude: {bus_stop['stop_lon']}"})
        else:
            return jsonify({'message': "Connected! But no data in the bus_stops table."})
    except Exception as e:
        return jsonify({'error': f"Database connection failed using mysql.connector: {str(e)}"}), 500

# get the closeby bus stop info and route info
@app.route('/get_bus_stops_and_routes', methods=['POST'])
def get_bus_stops():
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

    # Check if the address in range of the city
    if valid_range(latitude, longitude):
        stops = get_close_by_stops(latitude, longitude)
        routes = get_close_by_routes(latitude, longitude)
        stops_list = [{'stop_name': row[1], 'stop_lat': row[2], 'stop_long': row[3]} for row in stops]
        # stops_list = [{'id': row[0], 'stop_name': row[1], 'stop_lat': row[2], 'stop_long': row[3]} for row in stops]
        routes_list = [{'id': row[0], 'name': row[1]} for row in routes]
        info_list = [{'stopInfo': stops_list, 'routeInfo': routes_list}]
        return jsonify(info_list)
    else:
        return jsonify({'error': 'Not in the city'}), 400
    
# get the route_id and shape to populate the whole routes on the maps
@app.route('/get_route_shapes')
def get_route_shapes():
    try:
        shapes = {}
        shape_ids = [trip.shape_id for trip in Trips.query.all()]
        
        # Get all the points for each shape_id from the Shape table that matches the shape_id from the Trips table
        for shape_id in shape_ids:
            shape_points = Shape.query.filter_by(shape_id=shape_id).order_by(Shape.shape_pt_sequence).all()
            shapes[shape_id] = [{'lat': point.shape_pt_lat, 'lng': point.shape_pt_lon, 'sequence': point.shape_pt_sequence} for point in shape_points]

        # Convert a dictionary with (shape_id as key and all its points as values) to a list to serialize as JSON
        shapes_list = [{'shape_id': shape_id, 'points': points} for shape_id, points in shapes.items()]

        return jsonify(shapes_list)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# get the route_id and shape to populate the route
@app.route('/get_route_and_stops')
def get_route_and_stops():
    shape_id = request.args.get('shape_id')

    print(shape_id)
    route_shape = Shape.query.filter(Shape.shape_id == shape_id).order_by(Shape.shape_pt_sequence).all()
    shape_points = [{'lat': point.shape_pt_lat, 'lng': point.shape_pt_lon} for point in route_shape]

    # Get the stops for the route
    bus_stops = BusStop.query.join(Arrival, BusStop.stop_id == Arrival.stop_id).join(Trips, Arrival.trip_id == Trips.trip_id).filter(Trips.shape_id == shape_id).all()
    stops = [{'stop_name': stop.stop_name, 'stop_lat': stop.stop_lat, 'stop_lon': stop.stop_lon} for stop in bus_stops]


    return jsonify({'route_id': shape_id, 'shape': shape_points, 'stops': stops})



if __name__ == '__main__':
    app.run(debug=True)