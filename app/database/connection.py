from app.config import settings
from pymongo import AsyncMongoClient
from pymongo.server_api import ServerApi

client = AsyncMongoClient(settings.mongo_uri, server_api=ServerApi("1"), tz_aware=True)
