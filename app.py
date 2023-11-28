from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
# from flask_cors import CORS

import json
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

# favorites model
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

# Route model
class Route(db.Model):
    __tablename__ = 'Route'
    route_id = db.Column(db.String(9), primary_key=True)
    route_long_name = db.Column(db.String(256), nullable=True)
    route_color = db.Column(db.String(30), nullable=True)
    route_text_color = db.Column(db.String(30), nullable=True)
    fair_id = db.Column(db.String(21), nullable=False)

# Fares model
class Fares(db.Model):
    __tablename__ = 'Fares'
    fare_id = db.Column(db.String(23), primary_key=True)
    price = db.Column(db.Float, nullable=True)
    currency_type = db.Column(db.String(5), nullable=True)
    payment_method = db.Column(db.Integer, nullable=True)
    transfers = db.Column(db.String(3), nullable=True)
    transfer_duration = db.Column(db.Integer, nullable=True)

# Comment model
class Comment(db.Model):
    __tablename__ = 'Comment'
    email = db.Column(db.String(42), primary_key=True)
    route_id = db.Column(db.String(9), primary_key=True)
    crowdedness = db.Column(db.Text, nullable=True)
    safety = db.Column(db.Text, nullable=True)
    temperature = db.Column(db.Text, nullable=True)
    accessibility = db.Column(db.Text, nullable=True)

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

    # Check if the address in range of the city
    if valid_range(latitude, longitude):
        stops = get_close_by_stops(latitude, longitude)
        points = [{'lat': row[2], 'lng': row[3]} for row in stops]
        # stops_dic = {}
        # stops_list = [{'id': row[0], 'name': row[1]} for row in stops]
        for info in stops:
            print(info)

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

# register function
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    check_user_query = text("SELECT * FROM User WHERE email = :email OR username = :username LIMIT 1")
    insert_user_query = text("""
        INSERT INTO User (email, username, password) 
        VALUES (:email, :username, :password)
    """)
    try:
        with db.engine.connect() as connection:
            existing_user = connection.execute(check_user_query, {'email': data['email'], 'username': data['username']}).first()
            if existing_user:
                return jsonify({"error": "Email or username already in use"}), 400
            
            connection.execute(insert_user_query, {
                'email': data['email'], 
                'username': data['username'], 
                'password': data['password']
            })
            connection.commit()
            return jsonify({"message": "Registration successful"}), 201
    except Exception as e:
        app.logger.error(f"Error in register: {e}")
        return jsonify({'error': 'Database operation failed'}), 500
    

# login function
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    sql_query = text("SELECT * FROM User WHERE username = :username")
    try:
        with db.engine.connect() as connection:
            user = connection.execute(sql_query, {'username': data['username']}).first()
            if user and user.password == data['password']:
                return jsonify({"message": "Login successful", "email": user.email}), 200
            else:
                return jsonify({"error": "Invalid username or password"}), 401
    except Exception as e:
        app.logger.error(f"Error in login: {e}")
        return jsonify({'error': 'Database operation failed'}), 500

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
    print(longitude)

    # Check if the address in range of the city
    if valid_range(latitude, longitude):
        stops = get_close_by_stops(latitude, longitude)
        routes = get_close_by_routes(latitude, longitude)
        stops_list = [{'stop_name': row[1], 'stop_lat': row[2], 'stop_lon': row[3]} for row in stops]
        # stops_list = [{'id': row[0], 'stop_name': row[1], 'stop_lat': row[2], 'stop_long': row[3]} for row in stops]
        routes_list = [{'id': row[0]} for row in routes]
        # routes_list = [{'id': row[0], 'name': row[1]} for row in routes]
        info_list = [{'stopInfo': stops_list, 'routeInfo': routes_list}]
        return jsonify(info_list)
    else:
        return jsonify({'error': 'Given address is not in Sao Puolo'}), 400
    

# get the route_id and shape to populate the whole routes on the maps
@app.route('/get_route_shapes')
def get_route_shapes():
    try:
        with db.engine.connect() as connection:
            # Get distinct shape_ids from the Trips table
            shape_ids_query = text("SELECT DISTINCT shape_id FROM Trips")
            shape_ids = connection.execute(shape_ids_query).fetchall()
            
            shapes = {}
            for shape_id_record in shape_ids:
                shape_id = shape_id_record.shape_id
                shape_points_query = text("""
                    SELECT shape_pt_lat, shape_pt_lon, shape_pt_sequence 
                    FROM Shape 
                    WHERE shape_id = :shape_id 
                    ORDER BY shape_pt_sequence
                """)
                shape_points = connection.execute(shape_points_query, {'shape_id': shape_id}).fetchall()
                shapes[shape_id] = [{'lat': point.shape_pt_lat, 'lng': point.shape_pt_lon, 'sequence': point.shape_pt_sequence} for point in shape_points]
            
            shapes_list = [{'shape_id': shape_id, 'points': points} for shape_id, points in shapes.items()]
            return jsonify(shapes_list)
    except Exception as e:
        app.logger.error(f"Error in get_route_shapes: {e}")
        return jsonify({'error': 'Database operation failed'}), 500



# get the route_id and shape to populate the route
@app.route('/get_route_and_stops')
def get_route_and_stops():
    shape_id = request.args.get('shape_id')
    shape_query = text("SELECT * FROM Shape WHERE shape_id = :shape_id ORDER BY shape_pt_sequence")
    stops_query = text("""
        SELECT Bus_stops.stop_name, Bus_stops.stop_lat, Bus_stops.stop_lon 
        FROM Bus_stops 
        JOIN Arrival ON Bus_stops.stop_id = Arrival.stop_id 
        JOIN Trips ON Arrival.trip_id = Trips.trip_id 
        WHERE Trips.shape_id = :shape_id
    """)
    try:
        with db.engine.connect() as connection:
            route_shape = connection.execute(shape_query, {'shape_id': shape_id}).fetchall()
            shape_points = [{'lat': point.shape_pt_lat, 'lng': point.shape_pt_lon} for point in route_shape]
            
            bus_stops = connection.execute(stops_query, {'shape_id': shape_id}).fetchall()
            stops = [{'stop_name': stop.stop_name, 'stop_lat': stop.stop_lat, 'stop_lon': stop.stop_lon} for stop in bus_stops]
            
            return jsonify({'route_id': shape_id, 'shape': shape_points, 'stops': stops})
    except Exception as e:
        app.logger.error(f"Error in get_route_and_stops: {e}")
        return jsonify({'error': 'Database operation failed'}), 500
    

# get route info
@app.route('/get_route_info', methods=['GET'])
def get_route_info():
    route_id = request.args.get('route_id')

    # Construct the SQL query
    sql_query = text("""
        SELECT Route.route_id, Route.route_long_name, Fares.price 
        FROM Route 
        JOIN Fares ON Route.fare_id = Fares.fare_id 
        WHERE Route.route_id = :route_id;
    """)

    # Execute the query
    try:
        with db.engine.connect() as connection:
            result = connection.execute(sql_query, {'route_id': route_id}).first()
            if result:
                return jsonify({
                    'route_id': result.route_id, 
                    'route_long_name': result.route_long_name, 
                    'price': result.price
                })
            else:
                return jsonify({'error': 'Route not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

# comment functions
@app.route('/get_comments', methods=['GET'])
def get_comments():
    route_id = request.args.get('route_id')
    comments_query = text("""
        SELECT email, crowdedness, safety, temperature, accessibility 
        FROM Comment 
        WHERE route_id = :route_id
    """)
    try:
        with db.engine.connect() as connection:
            comments = connection.execute(comments_query, {'route_id': route_id}).fetchall()
            comments_data = [
                {
                    'email': c.email, 
                    'crowdedness': c.crowdedness, 
                    'safety': c.safety, 
                    'temperature': c.temperature, 
                    'accessibility': c.accessibility
                } for c in comments
            ]
            return jsonify(comments_data)
    except Exception as e:
        app.logger.error(f"Error in get_comments: {e}")
        return jsonify({'error': 'Database operation failed'}), 500



@app.route('/post_comment', methods=['POST'])
def post_comment():
    data = request.get_json()

    # Check for required fields
    if 'email' not in data or 'route_id' not in data:
        return jsonify({'error': 'Missing email or route_id'}), 400

    email = data['email']
    route_id = data['route_id']
    new_crowdedness = data.get('crowdedness', '')
    new_safety = data.get('safety', '')
    new_temperature = data.get('temperature', '')
    new_accessibility = data.get('accessibility', '')

    try:
        with db.engine.connect() as connection:
            # Set the isolation level to 'READ COMMITTED'
            connection.execution_options(isolation_level="READ COMMITTED")

            # Begin a new transaction
            trans = connection.begin()


            # Advanced Query 1: LEFT JOIN, WHERE clause, and Aggregation
            existing_comment_query = text("""
                SELECT c1.crowdedness, c1.safety, c1.temperature, c1.accessibility, COUNT(c3.route_id) AS route_comment_count
                FROM Comment c1
                LEFT JOIN Comment c2 ON c1.email = c2.email AND c2.route_id != :route_id
                LEFT JOIN Comment c3 ON c1.route_id = c3.route_id
                WHERE c1.email = :email AND c1.route_id = :route_id AND c2.email IS NULL
                GROUP BY c1.crowdedness, c1.safety, c1.temperature, c1.accessibility
            """)

            
            existing_comment = connection.execute(existing_comment_query, {'email': email, 'route_id': route_id}).first()

            if existing_comment:

                
                # Append new comments to existing ones
                updated_crowdedness = json.dumps(json.loads(existing_comment.crowdedness) + [new_crowdedness])
                updated_safety = json.dumps(json.loads(existing_comment.safety) + [new_safety])
                updated_temperature = json.dumps(json.loads(existing_comment.temperature) + [new_temperature])
                updated_accessibility = json.dumps(json.loads(existing_comment.accessibility) + [new_accessibility])

                # Update the existing comment
                update_comment_query = text("""
                    UPDATE Comment 
                    SET crowdedness = :crowdedness, safety = :safety, 
                        temperature = :temperature, accessibility = :accessibility
                    WHERE email = :email AND route_id = :route_id;
                """)
                connection.execute(update_comment_query, {
                    'email': email, 'route_id': route_id, 
                    'crowdedness': updated_crowdedness, 'safety': updated_safety, 
                    'temperature': updated_temperature, 'accessibility': updated_accessibility
                })
            else:
                # Advanced Query 2: Conditional Insert with Subquery and Set Operation (Intersection)
                insert_comment_query = text("""
                    INSERT INTO Comment (email, route_id, crowdedness, safety, temperature, accessibility)
                    SELECT :email, :route_id, :crowdedness, :safety, :temperature, :accessibility
                    FROM (SELECT 1) AS dummy
                    WHERE EXISTS (
                        SELECT 1 FROM User WHERE email = :email
                        INTERSECT
                        SELECT 1 FROM Route WHERE route_id = :route_id
                    );
                """)
                connection.execute(insert_comment_query, {
                    'email': email, 'route_id': route_id, 
                    'crowdedness': json.dumps([new_crowdedness]), 
                    'safety': json.dumps([new_safety]), 
                    'temperature': json.dumps([new_temperature]), 
                    'accessibility': json.dumps([new_accessibility])
                })

            # Commit the transaction
            trans.commit()
            return jsonify({'message': 'Comment added or updated successfully'}), 201

    except Exception as e:
        # Log the exception for debugging
        app.logger.error(f"Error in post_comment: {e}")
        return jsonify({'error': 'Database operation failed'}), 500

# get comment for each user
@app.route('/get_user_comments', methods=['GET'])
def get_user_comments():
    email = request.args.get('email')  # Assuming user_id is passed as a query parameter
    if not email:
        return jsonify({'error': 'Email is required'}), 400

    comments_query = text("""
        SELECT route_id, crowdedness, safety, temperature, accessibility 
        FROM Comment 
        WHERE email = :email
    """)
    try:
        with db.engine.connect() as connection:
            comments = connection.execute(comments_query, {'email': email}).fetchall()
            comments_data = {}
            for c in comments:
                route = f"Route {c.route_id}"
                if route not in comments_data:
                    comments_data[route] = {'crowdedness': [], 'safety': [], 'temperature': [], 'accessibility': []}
                comments_data[route]['crowdedness'].append(c.crowdedness)
                comments_data[route]['safety'].append(c.safety)
                comments_data[route]['temperature'].append(c.temperature)
                comments_data[route]['accessibility'].append(c.accessibility)
            return jsonify(comments_data)
    except Exception as e:
        app.logger.error(f"Error in get_user_comments: {e}")
        return jsonify({'error': 'Database operation failed'}), 500

@app.route('/get_route_and_trip_info', methods=['GET'])
def get_route_and_trip_info():
    route_id = request.args.get('route_id')

    # Construct the SQL query
    sql_query = text("""
        SELECT Route.route_id, Trips.trip_id, Trips.trip_headsign, Trips.direction_id
        FROM cs411.Route 
        JOIN cs411.Trips ON Trips.route_id = Route.route_id 
        WHERE Route.route_id = :route_id;
    """)

    # Execute the query
    try:
        with db.engine.connect() as connection:
            result = connection.execute(sql_query, {'route_id': route_id}).fetchall()
            if result:
                trips_data = [{
                    'trip_id': row.trip_id,
                    'trip_headsign': row.trip_headsign,
                    'direction_id': row.direction_id
                } for row in result]
                return jsonify({'route_id': route_id, 'trips_data': trips_data})
            else:
                return jsonify({'error': 'Route not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/post_schedule', methods = ['POST'])
def post_schedule():
    data = request.get_json()
    trip_id = data.get('trip_id')

    # Serialize the dictionary to JSON without sorting keys
    json_str = json.dumps(get_schedule(trip_id), sort_keys=False)
    # print(json_str)
    
    # Use jsonify with the serialized JSON string
    response = jsonify(json.loads(json_str)) 
    
    return response



if __name__ == '__main__':
    app.run(port=8000, debug=True)