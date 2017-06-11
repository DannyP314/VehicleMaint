import webapp2, cgi, jinja2, os, re
from google.appengine.ext import db
import hashutils

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)

class User(db.Model):
    """ Represents a user on our site """
    username = db.StringProperty(required = True)
    password = db.StringProperty(required = True)


class Vehicle(db.Model):
    """ Represents a movie that a user wants to watch or has watched """
    year = db.IntegerProperty(required = True)
    make = db.StringProperty(required = True)
    model = db.StringProperty(required = True)
    odometer = db.IntegerProperty()
    lastservice = db.DateProperty()
    vin = db.StringProperty(required = True)


class Driver(db.Model):
    name = db.StringProperty(required = True)
    employeeid = db.IntegerProperty(required = True)
    startdate = db.DateProperty()


class Handler(webapp2.RequestHandler):
    def renderError(self, error_code):
        """ Sends an HTTP error code and a generic "oops!" message to the client. """
        self.error(error_code)
        self.response.write("Oops! Something went wrong.")

    def get_vehicle_by_id(self, id):
        vehicle_id = db.GqlQuery("SELECT * from Vehicle WHERE ID = '%s'" % id)
        if vehicle_id:
            return vehicle_id.get()

    def get_user_by_name(self, username):
        """ Given a username, try to fetch the user from the database """
        user = db.GqlQuery("SELECT * from User WHERE username = '%s'" % username)
        if user:
            return user.get()

    def read_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        if cookie_val:
            return hashutils.check_secure_val(cookie_val)

    def set_cookie(self, name, val):
        cookie_val = hashutils.make_secure_val(val)
        self.response.headers.add('Set-Cookie', '%s=%s; Path=/' % (name, cookie_val))

    def login_user(self, user):
        user_id = user.key().id()
        self.set_cookie('user_id', str(user_id))

    def logout_user(self):
        self.set_cookie('user_id', '')

    def write(self, *a, **kw):
        self.response.write(*a, **kw)

    def get_vehicles(self):
        query = Vehicle.all()
        vehicles = query.run()
        return vehicles


class Index(Handler):
    def get(self):
        t = jinja_env.get_template("main.html")
        response = t.render()
        self.write(response)

class FleetList(Handler):
    def get(self):
        t = jinja_env.get_template("fleet.html")
        content = t.render(vehicles = self.get_vehicles())
        self.write(content)

    def post(self):
        new_vehicle_make = self.request.get("new-vehicle-make")
        new_vehicle_model = self.request.get("new-vehicle-model")
        new_vehicle_odometer = self.request.get("new-vehicle-odometer")
        new_vehicle_vin = self.request.get("new-vehicle-vin")
        new_vehicle_year = self.request.get("new-vehicle-year")
        new_vehicle_service = self.request.get("new-vehicle-service")

        #new_vehicle_escaped = cgi.escape(new_vehicle, quote=True)

        vehicle = Vehicle(year = int(new_vehicle_year), make = new_vehicle_make,
                          model = new_vehicle_model, odometer = int(new_vehicle_odometer),
                          vin = new_vehicle_vin, service = new_vehicle_service)
        vehicle.put()
        t = jinja_env.get_template("fleet.html")
        content = t.render(vehicle = vehicle)
        self.write(content)

class Maintenance(Handler):
    def get(self):
        t = jinja_env.get_template("maint.html")
        response = t.render()
        self.write(response)

class Inspection(Handler):
    def get(self):
        toInspect = self.request.get("vehicle")
        if toInspect:
            self.redirect('/inspect')
        else:
            t = jinja_env.get_template("inspectfront.html")
            response = t.render(vehicles = self.get_vehicles())
            self.write(response)

class InspectionForm(Handler):
    def get(self):
        inspect = self.request.get("vehicle")
        vehicle = self.get_vehicle_by_id(inspect)
        t = jinja_env.get_template("inspect.html")
        response = t.render(vehicle = vehicle)
        self.write(response)

class MaintNeeded(Handler):
    def get(self):
        t = jinja_env.get_template("maintneeded.html")
        response = t.render()
        self.write(response)

class Drivers(Handler):
    def get(self):
        t = jinja_env.get_template("drivers.html")
        response = t.render()
        self.write(response)

class MaintRecords(Handler):
    def get(self):
        t = jinja_env.get_template("records.html")
        response = t.render()
        self.write(response)

class SignupHandler(Handler):

    def validate_username(self, username):
        USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
        if USER_RE.match(username):
            return username
        else:
            return ""

    def validate_password(self, password):
        PWD_RE = re.compile(r"^.{3,20}$")
        if PWD_RE.match(password):
            return password
        else:
            return ""

    def validate_verify(self, password, verify):
        if password == verify:
            return verify

    def validate_email(self, email):

        # allow empty email field
        if not email:
            return ""

        EMAIL_RE = re.compile(r"^[\S]+@[\S]+.[\S]+$")
        if EMAIL_RE.match(email):
            return email

    def get(self):
        t = jinja_env.get_template("signup.html")
        response = t.render(errors={})
        self.response.out.write(response)

    def post(self):
        """
            Validate submitted data, creating a new user if all fields are valid.
            If data doesn't validate, render the form again with an error.

            This code is essentially identical to the solution to the Signup portion
            of the Formation assignment. The main modification is that we are now
            able to create a new user object and store it when we have valid data.
        """

        submitted_username = self.request.get("username")
        submitted_password = self.request.get("password")
        submitted_verify = self.request.get("verify")
        submitted_email = self.request.get("email")

        username = self.validate_username(submitted_username)
        password = self.validate_password(submitted_password)
        verify = self.validate_verify(submitted_password, submitted_verify)
        email = self.validate_email(submitted_email)

        errors = {}
        existing_user = self.get_user_by_name(username)
        has_error = False

        if existing_user:
            errors['username_error'] = "A user with that username already exists"
            has_error = True
        elif (username and password and verify and (email is not None) ):

            # create new user object and store it in the database
            pw_hash = hashutils.make_pw_hash(username, password)
            user = User(username=username, pw_hash=pw_hash)
            user.put()

            # login our new user
            self.login_user(user)
        else:
            has_error = True

            if not username:
                errors['username_error'] = "That's not a valid username"

            if not password:
                errors['password_error'] = "That's not a valid password"

            if not verify:
                errors['verify_error'] = "Passwords don't match"

            if email is None:
                errors['email_error'] = "That's not a valid email"

        if has_error:
            t = jinja_env.get_template("signup.html")
            response = t.render(username=username, email=email, errors=errors)
            self.response.out.write(response)
        else:
            self.redirect('/fleet')

class Login(Handler):
    def render_login_form(self, error=""):
        """ Render the login form with or without an error, based on parameters """
        t = jinja_env.get_template("login.html")
        response = t.render(error=error)
        self.response.out.write(response)

    def get(self):
        self.render_login_form()

    def post(self):
        submitted_username = self.request.get("username")
        submitted_password = self.request.get("password")

        user = self.get_user_by_name(submitted_username)

        if not user:
            self.render_login_form(error="Invalid username")
        elif hashutils.valid_pw(submitted_username, submitted_password, user.pw_hash):
            self.login_user(user)
            self.redirect('/')
        else:
            self.render_login_form(error="Invalid password")

class LogOut(Handler):
    def get(self):
        self.logout_user()
        self.redirect('/')


app = webapp2.WSGIApplication([
    ('/', Index),
    ('/fleet', FleetList),
    ('/maintenance', Maintenance),
    ('/inspection', Inspection),
    ('/inspect', InspectionForm),
    ('/maintneeded', MaintNeeded),
    ('/drivers', Drivers),
    ('/records', MaintRecords),
    ('/login', Login),
    ('/logout', LogOut)
], debug=True)