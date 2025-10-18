import argparse
import asyncio
import os
import sys
from typing import Optional

from db import init_database, close_database, get_pool
from db.users_db import get_user_by_email, create_user
from utils.security_ut import hash_password


def _isatty() -> bool:
    try:
        return sys.stdin.isatty()
    except Exception:
        return False


async def upsert_user(email: str, password: Optional[str], name: Optional[str], role: str) -> int:
    await init_database()
    try:
        email_lc = (email or "").strip().lower()
        if not email_lc:
            print("ERROR: email is required", file=sys.stderr)
            return 2

        user = await get_user_by_email(email_lc)
        if user:
            sets = []
            params = []
            if password:
                sets.append("password_hash=$1")
                params.append(hash_password(password))
            if role:
                sets.append(f"role=${len(params) + 1}")
                params.append(role)
            if sets:
                set_clause = ", ".join(sets)
                params.append(user["id"])
                await get_pool().execute(f"UPDATE users SET {set_clause} WHERE id=${len(params)}", *params)
                print(f"Updated user {email_lc}: "
                      f"{'password ' if password else ''}{'role='+role if role else ''}".strip())
            else:
                print(f"User {email_lc} exists; nothing to update.")
        else:
            pwd_hash = hash_password(password) if password else None
            new_user = await create_user(email_lc, pwd_hash, name)
            if role and role.lower() != "buyer":
                await get_pool().execute("UPDATE users SET role=$1 WHERE id=$2", role, new_user["id"])
            print(f"Created user {email_lc} with role={role or 'buyer'}")
        return 0
    finally:
        await close_database()


def main():
    parser = argparse.ArgumentParser(description="Create or update a user with the desired role")
    parser.add_argument("--email", help="User email")
    parser.add_argument("--password", help="User password")
    parser.add_argument("--name", default="Admin", help="User display name")
    parser.add_argument("--role", default="admin", choices=["buyer", "seller", "admin"], help="User role")
    args = parser.parse_args()

    email = args.email or os.getenv("ADMIN_EMAIL", "")
    password = args.password or os.getenv("ADMIN_PASSWORD", "")
    name = args.name or os.getenv("ADMIN_NAME", "Admin")
    role = args.role or os.getenv("ADMIN_ROLE", "admin")

    if not email and _isatty():
        email = input("Admin email: ").strip()
    if not password and _isatty():
        try:
            import getpass
            password = getpass.getpass("Admin password: ")
        except Exception:
            password = input("Admin password: ")

    if not email:
        print("ERROR: email is required (pass --email or set ADMIN_EMAIL). Non-interactive mode detected.", file=sys.stderr)
        sys.exit(2)

    rc = asyncio.run(upsert_user(email=email, password=password or None, name=name, role=role))
    sys.exit(rc)


if __name__ == "__main__":
    main()
