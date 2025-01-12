# Solana Token Listener Bot 🚀

A Telegram bot that helps you monitor Solana tokens from source chats and track their market performance.

## 🌟 Features

- Monitor specific users in Telegram chats for token mentions
- Forward token contract addresses to your target chat
- Track market cap and price multiples
- Detailed feed showing all monitored messages
- User-friendly setup and configuration

## 📋 Prerequisites

Before you start, you'll need:
1. Python 3.8 or higher installed on your computer
2. A Telegram account
3. Your Telegram API credentials (we'll help you get these!)

## 🔧 Initial Setup

### Step 1: Get Your Telegram API Credentials
1. Visit https://my.telegram.org/auth
2. Log in with your phone number
3. Click on "API development tools"
4. Create a new application (any name and short name will work)
5. Save your `api_id` and `api_hash` - you'll need these later!

### Step 2: Install Python Dependencies
1. Open a terminal/command prompt
2. Navigate to the bot's directory
3. Run this command:
```bash
pip install -r requirements.txt
```

### Step 3: Set Up Environment Variables
1. Find the `.env.sample` file in the project
2. Make a copy and rename it to `.env`
3. Open `.env` and fill in your details:
```
API_ID=your_api_id_here
API_HASH=your_api_hash_here
TARGET_CHAT=your_target_chat_here
TRACKING_CHAT=your_tracking_chat_here
```

## 🚀 Running the Bot

1. Open a terminal/command prompt
2. Navigate to the bot's directory
3. Run:
```bash
python main.py
```

4. On first run:
   - You'll be asked to enter your phone number
   - Telegram will send you a code - enter it when prompted
   - The bot will save your session for future use

## 📱 Basic Commands

When the bot is running, you can use these commands:
- `add` - Add new chats to monitor
- `list` - Show all monitored chats
- `remove` - Remove chats from monitoring
- `feed` - Toggle detailed message feed
- `stats` - Show bot statistics
- `tokens` - Manage tracked tokens
- `stop` - Stop the bot

## 🔍 How It Works

### 1. Source Chat Monitoring
- The bot watches messages in your chosen source chats
- It looks for Solana contract addresses in various formats:
  - Raw addresses
  - DexScreener links
  - Birdeye links
  - Jupiter links
  - And more!

### 2. User Filtering
- For each source chat, you can choose specific users to monitor
- Only messages from these users will be processed
- Other users' messages will be ignored

### 3. Token Forwarding
- When a valid contract address is found, it's forwarded to your target chat
- Each token is only forwarded once to avoid duplicates
- The bot maintains a list of processed tokens

### 4. Market Cap Tracking
- The bot tracks market cap for forwarded tokens
- It checks prices using Jupiter API (with GeckoTerminal as backup)
- You'll get notifications when tokens hit significant multiples (2x, 3x, etc.)

### 5. Detailed Feed
- See every message the bot processes in real-time
- Know exactly why messages are forwarded or filtered
- Track user activity and token discoveries

## ⚙️ Advanced Configuration

### Managing User Filters
1. Use the `add` command to select chats
2. For each chat, you can:
   - Choose specific users to monitor
   - Monitor all users
   - Remove existing filters

### Token Management
1. Use the `tokens` command to:
   - View all tracked tokens
   - Remove specific tokens
   - Clear all tracking data

## 🆘 Troubleshooting

### Common Issues:

1. **Bot won't connect:**
   - Check your internet connection
   - Verify API credentials in .env file
   - Ensure your Telegram session is valid

2. **Messages not forwarding:**
   - Confirm source chat configuration
   - Check user filters
   - Verify target chat settings

3. **Market cap not updating:**
   - Check your internet connection
   - Verify the token contract is valid
   - Wait a few minutes and try again

### Need Help?
- Check the detailed logs in the `logs` directory
- Look for error messages in the console
- Make sure all configuration files exist

## 🔐 Security Notes

- Never share your `session_string` or `.env` file
- Keep your API credentials private
- Don't run multiple instances of the bot with the same session

## 📝 Files You Should Know About

- `.env` - Your private configuration
- `sol_listener_config.json` - Bot settings and filters
- `processed_tokens.json` - List of processed tokens
- `tracked_tokens.json` - Current token tracking data

## 🔄 Updating the Bot

To update to the latest version:
1. Save your `.env` file
2. Pull the latest changes:
```bash
git pull
```
3. Restore your `.env` file if needed
4. Restart the bot

## 💡 Tips

1. Start with one or two source chats until you're comfortable
2. Use the detailed feed to understand what the bot is doing
3. Regularly check your tracked tokens
4. Back up your configuration files
5. Monitor the bot's performance and adjust filters as needed

Need more help? Feel free to reach out!
  