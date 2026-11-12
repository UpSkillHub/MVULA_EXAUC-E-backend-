
from getpass import getpass

from app import create_app
from app.extensions import db
from app.models.user import User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    print("Create the first Superadmin")

    name = input("Name: ").strip()
    email = input("Email: ").strip()
    password = getpass("Password: ")
    confirm_password = getpass("Confirm password: ")

    if not name or not email or not password:
        print("All fields are required.")
    elif password != confirm_password:
        print("Passwords do not match.")
    elif User.query.filter_by(email=email).first():
        print("A user with this email already exists.")
    else:
        superadmin = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            role="superadmin",
            organization_id=None
        )

        db.session.add(superadmin)
        db.session.commit()

        print("Superadmin created successfully!")
