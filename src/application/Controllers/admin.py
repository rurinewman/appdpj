# Controller for the Admin side of things.
# Do NOT run directly. Run main.py in the appdpj/src/ directory instead.

# New routes go here, not in __init__.

from flask import render_template, request, redirect, url_for, session, flash
from application.Models.Admin import *
from application.Models.Food import Food
from application.Models.Restaurant import Restaurant
from application import app, DB_NAME
from application.Models.Transaction import Transaction
from application.adminAddFoodForm import CreateFoodForm
from werkzeug.utils import secure_filename

from application.restaurantCertification import RestaurantCertification
import shelve, os
from application.rest_details_form import RestaurantDetailsForm


# <------------------------- ASHLEE ------------------------------>
@app.route("/admin")
@app.route("/admin/home")
def admin_home():  # ashlee
    return render_template("admin/home.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():  # ashlee
    # if already logged in, what's the point?
    if is_account_id_in_session():
        return redirect(url_for("admin_home"))

    def login_error():
        return redirect("%s?error=1" % url_for("admin_login"))

    if request.method == "POST":
        # That means user submitted login form. Check errors.
        login = Account.login_user(request.form["email"],
                                   request.form["password"])
        if login is not None:
            # user entered correct credentials
            # TODO Link dashboard or something from here
            session["account_id"] = login.account_id
            return redirect(url_for("admin_home"))
        return login_error()
    return render_template("admin/login.html")


@app.route("/admin/register", methods=["GET", "POST"])
def admin_register():  # ashlee
    # if already logged in, what's the point?
    if is_account_id_in_session():
        return redirect(url_for("admin_home"))

    def reg_error(ex=None):
        if ex is not None:
            if Account.EMAIL_ALREADY_EXISTS in ex.args:
                return redirect("%s?emailExists=1" % url_for("admin_register"))
        # Given js validation, shouldn't reach here by a normal user.
        return redirect("%s?error=1" % url_for("admin_register"))

    if request.method == "POST":
        # Check for errors in the form submitted
        if (request.form["tosAgree"] == "agreed"
                and request.form["email"] != ""  # not blank email
                and request.form["name"] != ""  # not blank restaurant name
                and request.form["password"] != ""  # not blank pw
                and request.form["password"] == request.form["passwordAgain"]):
            try:
                account = Admin(request.form["name"], request.form["email"],
                                request.form["password"])
            except Exception as e:
                logging.info("admin_register: error %s" % e)
                return reg_error(e)  # handle errors here
        else:
            return reg_error()

        # Successfully registered
        # TODO: Link dashboard or something
        # TODO: Set flask session
        session["account_id"] = account.account_id
        return redirect(url_for("admin_home"))

    return render_template("admin/register.html")


@app.route("/admin/logout")
def admin_logout():
    if "account_id" in session:
        logging.info("admin_logout(): Admin %s logged out"
                     % gabi(session["account_id"]).get_email())
        del session["account_id"]
    else:
        logging.info("admin_logout(): Failed logout - lag or click twice")

    return redirect(url_for("admin_home"))


# API for updating account, to be called by Account Settings
@app.route("/admin/updateAccount", methods=["GET", "POST"])
def admin_update_account():
    # TODO: Implement admin account soft-deletion
    #       and update restaurant name

    if request.method == "GET":
        return "fail"
    if not is_account_id_in_session():
        return "fail"

    # Check if current password entered was correct
    if not is_account_id_in_session() \
            .check_password_hash(request.form["updateSettingsPw"]):
        return "Current Password is Wrong"

    response = ""
    if "changeEmail" in request.form:
        if request.form["changeEmail"] != "":
            result = (is_account_id_in_session()
                      .set_email(request.form["changeEmail"]))
            if result == Account.EMAIL_CHANGE_SUCCESS:
                response = ("%sSuccessfully updated email<br>" % response)
            elif result == Account.EMAIL_CHANGE_ALREADY_EXISTS:
                response = ("%sFailed updating email, Email already Exists<br>"
                            % response)
            elif result == Account.EMAIL_CHANGE_INVALID:
                response = ("%sFailed updating email, email is Invalid<br>"
                            % response)

    if "changePw" in request.form:
        if request.form["changePw"] != request.form["changePwConfirm"]:
            response = ("%sConfirm Password does not match Password<br>"
                        % response)
        elif request.form["changePw"] != "":
            is_account_id_in_session() \
                .set_password_hash(request.form["changePw"])
            response = "%sSuccessfully updated Password<br>" % response

    return response


# IAIIS - is logged in?
def is_account_id_in_session() -> Account or None:  # for flask
    if "account_id" in session:
        # account value exists in session, check if admin account active
        if Admin.check_active(gabi(session["account_id"])) is not None:
            logging.info(
                "IAIIS: Account id of %s is active and inside session" %
                session["account_id"])
            return gabi(session["account_id"])
    else:
        logging.info("IAIIS: Account id is NOT inside session or disabled")
    return None


# Get account by ID
def gabi(account_id) -> Account:  # for flask
    return Account.get_account_by_id(account_id)


# Get ADMIN account by ID
# def gaabi(account_id):  # for our internal use to make other Flask functions
#     return Admin.get_account_by_id(account_id)


def get_restaurant_name_by_id(restaurant_id):
    restaurant_account = gabi(restaurant_id)
    return getattr(restaurant_account, "restaurant_name", None)


# Used for the Account Settings pane.
def get_account_email(account: Account):
    try:
        return account.get_email()
    except Exception as e:
        logging.info(e)
        return "ERROR"


# TODO; store Flask session info in shelve db

# Activate global function for jinja
app.jinja_env.globals.update(is_account_id_in_session=is_account_id_in_session)
# app.jinja_env.globals.update(gabi=gabi)
app.jinja_env.globals.update(
    get_restaurant_name_by_id=get_restaurant_name_by_id)
app.jinja_env.globals.update(get_account_email=get_account_email)


# <------------------------- CLARA ------------------------------>
# APP ROUTE TO FOOD MANAGEMENT clara
@app.route("/admin/foodManagement")
def food_management():
    food_dict = {}
    with shelve.open("foodypulse", "c") as db:
        try:
            if 'food' in db:
                food_dict = db['food']
            else:
                db['food'] = food_dict
        except Exception as e:
            logging.error("create_food: error opening db (%s)" % e)

    # storing the food keys in food_dict into a new list for displaying and deleting
    food_list = []
    for key in food_dict:
        food = food_dict.get(key)
        food_list.append(food)

    # food_dict = {}
    # food_list = []
    # with shelve.open(DB_NAME, 'c') as db:
    #     if "food" in db:
    #         food_list = db['food']
    #     else:
    #         for key in food_dict:
    #             food = food_dict.get(key)
    #             food_list.append(food)

    return render_template('admin/foodManagement.html', count=len(food_list), food_list=food_list)


MAX_SPECIFICATION_ID = 5  # for adding food
MAX_TOPPING_ID = 8


# ADMIN FOOD FORM clara
@app.route('/admin/addFoodForm', methods=['GET', 'POST'])
def create_food():
    create_food_form = CreateFoodForm(request.form)

    # get specifications as a List, no WTForms
    def get_specs() -> list:
        specs = []

        # do specifications exist in first place?
        for i in range(MAX_SPECIFICATION_ID + 1):
            if "specification%d" % i in request.form:
                specs.append(request.form["specification%d" % i])
            else:
                break

        logging.info("create_food: specs is %s" % specs)
        return specs

        # get toppings as a List, no WTForms

    def get_top() -> list:
        top = []

        # do toppings exist in first place?
        for i in range(MAX_TOPPING_ID + 1):
            if "topping%d" % i in request.form:
                top.append(request.form["topping%d" % i])
            else:
                break

        logging.info("create_food: top is %s" % top)
        return top

    # using the WTForms way to get the data
    if request.method == 'POST' and create_food_form.validate():
        food_dict = {}
        with shelve.open("foodypulse", "c") as db:
            try:
                if 'food' in db:
                    food_dict = db['food']
                else:
                    db['food'] = food_dict
            except Exception as e:
                logging.error("create_food: error opening db (%s)" % e)

            # Create a new food object
            food = Food(request.form["image"], create_food_form.item_name.data,
                        create_food_form.description.data,
                        create_food_form.price.data, create_food_form.allergy.data)

            food.specification = get_specs()  # set specifications as a List
            food.topping = get_top()  # set topping as a List
            food_dict[food.get_food_id()] = food  # set the food_id as key to store the food object
            db['food'] = food_dict

        # writeback
        with shelve.open("foodypulse", 'c') as db:
            db['food'] = food_dict

        return redirect(url_for('admin_home'))

    return render_template('admin/addFoodForm.html', form=create_food_form,
                           MAX_SPECIFICATION_ID=MAX_SPECIFICATION_ID,
                           MAX_TOPPING_ID=MAX_TOPPING_ID, )


@app.route('/deleteFood/<int:id>', methods=['POST'])
def delete_food(id):
    food_dict = {}
    with shelve.open("foodypulse", 'c') as db:
        food_dict = db['food']
        food_dict.pop(id)
        db['food'] = food_dict

    return redirect(url_for('food_management'))


@app.route('/updateFood/<int:id>/', methods=['GET', 'POST'])

#save new specification and list

def update_food(id):
    update_food_form = CreateFoodForm(request.form)

    if request.method == 'POST' and update_food_form.validate():
        food_dict = {}
        with shelve.open("foodypulse", 'w') as db:
            food_dict = db['food']

            food = food_dict.get(id)
            food.set_name(update_food_form.item_name.data)
            food.set_description(update_food_form.description.data)
            food.set_price(update_food_form.price.data)
            food.set_allergy(update_food_form.allergy.data)

            db['food'] = food_dict

        return redirect(url_for('food_management'))
    else:
        food_dict = {}
        with shelve.open("foodypulse", 'r') as db:
            food_dict = db['food']

        food = food_dict.get(id)
        update_food_form.item_name.data = food.get_item_name()
        update_food_form.description.data = food.get_description()
        update_food_form.price.data = food.get_price()
        update_food_form.allergy.data = food.get_allergy()

        return render_template('updateFood.html', form=update_food_form)


# <------------------------- YONGLIN ------------------------------>
@app.route("/admin/transaction")
def admin_transaction():
    # creating a shelve file with dummy data
    transaction_dict = {'1': ['Yong Lin', 'Delivery', '60.40', 'SPAGETIT', '1'],
                        '2': ['Yuen Loong', 'Dine-in', '40.35', 'SPAGETIT', '2']}

    # 1: transaction no. ; <user_id> ; <option> ; <price> ; <coupons> , <rating>
    # TODO: associate an transaction_id as transaction number as key
    # TODO: input the details of the transactions (eg userid, price, option, etc)

    # below code is only usable when we use nested dictionary
    for key, value in transaction_dict.items():  # for every transaction
        print(key, ":", value, "\n")
    #     for i in value:
    #         print(i +":", value[i])

    with shelve.open("transactions", "c") as db:
        try:
            if 'shop_transactions' in db:
                transaction_dict = db['shop_transactions']
            else:
                db['shop_transactions'] = transaction_dict
        except Exception as e:
            logging.error("read_transaction: error opening db (%s)" % e)

    # reading the shelve
    with shelve.open("transactions", "c") as db:
        try:
            print(db['shop_transactions'])  # debug
            if 'shop_transactions' in db:
                transaction_dict = db['shop_transactions']
            else:
                db['shop_transactions'] = transaction_dict
        except Exception as e:
            logging.error("read_transaction: error opening db (%s)" % e)

        transaction_list = []
        for key in transaction_dict:
            transaction = transaction_dict.get(key)
            transaction_list.append(transaction)

            print(transaction)
        print(transaction_list)

    return render_template("admin/transaction.html", count=len(transaction_list),
                           transaction_list=transaction_list)


# certification -- xu yong lin
# UPLOAD_FOLDER = 'application/static/restaurantCertification'  # where the
# files are stored to
# ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
#
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#
#
# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in
#     ALLOWED_EXTENSIONS
path = os.getcwd()

UPLOAD_CERT = os.path.join(path, 'uploads')

app.config['UPLOAD_CERT'] = UPLOAD_CERT


@app.route("/admin/certification", methods=['GET', 'POST'])
def admin_certification():
    # set upload directory path
    certification_form = RestaurantCertification()
    if certification_form.validate_on_submit():
        # assets_dir = os.path.join(
        #     os.path.dirname(app.instance_path), 'assets'
        # )
        hygiene = certification_form.hygiene_cert.data
        halal = certification_form.halal_cert.data
        vegetarian = certification_form.vegetarian_cert.data
        vegan = certification_form.vegan_cert.data

        halaldoc_name = secure_filename(halal.filename)
        vegetariandoc_name = secure_filename(vegetarian.filename)
        vegandoc_name = secure_filename(vegan.filename)

        # document save
        # halal.save(os.path.join(app.config['UPLOAD_FOLDER'], halaldoc_name))
        # TODO: SAVING OF FILE
        # TODO: DISPLAYING OF AVAILABLE FILES UNDER myrestaurant
        # todo: updating of cert under myrestaurant

        # halal.save(os.path.join('/application/static/restaurantCertification', halaldoc_name))
        # vegetarian.save(
        #     os.path.join('/application/static/restaurantCertification', vegetariandoc_name))
        # vegan.save(os.path.join('/application/static/restaurantCertification', vegandoc_name))

        flash('Document uploaded successfully')

        # return redirect(url_for('admin_myrestaurant'))

    return render_template("admin/certification.html",
                           certification_form=certification_form)


# <------------------------- RURI ------------------------------>
@app.route('/admin/myRestaurant', methods=['GET', 'POST'])
def admin_myrestaurant():  # ruri

    restaurant_details_form = RestaurantDetailsForm(request.form)
    restaurants_dict = {}
    if request.method == 'POST' and restaurant_details_form.validate():
        db = shelve.open(DB_NAME, 'c')
        try:
            restaurants_dict = db['Restaurants']
        except Exception as e:
            logging.error("Error in retrieving Restaurants from "
                          "restaurants.db (%s)" % e)

        restaurant = Restaurant(request.form["rest_logo"],
                                # request.form["alltasks"],
                                restaurant_details_form.rest_name.data,
                                restaurant_details_form.rest_contact.data,
                                restaurant_details_form.rest_hour_open.data,
                                restaurant_details_form.rest_hour_close.data,
                                restaurant_details_form.rest_address1.data,
                                restaurant_details_form.rest_address2.data,
                                restaurant_details_form.rest_postcode.data,
                                restaurant_details_form.rest_desc.data,
                                restaurant_details_form.rest_bank.data,
                                restaurant_details_form.rest_del1.data,
                                restaurant_details_form.rest_del2.data,
                                restaurant_details_form.rest_del3.data,
                                restaurant_details_form.rest_del4.data,
                                restaurant_details_form.rest_del5.data)
        restaurants_dict[restaurant.name] = restaurant
        db['Restaurants'] = restaurants_dict

        db.close()

    return render_template("admin/restaurant.html", form=restaurant_details_form)


# #
# @app.route('admin/myrestaurant', methods=['GET', 'POST'])
# def create_customer():
#     create_customer_form: CreateCustomerForm = CreateCustomerForm(request.form)
#     if request.method == 'POST' and create_customer_form.validate():
#         customers_dict = {}
#         db = shelve.open('customer.db', 'c')
#
#         try:
#             customers_dict = db['Customers']
#         except:
#             print("Error in retrieving Customers from customer.db.")
#
#         customer = Customer.Customer(create_customer_form.first_name.data, create_customer_form.last_name.data,
#                                      create_customer_form.gender.data, create_customer_form.membership.data,
#                                      create_customer_form.remarks.data, create_customer_form.email.data,
#                                      create_customer_form.date_joined.data,
#                                      create_customer_form.address.data, )
#         customers_dict[customer.get_customer_id()] = customer
#         db['Customers'] = customers_dict
#
#         db.close()
#
#         return redirect(url_for('home'))
#     return render_template('includes/createCustomer.html', form=create_customer_form)


@app.route("/admin/dashboard")
def dashboard():  # ruri
    return render_template("admin/dashboard.html")
