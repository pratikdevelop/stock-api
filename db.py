from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from typing import List
from fastapi import HTTPException


from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
import requests
from bson import ObjectId
from fastapi.responses import JSONResponse

client = AsyncIOMotorClient("mongodb+srv://stockUser:0IZYVE7KKFqIiad9@cluster0.nt431ty.mongodb.net/stocks?retryWrites=true&w=majority&appName=Cluster0")
db = client["stocks"]
user_collection = db["user_portfolio"]
watchlist_collection = db["watchlist"]

API_KEY = "cni30ghr01qv035kgaegcni30ghr01qv035kgaf0"
POLYGON_API_KEY = "DJiHWACutvMUIGG37cYjdxUbKhTgz1su"
BASE_URL = "https://finnhub.io/api/v1"



# Utility function to generate ObjectId from string
def str_to_objectid(id: str) -> ObjectId:
    return ObjectId(id)


# CRUD function to add a new user
async def create_user(user_data: dict) -> dict:
    try:
        # Inserting new user into MongoDB
        result = await user_collection.insert_one(user_data)
        return {"id": str(result.inserted_id), **user_data}
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="User already exists with this email.")


# CRUD function to get user by email
async def get_user_by_email(email: str) -> dict:
    user = await user_collection.find_one({"email": email})
    if user:
        user["id"] = str(user["_id"])  # Adding 'id' as a string
        return user
    return None


# CRUD function to get user by user_id (ObjectId)
async def get_user_by_id(user_id: str) -> dict:
    user = await user_collection.find_one({"_id": str_to_objectid(user_id)})
    if user:
        user["id"] = str(user["_id"])  # Adding 'id' as a string
        return user
    return None


# Utility function to generate ObjectId from string
def str_to_objectid(id: str) -> ObjectId:
    return ObjectId(id)


# CRUD function to add a new watchlist item
async def add_to_watchlist(watchlist_data: dict) -> dict:
    try:
        # Insert new watchlist item
        result = await watchlist_collection.insert_one(watchlist_data)
        return {"id": str(result.inserted_id), **watchlist_data}
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Watchlist item already exists.")


# CRUD function to get all watchlist items
async def get_watchlist() -> List[dict]:
    watchlist_items = await watchlist_collection.find().to_list(100)
    for item in watchlist_items:
        item["id"] = str(item["_id"])  # Adding 'id' as a string
    return watchlist_items


# CRUD function to remove an item from the watchlist
async def remove_from_watchlist(symbol: str) -> dict:
    result = await watchlist_collection.delete_one({"symbol": symbol})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    return {"message": "Item removed from watchlist"}


# Buy Stock
async def buy_stock(ticker: str, name: str, price: float, total_price: float, quantity: int):
    user = await user_portfolio_collection.find_one({})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user['totalAmount'] < total_price:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    existing_stock = next((stock for stock in user['stocks'] if stock['ticker'] == ticker), None)
    
    if existing_stock:
        existing_stock['totalQuantity'] += quantity
        existing_stock['totalQuantityBought'] += quantity
        existing_stock['totalPrice'] += total_price
    else:
        user['stocks'].append({
            'ticker': ticker,
            'name': name,
            'price': price,
            'totalPrice': total_price,
            'totalQuantityBought': quantity,
            'totalQuantity': quantity
        })
    
    user['totalAmount'] -= total_price
    
    await user_portfolio_collection.replace_one({'_id': user['_id']}, user)
    
    return {"message": "Stock bought successfully"}


# Sell Stock
async def sell_stock(ticker: str, quantity: int):
    user = await user_portfolio_collection.find_one({})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    stock_index = next((index for index, stock in enumerate(user['stocks']) if stock['ticker'] == ticker), None)
    
    if stock_index is None or user['stocks'][stock_index]['totalQuantity'] < quantity:
        raise HTTPException(status_code=400, detail="Stock not found or insufficient quantity to sell")
    
    stock = user['stocks'][stock_index]
    total_price = stock['price'] * quantity
    
    user['totalAmount'] += total_price
    stock['totalQuantity'] -= quantity
    
    if stock['totalQuantity'] == 0:
        user['stocks'].pop(stock_index)
    
    await user_portfolio_collection.replace_one({'_id': user['_id']}, user)
    
    return {"message": "Stock sold successfully"}


# Get All Stocks
async def get_all_stocks():
    user = await user_portfolio_collection.find_one({})
    
    if not user:
        return []
    
    return user.get("stocks", [])


# Add to Watchlist
async def add_to_watchlist(name: str, symbol: str):
    existing_stock = await watchlist_collection.find_one({"symbol": symbol})
    
    if existing_stock:
        raise HTTPException(status_code=400, detail="Stock already exists in the watchlist")
    
    new_stock = {"name": name, "symbol": symbol}
    await watchlist_collection.insert_one(new_stock)
    
    return {"message": "Stock added to watchlist successfully"}


# Remove from Watchlist
async def remove_from_watchlist(symbol: str):
    removed_stock = await watchlist_collection.find_one_and_delete({"symbol": symbol})
    
    if not removed_stock:
        raise HTTPException(status_code=404, detail="Stock not found in the watchlist")
    
    return {"message": "Stock removed from watchlist successfully"}


# Get All Watchlist Stocks
async def get_all_watchlist_stocks():
    stocks = await watchlist_collection.find().to_list(length=100)
    return stocks


# Helper Functions (Same as in Node.js but using Python's requests library for HTTP requests)
def fetch_data(url: str):
    response = requests.get(url)
    if not response.ok:
        raise HTTPException(status_code=400, detail="Network response was not ok")
    return response.json()



# Error handlin
# Run the server using Uvicorn
# uvicorn main:app --reload
