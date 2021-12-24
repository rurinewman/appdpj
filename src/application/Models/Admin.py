# Denotes a single restaurant's account

from application.Models.Account import *
from application.Models.Restaurant import Restaurant


class Admin(Account):
    def __init__(self, restaurant_name, email, password):
        super().__init__(email, password)  # comes first, so we can abort error
        # self.restaurant_name = restaurant_name
        # Create a new Restaurant object
        self.restaurant = Restaurant(restaurant_name)

        # todo:
        self.list_of_transactions = []
        logging.info("Admin Class: Created new Admin account with "
                     "email=%s, restaurant_name=%s, account_id=%s"
                     % (self.get_email(), self.restaurant_name,
                        self.account_id))
        save_db()  # ALWAYS REMEMBER THIS!!!!!!!!

    # Add a transaction to a shop's list
    def add_transaction(self, transaction):
        self.list_of_transactions.append(transaction)
        save_db()
