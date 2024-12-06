# Solana Token Listener Bot

A Telegram bot that monitors specified channels/groups for Solana token contract addresses and forwards them to a target chat.

## Features 🌟

- Monitor multiple Telegram channels/groups
- Extract Solana contract addresses from text and images
- Forward found tokens to a specified target chat
- Optional image analysis using OpenAI's GPT-4 Vision
- User filtering per channel
- Duplicate token detection
- Health monitoring and statistics

## Prerequisites 📋

- Python 3.8 or higher
- Telegram API credentials from https://my.telegram.org/apps
- (Optional) OpenAI API key for image analysis

## Installation 🚀

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/solana-token-listener.git
   cd solana-token-listener
   ```

2. Create and activate a virtual environment:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration ⚙️

1. Copy the sample config file:
   ```bash
   # Windows
   copy config.env.sample config.env
   
   # Linux/macOS
   cp config.env.sample config.env
   ```

2. Edit `config.env` with your credentials:
   ```env
   API_ID=your_api_id
   API_HASH=your_api_hash
   TARGET_CHAT=your_target_chat
   ```

### Important Setup Notes 📝

1. **First Time Setup**:
   - On first run, you'll need to verify your phone number
   - Enter the number in international format (e.g., +1234567890)
   - Enter the verification code sent to your Telegram

2. **Target Chat Setup**:
   - Set `TARGET_CHAT` to the username without @ (e.g., `TARGET_CHAT="channelname"`)
   - Make sure you're a member of the target chat
   - You need permission to send messages in the target chat

3. **Channel Selection**:
   - The bot will show a list of available channels
   - Select channels by entering their indices (e.g., 1,3,5)
   - You can monitor all users or select specific users per channel

4. **Troubleshooting**:
   - If you can't see channels, verify your API credentials
   - If you can't send messages, check your permissions in the target chat
   - For image analysis issues, verify your OpenAI API key

## Usage 🎯

1. Start the bot:
   ```bash
   python main.py
   ```

2. Follow the interactive setup:
   - Verify your phone number (first time only)
   - Select channels to monitor
   - Configure user filters if needed

3. The bot will now:
   - Monitor selected channels
   - Extract Solana contract addresses
   - Forward found tokens to your target chat
   - Show health statistics every hour

## Updating the Bot 🔄

To get the latest updates:

1. **Save your config**
   ```bash
   # Backup your config file
   copy config.env config.env.backup  # Windows
   # OR
   cp config.env config.env.backup    # macOS/Linux
   ```

2. **Pull Updates**
   ```bash
   git pull origin main
   ```

3. **Update Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Restore Config**
   ```bash
   # If there are new config options, merge them manually
   copy config.env.backup config.env  # Windows
   # OR
   cp config.env.backup config.env    # macOS/Linux
   ```

## Health Monitoring 📊

The bot provides regular health updates showing:
- Messages processed
- Tokens forwarded
- Unique tokens found
- Uptime
- Number of monitored chats

## Error Handling 🛠️

The bot includes comprehensive error handling:
- Connection issues
- Authentication problems
- Permission errors
- Message processing errors

## Contributing 🤝

Contributions are welcome! Please feel free to submit a Pull Request.

## License 📄

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer ⚠️

This bot is for educational and research purposes only. Always do your own research before trading any tokens.

## Support 💬

If you need help:
1. Check the troubleshooting section
2. Review error messages in the logs
3. Open an issue on GitHub
  