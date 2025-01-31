require("./models/config")
const fetch = require("node-fetch");
const userPortfolio = require("./models/userPortfolio")
const watchlist = require('./models/watchlist');

// API key and base URL for Finnhub API
const API_KEY = "cni30ghr01qv035kgaegcni30ghr01qv035kgaf0";
const POLYGON_API_KEY = "DJiHWACutvMUIGG37cYjdxUbKhTgz1su";
const BASE_URL = "https://finnhub.io/api/v1";

// Function to fetch data from an API endpoint
async function fetchData(url) {
    const response = await fetch(url);
    console.log(response)
    if (!response.ok) {
        throw new Error('Network response was not ok');
    }
    return response.json();
}

// Function to search for a symbol
async function searchUtil(keyword) {
    const data = await fetchData(`${BASE_URL}/search?q=${keyword}&token=${API_KEY}`);
    return data;
}

// Function to get the latest price for a symbol
async function getLatestPrice(keyword) {
    const data = await fetchData(`${BASE_URL}/quote?symbol=${keyword}&token=${API_KEY}`);
    return data;
}

// Function to get the market status
async function getMarketStatus() {
    const data = await fetchData(`${BASE_URL}/stock/market-status?exchange=US&token=${API_KEY}`);
    return data;
}

// Function to get company details for a symbol
async function getCompanyDetails(keyword) {
    const data = await fetchData(`${BASE_URL}/stock/profile2?symbol=${keyword}&token=${API_KEY}`);
    return data;
}

// Function to get peers for a symbol
async function getCompanyPeers(keyword) {
    const data = await fetchData(`${BASE_URL}/stock/peers?symbol=${keyword}&token=${API_KEY}`);
    return data;
}

async function getRecommendation(keyword) {
    const data = await fetchData(`${BASE_URL}/stock/recommendation?symbol=${keyword}&token=${API_KEY}`);
    return data;
}

async function getInsigntSettlement(keyword) {
    const data = await fetchData(`${BASE_URL}/stock/insider-sentiment?symbol=${keyword}&token=${API_KEY}`);
    let response = {
        totalMsrp: 0,
        totalChange: 0,
        postivveMspr: 0,
        postivvechange: 0,
        negativeChange: 0,
        negativeMspr: 0
    };
    data.data.forEach(element => {
        if (element.mspr > 0) {
            response.postivveMspr += element.mspr;

        }
        if (element.mspr < 0) {
            response.negativeMspr -= element.mspr;

        }
        if (element.change > 0) {
            response.postivvechange += element.change;

        }
        if (element.change < 0) {
            response.negativeChange -= element.change;

        }
        response.totalChange += element.change
        response.totalMsrp += element.mspr
    })
    data.postivveMspr = response.postivveMspr;

    data.negativeMspr = response.negativeMspr;

    data.postivvechange = response.postivvechange;
    data.negativeChange = response.negativeChange;
    data.totalMsrp = response.totalMsrp
    data.totalChange = response.totalChange
    return data;
}

async function getCompanyEarnings(keyword) {
    const data = await fetchData(`${BASE_URL}/stock/earnings?symbol=${keyword}&token=${API_KEY}`);
    return data;
}

async function getChartData(keyword, start_date, end_date, multiplier, timespan) {
    const data = await fetchData(`https://api.polygon.io/v2/aggs/ticker/${keyword}/range/${multiplier}/${timespan}/${start_date}/${end_date}?adjusted=true&sort=asc&apiKey=${POLYGON_API_KEY}`);
    return data;
}

async function getCompanyNews(keyword, start_date, end_date) {
    const response = await fetchData(`${BASE_URL}/company-news?symbol=${keyword}&from=${start_date}&to=${end_date}&token=${API_KEY}`);
    const news = [];
    response.forEach((res, index) => {
        if (index > 10) return;
        news.push({
            title: res.headline,
            description: res.summary,
            url: res.image,
            source: res.source,
            published_date: new Date(res.datetime)
        })
    })
    return news;
}

async function BuyStock(ticker, name, price, totalPrice, quantity) {
    try {
        // Find or create user
        let user = await userPortfolio.findOne();

        if (!user) {
            user = new userPortfolio();
        }

        // Calculate total price for the stock purchase

        // Check if user has enough balance to buy
        if (user.totalAmount < totalPrice) {
            return ({"code": 400, "mesaage": 'Insufficient balance'});
        }

        // Check if stock already exists in user's portfolio
        const existingStock = user.stocks.find(stock => stock.ticker === ticker);

        if (existingStock) {
            // Update existing stock
            existingStock.totalQuantity += quantity;
            existingStock.totalQuantityBought += quantity;
            existingStock.totalPrice += totalPrice;
        } else {
            // Create new stock record
            user.stocks.push({
                ticker,
                name,
                price,
                totalPrice,
                totalQuantityBought: quantity,
                totalQuantity: quantity
            });
        }

        // Update total amount
        user.totalAmount -= totalPrice;

        // Save updated user data
        await user.save();

        return {message: 'Stock bought successfully'};
    } catch (error) {
        console.error(error);
        return error;
    }
}

async function sellStock(ticker, quantity) {

    try {
        // Find user
        const user = await userPortfolio.findOne();

        // Find the stock in user's portfolio
        const stockIndex = user.stocks.findIndex(stock => stock.ticker === ticker);

        if (stockIndex === -1 || user.stocks[stockIndex].totalQuantity < quantity) {
            return ({"code": 400, "mesaage": 'Stock not found or insufficient quantity to sell'});
        }

        // Calculate total price for the stock sale
        const totalPrice = user.stocks[stockIndex].price * quantity;

        // Update total amount
        user.totalAmount += totalPrice;

        // Update total quantity of the stock
        user.stocks[stockIndex].totalQuantity -= quantity;

        // Remove stock from portfolio if quantity becomes zero
        if (user.stocks[stockIndex].totalQuantity === 0) {
            user.stocks.splice(stockIndex, 1);
        }

        // Save updated user data
        await user.save();

        return ({message: 'Stock sold successfully'});
    } catch (error) {
        console.error(error);
        return error;
    }
}

async function getAllStocks() {
    try {
        const user = await userPortfolio.findOne();
        return user || [];
    } catch (error) {
        throw error;
    }
}


async function addTowatchlist(name, symbol) {
    try {
        // Check if the stock already exists in the watchlist
        const existingStock = await watchlist.findOne({symbol});

        if (existingStock) {
            throw new Error('Stock already exists in the watchlist');
        }

        // Create a new watchlist entry
        const newStock = new watchlist({name, symbol});
        await newStock.save();

        return {message: 'Stock added to watchlist successfully'};
    } catch (error) {
        throw error;
    }
}

async function removeFromwatchlist(symbol) {
    try {
        // Find and remove the stock from the watchlist
        const removedStock = await watchlist.findOneAndDelete({symbol});

        if (!removedStock) {
            throw new Error('Stock not found in the watchlist');
        }

        return {message: 'Stock removed from watchlist successfully'};
    } catch (error) {
        throw error;
    }
}

async function getAllwatchlistStocks() {
    try {
        // Get all stocks from the watchlist
        const stocks = await watchlist.find();
        return stocks;
    } catch (error) {
        throw error;
    }
}


// Exporting functions to be used in other files
module.exports = {
    searchUtil,
    getLatestPrice,
    getRecommendation,
    getMarketStatus,
    getCompanyDetails,
    getCompanyPeers,
    getInsigntSettlement,
    getCompanyEarnings,
    getChartData,
    getCompanyNews,
    BuyStock,
    sellStock,
    getAllStocks,
    addTowatchlist,
    removeFromwatchlist,
    getAllwatchlistStocks
};
