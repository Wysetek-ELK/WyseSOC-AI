import argparse
import asyncio
import sys
import os

from sqlalchemy import select
from app.database import async_engine, Base, AsyncSessionLocal
from app.models.user import User
from app.models.rule import Rule
from app.models.incident import Incident
from app.utils.security import get_password_hash
from app.services.ingestion_service import IngestionService


async def create_admin(username: str, email: str, password: str, full_name: str = ""):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if user exists
        stmt = select(User).where((User.username == username) | (User.email == email))
        res = await session.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            print(f"Error: User '{username}' or email '{email}' already exists.")
            return

        user = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name or "Administrator",
            role="Administrator",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        print(f"Administrator '{username}' created successfully!")


async def import_data(file_path: str):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        return

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        ingestion = IngestionService(session)
        with open(file_path, "rb") as f:
            content = f.read()

        filename = os.path.basename(file_path)
        if filename.lower().endswith(".zip"):
            job, summary = await ingestion.ingest_zip(content, filename, "cli")
            print("=== IMPORT SUMMARY ===")
            print(f"Job ID: {summary['job_id']}")
            print(f"Status: {summary['status']}")
            print(f"Total entries found: {summary['total_found']}")
            print(f"Rules detected: {summary['rules_detected']}")
            print(f"Incidents imported: {summary['imported']}")
            print(f"Duplicates: {summary['duplicates']}")
            print(f"Errors: {summary['errors']}")
            if summary['error_messages']:
                print("Error details:")
                for err in summary['error_messages']:
                    print(f"  - {err}")
        else:
            print("Currently only .zip files are supported by CLI import.")


def main():
    parser = argparse.ArgumentParser(description="AI Verdict Management CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create-admin
    admin_parser = subparsers.add_parser("create-admin", help="Create an administrator account")
    admin_parser.add_argument("--username", required=True, help="Admin username")
    admin_parser.add_argument("--email", required=True, help="Admin email")
    admin_parser.add_argument("--password", required=True, help="Admin password")
    admin_parser.add_argument("--full-name", default="System Administrator", help="Full name")

    # import-data
    import_parser = subparsers.add_parser("import-data", help="Import incidents from a ZIP file")
    import_parser.add_argument("file_path", help="Path to ZIP archive")

    args = parser.parse_args()

    if args.command == "create-admin":
        asyncio.run(create_admin(args.username, args.email, args.password, args.full_name))
    elif args.command == "import-data":
        asyncio.run(import_data(args.file_path))


if __name__ == "__main__":
    main()

