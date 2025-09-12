#!/usr/bin/env python3
"""
API v1 router initialization
"""
from fastapi import APIRouter

from app.api.v1.arabic_tv import router as arabic_tv_router

api_router = APIRouter()
api_router.include_router(arabic_tv_router)