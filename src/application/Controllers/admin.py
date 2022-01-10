# Controller for the Admin side of things.
# Do NOT run directly. Run main.py in the appdpj/src/ directory instead.

# New routes go here, not in __init__.

from flask import render_template, request, redirect, url_for, session, flash
from application.Models.Admin import *
from application.Models.Certification import Certification
from application.Models.Food import Food
from application.Models.Restaurant import Restaurant
from application import app, DB_NAME
from application.Models.Transaction import Transaction
from application.adminAddFoodForm import CreateFoodForm

from application.restaurantCertification import DocumentUploadForm
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

    return render_template('admin/foodManagement.html',
                           food_list=food_list)


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
# save new specification and list

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


# <------------------------- YONG LIN ------------------------------>
# YL: for transactions -- creating of dummy data
@app.route("/admin/transaction/createExampleTransactions")
def create_example_transactions():
    # WARNING - Overrides ALL transactions in the db!
    transaction_list = []

    # creating a shelve file with dummy data
    # 1: <account id> ; <user_id> ; <option> ; <price> ; <coupons> , <rating>
    t1 = Transaction()
    t1.account_name = 'Yong Lin'
    t1.set_option('Delivery')
    t1.set_price(50.30)
    t1.set_used_coupons('SPAGETIT')
    t1.set_ratings(2)
    transaction_list.append(t1)

    t2 = Transaction()  # t2
    t2.account_name = 'Ching Chong'
    t2.set_option('Dine-in')
    t2.set_price(80.90)
    t2.set_used_coupons('50PASTA')
    t2.set_ratings(5)
    transaction_list.append(t2)

    t3 = Transaction()  # t3
    t3.account_name = 'Hosea'
    t3.set_option('Delivery')
    t3.set_price(20.10)
    t3.set_used_coupons('50PASTA')
    t3.set_ratings(1)
    transaction_list.append(t3)

    t4 = Transaction()  # t4
    t4.account_name = 'Clara'
    t4.set_option('Delivery')
    t4.set_price(58.30)
    t4.set_used_coupons('SPAGETIT')
    t4.set_ratings(2)
    transaction_list.append(t4)

    t5 = Transaction()  # t5
    t5.account_name = 'Ruri'
    t5.set_option('Dine-in')
    t5.set_price(80.90)
    t5.set_used_coupons('50PASTA')
    t5.set_ratings(3)
    transaction_list.append(t5)

    t6 = Transaction()  # t6
    t6.account_name = 'Ashlee'
    t6.set_option('Delivery')
    t6.set_price(100.10)
    t6.set_used_coupons('50PASTA')
    t6.set_ratings(2)
    transaction_list.append(t6)

    t7 = Transaction()
    t7.account_name = 'Hello'
    t7.set_option('Dine-in')
    t7.set_price(10.90)
    t7.set_used_coupons('50PASTA')
    t7.set_ratings(4)
    transaction_list.append(t7)

    # writing to the database
    with shelve.open(DB_NAME, "c") as db:
        try:
            db['shop_transactions'] = transaction_list
        except Exception as e:
            logging.error("create_example_transactions: error writing to db (%s)" % e)

    return redirect(url_for("admin_transaction"))


# YL: for transactions -- reading of data and displaying (R in CRUD)
@app.route("/admin/transaction")
def admin_transaction():
    # read transactions from db
    with shelve.open(DB_NAME, 'c') as db:
        if 'shop_transactions' in db:
            transaction_list = db['shop_transactions']
            print(db['shop_transactions'])
            logging.info("admin_transaction: reading from db['shop_transactions']"
                         ", %d elems" % len(db["shop_transactions"]))
        else:
            logging.info("admin_transaction: nothing found in db, starting empty")
            transaction_list = []

    def get_transaction_by_id(transaction_id):  # debug
        for transaction in transaction_list:
            if transaction_id == transaction.count_id:
                return transaction

    return render_template("admin/transaction.html", count=len(transaction_list),
                           transaction_list=transaction_list)


# YL: for transactions -- soft delete (D in CRUD)
# soft delete -> restaurant can soft delete transactions jic if the transaction is cancelled
@app.route('/admin/transaction/delete/<transaction_id>')
def delete_transaction(transaction_id):
    transaction_id = int(transaction_id)

    transaction_list = []
    with shelve.open(DB_NAME, 'c') as db:
        for transaction in db['shop_transactions']:
            transaction_list.append(transaction)

    def get_transaction_by_id(t_id):  # debug
        for t in transaction_list:
            if t_id == t.count_id:
                return t

    logging.info("delete_transaction: deleted transaction with id %d"
                 % transaction_id)

    # set instance attribute 'deleted' of Transaction.py = False
    get_transaction_by_id(transaction_id).deleted = True

    # writeback to shelve
    with shelve.open(DB_NAME, 'c') as db:
        db["shop_transactions"] = transaction_list

    return redirect(url_for('admin_transaction'))


# certification -- xu yong lin
# YL: for certification -- form (C in CRUD)
# TODO: FILE UPLOAD, FILE SAVING, SHELVE UPDATE
@app.route("/admin/uploadCertification", methods=['GET','POST'])
def upload_cert():
    certification_dict = {}
    if request.method == 'POST':
        with shelve.open(DB_NAME, 'c') as db:
            try:
                certification_dict = db['certification']
                print(certification_dict)
            except Exception as e:
                logging.error("Error in retrieving certificate from ""restaurants.db (%s)" % e)

            # create a new Certification Object
            certification = Certification(request.form["hygieneDocument"], request.form["halalDocument"],
                                          request.form["vegetarianDocument"], request.form["veganDocument"])
            print(certification)
            print(certification.count_id)

            certification_dict[Certification.count_id] = certification
            db['certification'] = certification_dict

            return redirect(url_for('read_cert'))

    return render_template("admin/certification.html")


# YL: for certification -- reading of data and displaying it to myRestaurant (C in CRUD)
@app.route("/admin/certification")
def read_cert():
    certification_dict = {}
    with shelve.open(DB_NAME, "c") as db:
        try:
            if 'certification' in db:
                certification_dict = db['certification']
                print(certification_dict)
            else:
                db['certification'] = certification_dict
                print(certification_dict)
                logging.info("read_cert: nothing found in db, starting empty")
        except:
            logging.error("no sleep")

        certificate_list = []
        for key in certification_dict:
            food = certification_dict.get(key)
            certificate_list.append(food)

    return render_template("admin/certification2.html", certificate_list=certificate_list)


# def upload_cert():
#     i = 1
#     certification_form = DocumentUploadForm(request.form)
#     certifications_dict = {}
#     if request.method == 'POST' and certification_form.validate():
#         db = shelve.open(DB_NAME, 'c')
#         try:
#             certifications_dict = db['certification']
#         except Exception as e:
#             logging.error("Error in retrieving Certification from "
#                           "certification.db (%s)" % e)
#
#         certifications_dict[i] = i
#         db['certification'] = certifications_dict
#
#         db.close()
#
#     certification = Certification(request.form["hygieneDocument"])
#
#     # if certification_form.validate_on_submit():
#     #     # file path to save files to:
#     #     assets_dir = os.path.join(os.path.dirname(app.instance_path), 'restaurantCertification')
#     #     # assests_dir ==> C:\Users\yongl\appdpj\src\restaurantCertification
#     #     hygiene = certification_form.hygiene_doc.data
#     #
#     #     # saving
#     #     hygiene.save(os.path.join(assets_dir, 'hygiene', hygiene.filename))
#     #
#     #     logging.info('Document uploaded successfully.')
#     #     return redirect(url_for('admin_home'))
#
#     return render_template("admin/certification2.html")


# @app.route("/admin/certification", methods=['GET', 'POST'])
# def admin_certification():
#     # TODO: FILE UPLOAD, FILE SAVING, SHELVE UPDATE
#     # set upload directory path
#     certification_form = RestaurantCertification()
#     if certification_form.validate_on_submit():
#         assets_dir = os.path.join(os.path.dirname('./static/restaurantCertification'))
#
#         hygiene = certification_form.hygiene_cert.data
#         halal = certification_form.halal_cert.data
#         vegetarian = certification_form.vegetarian_cert.data
#         vegan = certification_form.vegan_cert.data
#
#         # document save
#         # halal.save(os.path.join(app.config['UPLOAD_FOLDER'], halaldoc_name))
#         hygiene.save(os.path.join(assets_dir, '<userid>', hygiene))
#         halal.save(os.path.join(assets_dir, '<userid>', halal))
#         vegetarian.save(os.path.join(assets_dir, '<userid>', vegetarian))
#         vegan.save(os.path.join(assets_dir, '<userid>', vegan))
#
#         # halal.save(os.path.join('/application/static/restaurantCertification', halaldoc_name))
#         # vegetarian.save(
#         #     os.path.join('/application/static/restaurantCertification', vegetariandoc_name))
#         # vegan.save(os.path.join('/application/static/restaurantCertification', vegandoc_name))
#
#         flash('Document uploaded successfully')
#
#         return redirect(url_for('admin_transaction'))
#
#     return render_template("admin/certification.html",
#                            certification_form=certification_form)


# YL: for certification -- Update certification [if it expires/needs to be updated] (U in CRUD)
# TODO: REDIRECT BACK TO FORM IN 'C IN CRUD'
# TODO: CHECK IF THE FILES ARE THE SAME AND UPDATE THE DETAILS
# @app.route('/updateCertification/<int:id>', methods=['POST'])
# def update_cert(id):
#     return redirect(url_for('read_cert'))

# YL: for certification -- Delete (D in CRUD)
# TODO: DELETE BUTTON (similar to delete User in SimpleWebApplication)
# not soft delete!
# @app.route('/deleteCertification/<int:id>', methods=['POST'])
# def delete_cert(id):
#     with shelve.open(DB_NAME, 'w') as db:
#         try:
#             certification_dict = db['certification']
#             if id in certification_dict:
#                 certification_dict.pop(id)
#             db['certification'] = certification_dict
#         except Exception as e:
#             logging.error("delete_food: error opening db (%s)" % e)
#
#     return redirect(url_for('read_cert'))


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
