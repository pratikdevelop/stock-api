from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from datetime import timedelta
from passlib.context import CryptContext
from typing import List
import jwt
import yfinance as yf
import pandas as pd
from models import UserPortfolio, UserCreateResponse, Login, UserResponse
from db import create_user, get_user_by_email, get_user_by_id, fetch_data
from db import get_all_stocks, add_to_watchlist, remove_from_watchlist, get_watchlist, get_all_stocks, sell_stock, buy_stock
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# JWT Secret (for token generation)
SECRET_KEY = "e6c045ba39faa1dbf305693b463b25a90a23f91ae9484f28d72db668766334b9381c2561d0d9d748c79a0be200b6026fb49b053345508eaeedd97d8694e8f2ecae0eed40cb32f416e64335a95925868d2412d8e358338105d0bb30b17f42b6ac7de34c35131c1a0b1438278b081f044ead75f5b7257dd267aa65a36706d06ceb62a5ac1b1893b86d2a13da30efe14f535a510e8516975461518b0497e94780988b0c5e4bbe743d5062bb059e9ecebe6d128a7a1bbf10ecb7b2497aa6bcc9d8f305596037a0204e8108e412d618fadd687a23869d46e5d60e9305f80c20dcb03c3857a02b3b90f43d749c971b978d12122816842981c290e47f2933302a72b049"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Token expiration time in minutes

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Create the FastAPI app
app = FastAPI()

# Allow CORS from the frontend origin (e.g., localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # or use "*" to allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
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


# Function to fetch stock data from Yahoo Finance using yfinance
def get_stock_data(ticker: str, period: str = '1y', interval: str = '1d') -> pd.DataFrame:
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period=period, interval=interval)
        return data
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Error fetching data for {ticker}: {e}")


# Calculate Simple Moving Average (SMA)
def calculate_sma(data: pd.DataFrame, window: int = 20) -> pd.Series:
    return data['Close'].rolling(window=window).mean()

tock_data = {
    'AAPL': {'current_price': 175.15, 'market_cap': '2.8T', '52_week_high': 182.88, '52_week_low': 123.85},
    'MSFT': {'current_price': 310.32, 'market_cap': '2.3T', '52_week_high': 315.59, '52_week_low': 220.55},
    'GOOGL': {'current_price': 2814.29, 'market_cap': '1.9T', '52_week_high': 2950.42, '52_week_low': 2677.85},
    'AMZN': {'current_price': 135.67, 'market_cap': '1.4T', '52_week_high': 145.85, '52_week_low': 101.88},
    'TSLA': {'current_price': 199.97, 'market_cap': '0.8T', '52_week_high': 314.67, '52_week_low': 101.81},
    'META': {'current_price': 295.50, 'market_cap': '0.8T', '52_week_high': 345.91, '52_week_low': 169.88},
    'NFLX': {'current_price': 563.34, 'market_cap': '0.25T', '52_week_high': 600.99, '52_week_low': 350.70},
    'NVDA': {'current_price': 435.28, 'market_cap': '1.1T', '52_week_high': 475.52, '52_week_low': 179.88},
    'SPY': {'current_price': 406.32, 'market_cap': 'N/A', '52_week_high': 431.25, '52_week_low': 389.23},
    'GOOG': {'current_price': 2814.39, 'market_cap': '1.9T', '52_week_high': 2952.12, '52_week_low': 2680.25},
    # Add more stocks and data as needed
}

@app.get("/stocks/list")
async def get_stocks_by_limit(limit: int = 10):
    """
    Fetches a list of stock symbols and their respective analytics up to a specified limit.
    :param limit: The number of stock symbols to return. Default is 10.
    :return: List of stock symbols and their respective analytics.
    """
    # Simulated list of stock symbols (you can add more as needed)
    stock_symbols = list(stock_data.keys())
    
    # Ensure the limit doesn't exceed the available list length
    if limit > len(stock_symbols):
        limit = len(stock_symbols)
    
    # Prepare the stock data with analytics for each symbol
    stock_analytics = []
    for symbol in stock_symbols[:limit]:
        stock_info = stock_data[symbol]
        stock_analytics.append({
            'symbol': symbol,
            'current_price': stock_info['current_price'],
            'market_cap': stock_info['market_cap'],
            '52_week_high': stock_info['52_week_high'],
            '52_week_low': stock_info['52_week_low']
        })
    
    return {"stocks": stock_analytics}


# Route to get latest stock price (replaces external API call)
@app.get("/latestprice/{keyword}")
async def get_latest_price(keyword: str):
    data = get_stock_data(keyword)
    latest_price = data['Close'].iloc[-1]
    return {"ticker": keyword, "latest_price": latest_price}


# Route to get historical stock data (replaces external API call)
@app.get("/historical/{keyword}")
async def get_historical_data(keyword: str, period: str = '1y', interval: str = '1d'):
    data = get_stock_data(keyword, period, interval)
    return data[['Open', 'High', 'Low', 'Close', 'Volume']].tail(10).to_dict(orient="records")


# Route to get Simple Moving Average (SMA)
@app.get("/sma/{keyword}")
async def get_sma(keyword: str, window: int = 20):
    data = get_stock_data(keyword)
    sma_values = calculate_sma(data, window).tail(10)
    return {"ticker": keyword, "sma_values": sma_values.tolist()}


# Route to register a new user
@app.post("/register", response_model=UserCreateResponse)
async def register_user(user: UserPortfolio):
    existing_user = await get_user_by_email(user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = pwd_context.hash(user.password)

    user_data = user.dict()
    user_data["password"] = hashed_password
    
    new_user = await create_user(user_data)
    access_token = create_access_token(data={"sub": user.email})
    
    return {"access_token": access_token, "token_type": "bearer"}


# Route to login an existing user
@app.post("/login", response_model=UserCreateResponse)
async def login_user(login_data: Login):
    user = await get_user_by_email(login_data.email)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    if not pwd_context.verify(login_data.password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
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


# Route to add a stock to the watchlist
@app.post("/watchlist/add", response_model=dict)
async def add_to_watchlist_route(watchlist: dict):
    try:
        result = await add_to_watchlist(watchlist.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Route to remove a stock from the watchlist
@app.post("/watchlist/remove", response_model=dict)
async def remove_from_watchlist_route(watchlist: dict):
    try:
        result = await remove_from_watchlist(watchlist.symbol)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Route to get all items from the watchlist
@app.get("/watchlist", response_model=List[dict])
async def get_watchlist_items():
    try:
        items = await get_watchlist()
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Route to get portfolio
@app.get("/portfolio")
async def get_user_portfolio():
    try:
        portfolio = await get_all_stocks()
        return portfolio
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Route to update portfolio (buy and sell stocks)
@app.post("/portfolio/update", response_model=dict)
async def update_user_portfolio(portfolio):
    try:
        result = await update_portfolio(portfolio.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Route to get all stocks
@app.get("/stocks")
async def get_all_stocks_route():
    try:
        stocks = await get_all_stocks()
        return stocks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Define the FastAPI Endpoints

@app.get("/searchutil/{keyword}")
def search_util(keyword: str):
    # Search for the keyword in stock tickers using Yahoo Finance
    try:
        stock = yf.Ticker(keyword)
        info = stock.info  # Get stock information
        return info
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Error searching for {keyword}: {e}")


@app.get("/latestprice/{keyword}")
async def get_latest_price(keyword: str):
    data = get_stock_data(keyword)
    latest_price = data['Close'].iloc[-1]  # Get the latest close price
    return {"ticker": keyword, "latest_price": latest_price}


@app.get("/getmarketstatus")
async def get_market_status():
    # Here, you can simulate market status, since we don't have an external API anymore.
    # For now, we return a simple mock status.
    return {"market_status": "open"}


@app.get("/company-details/{keyword}")
async def get_company_details(keyword: str):
    data = get_stock_data(keyword)
    company_info = {
        "symbol": keyword,
        "name": data.info['longName'],
        "sector": data.info['sector'],
        "industry": data.info['industry'],
        "market_cap": data.info['marketCap'],
        "description": data.info.get('longBusinessSummary', 'No description available')
    }
    return company_info


@app.get("/company-peers/{keyword}")
async def get_company_peers(keyword: str):
    # This is simulated; ideally, we'd find related companies from a financial database.
    peers = ['AAPL', 'MSFT', 'GOOGL']  # Mock peers
    return {"ticker": keyword, "peers": peers}


@app.get("/insight-settlement/{keyword}")
async def get_insight_settlement(keyword: str):
    # Simulate insider sentiment data (this would need a real data source for insider sentiment)
    return {"ticker": keyword, "sentiment": "positive"}


@app.get("/recommendation/{keyword}")
async def get_recommendation(keyword: str):
    # Placeholder recommendation: return 'Buy' if the stock has increased in the last 10 days, otherwise 'Hold'
    data = get_stock_data(keyword)
    if data['Close'].iloc[-1] > data['Close'].iloc[-10]:  # Check last 10 days trend
        return {"ticker": keyword, "recommendation": "Buy"}
    else:
        return {"ticker": keyword, "recommendation": "Hold"}


@app.get("/earnings/{keyword}")
async def get_company_earnings(keyword: str):
    # Earnings data is typically fetched from financial reports, but we can simulate it.
    earnings = {
        "ticker": keyword,
        "quarterly_earnings": [
            {"quarter": "Q1", "eps": 2.34},
            {"quarter": "Q2", "eps": 3.12},
            {"quarter": "Q3", "eps": 2.98},
            {"quarter": "Q4", "eps": 3.45},
        ]
    }
    return earnings


@app.get("/charts/{keyword}/{from_date}/{to_date}/{multiplier}/{timespan}")
async def get_chart_data(keyword: str, from_date: str, to_date: str, multiplier: int, timespan: str):
    from datetime import datetime
    from_date = datetime.strptime(from_date, "%Y-%m-%d").date()
    to_date = datetime.strptime(to_date, "%Y-%m-%d").date()
    data = get_stock_data(keyword, period=f'{(to_date - from_date).days}d')
    return data[['Open', 'High', 'Low', 'Close', 'Volume']].to_dict(orient="records")


@app.get("/news/{keyword}/{from_date}/{to_date}")
async def get_company_news(keyword: str, from_date: str, to_date: str):
    # Simulate news data
    news_data = [
        {"date": from_date, "headline": f"{keyword} announces new product."},
        {"date": to_date, "headline": f"{keyword} stock rises due to positive earnings report."}
    ]
    return {"ticker": keyword, "news": news_data}


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