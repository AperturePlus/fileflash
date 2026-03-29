from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL= os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

engine = create_engine(
    url=DATABASE_URL,
    echo=True,  # Enable SQL query logging for debugging purposes
    pool_per_ping=True,  # Enable connection pool pre-ping to check if connections are alive
)