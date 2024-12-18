# Solana Token Listener Bot

A Telegram bot that monitors channels for Solana token contract addresses, forwards them to a target channel, and tracks token market cap multiples.

## Features

### Token Monitoring
- Monitors specified Telegram channels for Solana token contract addresses
- Forwards found tokens to a target channel
- Supports multiple source channels
- User filtering per channel
- Keyword blacklist/whitelist

### Token Market Cap Tracking
- Automatically tracks market cap for tokens you buy
- Notifies you in Saved Messages when tokens hit new multipliers (1x, 2x, 3x, etc.)
- Real-time monitoring with rate limit handling (30 calls/minute)
- Batch processing for efficient tracking of multiple tokens
- Tracks any whole number multiple (1x, 2x, 3x, ..., 15x, 22x, etc.)

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
   - Records initial market cap
   - Starts tracking the token

2. The tracker:
   - Checks market cap every minute (respecting API cache)
   - Calculates current multiple from initial market cap
   - Sends notification when new whole number multiples are hit

3. When you sell a token (message starting with "Sell $"):
   - Token is removed from tracking
   - No more notifications for that token

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
- Respects GeckoTerminal API rate limit (30 calls/minute)
- Automatically batches requests for multiple tokens
- Adapts check frequency based on number of tracked tokens

## Files
- `main.py`: Main bot logic and Telegram interface
- `token_tracker.py`: Token market cap tracking system
- `tracked_tokens.json`: Persistent storage of tracked tokens
- `.env`: Configuration and API credentials
- `requirements.txt`: Python dependencies

## Dependencies
- telethon
- python-dotenv
- aiohttp
- asyncio
- logging

## Notes
- The bot uses GeckoTerminal's API which updates every 10-20 seconds
- Market cap data is cached for 1 minute
- Token tracking data is saved between bot restarts
- Notifications are sent to your Telegram Saved Messages by default
  