from dotenv import dotenv_values
from pymongo import AsyncMongoClient
from pymongo.server_api import ServerApi

config = dotenv_values(".env")
MONGO_URI = config['MONGO_URI']
client = AsyncMongoClient(MONGO_URI, server_api=ServerApi('1'))
