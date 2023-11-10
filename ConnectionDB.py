import mysql.connector
import math

# Get the new coordinates of the 400 meter boundary of given address
def calculate_new_coordinates(lat, lon, bearing_degrees):
    earth_radius = 6371000
    distance_in_meters = 400

    # Convert latitude and longitude from degrees to radians
    lat = math.radians(lat)
    lon = math.radians(lon)

    # Convert bearing from degrees to radians
    bearing = math.radians(bearing_degrees)

    # Calculate new latitude
    new_lat = math.asin(math.sin(lat) * math.cos(distance_in_meters / earth_radius) +
                       math.cos(lat) * math.sin(distance_in_meters / earth_radius) * math.cos(bearing))

    # Calculate new longitude
    new_lon = lon + math.atan2(math.sin(bearing) * math.sin(distance_in_meters / earth_radius) * math.cos(lat),
                              math.cos(distance_in_meters / earth_radius) - math.sin(lat) * math.sin(new_lat))

    # Convert new latitude and longitude from radians to degrees
    new_lat = math.degrees(new_lat)
    new_lon = math.degrees(new_lon)

    return new_lat, new_lon

def valid_range(lat, lon):
  max_lat = calculate_new_coordinates(lat, lon, 0)[0]
  min_lat = calculate_new_coordinates(lat, lon, 180)[0]
  max_lon = calculate_new_coordinates(lat, lon, 90)[1]
  min_lon = calculate_new_coordinates(lat, lon, 270)[1]

  db = mysql.connector.connect(user='root', password='cs411t47db',
                                host='34.28.132.25',
                                database='cs411')

  mycursor = db.cursor()

  result = mycursor.callproc('inRange',[max_lat, min_lat, max_lon, min_lon, 0])

  if result[4] > 0:
    return True

# Get the close by stops within 400 meter circle of given address
def get_close_by_stops(lat, lon):
  db = mysql.connector.connect(user='root', password='cs411t47db',
                                host='34.28.132.25',
                                database='cs411')

  mycursor = db.cursor()

  mycursor.callproc('closeByStop',[lat,lon])

  for result in mycursor.stored_results():
    details = result.fetchall()

  # for det in details:
  #   print(det)

  return details
  mycursor.close()
  db.close()

# Get the close by routes within 400 meter circle of given address
def get_close_by_routes(lat, lon):
  db = mysql.connector.connect(user='root', password='cs411t47db',
                                host='34.28.132.25',
                                database='cs411')

  mycursor = db.cursor()

  mycursor.callproc('closeByRoutes',[lat,lon])

  for result in mycursor.stored_results():
    details = result.fetchall()

  return details

  mycursor.close()
  db.close()

# get_close_by_routes(-23.439609, -46.807039)
# get_close_by_stops(-23.439609, -46.807039)