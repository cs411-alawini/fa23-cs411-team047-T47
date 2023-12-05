from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
# from flask_cors import CORS

import json
import requests
import mysql.connector
from ConnectionDB import *
from werkzeug.security import generate_password_hash, check_password_hash


import logging

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

class CommentHistory(db.Model):
    __tablename__ = 'commentHistory'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100))
    route_id = db.Column(db.String(100))
    crowdedness = db.Column(db.Text)
    safety = db.Column(db.Text)
    temperature = db.Column(db.Text)
    accessibility = db.Column(db.Text)

# Geocoding API setup
GEOCODING_API_URL = 'https://maps.googleapis.com/maps/api/geocode/json'
GEOCODING_API_KEY = 'AIzaSyBS-S37L58YssF52HQocELjBEI4s1-NSiM'


def create_triggers():
    try:
        with db.engine.connect() as connection:
            # Drop the existing trigger if it exists
            connection.execute(text("DROP TRIGGER IF EXISTS after_comment_update;"))

            # Define and execute the CREATE TRIGGER statement for the new BEFORE DELETE trigger
            create_trigger_sql = text("""
                CREATE TRIGGER after_comment_update
                AFTER UPDATE ON Comment
                FOR EACH ROW
                BEGIN
                    IF NEW.safety != OLD.safety OR NEW.accessibility != OLD.accessibility THEN 
                        INSERT INTO commentHistory (email, route_id, crowdedness, safety, temperature, accessibility)
                        VALUES (OLD.email, OLD.route_id, OLD.crowdedness, OLD.safety, OLD.temperature, OLD.accessibility);
                    END IF;
                END;
            """)
            connection.execute(create_trigger_sql)
            print("Trigger created successfully")
    except Exception as e:
        app.logger.error(f"Error creating triggers: {e}")




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
    # routes_query = text("SELECT route_id FROM `Trips` WHERE shape_id = :shape_id")
    # try:
    #     with db.engine.connect() as connection:
    #         route_shape = connection.execute(shape_query, {'shape_id': shape_id}).fetchall()
    #         shape_points = [{'lat': point.shape_pt_lat, 'lng': point.shape_pt_lon} for point in route_shape]

    #         bus_stops = connection.execute(stops_query, {'shape_id': shape_id}).fetchall()
    #         route_id = connection.execute(routes_query, {'shape_id': shape_id}).fetchall()
    #         print(route_id[0][0])
    #         stops = [{'stop_name': stop.stop_name, 'stop_lat': stop.stop_lat, 'stop_lon': stop.stop_lon} for stop in bus_stops]
            
    #         return jsonify({'route_id': shape_id, 'shape': shape_points, 'stops': stops})
    # except Exception as e:
    #     app.logger.error(f"Error in get_route_and_stops: {e}")
    #     return jsonify({'error': 'Database operation failed'}), 500

    routes_query = text("SELECT route_id FROM `Trips` WHERE shape_id = :shape_id")
    try:
        with db.engine.connect() as connection:
            route_shape = connection.execute(shape_query, {'shape_id': shape_id}).fetchall()
            shape_points = [{'lat': point.shape_pt_lat, 'lng': point.shape_pt_lon} for point in route_shape]
            
            bus_stops = connection.execute(stops_query, {'shape_id': shape_id}).fetchall()
            route_id = connection.execute(routes_query, {'shape_id': shape_id}).fetchall()
            stops = [{'stop_name': stop.stop_name, 'stop_lat': stop.stop_lat, 'stop_lon': stop.stop_lon} for stop in bus_stops]
            
            return jsonify({'route_id': route_id[0][0], 'shape_id': shape_id, 'shape': shape_points, 'stops': stops})
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
            print(result)
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



# @app.route('/post_comment', methods=['POST'])
# def post_comment():
#     data = request.get_json()

#     # Check for required fields
#     if 'email' not in data or 'route_id' not in data:
#         return jsonify({'error': 'Missing email or route_id'}), 400

#     email = data['email']
#     route_id = data['route_id']
#     new_crowdedness = data.get('crowdedness', '')
#     new_safety = data.get('safety', '')
#     new_temperature = data.get('temperature', '')
#     new_accessibility = data.get('accessibility', '')

#     try:
#         with db.engine.connect() as connection:
#             # Set the isolation level to 'READ COMMITTED'
#             connection.execution_options(isolation_level="READ COMMITTED")

#             # Begin a new transaction
#             trans = connection.begin()


#             # Advanced Query 1: LEFT JOIN, WHERE clause, and Aggregation
#             existing_comment_query = text("""
#                 SELECT c1.crowdedness, c1.safety, c1.temperature, c1.accessibility
#                 FROM Comment c1
                
#                 WHERE c1.email = :email AND c1.route_id = :route_id
                
#             """)

            
#             existing_comment = connection.execute(existing_comment_query, {'email': email, 'route_id': route_id}).first()
            
#             print("check")
#             print(existing_comment)

#             if existing_comment:

                
#                 # Append new comments to existing ones
#                 updated_crowdedness = json.dumps(json.loads(existing_comment.crowdedness) + [new_crowdedness])
#                 updated_safety = json.dumps(json.loads(existing_comment.safety) + [new_safety])
#                 updated_temperature = json.dumps(json.loads(existing_comment.temperature) + [new_temperature])
#                 updated_accessibility = json.dumps(json.loads(existing_comment.accessibility) + [new_accessibility])

#                 # Update the existing comment
#                 update_comment_query = text("""
#                     UPDATE Comment 
#                     SET crowdedness = :crowdedness, safety = :safety, 
#                         temperature = :temperature, accessibility = :accessibility
#                     WHERE email = :email AND route_id = :route_id;
#                 """)
#                 connection.execute(update_comment_query, {
#                     'email': email, 'route_id': route_id, 
#                     'crowdedness': updated_crowdedness, 'safety': updated_safety, 
#                     'temperature': updated_temperature, 'accessibility': updated_accessibility
#                 })
#             else:
#                 # Advanced Query 2: Conditional Insert with Subquery and Set Operation (Intersection)
#                 insert_comment_query = text("""
#                     INSERT INTO Comment (email, route_id, crowdedness, safety, temperature, accessibility)
#                     SELECT :email, :route_id, :crowdedness, :safety, :temperature, :accessibility
#                     FROM (SELECT 1) AS dummy
#                     WHERE EXISTS (
#                         SELECT 1 FROM User WHERE email = :email
#                         INTERSECT
#                         SELECT 1 FROM Route WHERE route_id = :route_id
#                     );
#                 """)
#                 connection.execute(insert_comment_query, {
#                     'email': email, 'route_id': route_id, 
#                     'crowdedness': json.dumps([new_crowdedness]), 
#                     'safety': json.dumps([new_safety]), 
#                     'temperature': json.dumps([new_temperature]), 
#                     'accessibility': json.dumps([new_accessibility])
#                 })

#             # Commit the transaction
#             trans.commit()
#             return jsonify({'message': 'Comment added or updated successfully'}), 201

#     except Exception as e:
#         # Log the exception for debugging
#         app.logger.error(f"Error in post_comment: {e}")
#         return jsonify({'error': 'Database operation failed'}), 500


@app.route('/post_comment', methods=['POST'])
def post_comment():
    data = request.get_json()
    email = data.get('email')
    route_id = data.get('route_id')
    crowdedness = data.get('crowdedness', '')
    safety = data.get('safety', '')
    temperature = data.get('temperature', '')
    accessibility = data.get('accessibility', '')

    try:
        with db.engine.connect() as connection:
            # Call stored procedure and set @status
            connection.execute(
                text("CALL PostUserComment(:email, :route_id, :crowdedness, :safety, :temperature, :accessibility, @status)"),
                {
                    'email': email, 
                    'route_id': route_id, 
                    'crowdedness': crowdedness, 
                    'safety': safety, 
                    'temperature': temperature, 
                    'accessibility': accessibility
                }
            )

            connection.commit()

            # Get the status from the stored procedure
            status_result = connection.execute(text("SELECT @status")).fetchone()[0]
            app.logger.info(f"Stored Procedure Status: {status_result}")

            if status_result == 0:
                return jsonify({'message': 'Comment processed successfully'}), 200
            elif status_result == 1:
                return jsonify({'message': 'Duplicate comment not added'}), 409
            else:
                return jsonify({'message': 'An unknown error occurred'}), 500
    except Exception as e:
        app.logger.error(f"Error in post_comment: {e}")
        return jsonify({'error': 'Database operation failed', 'detail': str(e)}), 500


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
            print(comments)
            comments_data = {}
            print("end")
            for c in comments:
                route = f"Route {c.route_id}"
                print(route)
                print(comments_data)
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


# Update comment function
@app.route('/update_comment', methods=['POST'])
def update_comment():
    data = request.get_json()
    # print(data)
    email = data['email']
    route_id = data['route_id']
    new_comment = data['comment']
    original_comment = data['originalComment']
    category = data['category'].lower()

    # print('asdfsd')
    # print(email)

    if category not in ['crowdedness', 'safety', 'temperature', 'accessibility']:
        return jsonify({'error': 'Invalid category'}), 400

    try:
        with db.engine.connect() as connection:
            connection.execution_options(isolation_level="READ COMMITTED")
            trans = connection.begin()

            existing_comment_query = text(f"""
                SELECT {category}
                FROM Comment
                WHERE email = :email AND route_id = :route_id;
            """)

            existing_comment_result = connection.execute(existing_comment_query, {'email': email, 'route_id': route_id}).first()
            
            if existing_comment_result and existing_comment_result[0]:
                existing_comments = json.loads(existing_comment_result[0])
                print(existing_comments)
                if original_comment in existing_comments:
                    # Replace original comment with new comment
                    index = existing_comments.index(original_comment)
                    existing_comments[index] = new_comment
                    updated_comments_json = json.dumps(existing_comments)

                    update_comment_query = text(f"""
                        UPDATE Comment 
                        SET {category} = :updated_comments
                        WHERE email = :email AND route_id = :route_id;
                    """)
                    connection.execute(update_comment_query, {'updated_comments': updated_comments_json, 'email': email, 'route_id': route_id})
                else:
                    return jsonify({'error': 'Original comment not found'}), 404
            else:
                return jsonify({'error': 'No existing comment to update'}), 404

            trans.commit()
            return jsonify({'message': 'Comment updated successfully'}), 200

    except Exception as e:
        trans.rollback()
        app.logger.error(f"Error in update_comment: {e}")
        return jsonify({'error': 'Database operation failed', 'detail': str(e)}), 500


# Delete comment function
@app.route('/delete_comment', methods=['POST'])
def delete_comment():
    data = request.get_json()


    # print(data)
    
    if not data:
        return jsonify({'error': 'Request body is empty or not JSON'}), 400
    if 'email' not in data:
        return jsonify({'error': 'Email is missing'}), 400
    if 'route_id' not in data:
        return jsonify({'error': 'Route ID is missing'}), 400
    if 'category' not in data:
        return jsonify({'error': 'Category is missing'}), 400

    email = data['email']
    route_id = data['route_id']
    category = data['category'].lower()

    category = category[:-1]

    # print(category)

    if category not in ['crowdedness', 'safety', 'temperature', 'accessibility']:
        return jsonify({'error': 'Invalid category'}), 400

       # Initialize delete_result outside of try-except block
    delete_result = None

    null_comment = '[""]'

    try:
        with db.engine.connect() as connection:
            delete_query = text(f"""
                UPDATE Comment 
                SET {category} = :null_comment
                WHERE email = :email AND route_id = :route_id
            """)
            app.logger.info(f"Attempting to set category '{category}' to NULL for email '{email}' and route_id '{route_id}'")

            delete_result = connection.execute(delete_query, {'null_comment':null_comment, 'email': email, 'route_id': route_id})

            # delete the row
            check_query = text("""
                SELECT * FROM Comment 
                WHERE email = :email AND route_id = :route_id AND 
                      crowdedness = :null_comment AND safety = :null_comment AND 
                      temperature = :null_comment AND accessibility = :null_comment;
            """)
            
            result = connection.execute(check_query, {'email': email, 'route_id': route_id, 'null_comment':null_comment, 'null_comment':null_comment, 'null_comment':null_comment, 'null_comment':null_comment}).fetchone()
            # print("before trigger")
            if result:
                delete_row_query = text("""
                    DELETE FROM Comment 
                    WHERE email = :email AND route_id = :route_id;
                """)
                connection.execute(delete_row_query, {'email': email, 'route_id': route_id})
                
            
            # commit the result
            connection.commit()

            # print(delete_result)
            # Move the conditional statements inside the try block
            if delete_result.rowcount > 0:
                connection.commit()
                return jsonify({'message': f'{category.title()} comment deleted successfully'}), 200
            else:
                #Check if the category is already NULL for the given email and route_id
                check_query = text(f"""
                    SELECT {category} FROM Comment 
                    WHERE email = :email AND route_id = :route_id
                """)
                existing_category = connection.execute(check_query, {'email': email, 'route_id': route_id}).fetchone()
                if existing_category and existing_category[0] is None:
                    connection.commit()
                    return jsonify({'message': f'No update necessary. {category.title()} comment is already empty'}), 200
                else:
                    return jsonify({'error': 'No comment found for the specified category'}), 404
    except Exception as e:
        detailed_error = str(e)
        app.logger.error(f"Error in delete_comment: {detailed_error}")
        return jsonify({'error': 'Database operation failed', 'detail': detailed_error}), 500
        




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
    json_data = request.get_json()
    trip_id = json_data.get('trip_id')
    print(trip_id)
    schedule_data = get_schedule(trip_id)
    print(schedule_data[0])
    response = jsonify([{'stops': schedule_data[0], 'schedule': schedule_data[1]}])
    return response




if __name__ == '__main__':
    with app.app_context():
        create_triggers()
    app.run(port=8000, debug=True)