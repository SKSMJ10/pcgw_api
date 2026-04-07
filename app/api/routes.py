from fastapi import APIRouter, HTTPException
from app.scraper.client import PCGamingWiki

router = APIRouter(prefix ="/api/v1")

