"""Set or reset the admin password from the command line.

    python3 set_password.py 'your-new-password'

If you forget the password, run this to overwrite it.
"""
import sys
import sqlite3

import db
from werkzeug.security import generate_password_hash


def main():
    if len(sys.argv) < 2 or len(sys.argv[1]) < 6:
        print("usage: python3 set_password.py <password>   (min 6 chars)")
        sys.exit(1)
    db.init_db()
    conn = sqlite3.connect(db.DB_PATH)
    try:
        conn.execute(
            "INSERT INTO settings(key,value) VALUES('admin_password',?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (generate_password_hash(sys.argv[1], method="pbkdf2:sha256"),))
        conn.commit()
        print("admin password updated")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
