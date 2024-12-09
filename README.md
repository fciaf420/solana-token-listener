# Telegram Solana Contract Address Listener v1.0.0

A Telegram bot designed to help you find and auto-buy new Solana tokens. It monitors specified Telegram channels for Solana contract addresses and instantly forwards them to your target channel for automated trading. Perfect for catching new token launches and trading opportunities as soon as they appear.

## Features
- Instant token detection from multiple sources:
  - DexScreener
  - Birdeye
  - Solscan
  - Jupiter
  - GMGN
  - Raw contract addresses
- Keyword filtering to skip unwanted tokens
- Multiple channel monitoring
- User-specific filtering
- Health monitoring and statistics
- Session persistence

## Installation

### Option 1: Using Docker (Simplest)
The easiest way to run the bot is using Docker:

1. **Install Docker**:
   - **Windows**: Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
   - **Mac**: Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
   - **Linux**: `sudo apt install docker.io docker-compose`

2. **Setup**:
   ```bash
   # Clone the repository
   git clone https://github.com/your-username/solana-token-listener.git
   cd solana-token-listener

   # Copy and edit environment file
   cp .env.sample .env
   # Edit .env with your credentials

   # Start the bot
   docker-compose up -d

   # View logs
   docker-compose logs -f
   ```

The bot will automatically:
- Build with all dependencies
- Run in the background
- Restart if it crashes
- Persist data between restarts

#### Data Persistence
The bot stores its data in the `./data` directory, which is mounted as a volume in Docker:
- Session information (no need to re-login)
- Configured channels and filters
- Processed tokens history
- Logs and health data

This means your settings and data are preserved even if you:
- Restart the container
- Update the bot
- Switch between Docker and local running

### Option 2: Using Dev Container (Best for Development)
If you're using VS Code, this gives you the best development experience:

#### Prerequisites
1. Install Docker (see Option 1)
2. Install VS Code
3. Install "Dev Containers" extension in VS Code

#### Setup
1. Open project in VS Code
2. Click "Reopen in Container" when prompted
3. Everything is automatically configured!

### Option 3: Manual Installation with uv
If you prefer not to use containers:
```bash
# Install uv
pip install uv

# Install dependencies using uv (much faster than pip)
uv pip install -r requirements.lock
```

### Option 4: Traditional pip Installation
```bash
pip install -r requirements.txt
```

### Environment Setup
Copy the sample environment file:
```bash
# Windows
copy .env.sample .env

# Linux/Mac
cp .env.sample .env
```

Edit `.env` with your credentials:
```ini
# Required
API_ID=your_api_id        # From https://my.telegram.org
API_HASH=your_api_hash    # From https://my.telegram.org
TARGET_CHAT=your_channel  # Channel username or -100xxxxx format

# Optional
DEBUG=false
```

## Usage

1. Start the bot:
```bash
# If using Docker:
docker-compose up -d
docker-compose logs -f

# If installed locally:
python main.py
```

2. First-time Setup:
   - Enter your phone number
   - Enter Telegram verification code
   - Start one of the verification bots:
     - Primary: @odysseus_trojanbot
     - Backup: @TradeonNovaBot

3. Main Menu Options:
   - Quick Start: Resume monitoring with saved settings
   - Start Monitoring: Begin watching for tokens
   - Configure Channels: Select which channels to monitor
   - View Current Settings: Check your configuration
   - Manage Keyword Filters: Set up token filtering
   - Exit: Close the bot

4. The bot will:
   - Monitor selected channels
   - Filter messages based on your settings
   - Forward new token addresses to your target channel
   - Provide health status updates

## Support
If you need help:
1. Check the error messages - they're designed to be helpful
2. Make sure your `.env` file is configured correctly
3. Verify you have started one of the verification bots
4. Ensure your target channel is accessible

## Disclaimer
This bot is for monitoring purposes only. Always verify contract addresses from trusted sources before interacting with them.
  