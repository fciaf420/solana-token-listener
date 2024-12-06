# Telegram Solana Contract Address Listener

A Telegram bot that monitors specified channels for Solana token contract addresses and forwards them to a designated channel. Built with advanced filtering capabilities and health monitoring.

## Features

- Monitor multiple Telegram channels/groups
- User-specific filtering for each monitored channel
- Automatic Solana contract address detection
- Health monitoring and statistics
- Session persistence
- Configurable forwarding to target channel
- Environment settings editor

## Prerequisites

1. Python 3.8 or higher
2. Telegram API credentials from https://my.telegram.org/apps
3. A Telegram account
4. Access to @odysseus_trojanbot with referral code

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

2. Set up environment:
```bash
# Windows
copy .env.sample .env

# Linux/Mac
cp .env.sample .env
```

3. Edit `.env` with your credentials:
```ini
# Required
API_ID=your_api_id
API_HASH=your_api_hash
TARGET_CHAT=@your_channel  # Use @username or -100xxxxx format

# Optional
DEBUG=false
```

## Usage

1. Start the bot:
```bash
python main.py
```

2. Main Menu Options:
   - Start Monitoring: Begin monitoring channels
   - Edit Configuration: Modify channel and filter settings
   - View Current Settings: Display current configuration
   - Edit Environment Settings: Modify .env file settings
   - Exit: Close the bot

3. First-time Setup:
   - Verify access through @odysseus_trojanbot with referral code
   - Enter your phone number (if not previously authenticated)
   - Enter Telegram verification code
   - Enter 2FA password (if enabled)
   - Select channels to monitor
   - Configure user filters for each channel (optional)

4. The bot will then:
   - Monitor selected channels
   - Apply user filters if configured
   - Detect and forward Solana contract addresses
   - Provide hourly health checks

## Configuration Files

### .env
Contains API credentials and basic settings:
```ini
API_ID=your_api_id
API_HASH=your_api_hash
TARGET_CHAT=@your_channel  # Use @username or -100xxxxx format
DEBUG=false
```

### sol_listener_config.json
Stores bot configuration and session data:
```json
{
    "source_chats": [channel_ids],
    "filtered_users": {
        "channel_id": [user_ids]
    },
    "session_string": "your_session_string",
    "target_chat": "target_channel",
    "verified": true
}
```

### processed_tokens.json
Maintains a list of processed token addresses to prevent duplicates.

## Health Monitoring

The bot provides hourly health checks with:
- Connection status
- Messages processed count
- Tokens forwarded count
- Unique tokens tracked
- Uptime statistics
- Number of monitored chats

Health logs are stored in `logs/bot.log`

## User Filtering

For each monitored channel, you can:
1. Monitor all users
2. Monitor specific users by ID
3. Update filters during runtime

## Environment Settings

You can edit these settings through the bot menu:
1. API_ID: Your Telegram API ID
2. API_HASH: Your Telegram API Hash
3. TARGET_CHAT: Destination for found tokens (@username or -100xxxxx format)
4. DEBUG: Enable/disable debug mode

## Troubleshooting

1. **Database Locked Error**
   - Close all Python processes
   - Delete the `solana_listener.session` file
   - Restart the bot

2. **Authentication Failed**
   - Verify API credentials in `.env`
   - Check referral access with @odysseus_trojanbot
   - Clear session files and restart

3. **Access Verification Failed**
   - Ensure you've used the correct referral link
   - Verify bot interaction history
   - Check configuration in `sol_listener_config.json`

4. **No Messages Being Processed**
   - Verify selected channels in configuration
   - Check user filters if configured
   - Ensure bot has access to monitored channels

5. **TARGET_CHAT Format Error**
   - Ensure TARGET_CHAT starts with @ for usernames
   - Or starts with -100 for channel IDs
   - Use the Edit Environment Settings menu to fix

## Security Notes

- Never share your session string or API credentials
- Keep your `.env` and configuration files secure
- Regularly backup your configuration files
- Monitor the health checks for unusual activity

## Disclaimer

This bot is for monitoring purposes only. Always verify contract addresses from trusted sources before interacting with them.
  