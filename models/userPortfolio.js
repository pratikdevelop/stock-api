const mongoose = require("mongoose");

// Mongoose schema for user portfolio data
const userPortfolioSchema = new mongoose.Schema({
  name: {
    type: String,
    required: true
  },
  email: {
    type: String,
    required: true,
    unique: true, // Ensure email is unique
    match: [/^\S+@\S+\.\S+$/, 'Please use a valid email address.'] // Email format validation
  },
  password: {
    type: String,
    required: true,
    minlength: 6 // Minimum length for the password
  },
  profilePicture: {
    type: String,
    default: 'default-profile-pic.jpg' // Default value for profile picture
  },
  phone: {
    type: String,
    match: [/^\d{10}$/, 'Please provide a valid 10-digit phone number.'] // Phone number validation
  },
  totalAmount: {
    type: Number,
    default: 25000 // Default amount for new user portfolios
  },
  stocks: [{
    ticker: {
      type: String,
      required: true
    },
    name: {
      type: String,
      required: true
    },
    price: {
      type: Number,
      required: true
    },
    totalPrice: {
      type: Number, // Total price for the total quantity of stock bought
      required: true
    },
    totalQuantityBought: {
      type: Number,
      required: true,
      min: [0, 'Quantity cannot be negative.']
    },
    totalQuantity: {
      type: Number,
      required: true,
      min: [0, 'Quantity cannot be negative.']
    }
  }]
}, {
  timestamps: true // Add createdAt and updatedAt fields automatically
});

const UserPortfolio = mongoose.model("UserPortfolio", userPortfolioSchema);

module.exports = UserPortfolio;
