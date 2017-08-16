import webapp2, cgi, jinja2, os, re
from google.appengine.ext import db
import hashutils
import datetime
from datetime import datetime
import random
from models import User, Vehicle, Driver, MaintRecord, InspectForm

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)

class Handler(webapp2.RequestHandler):
    def renderError(self, error_code):
        self.error(error_code)
        self.response.write("Oops! Something went wrong.")

    def get_maint_needed_vehicles(self):
        vehicle = db.GqlQuery("SELECT * from Vehicle WHERE maintreq = True")
        if vehicle:
            return vehicle

    def get_vehicle_by_unit(self, unit):
        q = Vehicle.all()

        return q.filter('unit =', unit)

    def get_records_by_vehicle(self, vehicle):
        q= MaintRecord.all()

        return q.filter('vehicle =', vehicle)

    def get_user_by_name(self, username):
        user = db.GqlQuery("SELECT * from User WHERE username = '%s'" % username)
        if user:
            return user.get()

    def get_records(self):
        q = MaintRecord.all()
        records = q.run()

        return records

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

    def get_drivers(self):
        query= Driver.all()
        drivers = query.run()
        return drivers

    def get_driver_by_name(self, name):
        query= Driver.all()
        return query.filter('name =', name)

    def get_driver_by_num(self, employeeid):
        query=Driver.all()
        return query.filter('employeeid =', employeeid)

    def get_inspections(self):
        query= InspectForm.all()
        forms = query.run()
        return forms

    def login_user(self, user):
        """ Login a user specified by a User object user """
        user_id = user.key().id()
        self.set_secure_cookie('user_id', str(user_id))

    def logout_user(self):
        """ Logout a user specified by a User object user """
        self.set_secure_cookie('user_id', '')

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        if cookie_val:
            return hashutils.check_secure_val(cookie_val)

    def set_secure_cookie(self, name, val):
        cookie_val = hashutils.make_secure_val(val)
        self.response.headers.add_header('Set-Cookie', '%s=%s; Path=/' % (name, cookie_val))

    def initialize(self, *a, **kw):
        """
            A filter to restrict access to certain pages when not logged in.
            If the request path is in the global auth_paths list, then the user
            must be signed in to access the path/resource.
        """
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.get_by_id(int(uid))

        if not self.user and self.request.path in auth_paths:
            self.redirect('/')


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
        new_vehicle_unit = self.request.get("new-vehicle-unit")

        #new_vehicle_escaped = cgi.escape(new_vehicle, quote=True)
        errors = {}
        existing_unit_num = self.get_vehicle_by_unit(new_vehicle_unit)
        has_error = False

        if not new_vehicle_unit:
            errors['unit_error'] = "Please choose a unit number"
            has_error = True

        elif not existing_unit_num:
            errors['unit_error'] = "A vehicle already has that unit number"
            has_error = True

        elif (new_vehicle_vin and new_vehicle_make and new_vehicle_unit and new_vehicle_year and new_vehicle_model):

            vehicle = Vehicle(year = int(new_vehicle_year), make = new_vehicle_make,
                              model = new_vehicle_model, odometer = int(new_vehicle_odometer),
                              vin = new_vehicle_vin, service = new_vehicle_service, unit = int(new_vehicle_unit),
                              maintreq = False)
            vehicle.put()

            self.redirect('/fleet')
        else:
            has_error = True

            if not new_vehicle_vin:
                errors['vin_error'] = "Please enter VIN"

            if not new_vehicle_make:
                errors['make_error'] = "Please enter a vehicle make"

            if not new_vehicle_year:
                errors['year_error'] = "Please enter a year"

            if not new_vehicle_model:
                errors['model_error'] = "Please enter a model"

        if has_error:
            t = jinja_env.get_template("fleet.html")
            response = t.render(vin=new_vehicle_vin, model=new_vehicle_model, make=new_vehicle_make, unit=new_vehicle_unit, year=new_vehicle_year, service=new_vehicle_service, odometer=new_vehicle_odometer, errors=errors)
            self.response.out.write(response)
        else:
            t = jinja_env.get_template("fleet.html")
            content = t.render(vehicles = self.get_vehicles())
            self.redirect('/fleet')

class EditVehicle(Handler):
    def get(self):
        vehicle = int(self.request.get("edit"))
        edit_vehicle = Vehicle.get_by_id(vehicle)

        t = jinja_env.get_template("vehicleedit.html")
        content = t.render(vehicle=edit_vehicle)
        self.write(content)

    def post(self):
        vehicle = int(self.request.get("vehicle"))
        edit_vehicle = Vehicle.get_by_id(vehicle)
        make = self.request.get("make")
        model = self.request.get("model")
        year = int(self.request.get("year"))
        odometer = int(self.request.get("odometer"))
        vin = self.request.get("vin")

        edit_vehicle.make = make
        edit_vehicle.model = model
        edit_vehicle.year = year
        edit_vehicle.odometer = odometer
        edit_vehicle.vin = vin
        edit_vehicle.put()

        self.redirect('/fleet')



class DeleteVehicle(Handler):
    def post(self):
        vehicle = int(self.request.get("delete"))
        delete_vehicle = Vehicle.get_by_id(vehicle)

        delete_vehicle.delete()

        t = jinja_env.get_template("delete-confirm.html")
        content = t.render(vehicle=delete_vehicle)
        self.write(content)



class ViewVehicle(Handler):
    def get(self, id):

        vehicle = Vehicle.get_by_id(int(id))
        if vehicle:
            t = jinja_env.get_template("vehicle.html")
            response = t.render(vehicle=vehicle)
        else:
            error = "there is no post with id %s" % id
            t = jinja_env.get_template("404.html")
            response = t.render(error=error)

class Maintenance(Handler):
    def get(self):
        vehicles =self.get_maint_needed_vehicles()
        if vehicles:
            t = jinja_env.get_template("maint.html")
            content = t.render(vehicles = vehicles)
        else:
            t = jinja_env.get_template("maint.html")
            content = t.render(vehicles = None)

        self.write(content)

    def post(self):
        maint_vehicle = self.request.get("maint_vehicle")
        vehicle = Vehicle.get_by_id(int(maint_vehicle))

        vehicle.maintreq = False
        vehicle.put()

        self.redirect("/maintenance")

class MaintNeeded(Handler):
    def get(self):
        maintvehicle = self.request.get("vehicle")
        t = jinja_env.get_template("maintneeded.html")
        response = t.render(vehicle = Vehicle.get_by_id(int(maintvehicle)))
        self.write(response)

class Inspection(Handler): #/inspection pass driver through url
    def get(self):
        toInspect = self.request.get("vehicle")
        driver = self.request.get("driver")
        if toInspect:
            self.redirect('/inspect?vehicle={0}&?driver={1}'.format(toInspect,driver))
        else:
            t = jinja_env.get_template("inspectfront.html")
            response = t.render(vehicles = self.get_vehicles(), drivers = self.get_drivers())
            self.write(response)
    def post(self):
        general_checkbox = self.request.get("general")
        oil_checkbox = self.request.get("oil")
        coolant_checkbox = self.request.get("coolant")
        belts_checkbox = self.request.get("belts")
        battery_checkbox = self.request.get("battery")
        engine_checkbox = self.request.get("engine")
        gauges_checkbox = self.request.get("gauges")
        wipers_checkbox = self.request.get("wipers")
        horn_checkbox = self.request.get("horn")
        heat_checkbox = self.request.get("heat")
        mirrors_checkbox = self.request.get("mirrors")
        steering_checkbox = self.request.get("steering")
        brakes_checkbox = self.request.get("brakes")
        ebrake_checkbox = self.request.get("ebrake")
        seatbelts_checkbox = self.request.get("seatbelts")
        safety_checkbox = self.request.get("safety")
        lights_checkbox = self.request.get("lights")
        reflectors_checkbox = self.request.get("reflectors")
        suspension_checkbox = self.request.get("suspension")
        tires_checkbox = self.request.get("tires")
        exhaust_checkbox = self.request.get("exhaust")
        wheels_checkbox = self.request.get("wheels")
        exbrakes_checkbox = self.request.get("exbrakes")
        action_checkbox = self.request.get("action")
        form_num = self.request.get("formnum")
        current_vehicle = self.request.get("vehicle")
        current_driver = self.request.get("driver")

        checkboxes = [general_checkbox, oil_checkbox, coolant_checkbox, belts_checkbox,
                    battery_checkbox, engine_checkbox, gauges_checkbox, wipers_checkbox,
                    horn_checkbox, heat_checkbox, mirrors_checkbox, steering_checkbox,
                    brakes_checkbox, ebrake_checkbox, seatbelts_checkbox, safety_checkbox,
                    lights_checkbox, reflectors_checkbox, suspension_checkbox, tires_checkbox,
                    exhaust_checkbox, wheels_checkbox, exbrakes_checkbox]
        action_items = []
        vehicle = Vehicle.get_by_id(int(current_vehicle))
        driver = Driver.get_by_id(int(current_driver))
        for i in checkboxes:
            if i != "":
                action_items.append(i)
        #if action_items != []:
            #vehicle.maintreq = True
            #vehicle.put()
        #else:
            #form = Inspection(formnum = form_num, items = "No maintenance required",
                               #vehicle = vehicle)
            #form.put()



        t = jinja_env.get_template("inspectdetails.html")
        response = t.render(action_items = action_items, form_num = form_num,
                            vehicle = vehicle, driver=driver)
        self.write(response)

class InspectionForm(Handler): #/inspect
    def get(self):
        current_vehicle = self.request.get("vehicle")
        current_driver = self.request.get("driver")
        vehicle = Vehicle.get_by_id(int(current_vehicle))
        driver = Driver.get_by_id(int(current_driver))
        drivetype = type(current_driver)

        month = str(datetime.today().month)
        year = str(datetime.today().year)
        rand_num = str(random.randint(100,999))
        today = rand_num + month + year

        t = jinja_env.get_template("inspectdetails.html")
        response = t.render(type=drivetype, driver = driver, vehicle = vehicle, date = datetime.now(), formid = today)
        self.write(response)

    def post(self):
        formnum = self.request.get("form")
        details = self.request.get("details")
        items = self.request.POST.getall("items")
        current_vehicle = self.request.get("vehicle")
        vehicle = Vehicle.get_by_id(int(current_vehicle))
        current_driver = self.request.get("driver")
        #driver = Driver.get_by_id(int(current_driver))

        item = []
        for x in items:
            x = str(x)
            item.append(x)

        drivertype=type(current_driver)

        #form = InspectForm(formnum=str(formnum),items=item,details=str(details),vehicle=vehicle, driver=driver)
        #form.put()

        t = jinja_env.get_template("test.html")
        #response = t.render(forms=self.get_inspections())
        response = t.render(driver=current_driver,type=drivertype)
        self.write(response)


#class Test(Handler):
#    def get(self):
#        inspect = self.request.get("vehicle")
#        vehicle = self.get_vehicle_by_id(inspect)
#        t =jinja_env.get_template("test.html")
#        response = t.render(vehicle = vehicle.make)
#        self.write(response)

class Drivers(Handler):
    def get(self):
        t = jinja_env.get_template("drivers.html")
        response = t.render(drivers = self.get_drivers())
        self.write(response)

    def post(self):
        new_name = self.request.get("name")
        new_employeeid = self.request.get("employeeid")

        errors = {}
        existing_driver = self.get_driver_by_name(new_name)
        has_error = False

        if not new_name:
            errors['name_error'] = "Please enter a name."
            has_error = True

        elif (new_employeeid):

            driver = Driver(name=new_name, employeeid = int(new_employeeid))
            driver.put()

            self.redirect('/drivers')
        else:
            has_error = True

            if not new_employeeid:
                errors['employeeid_error'] = "Please enter an Employee ID"


        if has_error:
            t = jinja_env.get_template("drivers.html")
            response = t.render(name=new_name, employeeid=new_employeeid, errors=errors, drivers=self.get_drivers())
            self.response.out.write(response)
        else:
            t = jinja_env.get_template("drivers.html")
            content = t.render(drivers = self.get_drivers())
            self.redirect('/drivers')

class EditDriver(Handler):
    def get(self):
        driver = int(self.request.get("edit"))
        edit_driver = Driver.get_by_id(driver)

        t = jinja_env.get_template("driveredit.html")
        content = t.render(driver=edit_driver)
        self.write(content)

    def post(self):
        driver = int(self.request.get("driver"))
        edit_driver = Driver.get_by_id(driver)
        name = self.request.get("name")
        employeeid = int(self.request.get("employeeid"))

        edit_driver.name = name
        edit_driver.employeeid = employeeid
        edit_driver.put()

        self.redirect('/drivers')



class DeleteDriver(Handler):
    def post(self):
        driver = int(self.request.get("delete"))
        delete_driver = Driver.get_by_id(driver)

        delete_driver.delete()

        t = jinja_env.get_template("delete-confirm.html")
        content = t.render(driver=delete_driver)
        self.write(content)


class MaintRecords(Handler):
    def get(self):
        vehicles = self.get_vehicles()
        records = self.get_records()

        t = jinja_env.get_template("records.html")
        response = t.render(records=records)
        self.write(response)

    def post(self):
        vehicle_id = self.request.get("vehicle")
        vehicle = Vehicle.get_by_id(int(vehicle_id))

        vehicle.maintreq = True
        vehicle.put()

        t = jinja_env.get_template("request-confirmation.html")
        response = t.render(vehicle=vehicle)
        self.write(response)

class NewMaint(Handler):
    def get(self):
        vehicles = self.get_vehicles()

        t=jinja_env.get_template("newmaint.html")
        response= t.render(vehicles=vehicles)
        self.write(response)

    def post(self):
        current_vehicle = self.request.get("vehicle")
        chosen_type = self.request.get("type")
        description = self.request.get("description")
        chosen_vehicle = Vehicle.get_by_id(int(current_vehicle))

        maint = MaintRecord(typeofmaint = chosen_type, description=description, vehicle=chosen_vehicle)
        maint.put()
        chosen_vehicle.lastservic = datetime.today()
        chosen_vehicle.put()

        self.redirect('/records')

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

class Register(Handler):


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

        username = self.validate_username(submitted_username)
        password = self.validate_password(submitted_password)
        verify = self.validate_verify(submitted_password, submitted_verify)

        errors = {}
        existing_user = self.get_user_by_name(username)
        has_error = False

        if existing_user:
            errors['username_error'] = "A user with that username already exists"
            has_error = True
        elif (username and password and verify):

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


        if has_error:
            t = jinja_env.get_template("signup.html")
            response = t.render(username=username, email=email, errors=errors)
            self.response.out.write(response)
        else:
            self.redirect('/fleet')

app = webapp2.WSGIApplication([
    ('/', Index),
    ('/fleet', FleetList),
    ('/maintenance', Maintenance),
    ('/inspection', Inspection),
    ('/inspect', InspectionForm),
    ('/maintneeded', MaintNeeded),
    ('/drivers', Drivers),
    ('/records', MaintRecords),
    ('/newmaint', NewMaint),
    ('/driveredit', EditDriver),
    ('/driverdelete', DeleteDriver),
    ('/vehicleedit', EditVehicle),
    ('/vehicledelete', DeleteVehicle),
    ('/login', Login),
    ('/logout', LogOut),
    ('/register', Register),
    #('/test', Test)
], debug=True)

auth_paths = [
    '/fleet',
    '/maintenance',
    '/inspection',
    '/inspect',
    '/maintneeded',
    '/drivers',
    '/records',
    '/newmaint',
    '/driveredit',
    '/driverdelete',
    '/vehicleedit',
    '/vehicledelete'
]
