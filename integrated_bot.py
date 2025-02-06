#!/usr/bin/env python3
"""
integrated_bot.py

An integrated bot that:
  - Runs a Flask web dashboard (with Phantom wallet integration and Dexscreener top trader tracker).
  - Listens in real time to tweets from specified X accounts.
  - Performs social media sentiment analysis on incoming tweets.
  - Detects tweets about new tokens (by checking for wallet addresses in the tweet text).
  - Immediately executes a simulated trade on Raydium if conditions are met.
  
Develop and run this file on Cursor.
"""

import os
import re
import time
import random
import threading
import logging
import requests
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request
from dotenv import load_dotenv
from flask_socketio import SocketIO, emit
import eventlet
from tweepy import StreamingClient, StreamRule, Client
import tweepy
from nltk.sentiment import SentimentIntensityAnalyzer
from flask_cors import CORS

# --- Flask & Web Dashboard Imports ---
# (Flask is used for a simple web dashboard.)

# --- Twitter Streaming & Sentiment Analysis Imports ---
import tweepy
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

# Download the VADER lexicon if not already available.
nltk.download('vader_lexicon', quiet=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# --------------------------------------------------------------------
# Configuration & Environment Variables
# --------------------------------------------------------------------
# Twitter API credentials (for streaming)
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "YOUR_TWITTER_BEARER_TOKEN_HERE")
# (If using additional Twitter API keys, add them as needed.)

# List of Twitter usernames (without the "@") to track
TRACKED_TWITTER_ACCOUNTS = [
    "elonmusk",           # High-profile crypto influencer
    "SBF_FTX",           # Example crypto figure
    "cz_binance",        # Binance CEO
    "solana",            # Official Solana account
    "raydium_io"         # Raydium DEX account
]

# Hypothetical Dexscreener API endpoint for top traders
DEXSCREENER_TOP_TRADERS_API_URL = "https://api.dexscreener.com/latest/traders"

# Add this near the top of the file, after the TRACKED_TWITTER_ACCOUNTS definition
twitter_stream = None

# Add after existing global variables
whale_activity_data = []

# Add near your other global variables
user_settings = {
    "trade_amount": 0.5,  # SOL
    "stop_loss": 5,       # percent
    "risk_reward": 3      # ratio
}

# --------------------------------------------------------------------
# Flask Web Dashboard (Phantom Wallet & Dexscreener Tracker)
# --------------------------------------------------------------------
app = Flask(__name__)
CORS(app)  # Enable CORS
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

# Update the INDEX_HTML template to include Bootstrap and new UI elements
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Solana Trade Bot Dashboard</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <style>
        body { padding-top: 70px; }
        .section { margin-bottom: 30px; }
    </style>
</head>
<body>
    <!-- Navigation Bar -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark fixed-top">
        <a class="navbar-brand" href="#">Solana Trade Bot</a>
        <div class="collapse navbar-collapse">
            <ul class="navbar-nav mr-auto">
                <li class="nav-item active">
                    <a class="nav-link" id="dashboardTab" data-toggle="tab" href="#dashboard">Dashboard</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" id="tradeLogsTab" data-toggle="tab" href="#tradeLogs">Trade Logs</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" id="settingsTab" data-toggle="tab" href="#settings">Settings</a>
                </li>
            </ul>
        </div>
    </nav>

    <!-- Tab Content -->
    <div class="container">
        <div class="tab-content">
            <!-- Dashboard Tab -->
            <div class="tab-pane fade show active" id="dashboard">
                <div class="section">
                    <h3>Phantom Wallet</h3>
                    <button class="btn btn-primary" id="connectWalletBtn">Connect Phantom Wallet</button>
                    <p id="walletAddress" class="mt-2">Not connected</p>
                </div>
                <div class="section">
                    <h3>Top Trader Wallets (Dexscreener)</h3>
                    <button class="btn btn-secondary mb-2" id="refreshTopTradersBtn">Refresh Top Traders</button>
                    <table class="table table-striped" id="topTradersTable">
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>Wallet Address</th>
                                <th>Volume</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td colspan="3">Loading data...</td></tr>
                        </tbody>
                    </table>
                </div>
                <div class="section">
                    <h3>Whale Activity</h3>
                    <button class="btn btn-secondary mb-2" id="refreshWhaleBtn">Refresh Whale Activity</button>
                    <table class="table table-striped" id="whaleActivityTable">
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Wallet</th>
                                <th>Amount (SOL)</th>
                                <th>Type</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td colspan="4">Loading data...</td></tr>
                        </tbody>
                    </table>
                </div>
                <div class="section">
                    <h3>Tracked Twitter Accounts</h3>
                    <div class="input-group mb-3">
                        <input type="text" class="form-control" id="twitterUsername" 
                               placeholder="Enter Twitter username (without @)">
                        <div class="input-group-append">
                            <button class="btn btn-primary" id="addTwitterAccount">Add Account</button>
                        </div>
                    </div>
                    <div id="trackedAccounts" class="mb-3">
                        <!-- Tracked accounts will appear here -->
                    </div>
                    <div class="card">
                        <div class="card-header">
                            Live Tweet Feed
                        </div>
                        <div class="card-body">
                            <div id="tweetFeed" style="max-height: 400px; overflow-y: auto;">
                                <!-- Real-time tweets will appear here -->
                            </div>
                        </div>
                    </div>
                </div>
                <div class="section">
                    <h3>Simulate Trade</h3>
                    <button class="btn btn-warning" id="simulateTradeBtn">Simulate Trade on Raydium</button>
                    <div id="tradeResult" class="mt-2"></div>
                </div>
            </div>

            <!-- Trade Logs Tab -->
            <div class="tab-pane fade" id="tradeLogs">
                <h3>Trade Logs</h3>
                <div id="tradeLogsContent">Coming Soon...</div>
            </div>

            <!-- Settings Tab -->
            <div class="tab-pane fade" id="settings">
                <h3>Settings</h3>
                <form id="settingsForm">
                    <div class="form-group">
                        <label for="tradeAmountInput">Trade Amount (SOL):</label>
                        <input type="number" class="form-control" id="tradeAmountInput" min="0.1" max="1" step="0.1" value="0.5">
                    </div>
                    <div class="form-group">
                        <label for="stopLossInput">Stop Loss (%):</label>
                        <input type="number" class="form-control" id="stopLossInput" min="1" max="10" step="0.5" value="5">
                    </div>
                    <div class="form-group">
                        <label for="riskRewardInput">Risk Reward Ratio:</label>
                        <input type="number" class="form-control" id="riskRewardInput" min="1" max="10" step="1" value="3">
                    </div>
                    <button type="submit" class="btn btn-success">Save Settings</button>
                </form>
                <div id="settingsStatus" class="mt-2"></div>
            </div>
        </div>
    </div>

    <!-- JavaScript Libraries -->
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@4.5.2/dist/js/bootstrap.bundle.min.js"></script>

    <script>
        // First, check if Phantom is available
        const getProvider = () => {
            if ('phantom' in window) {
                const provider = window.phantom?.solana;

                if (provider?.isPhantom) {
                    return provider;
                }
            }

            window.open('https://phantom.app/', '_blank');
            throw new Error('Please install Phantom wallet');
        };

        async function connectPhantomWallet() {
            try {
                const provider = getProvider(); // This will handle availability check
                
                // Connect to wallet
                const resp = await provider.connect();
                const publicKey = resp.publicKey.toString();
                
                // Update UI
                const btn = document.getElementById('connectWalletBtn');
                btn.textContent = 'Connected';
                document.getElementById('walletAddress').textContent = 
                    `Connected: ${publicKey.slice(0,4)}...${publicKey.slice(-4)}`;
                
                // Store wallet info
                localStorage.setItem('phantomWallet', publicKey);
                
                return publicKey;
            } catch (err) {
                console.error("Error connecting to Phantom wallet:", err);
                if (err.message !== 'Please install Phantom wallet') {
                    alert(`Error connecting wallet: ${err.message}`);
                }
                return null;
            }
        }

        async function disconnectPhantomWallet() {
            try {
                const provider = getProvider();
                await provider.disconnect();
                document.getElementById('connectWalletBtn').textContent = 'Connect Phantom Wallet';
                document.getElementById('walletAddress').textContent = 'Not connected';
                localStorage.removeItem('phantomWallet');
            } catch (err) {
                console.error("Error disconnecting wallet:", err);
            }
        }

        // Initialize wallet connection on page load
        document.addEventListener('DOMContentLoaded', async function() {
            const btn = document.getElementById('connectWalletBtn');
            
            // Add click handler
            btn.addEventListener('click', async function() {
                if (btn.textContent === 'Connect Phantom Wallet') {
                    await connectPhantomWallet();
                } else {
                    await disconnectPhantomWallet();
                }
            });

            // Check if previously connected
            try {
                const provider = getProvider();
                const savedWallet = localStorage.getItem('phantomWallet');
                
                if (savedWallet && provider.isConnected) {
                    btn.textContent = 'Connected';
                    document.getElementById('walletAddress').textContent = 
                        `Connected: ${savedWallet.slice(0,4)}...${savedWallet.slice(-4)}`;
                }
            } catch (err) {
                console.error("Error checking wallet connection:", err);
                localStorage.removeItem('phantomWallet');
            }
        });

        // Fetch Top Traders Data
        async function fetchTopTraders() {
            try {
                const response = await fetch("/api/top-traders");
                const data = await response.json();
                let tbody = document.querySelector("#topTradersTable tbody");
                tbody.innerHTML = "";
                if (data.traders.length === 0) {
                    tbody.innerHTML = "<tr><td colspan='3'>No data available</td></tr>";
                } else {
                    data.traders.forEach((trader, index) => {
                        tbody.innerHTML += `<tr>
                            <td>${index+1}</td>
                            <td>${trader.wallet}</td>
                            <td>${trader.volume}</td>
                        </tr>`;
                    });
                }
            } catch(err) {
                console.error("Error fetching top traders", err);
                document.querySelector("#topTradersTable tbody").innerHTML = 
                    "<tr><td colspan='3'>Error loading data</td></tr>";
            }
        }

        // Auto-refresh data
        setInterval(fetchTopTraders, 30000);  // Every 30 seconds
        setInterval(fetchWhaleActivity, 30000);

        // Initialize everything when page loads
        document.addEventListener('DOMContentLoaded', function() {
            fetchTopTraders();
            fetchWhaleActivity();
        });

        // Twitter Account Management
        async function loadTrackedAccounts() {
            try {
                const response = await fetch('/api/twitter/tracked-accounts');
                const data = await response.json();
                updateTrackedAccountsDisplay(data.accounts);
            } catch (err) {
                console.error('Error loading tracked accounts:', err);
            }
        }

        function updateTrackedAccountsDisplay(accounts) {
            const container = document.getElementById('trackedAccounts');
            container.innerHTML = accounts.map(username => `
                <span class="badge badge-primary mr-2 mb-2 p-2">
                    @${username}
                    <button type="button" class="btn-close ml-2" 
                            onclick="untrackAccount('${username}')">&times;</button>
                </span>
            `).join('');
        }

        async function addTwitterAccount() {
            const input = document.getElementById('twitterUsername');
            const username = input.value.trim().replace('@', '');
            if (!username) return;

            try {
                const response = await fetch('/api/twitter/track', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ username })
                });
                
                const data = await response.json();
                if (data.status === 'success') {
                    input.value = '';
                    loadTrackedAccounts();
                } else {
                    alert(data.message);
                }
            } catch (err) {
                console.error('Error adding account:', err);
                alert('Failed to add account');
            }
        }

        async function untrackAccount(username) {
            try {
                const response = await fetch('/api/twitter/untrack', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ username })
                });
                
                const data = await response.json();
                if (data.status === 'success') {
                    loadTrackedAccounts();
                } else {
                    alert(data.message);
                }
            } catch (err) {
                console.error('Error removing account:', err);
                alert('Failed to remove account');
            }
        }

        // WebSocket connection for real-time tweets
        const socket = io();
        socket.on('new_tweet', function(tweet) {
            const tweetFeed = document.getElementById('tweetFeed');
            const tweetElement = document.createElement('div');
            tweetElement.className = 'alert alert-info mb-2';
            
            let signalBadge = '';
            if (tweet.signals.should_trade) {
                signalBadge = `
                    <span class="badge badge-warning">
                        Trading Signal Detected
                    </span>`;
            }
            
            tweetElement.innerHTML = `
                <small class="text-muted">@${tweet.author} - ${new Date(tweet.created_at).toLocaleTimeString()}</small>
                ${signalBadge}
                <p class="mb-1">${tweet.text}</p>
            `;
            
            tweetFeed.insertBefore(tweetElement, tweetFeed.firstChild);
            if (tweetFeed.children.length > 50) {
                tweetFeed.removeChild(tweetFeed.lastChild);
            }
        });

        // Add event listeners
        document.getElementById('addTwitterAccount').addEventListener('click', addTwitterAccount);
        document.getElementById('twitterUsername').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                addTwitterAccount();
            }
        });

        // Load tracked accounts on page load
        loadTrackedAccounts();
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/api/top-traders")
def api_top_traders():
    try:
        response = requests.get(DEXSCREENER_TOP_TRADERS_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        traders = data.get("traders", [])
        logging.info("Fetched top traders data from Dexscreener.")
    except Exception as e:
        logging.error("Error fetching top traders: %s", e)
        traders = [
            {"wallet": "7Tz...dummy1", "volume": 1200},
            {"wallet": "9Xf...dummy2", "volume": 950},
            {"wallet": "3Ab...dummy3", "volume": 870}
        ]
    return jsonify({"traders": traders})

# --------------------------------------------------------------------
# Trade Simulation Module (Integrated with Raydium)
# --------------------------------------------------------------------
class TradeParameters:
    def __init__(self, trade_amount, slippage_tolerance, take_profit_multiplier,
                 moonbag_percentage, priority_fee, stop_loss_percent=5,
                 max_risk_percent=2, risk_reward_ratio=3):
        self.trade_amount = trade_amount                # e.g., 0.5 SOL (0.1 to 1 SOL range)
        self.slippage_tolerance = slippage_tolerance      # e.g., (15, 25) %
        self.take_profit_multiplier = take_profit_multiplier  # e.g., 10x
        self.moonbag_percentage = moonbag_percentage      # e.g., 15%
        self.priority_fee = priority_fee                  # e.g., 0.01 SOL
        # New risk management parameters
        self.stop_loss_percent = stop_loss_percent
        self.max_risk_percent = max_risk_percent
        self.risk_reward_ratio = risk_reward_ratio

class TradeOrder:
    def __init__(self, token_symbol, entry_price, trade_params: TradeParameters):
        self.token_symbol = token_symbol
        self.entry_price = entry_price
        self.trade_params = trade_params
        self.target_price = entry_price * trade_params.take_profit_multiplier

    def simulate_trade_execution(self):
        applied_slippage = random.uniform(*self.trade_params.slippage_tolerance)
        effective_price = self.entry_price * (1 + applied_slippage / 100)
        tokens_acquired = self.trade_params.trade_amount / effective_price
        logging.info(f"[{self.token_symbol}] Trade executed at effective price {effective_price:.4f} SOL "
                     f"(entry {self.entry_price:.4f} SOL, slippage: {applied_slippage:.2f}%). "
                     f"Tokens acquired: {tokens_acquired:.4f}")
        return tokens_acquired, effective_price, applied_slippage

class TradeManager:
    def __init__(self):
        pass

    def place_trade(self, token_symbol, entry_price, trade_params: TradeParameters):
        logging.info(f"Placing trade for {token_symbol}: Entry price = {entry_price} SOL, "
                     f"Trade amount = {trade_params.trade_amount} SOL, Priority fee = {trade_params.priority_fee} SOL.")
        order = TradeOrder(token_symbol, entry_price, trade_params)
        tokens_acquired, effective_price, applied_slippage = order.simulate_trade_execution()
        trade_details = {
            "token": token_symbol,
            "entry_price": entry_price,
            "effective_price": effective_price,
            "tokens_acquired": tokens_acquired,
            "applied_slippage": applied_slippage,
            "target_price": order.target_price,
            "trade_amount": trade_params.trade_amount,
            "priority_fee": trade_params.priority_fee,
            "moonbag_percentage": trade_params.moonbag_percentage
        }
        logging.info(f"Trade details: {trade_details}")
        return trade_details

    def monitor_trade(self, trade_details, current_price):
        target_price = trade_details["target_price"]
        token = trade_details["token"]
        if current_price >= target_price:
            logging.info(f"[{token}] Target reached: Current price {current_price:.4f} SOL >= Target price {target_price:.4f} SOL.")
            tokens_acquired = trade_details["tokens_acquired"]
            retention_ratio = trade_details["moonbag_percentage"] / 100
            tokens_to_sell = tokens_acquired * (1 - retention_ratio)
            moonbag = tokens_acquired - tokens_to_sell
            logging.info(f"[{token}] Executing take profit: Selling {tokens_to_sell:.4f} tokens, "
                         f"retaining {moonbag:.4f} tokens as moonbag.")
            return {
                "take_profit_executed": True,
                "tokens_sold": tokens_to_sell,
                "moonbag": moonbag,
                "current_price": current_price,
                "target_price": target_price
            }
        else:
            logging.info(f"[{token}] Trade active: Current price {current_price:.4f} SOL is below target {target_price:.4f} SOL.")
            return {"take_profit_executed": False}

def execute_trade_on_raydium(token_symbol, entry_price):
    """
    Simulates executing a trade on the Raydium DEX.
    In a real implementation, you would integrate with Raydium's SDK/RPC.
    """
    # Set trade parameters (you could adjust these or derive them from context)
    params = TradeParameters(
        trade_amount=0.5,              # between 0.1 and 1 SOL
        slippage_tolerance=(15, 25),   # 15-25% slippage
        take_profit_multiplier=10,     # 10x target
        moonbag_percentage=15,         # keep 15% as moonbag
        priority_fee=0.01              # example priority fee in SOL
    )
    manager = TradeManager()
    trade_details = manager.place_trade(token_symbol, entry_price, params)
    # For simulation, assume the current price reaches target immediately.
    simulated_current_price = trade_details["target_price"]
    result = manager.monitor_trade(trade_details, simulated_current_price)
    logging.info(f"Raydium trade execution result: {result}")
    return result

# --------------------------------------------------------------------
# Twitter Streaming & Real-Time Sentiment Analysis
# --------------------------------------------------------------------
# Initialize VADER sentiment analyzer.
sia = SentimentIntensityAnalyzer()

class TwitterStreamListener(StreamingClient):
    def __init__(self, bearer_token, trade_manager):
        super().__init__(bearer_token)
        self.trade_manager = trade_manager
        
    def on_tweet(self, tweet):
        if hasattr(tweet, 'text'):  # Ensure tweet has text content
            # Parse tweet for trading signals
            signals = self.parse_trading_signals(tweet.text)
            
            if signals:
                # Emit to frontend via socketio
                tweet_data = {
                    "id": tweet.id,
                    "text": tweet.text,
                    "author": tweet.author_id,
                    "created_at": tweet.created_at.isoformat(),
                    "signals": signals
                }
                socketio.emit('new_tweet', tweet_data)
                
                # Execute trade if signals warrant it
                if signals.get('should_trade', False):
                    self.trade_manager.execute_trade(signals)
    
    def parse_trading_signals(self, text):
        signals = {
            'should_trade': False,
            'token_address': None,
            'token_symbol': None,
            'sentiment': 0
        }
        
        # Look for Solana token addresses
        sol_address_match = re.search(r'[1-9A-HJ-NP-Za-km-z]{32,44}', text)
        if sol_address_match:
            signals['token_address'] = sol_address_match.group(0)
            signals['should_trade'] = True
            
        # Look for cashtags or token symbols
        token_matches = re.findall(r'\$([A-Za-z0-9]+)', text)
        if token_matches:
            signals['token_symbol'] = token_matches[0]
            signals['should_trade'] = True
            
        return signals

def start_twitter_stream():
    # Create an instance of our stream listener using our bearer token.
    stream = TwitterStreamListener(
        bearer_token=TWITTER_BEARER_TOKEN,
        trade_manager=trade_manager
    )
    
    # Build a query rule to listen for tweets from our tracked accounts.
    # Using Twitter API v2 syntax, we add rules like: "from:username"
    # Note: You might need to convert usernames to user IDs in production.
    rules = []
    for username in TRACKED_TWITTER_ACCOUNTS:
        rule_value = f"from:{username}"
        rules.append(StreamRule(value=rule_value, tag=username))
    
    # Remove any preexisting rules, then add our new ones.
    existing_rules = stream.get_rules().data
    if existing_rules is not None:
        rule_ids = [rule.id for rule in existing_rules]
        stream.delete_rules(rule_ids)
    stream.add_rules(rules)
    logging.info(f"Twitter stream rules added: {rules}")
    
    # Start streaming (filtering mode).
    stream.filter(threaded=True)  # Run in a separate thread

# --------------------------------------------------------------------
# Main – Launch Flask App and Twitter Stream in Parallel
# --------------------------------------------------------------------
def validate_twitter_credentials():
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    
    if not bearer_token or bearer_token == "your_actual_twitter_bearer_token_here":
        logging.error("""
        Twitter Bearer Token not found!
        
        Please follow these steps:
        1. Go to https://developer.twitter.com/en/portal/dashboard
        2. Create or select your app
        3. Get your Bearer Token
        4. Add it to your .env file as:
           TWITTER_BEARER_TOKEN=your_actual_token_here
        """)
        raise ValueError("Twitter Bearer Token not properly configured")
    
    return bearer_token

class TwitterManager:
    def __init__(self):
        load_dotenv()  # Load environment variables
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        if not self.bearer_token or self.bearer_token == "YOUR_TWITTER_BEARER_TOKEN_HERE":
            raise ValueError("Twitter Bearer Token not configured properly in .env file")
        
        # Initialize Twitter client
        self.client = Client(bearer_token=self.bearer_token)
        self.stream = None
    
    def test_connection(self):
        """Test Twitter API connection"""
        try:
            # Try to get a test user (e.g., Twitter's official account)
            response = self.client.get_user(username="Twitter")
            if response.data:
                logging.info("Twitter API connection successful!")
                return True
            return False
        except Exception as e:
            logging.error(f"Twitter API connection failed: {e}")
            return False

    def start_stream(self, accounts_to_track):
        """Start Twitter stream with specified accounts"""
        try:
            if self.stream:
                self.stream.disconnect()
            
            self.stream = TwitterStreamListener(
                bearer_token=self.bearer_token,
                trade_manager=trade_manager
            )
            
            # Clear existing rules
            existing_rules = self.stream.get_rules()
            if existing_rules.data:
                rule_ids = [rule.id for rule in existing_rules.data]
                self.stream.delete_rules(rule_ids)
            
            # Add new rules
            rules = [StreamRule(value=f"from:{username}") for username in accounts_to_track]
            if rules:
                self.stream.add_rules(rules)
                self.stream.filter(tweet_fields=['author_id', 'created_at'], threaded=True)
                logging.info(f"Started streaming {len(accounts_to_track)} accounts")
                return True
            
            logging.warning("No accounts to track")
            return False
            
        except Exception as e:
            logging.error(f"Error starting Twitter stream: {e}")
            return False

def initialize_twitter():
    """Initialize Twitter connection and return manager"""
    try:
        twitter_manager = TwitterManager()
        if twitter_manager.test_connection():
            return twitter_manager
        raise ValueError("Failed to establish Twitter connection")
    except Exception as e:
        logging.error(f"Twitter initialization failed: {e}")
        raise

def main():
    try:
        # Initialize Twitter
        twitter_manager = initialize_twitter()
        logging.info("Twitter API initialized successfully")
        
        # Start tracking configured accounts
        if TRACKED_TWITTER_ACCOUNTS:
            twitter_manager.start_stream(TRACKED_TWITTER_ACCOUNTS)
        
        # Start Flask app
        logging.info("Starting web server on http://localhost:5002")
        socketio.run(app, debug=True, port=5002, host='0.0.0.0')
        
    except Exception as e:
        logging.error(f"Application startup failed: {e}")
        raise

# Update the Twitter management routes
@app.route("/api/twitter/tracked-accounts", methods=["GET"])
def get_tracked_accounts():
    return jsonify({"accounts": TRACKED_TWITTER_ACCOUNTS})

@app.route("/api/twitter/track", methods=["POST"])
def track_twitter_account():
    data = request.get_json()
    username = data.get("username", "").strip().replace("@", "")
    
    if not username:
        return jsonify({"status": "error", "message": "Invalid username"}), 400
        
    try:
        # Verify the account exists using Twitter API
        user = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN).get_user(username=username)
        user_id = user.data.id
        
        if username not in TRACKED_TWITTER_ACCOUNTS:
            TRACKED_TWITTER_ACCOUNTS.append(username)
            # Update stream rules
            restart_twitter_stream()
            
        return jsonify({
            "status": "success",
            "message": f"Now tracking @{username}",
            "user_id": user_id
        })
    except Exception as e:
        logging.error(f"Error adding Twitter account: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error adding account: {str(e)}"
        }), 400

@app.route("/api/twitter/untrack", methods=["POST"])
def untrack_twitter_account():
    data = request.get_json()
    username = data.get("username", "").strip().replace("@", "")
    
    if username in TRACKED_TWITTER_ACCOUNTS:
        TRACKED_TWITTER_ACCOUNTS.remove(username)
        restart_twitter_stream()
        return jsonify({"status": "success", "message": f"Stopped tracking @{username}"})
    
    return jsonify({"status": "error", "message": "Account not found"}), 404

def restart_twitter_stream():
    global twitter_stream
    try:
        if twitter_stream:
            twitter_stream.disconnect()
        
        # Validate token before creating new stream
        bearer_token = validate_twitter_credentials()
        
        # Create new stream
        twitter_stream = TwitterStreamListener(
            bearer_token=bearer_token,
            trade_manager=trade_manager
        )
        
        # Clear existing rules
        existing_rules = twitter_stream.get_rules()
        if existing_rules.data:
            rule_ids = [rule.id for rule in existing_rules.data]
            twitter_stream.delete_rules(rule_ids)
        
        # Add new rules for each tracked account
        rules = [StreamRule(value=f"from:{username}") for username in TRACKED_TWITTER_ACCOUNTS]
        if rules:  # Only add rules if we have accounts to track
            twitter_stream.add_rules(rules)
            
            # Start streaming
            twitter_stream.filter(tweet_fields=['author_id', 'created_at'], threaded=True)
            
            logging.info(f"Twitter stream restarted with {len(TRACKED_TWITTER_ACCOUNTS)} accounts")
        else:
            logging.info("No accounts to track. Stream ready but inactive.")
            
    except ValueError as ve:
        logging.error(f"Twitter configuration error: {ve}")
        raise
    except Exception as e:
        logging.error(f"Error restarting Twitter stream: {str(e)}")
        raise

# Add before main()
def scalping_algorithm():
    """
    Simulates an automated sniping and scalping strategy.
    """
    while True:
        time.sleep(5)  # Check every 5 seconds
        token_symbol = "SCALP"
        current_price = 1.0 * random.uniform(0.95, 1.05)
        if random.random() < 0.3:  # 30% chance of trigger
            logging.info(f"Scalping trigger: Rapid move for {token_symbol} at {current_price:.4f} SOL.")
            execute_trade_on_raydium(token_symbol, current_price)

def monitor_whale_activity():
    """
    Simulates monitoring on-chain data for whale activity.
    """
    global whale_activity_data
    while True:
        time.sleep(10)
        if random.random() < 0.2:  # 20% chance of whale event
            event = {
                "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "wallet": f"0x{random.randint(10**39, 10**40-1):x}"[:42],
                "amount": round(random.uniform(50, 200), 2),
                "type": random.choice(["buy", "sell"])
            }
            whale_activity_data.append(event)
            logging.info(f"Whale event detected: {event}")
        whale_activity_data = whale_activity_data[-50:]  # Keep last 50 events

@app.route("/api/whale-activity")
def api_whale_activity():
    return jsonify({"activities": whale_activity_data})

# Add near your other routes
@app.route("/api/save-settings", methods=["POST"])
def save_settings():
    global user_settings
    data = request.get_json()
    if data:
        user_settings["trade_amount"] = float(data.get("tradeAmount", 0.5))
        user_settings["stop_loss"] = float(data.get("stopLoss", 5))
        user_settings["risk_reward"] = float(data.get("riskReward", 3))
        return jsonify({"message": "Settings updated successfully."})
    return jsonify({"message": "Invalid settings."}), 400

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Shutting down gracefully...")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
