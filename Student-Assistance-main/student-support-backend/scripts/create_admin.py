import argparse
from datetime import datetime
from pathlib import Path
import re
import sys

import bcrypt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import admins_collection


def _hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def main():
    parser = argparse.ArgumentParser(description="Create or update an admin account")
    parser.add_argument("--username", required=True, help="Admin username")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--password", required=True, help="Admin password")
    args = parser.parse_args()

    username = args.username.strip()
    email = args.email.strip().lower()
    password = args.password

    if not username or not email or not password:
        raise SystemExit("username, email and password are required")

    hashed_password = _hash_password(password)
    now = datetime.utcnow()

    result = admins_collection.update_one(
        {
            "$or": [
                {"username": {"$regex": f"^{re.escape(username)}$", "$options": "i"}},
                {"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}},
            ]
        },
        {
            "$set": {
                "username": username,
                "email": email,
                "password": hashed_password,
                "updated_at": now,
            },
            "$setOnInsert": {
                "created_at": now,
            },
        },
        upsert=True,
    )

    if result.upserted_id:
        print(f"Admin created: {username} ({email})")
    else:
        print(f"Admin updated: {username} ({email})")


if __name__ == "__main__":
    main()
