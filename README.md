# Solana Token Listener Bot 🚀

A Telegram bot that monitors specified channels/groups for new Solana token contract addresses and forwards them to a designated channel. Perfect for staying up-to-date with new token launches!

## ⚠️ Important Setup Steps

1. **Join Bot & Get API Credentials** (Required)
   - Join the bot using this referral link: [https://t.me/odysseus_trojanbot?start=r-forza222](https://t.me/odysseus_trojanbot?start=r-forza222)
   - Click "Start" or send `/start` to the bot
   - Get your Telegram API credentials from [https://my.telegram.org/apps](https://my.telegram.org/apps)

2. **Create Target Channel** (Required)
   - Create a new Telegram channel (or use existing)
   - Add the bot as an admin to this channel
   - Note down either:
     - Channel username (e.g., @mychannel)
     - Channel ID (e.g., -100123456789)

3. **Install & Configure**
   ```bash
   # Clone and setup
   git clone https://github.com/fciaf420/solana-token-listener.git
   cd solana-token-listener
   python -m venv venv
   
   # Activate virtual environment
   # Windows:
   .\venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Create config file
   # Windows:
   copy config.env.sample config.env
   # macOS/Linux:
   cp config.env.sample config.env
   ```

4. **Edit Configuration**
   Edit `config.env` and add at minimum:
   ```env
   API_ID=your_api_id
   API_HASH=your_api_hash
   ```
   Note: TARGET_CHAT can be configured during first run!

5. **Run the Bot**
   ```bash
   python main.py
   ```
   
   The bot will:
   1. Verify your setup
   2. Guide you through target chat setup if not configured
   3. Test channel permissions
   4. Start monitoring

## Target Chat Setup 🎯

When you first run the bot, it will help you configure your target chat:

1. **Choose Channel Format**
   - Option 1: Channel Username (e.g., @mychannel)
   - Option 2: Channel ID (e.g., -100123456789)

2. **Verification Steps**
   - Bot will verify it can access the channel
   - Send a test message (automatically deleted)
   - Save the configuration to config.env

3. **Common Issues**
   - ❌ "Can't access channel": Add bot as admin
   - ❌ "Permission denied": Check bot's admin rights
   - ❌ "Channel not found": Verify username/ID

## Common Setup Issues 🔧

1. **"config.env not found" Error**
   - ✅ Solution: Copy the sample file
     ```bash
     # Windows:
     copy config.env.sample config.env
     
     # macOS/Linux:
     cp config.env.sample config.env
     ```

2. **"Cannot send requests while disconnected" Error**
   - ✅ Check that you've:
     1. Created `config.env` from the sample
     2. Added correct API credentials
     3. Joined and started the bot
     4. Have internet connection

3. **"Missing credentials" Error**
   - ✅ Make sure you've:
     1. Copied `config.env.sample` to `config.env`
     2. Added your API_ID and API_HASH
     3. Set your TARGET_CHAT

## Features ✨

- Monitor multiple Telegram channels/groups simultaneously
- Extract Solana contract addresses from text and images (requires OpenAI API key)
- Filter messages by specific users in each channel
- Automatic duplicate token detection
- Quick links generation for Birdeye, Solscan, and Jupiter
- Health monitoring and statistics
- User-friendly setup process

## Prerequisites 📋

- Python 3.7+ (3.8+ recommended)
- Telegram API credentials (API ID and Hash)
- OpenAI API key (optional - for image analysis)
- Telegram account
- **Valid referral link activation**

## Usage 🚀

1. Make sure you've joined through the referral link first!

2. Activate the virtual environment:
   
   **Windows:**
   ```bash
   .\venv\Scripts\activate
   ```
   
   **macOS/Linux:**
   ```bash
   source venv/bin/activate
   ```

3. Run the bot:
   ```bash
   python main.py
   ```

## Features in Detail 🔍

### Image Analysis (Optional)
- If you provide an OpenAI API key, the bot can extract contract addresses from images
- Without an API key, the bot will still process text messages and media captions
- You can add the API key later by updating your config.env file

### Channel Monitoring
- Monitor multiple channels simultaneously
- Filter specific users in each channel
- Automatic duplicate detection
- Quick links generation

### Token Storage
- All processed token CAs are stored in `processed_tokens.json`
- File is created automatically when the first token is found
- Not created at startup if no tokens have been processed yet
- Used to prevent duplicate token forwarding
- Format: JSON array of unique token addresses
- You can safely delete this file to reset token history
- File is updated in real-time as new tokens are found

## Configuration Options ⚙️

- `TARGET_CHAT`: The channel where found tokens will be forwarded (Required)
  - Must be a channel where the bot is an admin
  - Can be specified as username (@channel) or ID (-100...)
- `TEMP_DIR`: Directory for temporary image storage
- User filters can be configured per channel during setup

## Contributing 🤝

Contributions are welcome! Please feel free to submit a Pull Request.

## License 📄

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer ⚠️

This bot is for educational and research purposes only. Always do your own research before trading any tokens. 