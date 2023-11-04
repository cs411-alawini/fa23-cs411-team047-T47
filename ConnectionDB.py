import mysql.connector

def getCloseByStops(lat, lon):
  db = mysql.connector.connect(user='root', password='cs411t47db',
                                host='34.28.132.25',
                                database='cs411')

  mycursor = db.cursor()

  # mycursor.execute(sql)

  mycursor.callproc('closeByStop',[lat,lon])

  for result in mycursor.stored_results():
    details = result.fetchall()

  # for det in details:
  #   print(det)

  return details
  mycursor.close()
  db.close()

def getCloseByRoutes(lat, lon):
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

# getCloseByStops(-23.432174,-46.787095)
# # getCloseByRoutes(-23.432174,-46.787095)