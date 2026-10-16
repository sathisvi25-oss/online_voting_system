"""
One-time helper to create (or reset) an admin account.

The app has no self-service admin signup (by design — admin
access shouldn't be self-serve), so run this locally, after
setting up MongoDB, to create the account you'll use to log
into pages/5_Admin.py — or to reset an existing admin's
password if it's been lost.

Usage:
    python scripts/seed_admin.py

Reads MONGO_URI / DATABASE_NAME from .streamlit/secrets.toml
(same file the Streamlit app uses), or from environment
variables of the same name if secrets.toml isn't present.
"""

import os
import re
import sys
import getpass
from pathlib import Path

import bcrypt
from pymongo import MongoClient
from pymongo.errors import PyMongoError

try:
    import tomllib
except ImportError:  # Python < 3.11
    import tomli as tomllib


MIN_LENGTH = 8


def load_config():
    secrets_path = (
        Path(__file__).resolve().parent.parent
        / ".streamlit"
        / "secrets.toml"
    )

    if secrets_path.exists():
        with open(secrets_path, "rb") as f:
            data = tomllib.load(f)
        return data.get("MONGO_URI"), data.get("DATABASE_NAME")

    return os.environ.get("MONGO_URI"), os.environ.get("DATABASE_NAME")


def connect(mongo_uri, database_name):
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
        client.admin.command("ping")
    except PyMongoError as e:
        print(f"Could not connect to MongoDB: {e}")
        sys.exit(1)

    return client[database_name]


def password_problems(password):
    """
    Return a list of reasons the password is too weak, or an
    empty list if it's acceptable. Kept simple on purpose —
    length plus a mix of character types, no external service
    or dictionary check.
    """

    problems = []

    if len(password) < MIN_LENGTH:
        problems.append(f"at least {MIN_LENGTH} characters")

    if not re.search(r"[a-zA-Z]", password):
        problems.append("at least one letter")

    if not re.search(r"[0-9]", password):
        problems.append("at least one digit")

    return problems


def prompt_password(label="New admin password"):
    """
    Prompt for a password twice, validating strength and match.
    Falls back to a visible input() if the terminal doesn't
    support hidden input (e.g. some IDEs / non-interactive
    shells), rather than crashing outright.
    """

    while True:

        try:
            password = getpass.getpass(f"{label}: ")
        except (EOFError, getpass.GetPassWarning):
            print(
                "(Hidden input isn't supported in this terminal — "
                "your typing will be visible.)"
            )
            password = input(f"{label}: ")

        problems = password_problems(password)

        if problems:
            print("Password needs: " + ", ".join(problems) + ".")
            continue

        try:
            confirm = getpass.getpass("Confirm password: ")
        except (EOFError, getpass.GetPassWarning):
            confirm = input("Confirm password: ")

        if password != confirm:
            print("Passwords do not match. Try again.")
            continue

        return password


def main():
    mongo_uri, database_name = load_config()

    if not mongo_uri or not database_name:
        print(
            "MONGO_URI / DATABASE_NAME not found. "
            "Set up .streamlit/secrets.toml first "
            "(see .streamlit/secrets.toml.example)."
        )
        sys.exit(1)

    db = connect(mongo_uri, database_name)
    admins = db["admins"]

    admins.create_index("username", unique=True)

    username = input("Admin username: ").strip()

    if not username:
        print("Username cannot be empty.")
        sys.exit(1)

    existing = admins.find_one({"username": username})

    if existing:

        choice = input(
            f"An admin named '{username}' already exists. "
            "Reset their password instead? [y/N]: "
        ).strip().lower()

        if choice != "y":
            print("No changes made.")
            sys.exit(0)

        password = prompt_password("New password")

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        )

        admins.update_one(
            {"username": username},
            {"$set": {"password_hash": password_hash}}
        )

        print(f"Password for '{username}' has been reset.")
        return

    password = prompt_password("New admin password")

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    admins.insert_one({
        "username": username,
        "password_hash": password_hash,
    })

    print(f"Admin '{username}' created successfully.")


if __name__ == "__main__":
    main()