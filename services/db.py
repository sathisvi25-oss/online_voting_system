import streamlit as st
from pymongo import MongoClient
import gridfs


# ============================================================
# DATABASE CONNECTION
# ============================================================

@st.cache_resource
def get_database():
    """
    Connect to MongoDB Atlas and return the database.
    """

    try:
        mongo_uri = st.secrets["MONGO_URI"]
        database_name = st.secrets["DATABASE_NAME"]

        client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=10000
        )

        # Test connection
        client.admin.command("ping")

        db = client[database_name]

        _ensure_indexes(db)

        return db

    except Exception as e:
        raise ConnectionError(
            f"MongoDB Atlas connection failed: {e}"
        )


# ============================================================
# INDEXES
# ============================================================

def _ensure_indexes(db):
    """
    Create required indexes if they don't already exist.

    This is what actually makes voter_id / email unique at the
    database level (the app-level duplicate checks in Register
    can still race under concurrent submissions, so the unique
    index is the real guarantee). Safe to call every time the
    connection is created - creating an index that already
    exists is a no-op.
    """

    db["voters"].create_index("voter_id", unique=True)
    db["voters"].create_index("email", unique=True)

    db["admins"].create_index("username", unique=True)

    db["votes"].create_index("receipt_id", unique=True)
    db["votes"].create_index("election_id")

    db["candidates"].create_index("election_id")
    db["candidates"].create_index([("election_id", 1), ("status", 1)])

    db["auth_logs"].create_index("attempt_time")


# ============================================================
# GRIDFS
# ============================================================

@st.cache_resource
def get_gridfs(_db):
    """
    Return GridFS instance.

    The leading underscore tells Streamlit not to hash
    the PyMongo Database object.
    """

    return gridfs.GridFS(_db)


# ============================================================
# COLLECTIONS
# ============================================================

def get_collections(db):

    return {
        "voters": db["voters"],
        "votes": db["votes"],
        "auth_logs": db["auth_logs"],
        "elections": db["elections"],
        "candidates": db["candidates"],
        "admins": db["admins"],
    }