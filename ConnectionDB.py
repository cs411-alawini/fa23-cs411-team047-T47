import mysql.connector
import math
from datetime import datetime
import numpy as np

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
  
  mycursor.close()
  db.close()

  return details

# Get the close by routes within 400 meter circle of given address
def get_close_by_routes(lat, lon):
  db = mysql.connector.connect(user='root', password='cs411t47db',
                                host='34.28.132.25',
                                database='cs411')

  mycursor = db.cursor()

  mycursor.callproc('closeByRoutes',[lat,lon])

  for result in mycursor.stored_results():
    details = result.fetchall()

  mycursor.close()
  db.close()

  return details


# Get the whole schedule for a route toward a direction (trip)
def get_schedule(trip_id):
  db = mysql.connector.connect(user='root', password='cs411t47db',
                                host='34.28.132.25',
                                database='cs411')

  mycursor = db.cursor()
  
  # To get the number of freqency per this trip
  result = mycursor.callproc('frequency',[trip_id, 0])
  freq_num = result[1]

  # To get the number of stops per this trip
  result = mycursor.callproc('stopNum',[trip_id, 0])
  stop_num = result[1]

  schedule = np.zeros([freq_num + 1,stop_num])
  schedule = schedule.astype('str') 

  f_count = 0

  s_count = 0

  # To get the list of stop names in order
  mycursor.callproc('stopName',[trip_id])

  for result in mycursor.stored_results():
    details = result.fetchall()

  for det in details:
    schedule[0][s_count] = det[0]
    s_count += 1

  mycursor.callproc('schedule',[trip_id])

  # To put the schedule data in 
  for result in mycursor.stored_results():
    details = result.fetchall()

  for det in details:
    if (det[1] == 1):
      f_count += 1
    schedule[f_count,det[1]-1] = str(det[0])

  mycursor.close()
  db.close()

  return schedule

# get_close_by_routes(-23.439609, -46.807039)
# get_schedule('1012-10-0')