import mysql.connector

def getCloseByStops(lat, lon):
  db = mysql.connector.connect(user='root', password='cs411t47db',
                                host='34.28.132.25',
                                database='cs411')

  mycursor = db.cursor()

  # sql = ("CALL `closeByStop`({},{});".format(lat,lon))
  # # address = (lat,lon)

  # mycursor.execute(sql)

  mycursor.callproc('closeByStop',[lat,lon])

  for result in mycursor.stored_results():
    details = result.fetchall()

  # myresult = mycursor.fetchall()

  for det in details:
    print(det)

  
  # for x in myresult:
  #   print(x)

  # print (len(myresult))

getCloseByStops(-23.432174,-46.787095)