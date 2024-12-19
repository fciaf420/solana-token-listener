# Solana Token Listener Bot

A Telegram bot that monitors channels for Solana token contract addresses, forwards them to a target channel, and tracks token market cap multiples using Jupiter API.

## Features

### Token Monitoring
- Monitors specified Telegram channels for Solana token contract addresses
- Forwards found tokens to a target channel
- Supports multiple source channels
- User filtering per channel
- Keyword blacklist/whitelist

### Token Market Cap Tracking
- Automatically tracks market cap for tokens you buy
- Notifies you when tokens hit new multipliers (2x, 3x, etc.)
- Uses Jupiter API for real-time market cap updates (600 calls/minute)
- Batch processing for efficient tracking of multiple tokens
- Tracks any whole number multiple (2x, 3x, ..., 15x, 22x, etc.)
- Automatically removes tokens when sell messages are detected

### Message Detection
- Buy Message Format:
  ```
  Buy $TOKEN - (details)
  CA: ADDRESS
  MC: $100K
  ```
- Sell Message Format:
  ```
  Sell $TOKEN - (details)
  🟢 sell success
  ```
- Supports various message formats and links:
  - Birdeye links
  - DexScreener links
  - Solscan links
  - Jupiter links
  - Raw contract addresses

### Interactive Menu
- Quick start with saved settings
- Channel configuration
- User filtering
- Keyword management
- Token tracking status
- Real-time monitoring statistics

## Setup

1. Clone the repository:
```bash
git clone [repository-url]
cd [repository-name]
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file from the template:
```bash
cp .env.sample .env
```

4. Fill in your `.env` file:
```env
# Get these from https://my.telegram.org/apps
API_ID=your_api_id
API_HASH=your_api_hash

# Target chat for forwarding tokens (username without @ or channel ID)
TARGET_CHAT=your_target_chat

# Where to send tracking notifications (default: 'me' for Saved Messages)
TRACKING_CHAT=me

# Optional settings
DEBUG=false
```

## Usage

1. Start the bot:
```bash
python main.py
```

2. Main Menu Options:
- `0`: Quick Start - Resume monitoring with saved settings
- `1`: Start Monitoring
- `2`: Configure Channels
- `3`: View Current Settings
- `4`: Manage Keyword Filters
- `5`: View Tracked Tokens
- `6`: Exit

3. Monitoring Commands:
- `feed`: Toggle detailed message feed
- `stats`: Show monitoring statistics
- `add`: Add new channels
- `list`: Show monitored channels
- `remove`: Remove channels
- `tokens`: Show tracked tokens
- `stop`: Stop monitoring

## Token Tracking

### How It Works
1. When you buy a token (message starting with "Buy $"), the bot:
   - Extracts the contract address
   - Records initial market cap from the message
   - Starts tracking the token

2. The tracker:
   - Uses Jupiter API to check market cap every minute
   - Calculates current multiple from initial market cap
   - Sends notification when new whole number multiples are hit (2x, 3x, etc.)
   - Shows current status in startup summary

3. When you sell a token (message starting with "Sell $"):
   - Token is removed from tracking
   - No more notifications for that token
   - Token is added to sold list to prevent re-tracking

### Startup Summary
When starting the bot, you'll see a summary like this:
```
📊 Initial Token Check Summary
==================================================
Initial tokens: 13
🗑️ Removed tokens: 0
✨ Added tokens: 0
📈 Now tracking 13 tokens

📈 Current Token Status:
• TOKEN1: 1.05x ($21,064.51)
• TOKEN2: 0.92x ($26,794.40)
• TOKEN3: 1.12x ($46,476.00)
==================================================
```

### Notifications
You'll receive notifications in your Telegram Saved Messages when tokens hit new multipliers:
```
💰 Token Multiple Alert 💰

🪙 Token: TOKEN_NAME
🎯 Multiple: 5x

📊 Market Cap:
  • Initial: $100,000.00
  • Current: $500,000.00
  • Change: +$400,000.00

⏱ Time since entry: 2h 30m

🔗 Quick Links:
• Birdeye: https://birdeye.so/token/...
• DexScreener: https://dexscreener.com/solana/...
• Solscan: https://solscan.io/token/...
```

### Rate Limiting
- Uses Jupiter API rate limit (600 calls/minute)
- Automatically batches requests for multiple tokens
- Adapts check frequency based on number of tracked tokens
- Minimum 60-second interval between checks per token

## Files
- `main.py`: Main bot logic and Telegram interface
- `token_tracker.py`: Token market cap tracking system using Jupiter API
- `tracked_tokens.json`: Persistent storage of tracked tokens
- `sold_tokens.json`: List of sold tokens to prevent re-tracking
- `.env`: Configuration and API credentials
- `requirements.txt`: Python dependencies

## Dependencies
- telethon
- python-dotenv
- aiohttp
- asyncio
- logging

## Notes
- Initial market cap is taken from the buy message
- Ongoing market cap updates use Jupiter's Price API V2
- Market cap updates are calculated using Jupiter price and on-chain supply data
- Token tracking data is saved between bot restarts
- Notifications are sent to your Telegram Saved Messages by default
- Cleanup checks run every hour to remove sold tokens
- Catchup checks run every 15 minutes to find missed buy/sell signals
  