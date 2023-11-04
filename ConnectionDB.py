import mysql.connector

db = mysql.connector.connect(user='root', password='cs411t47db',
                              host='34.28.132.25',
                              database='cs411')

mycursor = db.cursor()

mycursor.execute("SELECT * FROM Calendar")

myresult = mycursor.fetchall()

for x in myresult:
  print(x)
  