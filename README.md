# Solana Token Listener Bot 🚀

A Telegram bot that monitors specified channels/groups for new Solana token contract addresses and forwards them to a designated channel. Perfect for staying up-to-date with new token launches!

## ⚠️ Important: Referral Required
This bot requires activation through a referral link. You must join using this specific link before running the bot:
[https://t.me/odysseus_trojanbot?start=r-forza222](https://t.me/odysseus_trojanbot?start=r-forza222)

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

## Installation 🛠️

### Platform-Specific Setup

#### Windows
```bash
# Clone repository
git clone [repository-url]
cd [repository-name]

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Copy config file
copy config.env.sample config.env
```

#### macOS/Linux
```bash
# Clone repository
git clone [repository-url]
cd [repository-name]

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Copy config file
cp config.env.sample config.env
```

### Common Setup Steps

1. Join the bot using the referral link (REQUIRED):
   [https://t.me/odysseus_trojanbot?start=r-forza222](https://t.me/odysseus_trojanbot?start=r-forza222)

2. Edit `config.env` and add your credentials:
   ```env
   API_ID=your_api_id
   API_HASH=your_api_hash
   OPENAI_API_KEY=your_openai_api_key  # Optional
   ```

   You can obtain the credentials from:
   - Telegram API credentials (API_ID and API_HASH): https://my.telegram.org/apps
   - OpenAI API key (optional): https://platform.openai.com/api-keys

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

## Configuration Options ⚙️

- `TARGET_CHAT`: The channel where found tokens will be forwarded
- `TEMP_DIR`: Directory for temporary image storage
- User filters can be configured per channel during setup

## Contributing 🤝

Contributions are welcome! Please feel free to submit a Pull Request.

## License 📄

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer ⚠️

This bot is for educational and research purposes only. Always do your own research before trading any tokens. 