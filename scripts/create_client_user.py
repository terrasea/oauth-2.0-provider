from database.models import Client, User
from database.DB import DB

#runzeo -a '':6000 -f tmp.fs

client = Client('My Client', 'o9999o', 'secret', 'http://localhost:8080')
user = User('terrasea', 'password', 'James', 'Hurford')
db = DB()
db.put(client.id, client)
db.put(user.id, user)
db.close()
