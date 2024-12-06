# Simple Solana Listener

A Telegram bot that monitors specified channels for Solana token contract addresses and provides detailed information about them.

## Features

- Monitor multiple Telegram channels/groups
- Detect Solana token contract addresses
- Fetch token information from blockchain
- Forward findings to a designated channel
- Optional image analysis with OpenAI

## Prerequisites

1. Python 3.8 or higher
2. Telegram API credentials from https://my.telegram.org/apps
3. A Telegram account
4. (Optional) OpenAI API key for image analysis

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/solana-token-listener.git
cd solana-token-listener
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Set up environment:
```bash
# Windows
copy .env.sample .env

# Linux/Mac
cp .env.sample .env
```

4. Edit `.env` with your credentials:
- API_ID (from https://my.telegram.org/apps)
- API_HASH (from https://my.telegram.org/apps)
- TARGET_CHAT (will be configured on first run)
- OPENAI_API_KEY (optional, for image analysis)

## Usage

1. Start the bot:
```bash
python main.py
```

2. On first run:
- Enter your phone number
- Enter the verification code sent to your Telegram
- Select target chat for forwarding messages

3. The bot will now:
- Monitor specified channels
- Detect Solana contract addresses
- Forward findings to your target chat

## Configuration

The `.env` file contains all configuration options:

```ini
# Required
API_ID=your_api_id
API_HASH=your_api_hash
TARGET_CHAT=@your_channel

# Optional
OPENAI_API_KEY=your_openai_key
DEBUG=false
```

## Backup & Restore

To backup your configuration:
```bash
# Windows
copy .env .env.backup

# Linux/Mac
cp .env .env.backup
```

To restore from backup:
```bash
# Windows
copy .env.backup .env

# Linux/Mac
cp .env.backup .env
```

## Troubleshooting

1. **Authentication Failed**
   - Verify API_ID and API_HASH in `.env`
   - Try removing the session file and restart

2. **Can't Access Channel**
   - Ensure you're a member of the channel
   - Check if TARGET_CHAT is correct

3. **No Contract Addresses Found**
   - Verify the channels you're monitoring
   - Check if messages contain valid Solana addresses

## Contributing

Pull requests are welcome! For major changes:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to your branch
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This bot is for educational purposes only. Always verify contract addresses from trusted sources before interacting with them.
  