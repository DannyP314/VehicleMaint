from google.appengine.ext import db

class User(db.Model):
    username = db.StringProperty(required = True)
    password = db.StringProperty(required = True)


class Vehicle(db.Model):
    year = db.IntegerProperty(required = True)
    make = db.StringProperty(required = True)
    model = db.StringProperty(required = True)
    odometer = db.IntegerProperty()
    lastservice = db.DateProperty()
    vin = db.StringProperty(required = True)
    unit = db.IntegerProperty(required = True)
    maintreq = db.BooleanProperty(required = True)


class Driver(db.Model):
    name = db.StringProperty(required = True)
    employeeid = db.IntegerProperty(required = True)

class MaintRecord(db.Model):
    typeofmaint = db.StringProperty(required = True)
    date = db.DateProperty(required = True)
    description = db.TextProperty()
    vehicle = db.ReferenceProperty(Vehicle, required = True)