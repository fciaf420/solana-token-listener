import asyncio
import re
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
import logging
from typing import List, Dict
import json
import os
import base64
import aiohttp
import io
import time
import platform
from pathlib import Path
from dotenv import load_dotenv
from telethon.errors import SessionPasswordNeededError
import sys

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleCP(65001)
    kernel32.SetConsoleOutputCP(65001)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Configuration
BOT_USERNAME = "odysseus_trojanbot"
REQUIRED_REF = "r-forza222"  # Required referral code

def load_and_validate_env():
    """Load and validate environment variables"""
    try:
        env_file = '.env'
        if not Path(env_file).exists():
            env_file = 'config.env'
            if not Path(env_file).exists():
                logger.error("❌ No .env or config.env file found!")
                logger.info("Creating .env file with template...")
                with open('.env', 'w') as f:
                    f.write("API_ID=\nAPI_HASH=\nTARGET_CHAT=\nDEBUG=false\n")
                logger.info("Please fill in your credentials in the .env file")
                sys.exit(1)
        
        logger.info(f"📁 Loading environment from: {env_file}")
        load_dotenv(env_file)
        
        # Validate required credentials
        api_id = os.getenv('API_ID')
        api_hash = os.getenv('API_HASH')
        target_chat = os.getenv('TARGET_CHAT')
        
        if not api_id or not api_hash:
            logger.error("❌ API credentials missing! Please get them from https://my.telegram.org/apps")
            sys.exit(1)
            
        # Validate API_ID
        try:
            api_id = int(api_id)
        except (TypeError, ValueError):
            logger.error("❌ API_ID must be a valid integer!")
            sys.exit(1)
        
        return api_id, api_hash, target_chat
        
    except Exception as e:
        logger.error(f"❌ Error loading environment: {str(e)}")
        sys.exit(1)

# Load and validate environment variables
API_ID, API_HASH, TARGET_CHAT = load_and_validate_env()

# Define global variables first
BOT_USERNAME = 'odysseus_trojanbot'
REQUIRED_REF = 'r-forza222'

# Configure logging with platform-specific path
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, "bot.log"), encoding='utf-8')
    ]
)

# Log platform info
logging.info(f"Platform: {platform.system()} {platform.release()}")
logging.info(f"Python version: {platform.python_version()}")

# Config file - use platform-agnostic path
CONFIG_FILE = str(Path('.') / 'sol_listener_config.json')

# Temp directory for downloaded images - use platform-agnostic path
TEMP_DIR = str(Path('.') / 'temp_images')
os.makedirs(TEMP_DIR, exist_ok=True)

class SimpleSolListener:
    def __init__(self):
        """Initialize the bot"""
        session = 'solana_listener'
        self.client = TelegramClient(session, API_ID, API_HASH)
        self.source_chats = []
        self.filtered_users = {}
        self.processed_count = 0
        self.forwarded_count = 0
        self.authorized = False
        self.available_chats = []
        self.dialogs_cache = {}
        self.start_time = time.time()
        
        # Initialize necessary files and directories
        print("\n📁 Initializing file structure...")
        
        # Create necessary directories
        os.makedirs('logs', exist_ok=True)
        os.makedirs('temp_images', exist_ok=True)
        
        # Initialize config
        self.config_file = 'sol_listener_config.json'
        if not os.path.exists(self.config_file):
            print("✨ Creating new configuration file...")
            self.config = {
                'verified': False,
                'source_chats': [],
                'filtered_users': {},
                'target_chat': None
            }
            self.save_config()
        else:
            self.config = self.load_config()
        
        # Initialize processed tokens
        self.tokens_file = 'processed_tokens.json'
        if not os.path.exists(self.tokens_file):
            print("✨ Creating processed tokens file...")
            self.processed_tokens = set()
            self.save_processed_tokens()
        else:
            self.processed_tokens = self.load_processed_tokens()
        
        print("✅ File structure initialized")

    def load_config(self):
        """Load configuration from file"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error loading config: {str(e)}")
            return {}

    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"⚠️ Error saving config: {str(e)}")

    def load_processed_tokens(self) -> set:
        """Load processed tokens from file"""
        try:
            with open(self.tokens_file, 'r') as f:
                return set(json.load(f))
        except Exception as e:
            print(f"⚠️ Error loading processed tokens: {str(e)}")
            return set()

    def save_processed_tokens(self):
        """Save processed tokens to file"""
        try:
            with open(self.tokens_file, 'w') as f:
                json.dump(list(self.processed_tokens), f, indent=4)
        except Exception as e:
            print(f"⚠️ Error saving processed tokens: {str(e)}")

    async def check_referral(self) -> bool:
        """Check if the user joined through the correct referral link or is an existing user"""
        # Check if already verified
        if self.config.get('verified', False):
            print("✅ Access previously verified")
            return True
            
        try:
            print("\n🔍 Checking Telegram connection...")
            
            # First verify we can connect to Telegram
            try:
                await self.client.connect()
                print("✅ Connected to Telegram")
                
                # Handle authentication if needed
                if not await self.client.is_user_authorized():
                    print("\n📱 Phone verification needed")
                    phone = input("Enter your phone number (international format, e.g. +1234567890): ")
                    code = await self.client.send_code_request(phone)
                    verification_code = input("\n📲 Enter the verification code sent to your phone: ")
                    try:
                        await self.client.sign_in(phone, verification_code)
                    except SessionPasswordNeededError:
                        password = input("\n🔐 2FA is enabled. Please enter your password: ")
                        await self.client.sign_in(password=password)
                    print("✅ Successfully verified!")

                print("\n🤖 Checking bot access...")
                try:
                    bot_entity = await self.client.get_input_entity(BOT_USERNAME)
                    print("✅ Found @" + BOT_USERNAME)
                    
                    print("\n🔍 Checking your access status...")
                    # First check if we're already a member by looking at message history
                    messages = []
                    async for message in self.client.iter_messages(bot_entity, limit=10):
                        if message.message:
                            messages.append(message.message)
                    
                    # Check for any previous interaction
                    has_history = len(messages) > 0
                    has_start = any('/start' in msg.lower() for msg in messages)
                    
                    # If there's any history with the bot, consider it verified
                    if has_history or has_start:
                        print("✅ Access verified - Existing bot user!")
                        # Store verification status
                        self.config['verified'] = True
                        self.save_config()
                        return True
                    
                    # If no history, guide user through referral process
                    print("\n👋 Welcome! Let's get you set up...")
                    print("\n📱 Please complete these steps:")
                    print(f"1. Click this link: https://t.me/{BOT_USERNAME}?start={REQUIRED_REF}")
                    print("2. Click 'Start' in the Telegram bot chat")
                    print("3. Press Enter here after clicking Start")
                    input()
                    
                    print("\n🔄 Verifying your access...")
                    # Check for new activation
                    async for message in self.client.iter_messages(bot_entity, limit=3):
                        if message.message and '/start' in message.message.lower():
                            print("✅ Access verified!")
                            # Store verification status
                            self.config['verified'] = True
                            self.save_config()
                            return True
                    
                    print("\n❌ Couldn't verify bot access")
                    print("\nPlease make sure you:")
                    print(f"1. Use this exact link: https://t.me/{BOT_USERNAME}?start={REQUIRED_REF}")
                    print("2. Click 'Start' in the bot chat")
                    print("3. Then run this script again")
                    return False
                    
                except Exception as e:
                    if "BOT_ALREADY_STARTED" in str(e):
                        print("✅ Access verified - Bot already started!")
                        # Store verification status
                        self.config['verified'] = True
                        self.save_config()
                        return True
                    else:
                        print("\n❌ Bot access verification failed")
                        print("\nTroubleshooting steps:")
                        print(f"1. Open this link: https://t.me/{BOT_USERNAME}?start={REQUIRED_REF}")
                        print("2. Click 'Start' in the bot chat")
                        print("3. Run this script again")
                        if "DEBUG" in os.environ and os.environ["DEBUG"].lower() == "true":
                            print(f"\nDebug - Error: {str(e)}")
                        return False
                        
            except Exception as e:
                print(f"\n❌ Connection error: {str(e)}")
                print("\nPlease check:")
                print("1. Your internet connection")
                print("2. Your API credentials in .env file")
                return False
                
        except Exception as e:
            print(f"\n❌ Verification failed: {str(e)}")
            return False

    async def setup_target_chat(self):
        """Interactive setup for target chat"""
        print("\n📋 Target Chat Setup")
        print("=" * 50)
        print("The bot needs a channel where it will forward found tokens.")
        print("\nOptions:")
        print("1. Use channel username (e.g., @mychannel)")
        print("2. Use channel ID (e.g., -100123456789)")
        
        while True:
            choice = input("\nEnter your choice (1-2): ").strip()
            
            if choice == "1":
                channel = input("\nEnter channel username (including @): ").strip()
                if not channel.startswith("@"):
                    print("❌ Channel username must start with @")
                    continue
                return channel
            
            elif choice == "2":
                channel_id = input("\nEnter channel ID: ").strip()
                if not channel_id.startswith("-100"):
                    print("❌ Channel ID must start with -100")
                    continue
                try:
                    int(channel_id)  # Verify it's a valid number
                    return channel_id
                except ValueError:
                    print("❌ Invalid channel ID format")
                    continue
            
            else:
                print("❌ Please enter 1 or 2")

    async def verify_target_chat(self, chat):
        """Verify bot has access to target chat"""
        try:
            entity = await self.client.get_entity(chat)
            try:
                # Try to send a test message
                msg = await self.client.send_message(
                    entity,
                    "🔄 Bot setup test message - Verifying channel access..."
                )
                await msg.delete()  # Delete the test message
                print("\n✅ Successfully verified access to target channel!")
                return True
            except Exception as e:
                print("\n❌ Bot doesn't have permission to send messages!")
                print("Please:")
                print("1. Add the bot as an admin to the channel")
                print("2. Ensure the bot has permission to send messages")
                print(f"\nError: {str(e)}")
                return False
        except Exception as e:
            print("\n❌ Failed to access target channel!")
            print("Please check:")
            print("1. The channel exists")
            print("2. You've entered the correct channel username/ID")
            print("3. The bot is a member of the channel")
            print(f"\nError: {str(e)}")
            return False

    async def check_setup(self):
        """Check if all required setup is complete"""
        print("\n Checking setup...")
        
        # Check if .env exists
        if not os.path.exists('.env'):
            print("\n❌ .env file not found!")
            print("\nRequired Steps:")
            print("1. Rename or copy .env.sample to .env:")
            print("   Windows: copy .env.sample .env")
            print("   Linux/Mac: cp .env.sample .env")
            print("\n2. Edit .env with your credentials:")
            print("   - API_ID (from https://my.telegram.org/apps)")
            print("   - API_HASH (from https://my.telegram.org/apps)")
            return False
            
        # Check API credentials
        if not API_ID or not API_HASH:
            print("\n❌ Missing API credentials in .env!")
            print("\nPlease edit .env and set:")
            print("- API_ID")
            print("- API_HASH")
            print("\nGet these from https://my.telegram.org/apps")
            return False
            
        return True

    async def configure_target_chat(self):
        """Configure the target chat for forwarding messages"""
        print("\n🎯 Select target chat for forwarding messages")
        
        try:
            # Get dialogs
            print("\nFetching available chats...")
            async for dialog in self.client.iter_dialogs():
                if dialog.is_channel or dialog.is_group:
                    self.available_chats.append({
                        'id': dialog.id,
                        'title': dialog.title,
                        'type': 'channel' if dialog.is_channel else 'group'
                    })
                    
            if not self.available_chats:
                print("\n❌ No channels or groups found!")
                print("Please join some channels/groups first")
                return False
                
            # Display available chats
            print("\nAvailable chats:")
            for i, chat in enumerate(self.available_chats, 1):
                print(f"{i}. {chat['title']} ({chat['type']})")
                
            while True:
                choice = input("\n🎯 Select chats to monitor (or 'q' to finish): ")
                if choice.lower() == 'q':
                    break
                    
                try:
                    indices = [int(x.strip()) for x in choice.split(',')]
                    selected_chats = []
                    
                    for idx in indices:
                        if 1 <= idx <= len(self.available_chats):
                            chat = self.available_chats[idx-1]
                            selected_chats.append(str(chat['id']))
                            print(f"✅ Added: {chat['title']}")
                        else:
                            print(f"❌ Invalid number: {idx}")
                    
                    if selected_chats:
                        # Update .env with the new target chat
                        config_path = Path('.env')
                        if config_path.exists():
                            config_text = config_path.read_text()
                            # Update TARGET_CHAT line
                            new_config = re.sub(
                                r'TARGET_CHAT=.*',
                                f'TARGET_CHAT={",".join(selected_chats)}',
                                config_text
                            )
                            config_path.write_text(new_config)
                            print("\n✅ Target chat configured and saved to .env!")
                            return True
                            
                except ValueError:
                    print("❌ Please enter valid numbers separated by commas")
                    
        except Exception as e:
            print(f"\n❌ Error configuring target chat: {str(e)}")
            return False
            
        return False

    async def display_main_menu(self):
        """Display the main menu options"""
        while True:
            print("\n🔧 Main Menu")
            print("=" * 50)
            print("1. Start Monitoring")
            print("2. Edit Configuration")
            print("3. View Current Settings")
            print("4. Edit Environment Settings")
            print("5. Exit")
            
            choice = input("\nEnter choice (1-5): ").strip()
            
            if choice == "1":
                return "start"
            elif choice == "2":
                return "edit"
            elif choice == "3":
                await self.display_current_settings()
            elif choice == "4":
                await self.edit_environment_settings()
            elif choice == "5":
                print("\n👋 Goodbye!")
                sys.exit(0)
            else:
                print("\n❌ Invalid choice. Please try again.")

    async def edit_environment_settings(self):
        """Edit environment settings in .env file"""
        print("\n⚙️ Environment Settings")
        print("=" * 50)
        
        # Read current settings
        try:
            with open('.env', 'r') as f:
                current_settings = f.read()
            
            print("\nCurrent settings:")
            print("-" * 20)
            print(current_settings)
            print("-" * 20)
            
            print("\nOptions:")
            print("1. Edit API_ID")
            print("2. Edit API_HASH")
            print("3. Edit TARGET_CHAT")
            print("4. Edit DEBUG mode")
            print("5. Back to main menu")
            
            choice = input("\nEnter choice (1-5): ").strip()
            
            if choice == "5":
                return
            
            if choice in ["1", "2", "3", "4"]:
                settings_map = {
                    "1": ("API_ID", "Enter new API_ID: "),
                    "2": ("API_HASH", "Enter new API_HASH: "),
                    "3": ("TARGET_CHAT", "Enter new TARGET_CHAT (@username or -100xxxxx): "),
                    "4": ("DEBUG", "Enter DEBUG mode (true/false): ")
                }
                
                setting, prompt = settings_map[choice]
                new_value = input(prompt).strip()
                
                # Validate TARGET_CHAT format
                if setting == "TARGET_CHAT":
                    if not (new_value.startswith('@') or new_value.startswith('-100')):
                        print("\n❌ Invalid TARGET_CHAT format!")
                        print("Must start with @ for usernames or -100 for channel IDs")
                        input("\nPress Enter to continue...")
                        return
                
                # Update the setting in the file
                with open('.env', 'r') as f:
                    lines = f.readlines()
                
                with open('.env', 'w') as f:
                    for line in lines:
                        if line.startswith(f"{setting}="):
                            f.write(f"{setting}={new_value}\n")
                        else:
                            f.write(line)
                
                print(f"\n✅ {setting} updated successfully!")
                print("⚠️ Please restart the bot for changes to take effect.")
                input("\nPress Enter to continue...")
            else:
                print("\n❌ Invalid choice!")
                input("\nPress Enter to continue...")
                
        except Exception as e:
            print(f"\n❌ Error editing environment settings: {str(e)}")
            input("\nPress Enter to continue...")

    async def display_current_settings(self):
        """Display current configuration"""
        print("\n📊 Current Settings")
        print("=" * 50)
        print(f"Monitored Chats: {len(self.source_chats)}")
        for chat_id in self.source_chats:
            chat_name = await self.get_chat_name(chat_id)
            if str(chat_id) in self.filtered_users:
                print(f"- {chat_name} (Filtered: {len(self.filtered_users[str(chat_id)])} users)")
            else:
                print(f"- {chat_name} (All users)")
        print(f"\nTarget Chat: {self.config.get('target_chat', TARGET_CHAT)}")
        input("\nPress Enter to continue...")

    async def display_chat_selection_menu(self):
        """Display menu for previous or new chat selection"""
        print("\n📋 Chat Selection")
        print("=" * 50)
        print("1. Continue with previous selection")
        print("2. Select new chats")
        print("3. Back to main menu")
        
        while True:
            choice = input("\nEnter choice (1-3): ").strip()
            if choice == "1":
                return "previous"
            elif choice == "2":
                return "new"
            elif choice == "3":
                return "back"
            else:
                print("❌ Invalid choice. Please try again.")

    async def start(self):
        """Start the bot"""
        while True:  # Main loop
            try:
                # First check referral
                print("\n🔍 Verifying access...")
                self.authorized = await self.check_referral()
                if not self.authorized:
                    print("\n❌ Bot startup cancelled. Please make sure you:")
                    print(f"1. Join using the correct referral link: https://t.me/{BOT_USERNAME}?start={REQUIRED_REF}")
                    print("2. Have valid API credentials in your .env file")
                    return False

                # Initialize client if not already done
                if not hasattr(self, '_client_initialized'):
                    await self.client.start()
                    self._client_initialized = True
                
                # Main menu loop
                menu_choice = await self.display_main_menu()
                
                if menu_choice == "start" or menu_choice == "edit":
                    should_continue = await self.handle_chat_selection(menu_choice)
                    if should_continue:
                        continue
                    
                    # If we got here, we're ready to start monitoring
                    print("\n🚀 Starting message monitoring...")
                    await self.setup_message_handler()
                    await self.client.run_until_disconnected()
                    return True
                    
            except Exception as e:
                print(f"\n❌ Error during startup: {str(e)}")
                await asyncio.sleep(2)  # Wait before showing menu again
                continue

        return False

    async def handle_chat_selection(self, menu_choice):
        """Handle chat selection and configuration"""
        # Handle chat selection
        if menu_choice == "start" and self.config.get('source_chats'):
            chat_menu_choice = await self.display_chat_selection_menu()
            
            if chat_menu_choice == "back":
                return True  # Go back to main menu
            elif chat_menu_choice == "previous":
                self.source_chats = self.config['source_chats']
                self.filtered_users = self.config.get('filtered_users', {})
            else:  # "new"
                new_chats = await self.display_chat_selection()
                if not new_chats:
                    return True  # Go back to main menu
                self.source_chats = new_chats
        else:
            new_chats = await self.display_chat_selection()
            if not new_chats:
                return True  # Go back to main menu
            self.source_chats = new_chats

        # Set up user filters
        print("\n👥 User Filter Setup")
        print("=" * 50)
        print(f"Setting up filters for {len(self.source_chats)} selected chats...")
        
        for i, chat_id in enumerate(self.source_chats, 1):
            chat_name = await self.get_chat_name(chat_id)
            print(f"\n🔍 Chat {i} of {len(self.source_chats)}")
            print(f"Channel: {chat_name}")
            print(f"Chat ID: {chat_id}")
            print("=" * 50)
            print("\n1. Configure filters")
            print("2. Skip this chat")
            print("3. Back to main menu")
            
            filter_choice = input("\nEnter choice (1-3): ").strip()
            if filter_choice == "3":
                return True  # Go back to main menu
            elif filter_choice == "1":
                filtered_users = await self.display_user_filter_menu(chat_id)
                if filtered_users:
                    self.filtered_users[str(chat_id)] = filtered_users
                    print(f"✅ User filter set for {chat_name}")
                else:
                    print(f"👥 Monitoring all users in {chat_name}")
            
            if i < len(self.source_chats):
                proceed = input("\nContinue to next chat? (Enter to continue, 'q' to skip remaining, 'b' for main menu): ")
                if proceed.lower() == 'b':
                    return True  # Go back to main menu
                elif proceed.lower() == 'q':
                    print("\n⏩ Skipping remaining chat configurations...")
                    break
        
        self.save_config()
        
        # Show summary and confirm
        print("\n📊 Configuration Summary")
        print("=" * 50)
        for chat_id in self.source_chats:
            chat_name = await self.get_chat_name(chat_id)
            if str(chat_id) in self.filtered_users:
                user_count = len(self.filtered_users[str(chat_id)])
                print(f"👥 {chat_name}: Monitoring {user_count} specific users")
            else:
                print(f"✅ {chat_name}: Monitoring all users")
        
        print("\n1. Start Monitoring")
        print("2. Back to Main Menu")
        final_choice = input("\nEnter choice (1-2): ")
        if final_choice == "2":
            return True  # Go back to main menu
        
        return False  # Proceed with monitoring

    async def forward_message(self, message, contract_address, content_type="text"):
        try:
            # Log details to terminal only
            try:
                chat = await self.client.get_entity(message.chat_id)
                sender = await self.client.get_entity(message.sender_id)
                logging.info(
                    f"\nToken Found!\n"
                    f"Source: {chat.title}\n"
                    f"Posted by: @{sender.username or sender.first_name}\n"
                    f"Type: {content_type}\n"
                    f"CA: {contract_address}\n"
                    f"Quick Links:\n"
                    f"• Birdeye: https://birdeye.so/token/{contract_address}\n"
                    f"• Solscan: https://solscan.io/token/{contract_address}\n"
                    f"• Jupiter: https://jup.ag/swap/SOL-{contract_address}"
                )
            except Exception as e:
                logging.error(f"Error getting message details: {e}")

            # Forward just the CA to Telegram target chat
            target = self.config.get('target_chat', TARGET_CHAT)
            await self.client.send_message(
                target,
                contract_address
            )
            
        except Exception as e:
            logging.error(f"Error forwarding message: {str(e)}")

    async def get_dialogs(self) -> List[Dict]:
        """Fetch and return all dialogs (chats/channels)"""
        dialogs = []
        async for dialog in self.client.iter_dialogs():
            if dialog.is_channel or dialog.is_group:  # Only include channels and groups
                self.dialogs_cache[len(dialogs)] = dialog.id
                dialogs.append({
                    'id': dialog.id,
                    'name': dialog.name,
                    'type': 'Channel' if dialog.is_channel else 'Group'
                })
        return dialogs

    async def is_token_processed(self, contract_address: str) -> bool:
        """Check if token was already processed"""
        return contract_address in self.processed_tokens

    async def add_processed_token(self, contract_address: str):
        """Add token to processed list"""
        self.processed_tokens.add(contract_address)
        self.save_processed_tokens()

    async def monitor_health(self):
        """Monitor bot health and connection"""
        while True:
            try:
                # Check connection without await
                if not self.client.is_connected():
                    logging.warning("Connection lost, attempting to reconnect...")
                    await self.client.connect()
                
                uptime = time.time() - self.start_time
                hours = int(uptime // 3600)
                minutes = int((uptime % 3600) // 60)
                
                logging.info(
                    f"Health Check:\n"
                    f"✓ Messages Processed: {self.processed_count}\n"
                    f"✓ Tokens Forwarded: {self.forwarded_count}\n"
                    f"✓ Unique Tokens: {len(self.processed_tokens)}\n"
                    f"✓ Uptime: {hours}h {minutes}m\n"
                    f"✓ Monitoring: {len(self.source_chats)} chats"
                )
                
                await asyncio.sleep(3600)  # Check every hour
            except Exception as e:
                logging.error(f"Health monitor error: {e}")
                await asyncio.sleep(60)  # Wait before retry

    async def run(self):
        try:
            started = await self.start()
            if started:
                print("\n🚀 Bot is running! Press Ctrl+C to stop.")
                print(f"✨ Monitoring {len(self.source_chats)} chats for Solana contracts")
                print(f"📬 Forwarding to: {TARGET_CHAT}")
                
                # Start health monitoring
                asyncio.create_task(self.monitor_health())
                
                await self.client.run_until_disconnected()
            else:
                print("\n Bot startup cancelled. Please make sure you:")
                print(f"1. Join using the correct referral link: https://t.me/{BOT_USERNAME}?start={REQUIRED_REF}")
                print("2. Have valid API credentials in your config.env file")
        except KeyboardInterrupt:
            logging.info("Bot stopped by user.")
        finally:
            self.save_processed_tokens()
            await self.client.disconnect()

    async def get_chat_name(self, chat_id):
        """Get chat name from ID"""
        try:
            entity = await self.client.get_entity(int(chat_id))
            return entity.title
        except Exception as e:
            return f"Chat {chat_id}"

    async def display_chat_selection(self):
        """Display and handle chat selection"""
        print("\n📋 Select chats to monitor")
        print("=" * 50)
        
        try:
            # Get dialogs
            print("\nFetching available chats...")
            self.available_chats = []
            async for dialog in self.client.iter_dialogs():
                if dialog.is_channel or dialog.is_group:
                    self.available_chats.append({
                        'id': dialog.id,
                        'title': dialog.title,
                        'type': 'channel' if dialog.is_channel else 'group'
                    })
            
            if not self.available_chats:
                print("\n❌ No channels or groups found!")
                return []
            
            # Display available chats
            for i, chat in enumerate(self.available_chats, 1):
                print(f"{i}. {chat['title']} ({chat['type']})")
            
            selected_chats = []
            while True:
                choice = input("\nEnter chat numbers to monitor (comma-separated) or 'q' to finish: ")
                if choice.lower() == 'q':
                    break
                
                try:
                    indices = [int(x.strip()) for x in choice.split(',')]
                    for idx in indices:
                        if 1 <= idx <= len(self.available_chats):
                            chat_id = self.available_chats[idx-1]['id']
                            if chat_id not in selected_chats:
                                selected_chats.append(chat_id)
                                print(f"✅ Added: {self.available_chats[idx-1]['title']}")
                        else:
                            print(f"❌ Invalid number: {idx}")
                except ValueError:
                    print("❌ Please enter valid numbers separated by commas")
            
            return selected_chats
        
        except Exception as e:
            print(f"\n❌ Error during chat selection: {str(e)}")
            return []

    async def display_user_filter_menu(self, chat_id):
        """Display and handle user filter selection"""
        try:
            print("\n👥 User Filter Options:")
            print("1. Monitor all users")
            print("2. Monitor specific users")
            
            choice = input("\nEnter choice (1-2): ").strip()
            
            if choice == "1":
                return []
            elif choice == "2":
                filtered_users = []
                print("\nEnter user IDs to monitor (one per line)")
                print("Press Enter twice when done")
                
                while True:
                    user_input = input().strip()
                    if not user_input:
                        break
                    try:
                        user_id = int(user_input)
                        filtered_users.append(user_id)
                    except ValueError:
                        print("❌ Please enter valid numeric user IDs")
                
                return filtered_users
            else:
                print("❌ Invalid choice")
                return []
                
        except Exception as e:
            print(f"❌ Error setting up user filter: {str(e)}")
            return []

    async def setup_message_handler(self):
        """Set up the message handler"""
        @self.client.on(events.NewMessage(chats=self.source_chats))
        async def message_handler(event):
            try:
                # Increment processed count
                self.processed_count += 1
                
                # Check if message is from a filtered user
                chat_id = str(event.chat_id)
                if chat_id in self.filtered_users and self.filtered_users[chat_id]:
                    if event.sender_id not in self.filtered_users[chat_id]:
                        return
                
                # Extract Solana contract address (simple regex for testing)
                message_text = event.message.text or ""
                matches = re.findall(r'[1-9A-HJ-NP-Za-km-z]{32,44}', message_text)
                
                for contract_address in matches:
                    if await self.is_token_processed(contract_address):
                        continue
                        
                    await self.forward_message(event.message, contract_address)
                    await self.add_processed_token(contract_address)
                    self.forwarded_count += 1
                    
            except Exception as e:
                logging.error(f"Error processing message: {str(e)}")

async def main():
    bot = SimpleSolListener()
    await bot.run()

if __name__ == "__main__":
    print("🤖 Welcome to Simple Solana Listener!")
    asyncio.run(main()) 