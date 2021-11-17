### python-packages
import sys
import os
from werkzeug.security import generate_password_hash

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(SCRIPT_DIR, "..", ".."))

### local-packages
from project.models import User
from project.__init__ import db, create_app
from project.utilities.logger import *

def create_user(username, password):
    log.info("Initiated Script to Create New User")

    with create_app().app_context():

        user = User.query.filter_by(username=username).first()
        if user:
            log.info(f"Username {username} already exists. Aborting.")
            return None
        
        new_user = User(username=username, password=generate_password_hash(password, method='sha256'))
        db.session.add(new_user)
        db.session.commit()
        log.info(f"User {username} added to database.")

def remove_user(username):
    log.info("Initiated Script to Remove User")

    with create_app().app_context():

        user = User.query.filter_by(username=username).first()
        if not user:
            log.info(f"Username {username} does not exist. Aborting.")
            return None
        
        db.session.query(User).filter_by(username=username).delete()
        db.session.commit()
        log.info(f"User {username} removed from database.")

def clear_user_database():
    log.info("Initiated Script to Clear Database")
    
    with create_app().app_context():

        if User.query.count() > 0:
            db.session.query(User).delete()
            db.session.commit()
            log.info("All User records deleted from the database")
        else:
            log.info("No User records found in the database")

if __name__ == '__main__':
    print("Pick and Option: ")
    print("1. Create User")
    print("2. Remove User")
    print("3. Clear User Database")

    method = input("Enter Option: ")

    if method == "1":
        username = input("Enter username: ")
        password = input("Enter password: ")
        create_user(username, password)
    elif method == "2":
        username = input("Enter username: ")
        remove_user(username)
    elif method == "3":
        clear_user_database()
    