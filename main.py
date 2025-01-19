from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from datetime import timedelta
from passlib.context import CryptContext
from typing import List
import jwt
from models import UserPortfolio, UserCreateResponse, Login, UserResponse
from db import create_user, get_user_by_email, get_user_by_id
from db import get_all_stocks, add_to_watchlist, remove_from_watchlist, get_watchlist, get_all_stocks, sell_stock,buy_stock,fetch_data
from fastapi.middleware.cors import CORSMiddleware

# JWT Secret (for token generation)
SECRET_KEY = "e6c045ba39faa1dbf305693b463b25a90a23f91ae9484f28d72db668766334b9381c2561d0d9d748c79a0be200b6026fb49b053345508eaeedd97d8694e8f2ecae0eed40cb32f416e64335a95925868d2412d8e358338105d0bb30b17f42b6ac7de34c35131c1a0b1438278b081f044ead75f5b7257dd267aa65a36706d06ceb62a5ac1b1893b86d2a13da30efe14f535a510e8516975461518b0497e94780988b0c5e4bbe743d5062bb059e9ecebe6d128a7a1bbf10ecb7b2497aa6bcc9d8f305596037a0204e8108e412d618fadd687a23869d46e5d60e9305f80c20dcb03c3857a02b3b90f43d749c971b978d12122816842981c290e47f2933302a72b049"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Token expiration time in minutes

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()
origins = [
    "http://localhost",
    "http://localhost:4200",
]
BASE_URL = "https://finnhub.io/api/v1"

API_KEY = "cni30ghr01qv035kgaegcni30ghr01qv035kgaf0"
POLYGON_API_KEY = "DJiHWACutvMUIGG37cYjdxUbKhTgz1su"
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 Password Bearer scheme (for token extraction)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# Utility function to create JWT token
def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)) -> str:
    to_encode = data.copy()
    expire = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Route to register a new user
@app.post("/register", response_model=UserCreateResponse)
async def register_user(user: UserPortfolio):
    # Check if the user already exists
    existing_user = await get_user_by_email(user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed_password = pwd_context.hash(user.password)

    # Convert user data to a dictionary and add the hashed password
    user_data = user.dict()
    user_data["password"] = hashed_password
    
    # Store the user in the database
    new_user = await create_user(user_data)

    # Generate JWT token
    access_token = create_access_token(data={"sub": user.email})
    
    return {"access_token": access_token, "token_type": "bearer"}


# Route to login an existing user
@app.post("/login", response_model=UserCreateResponse)
async def login_user(login_data: Login):
    # Check if the user exists
    user = await get_user_by_email(login_data.email)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    # Verify the password
    if not pwd_context.verify(login_data.password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    # Generate JWT token
    access_token = create_access_token(data={"sub": login_data.email})
    
    return {"access_token": access_token, "token_type": "bearer"}


# Route to get user profile by token (using OAuth2 Bearer Token)
@app.get("/profile", response_model=UserResponse)
async def get_profile(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        user = await get_user_by_email(email)
        if user is None:
            raise credentials_exception
    except jwt.JWTError:
        raise credentials_exception
    
    return user

# Route to add a stock to the watchlist (like '/watchlist/add' in Express)
@app.post("/watchlist/add", response_model=dict)
async def add_to_watchlist_route(watchlist: dict):
    try:
        result = await add_to_watchlist(watchlist.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Route to remove a stock from the watchlist (like '/watchlist/remove' in Express)
@app.post("/watchlist/remove", response_model=dict)
async def remove_from_watchlist_route(watchlist: dict):
    try:
        result = await remove_from_watchlist(watchlist.symbol)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Route to get all items from the watchlist (like '/watchlist' in Express)
@app.get("/watchlist", response_model=List[dict])
async def get_watchlist_items():
    try:
        items = await get_watchlist()
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Route to get portfolio (like '/portfolio/money' in Express)
@app.get("/portfolio")
async def get_user_portfolio():
    try:
        portfolio = await get_all_stocks()
        return portfolio
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Route to update portfolio (like the buy and sell routes in Express)
@app.post("/portfolio/update", response_model=dict)
async def update_user_portfolio(portfolio):
    try:
        result = await update_portfolio(portfolio.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Route to get all stocks (like '/stocks' in Express)
@app.get("/stocks")
async def get_all_stocks_route():
    try:
        stocks = await get_all_stocks()
        return stocks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# Define FastAPI Endpoints
@app.get("/searchutil/{keyword}")
async def search_util(keyword: str):
    url = f"{BASE_URL}/search?q={keyword}&token={API_KEY}"
    data = fetch_data(url)
    return data

@app.get("/latestprice/{keyword}")
async def get_latest_price(keyword: str):
    url = f"{BASE_URL}/quote?symbol={keyword}&token={API_KEY}"
    data = fetch_data(url)
    return data

@app.get("/getmarketstatus")
async def get_market_status():
    url = f"{BASE_URL}/stock/market-status?exchange=US&token={API_KEY}"
    data = fetch_data(url)
    return data

@app.get("/company-details/{keyword}")
async def get_company_details(keyword: str):
    url = f"{BASE_URL}/stock/profile2?symbol={keyword}&token={API_KEY}"
    data = fetch_data(url)
    return data

@app.get("/company-peers/{keyword}")
async def get_company_peers(keyword: str):
    url = f"{BASE_URL}/stock/peers?symbol={keyword}&token={API_KEY}"
    data = fetch_data(url)
    return data

@app.get("/insight-settlement/{keyword}")
async def get_insight_settlement(keyword: str):
    url = f"{BASE_URL}/stock/insider-sentiment?symbol={keyword}&token={API_KEY}"
    data = fetch_data(url)
    # Transform the data similarly as in the Node.js code
    return data

@app.get("/recommendation/{keyword}")
async def get_recommendation(keyword: str):
    url = f"{BASE_URL}/stock/recommendation?symbol={keyword}&token={API_KEY}"
    data = fetch_data(url)
    return data

@app.get("/earnings/{keyword}")
async def get_company_earnings(keyword: str):
    url = f"{BASE_URL}/stock/earnings?symbol={keyword}&token={API_KEY}"
    data = fetch_data(url)
    return data

@app.get("/charts/{keyword}/{from_date}/{to_date}/{multiplier}/{timespan}")
async def get_chart_data(keyword: str, from_date: str, to_date: str, multiplier: int, timespan: str):
    from datetime import datetime
    from_date = datetime.strptime(from_date, "%Y-%m-%d").date()
    to_date = datetime.strptime(to_date, "%Y-%m-%d").date()
    url = f"https://api.polygon.io/v2/aggs/ticker/{keyword}/range/{multiplier}/{timespan}/{from_date}/{to_date}?adjusted=true&sort=asc&apiKey={POLYGON_API_KEY}"
    data = fetch_data(url)
    return data

@app.get("/news/{keyword}/{from_date}/{to_date}")
async def get_company_news(keyword: str, from_date: str, to_date: str):
    url = f"{BASE_URL}/company-news?symbol={keyword}&from={from_date}&to={to_date}&token={API_KEY}"
    data = fetch_data(url)
    return data

@app.post("/buy")
async def buy_stock(ticker: str, name: str, price: float, totalPrice: float, quantity: int):
    return await buy_stock(ticker, name, price, total_price, quantity)
@app.post("/sell")
async def sell_stock(ticker: str, quantity: int):
    return await sell_stock(ticker, quantity)

@app.exception_handler(HTTPException)
async def validation_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
