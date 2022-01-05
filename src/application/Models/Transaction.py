# xu yong lin
# yet to include this part in python
import logging
import shelve

from application import DB_NAME
from application.Models.Account import Account


class Transaction:
    transaction_id = 1

    def __init__(self, account_name=None, option=None, price=0, used_coupons=None,
                 ratings=0):
        with shelve.open(DB_NAME, 'c') as db:
            try:
                Transaction.transaction_id = db['transaction_id_count']
            except Exception as e:
                logging.info("transaction_id_count: error reading from db (%s)" % e)
        self.count_id = Transaction.transaction_id  # temporary as the 'count id' in Account is not set for users yet
        self.account_name = account_name
        self.__option = option
        self.__price = float(price)
        self.__used_coupons = used_coupons
        self.__ratings = int(ratings)
        self.deleted = False
        Transaction.transaction_id += 1
        with shelve.open(DB_NAME, 'c') as db:
            db['transaction_id_count'] = Transaction.transaction_id

    print(Account.count_id)

    def set_option(self, option):
        self.__option = option

    def get_option(self):
        return self.__option

    def set_price(self, price):
        self.__price = price

    def get_price(self):
        return self.__price

    def set_used_coupons(self, used_coupons):
        self.__used_coupons = used_coupons

    def get_used_coupons(self):
        return self.__used_coupons

    def set_ratings(self, ratings):
        self.__ratings = ratings

    def get_ratings(self):
        return self.__ratings
