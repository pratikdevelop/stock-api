from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime

# Stock schema
class Stock(BaseModel):
    ticker: str
    name: str
    price: float
    totalPrice: float
    totalQuantityBought: int
    totalQuantity: int

# User Portfolio schema
class UserPortfolio(BaseModel):
    name: str
    email: EmailStr
    password: str
    profilePicture: Optional[str] = "default-profile-pic.jpg"  # Default profile picture
    phone: Optional[str] = None
    totalAmount: Optional[float] = 25000  # Default amount for new user portfolios
    stocks: List[Stock] = []

    class Config:
        # This ensures the model is compatible with MongoDB ObjectId type
        orm_mode = True


# User creation response (JWT Token)
class UserCreateResponse(BaseModel):
    access_token: str
    token_type: str


# Login data model
class Login(BaseModel):
    email: EmailStr
    password: str


# User response with additional details (e.g., for profile route)
class UserResponse(BaseModel):
    name: str
    email: EmailStr
    profilePicture: str
    phone: Optional[str] = None
    totalAmount: float
    stocks: List[Stock]

    class Config:
        orm_mode = True


# Watchlist schema
class Watchlist(BaseModel):
    name: str
    symbol: str

    class Config:
        orm_mode = True


# Watchlist creation response model
class WatchlistResponse(BaseModel):
    name: str
    symbol: str

    class Config:
        orm_mode = True