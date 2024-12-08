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

### Option 1: Using Dev Container (Recommended)
The fastest and most reliable way to get started is using VS Code with Dev Containers. This setup includes:
- Optimized Python 3.12 environment
- Ultra-fast `uv` package manager (10-100x faster than pip)
- Automatic dependency management
- Type checking and code formatting

#### Prerequisites
1. **Install Docker**:
   - **Windows**: 
     1. Enable WSL2 in Windows Features
     2. Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
     3. Run the installer and follow the prompts
     4. Start Docker Desktop
   
   - **Mac**: 
     1. Download [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)
     2. Run the installer
     3. Start Docker from Applications
   
   - **Linux**:
     ```bash
     # Ubuntu/Debian
     sudo apt update
     sudo apt install docker.io
     sudo systemctl start docker
     sudo systemctl enable docker
     sudo usermod -aG docker $USER
     # Log out and back in for changes to take effect
     ```

2. **Install VS Code**:
   - Download from [code.visualstudio.com](https://code.visualstudio.com/)
   - Run the installer for your OS
   - Launch VS Code

3. **Install Dev Containers Extension**:
   1. Open VS Code
   2. Press Ctrl+P (Cmd+P on Mac)
   3. Paste: `ext install ms-vscode-remote.remote-containers`
   4. Press Enter

#### Setup Steps
1. Clone this repository:
   ```bash
   git clone https://github.com/your-username/solana-token-listener.git
   cd solana-token-listener
   ```

2. Open in VS Code:
   ```bash
   code .
   ```

3. When prompted "Reopen in Container", click it
   - Or press F1, type "Reopen in Container", and press Enter

The container will automatically:
- Set up the Python environment
- Install dependencies using `uv`
- Configure VS Code settings
- Enable type checking and formatting

### Option 2: Manual Installation with uv
If you prefer not to use containers:
```bash
# Install uv
pip install uv

# Install dependencies using uv (much faster than pip)
uv pip install -r requirements.lock
```

### Option 3: Traditional pip Installation
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
python main.py
```

2. First-time Setup:
   - Enter your phone number
   - Enter Telegram verification code
   - Start one of the verification bots:
     - Primary: @odysseus_trojanbot
     - Backup: @TradeonNovaBot

3. Main Menu Options:
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
  