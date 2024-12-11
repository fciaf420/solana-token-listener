"""
Solana Token Listener Bot
Version: 1.0.0

A Telegram bot that monitors channels for Solana token contract addresses
and forwards them to a target channel for automated trading.
"""

import asyncio
import re
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
import logging
from typing import List, Dict
import json
import os
import base64
import aiohttp
import io
import time
from pathlib import Path
from dotenv import load_dotenv
import sys

__version__ = "1.0.0"

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleCP(65001)
    kernel32.SetConsoleOutputCP(65001)

# Use Path for cross-platform compatibility
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / 'sol_listener_config.json'
TEMP_DIR = BASE_DIR / 'temp_images'
ENV_FILE = BASE_DIR / '.env'
LOGS_DIR = BASE_DIR / 'logs'

# Create required directories
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOGS_DIR / 'bot.log', encoding='utf-8')
    ]
)

# Bot Configuration
PRIMARY_BOT = {
    'username': 'odysseus_trojanbot',
    'ref': 'r-forza222'
}
BACKUP_BOT = {
    'username': 'TradeonNovaBot',
    'ref': 'r-F6AGNG'
}

# Load environment variables
load_dotenv(ENV_FILE)
try:
    api_id = os.getenv('API_ID')
    if not api_id:
        raise ValueError("API_ID environment variable is not set in .env file")
    API_ID = int(api_id)
    
    API_HASH = os.getenv('API_HASH')
    if not API_HASH:
        raise ValueError("API_HASH environment variable is not set in .env file")
        
    TARGET_CHAT = os.getenv('TARGET_CHAT')
    if not TARGET_CHAT:
        raise ValueError("TARGET_CHAT environment variable is not set in .env file")
    # Clean up target chat value
    TARGET_CHAT = TARGET_CHAT.lstrip('@').strip()  # Remove @ prefix and whitespace
except (ValueError, TypeError) as e:
    print("\n❌ Error with environment variables:")
    print(f"1. Make sure you have a .env file in: {ENV_FILE}")
    print("2. Your .env file should contain:")
    print("   API_ID=your_api_id_here")
    print("   API_HASH=your_api_hash_here")
    print("   TARGET_CHAT=target_chat_here")
    print("\n3. API_ID should be a number")
    print("4. Get API_ID and API_HASH from https://my.telegram.org")
    print(f"\nSpecific error: {str(e)}")
    sys.exit(1)

class SimpleSolListener:
    """Telegram bot for monitoring and forwarding Solana contract addresses"""
    
    def __init__(self):
        """Initialize the bot with environment and file structure checks"""
        self.version = __version__
        print(f"\n🤖 Solana Token Listener v{self.version}")
        
        print("\n🔍 Checking environment setup...")
        if not self._check_environment():
            raise Exception("Environment setup failed")
            
        print("\n📂 Setting up directory structure...")
        required_dirs = [TEMP_DIR, LOGS_DIR]
        for dir_path in required_dirs:
            os.makedirs(dir_path, exist_ok=True)
            print(f"✓ {dir_path.name}/")
            
        print("\n📄 Checking configuration files...")
        self._initialize_config_files()
        
        self.config = self.load_config()
        session = StringSession(self.config.get('session_string', ''))
        self.client = TelegramClient(session, API_ID, API_HASH)
        
        self.processed_tokens = self.load_processed_tokens()
        self.start_time = time.time()
        
        self.processed_count = 0
        self.forwarded_count = 0
        # Load saved source chats from config
        self.source_chats = self.config.get('source_chats', [])
        self.filtered_users = self.config.get('filtered_users', {})
        self.dialogs_cache = {}
        self.verified = self.config.get('verified', False)
        
        print("\n✅ Initialization complete!")
        
    def _check_environment(self) -> bool:
        """Check if all required environment variables are set"""
        required_vars = {
            'API_ID': API_ID,
            'API_HASH': API_HASH,
            'TARGET_CHAT': TARGET_CHAT
        }
        
        all_present = True
        for var_name, var_value in required_vars.items():
            if not var_value:
                print(f"❌ Missing {var_name} in environment")
                all_present = False
            else:
                print(f"✓ {var_name} found")
                
        return all_present
        
    def _initialize_config_files(self):
        """Initialize required configuration files if they don't exist"""
        # Config file
        if not os.path.exists(CONFIG_FILE):
            print("✨ Creating new configuration file...")
            initial_config = {
                'source_chats': [],
                'filtered_users': {},
                'session_string': None,
                'verified': False,
                'blacklisted_keywords': []
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(initial_config, f, indent=4)
            print("✓ sol_listener_config.json")
        else:
            print("✓ sol_listener_config.json (existing)")
            
        # Processed tokens file
        tokens_file = BASE_DIR / 'processed_tokens.json'
        if not os.path.exists(tokens_file):
            print("✨ Creating processed tokens file...")
            with open(tokens_file, 'w') as f:
                json.dump([], f)
            print("✓ processed_tokens.json")
        else:
            print("✓ processed_tokens.json (existing)")
            
        # Environment file check
        if not os.path.exists(ENV_FILE):
            print("❌ No .env file found!")
            print("Creating template .env file...")
            with open(ENV_FILE, 'w') as f:
                f.write("API_ID=\nAPI_HASH=\nTARGET_CHAT=\nDEBUG=false\n")
            print("⚠️ Please fill in your credentials in the .env file")
            return False
        else:
            print("✓ .env file found")

    def load_config(self) -> dict:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error loading config: {str(e)}")
        return {
            'source_chats': [],
            'filtered_users': {},
            'session_string': None
        }

    def save_config(self):
        try:
            if not self.config.get('session_string'):
                self.config['session_string'] = self.client.session.save()
            self.config['source_chats'] = self.source_chats
            self.config['filtered_users'] = self.filtered_users
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving config: {str(e)}")

    async def extract_ca_from_text(self, text: str) -> str:
        """Extract Solana CA from text"""
        if not text:
            return None
            
        logging.info(f"Checking text for CA: {text}")
        
        # Common Solana link formats
        link_patterns = [
            r'dexscreener\.com/solana/([1-9A-HJ-NP-Za-km-z]{32,44})',  # DexScreener
            r'pump\.fun/coin/([1-9A-HJ-NP-Za-km-z]{32,44})',           # Pump.fun
            r'gmgn\.ai/sol/token/([1-9A-HJ-NP-Za-km-z]{32,44})',       # GMGN
            r'birdeye\.so/token/([1-9A-HJ-NP-Za-km-z]{32,44})',        # Birdeye
            r'solscan\.io/token/([1-9A-HJ-NP-Za-km-z]{32,44})',        # Solscan
            r'jup\.ag/swap/[^-]+-([1-9A-HJ-NP-Za-km-z]{32,44})',       # Jupiter
            r'\b([1-9A-HJ-NP-Za-km-z]{32,44})\b'                       # Raw CA
        ]
        
        for pattern in link_patterns:
            match = re.search(pattern, text)
            if match:
                ca = match.group(1)
                logging.info(f"Found CA: {ca}")
                return ca
                
        logging.info("No CA match found")
        return None

    async def process_message_content(self, message) -> tuple[str, str]:
        """Process different types of message content"""
        content_type = "text"
        ca = None
        
        try:
            if message.message:  # Text message
                ca = await self.extract_ca_from_text(message.message)
        
        except Exception as e:
            logging.error(f"Error processing message content: {str(e)}")
        
        return content_type, ca

    async def display_chat_selection(self):
        """Display menu for selecting multiple chats"""
        print("\n🔍 Loading your chats and channels...\n")
        dialogs = await self.get_dialogs()
        
        print("📋 Available Chats and Channels:")
        print("=" * 50)
        print(f"{'Index':<6} {'Type':<10} {'Name':<30} {'ID':<15}")
        print("-" * 61)
        
        for i, dialog in enumerate(dialogs):
            print(f"{i:<6} {dialog['type']:<10} {dialog['name'][:30]:<30} {dialog['id']:<15}")
        
        print("\n" + "=" * 50)
        print("Enter chat indices separated by commas (e.g., 1,3,5)")
        
        selected_chats = []
        while True:
            choice = input("\n🎯 Select chats to monitor (or 'q' to finish): ").strip()
            if choice.lower() == 'q':
                if selected_chats:  # If we have selections, confirm and exit
                    print("\nSelected chats:")
                    for chat_id in selected_chats:
                        dialog = next((d for d in dialogs if d['id'] == chat_id), None)
                        if dialog:
                            print(f"✅ {dialog['name']}")
                    
                    confirm = input("\nConfirm these selections? (y/n): ").lower()
                    if confirm == 'y':
                        break
                    else:
                        selected_chats = []  # Reset selections if not confirmed
                        continue
                else:
                    print("❌ No chats selected")
                    continue
                
            try:
                indices = [int(x.strip()) for x in choice.split(',')]
                new_selections = False
                
                for idx in indices:
                    if 0 <= idx < len(dialogs):
                        chat_id = dialogs[idx]['id']
                        if chat_id not in selected_chats:
                            selected_chats.append(chat_id)
                            print(f"✅ Added: {dialogs[idx]['name']}")
                            new_selections = True
                    else:
                        print(f"❌ Invalid index: {idx}")
                
                if new_selections:
                    print("\nCurrent selections:")
                    for chat_id in selected_chats:
                        dialog = next((d for d in dialogs if d['id'] == chat_id), None)
                        if dialog:
                            print(f"• {dialog['name']}")
                    print("\nEnter more indices or 'q' to finish")
                    
            except ValueError:
                print(" Please enter valid numbers separated by commas")
        
        return selected_chats

    async def display_user_filter_menu(self, chat_id):
        """Display menu for selecting users to filter in a chat"""
        print("\n👥 User Filter Options:")
        print("1. Monitor all users")
        print("2. Select specific users to monitor")
        
        choice = input("\nEnter your choice (1-2): ")
        if choice == "2":
            print("\n🔍 Loading recent users from chat...")
            users = set()
            try:
                async for message in self.client.iter_messages(chat_id, limit=100):
                    if message.sender_id:
                        try:
                            user = await self.client.get_entity(message.sender_id)
                            users.add((user.id, getattr(user, 'username', None) or user.first_name))
                        except:
                            continue
                
                if not users:
                    print("❌ No users found in recent messages")
                    return None
                
                print("\n Recent Users:")
                print("=" * 50)
                users_list = list(users)
                for i, (user_id, username) in enumerate(users_list):
                    print(f"{i:<3} | {username:<30} | {user_id}")
                
                selected_users = []
                while True:
                    choice = input("\nEnter user indices to monitor (comma-separated) or 'q' to finish: ")
                    if choice.lower() == 'q':
                        break
                    
                    try:
                        indices = [int(x.strip()) for x in choice.split(',')]
                        for idx in indices:
                            if 0 <= idx < len(users_list):
                                user_id, username = users_list[idx]
                                selected_users.append(user_id)
                                print(f"✅ Added: {username}")
                    except ValueError:
                        print(" Please enter valid numbers")
                
                return selected_users if selected_users else None
                
            except Exception as e:
                logging.error(f"Error loading users: {e}")
                return None
        
        return None  # Monitor all users

    async def start(self):
        """Start the bot and show main menu"""
        if not await self.verify_access():
            return False
            
        # Ensure we're connected
        if not self.client.is_connected():
            await self.client.connect()
            
        while True:
            # Get chat names for display
            chat_info = "No channels configured"
            if self.source_chats:
                try:
                    chat_count = len(self.source_chats)
                    chat_names = []
                    for chat_id in self.source_chats[:3]:  # Show first 3 chats
                        try:
                            entity = await self.client.get_entity(int(chat_id))
                            chat_name = entity.title if hasattr(entity, 'title') else str(chat_id)
                            if str(chat_id) in self.filtered_users:
                                user_count = len(self.filtered_users[str(chat_id)])
                                chat_names.append(f"{chat_name} ({user_count} users)")
                            else:
                                chat_names.append(f"{chat_name} (all users)")
                        except:
                            chat_names.append(f"Chat {chat_id}")
                    
                    if chat_count > 3:
                        chat_info = f"{chat_count} chats configured: {', '.join(chat_names[:3])} +{chat_count - 3} more"
                    else:
                        chat_info = f"{chat_count} chats configured: {', '.join(chat_names)}"
                except Exception as e:
                    chat_info = f"{len(self.source_chats)} chats configured"
                    logging.error(f"Error getting chat names: {e}")
            
            print("\n🔧 Main Menu")
            print("=" * 50)
            print(f"0. Quick Start - Resume Monitoring ({chat_info})")
            print("1. Start Monitoring")
            print("2. Configure Channels")
            print("3. View Current Settings")
            print("4. Manage Keyword Filters")
            print("5. Exit\n")
            choice = input("Enter your choice (0-5): ").strip()
            
            try:
                if choice == "0":
                    if self.source_chats:
                        print("\n🚀 Quick starting with saved settings...")
                        await self.view_settings()  # Show current config
                        await self.start_monitoring()
                    else:
                        print("\n❌ No channels configured! Please configure channels first (option 2).")
                        input("\nPress Enter to continue...")
                elif choice == "1":
                    await self.start_monitoring()
                elif choice == "2":
                    await self.configure_channels()
                elif choice == "3":
                    await self.view_settings()
                elif choice == "4":
                    await self.manage_keyword_filters()
                elif choice == "5":
                    print("\n👋 Goodbye!")
                    await self.client.disconnect()
                    return False
                else:
                    print("\n❌ Invalid choice. Please try again.")
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                if not self.client.is_connected():
                    print("Reconnecting...")
                    await self.client.connect()
        
        return True

    async def start_monitoring(self):
        """Start monitoring selected chats"""
        if not self.source_chats:
            print("\n❌ No channels configured! Please configure channels first.")
            print("\nPress Enter to return to main menu...")
            input()
            return
            
        print("\n🚀 Starting monitoring...")
        print(f"✨ Monitoring {len(self.source_chats)} chats for Solana contracts")
        print(f"📬 Forwarding to: {TARGET_CHAT}")
        
        # Register event handler for new messages
        @self.client.on(events.NewMessage())
        async def message_handler(event):
            await self.handle_new_message(event)
        
        # Start health monitoring
        asyncio.create_task(self.monitor_health())
        
        await self.client.run_until_disconnected()

    async def configure_channels(self):
        """Configure channels for monitoring"""
        try:
            if not self.client.is_connected():
                await self.client.connect()
                
            print("\n🔍 Loading your chats and channels...")
            dialogs = await self.get_dialogs()
            
            print("\n📋 Available Chats and Channels:")
            print("=" * 50)
            print(f"{'Index':<6} {'Type':<10} {'Name':<30} {'ID':<15}")
            print("-" * 61)
            
            for i, dialog in enumerate(dialogs):
                print(f"{i:<6} {dialog['type']:<10} {dialog['name'][:30]:<30} {dialog['id']:<15}")
            
            print("\n" + "=" * 50)
            print("Enter chat indices separated by commas (e.g., 1,3,5)")
            
            selected_chats = []
            while True:
                choice = input("\n🎯 Select chats to monitor (or 'q' to finish): ").strip()
                if choice.lower() == 'q':
                    break
                    
                try:
                    indices = [int(x.strip()) for x in choice.split(',')]
                    for idx in indices:
                        if 0 <= idx < len(dialogs):
                            chat_id = int(dialogs[idx]['id'])
                            if chat_id not in selected_chats:
                                selected_chats.append(chat_id)
                                print(f"✅ Added: {dialogs[idx]['name']}")
                        else:
                            print(f"❌ Invalid index: {idx}")
                except ValueError:
                    print("❌ Please enter valid numbers separated by commas")
            
            if selected_chats:
                self.source_chats = selected_chats
                self.save_config()
                print(f"\n✅ Now monitoring {len(selected_chats)} chats")
                
                # Configure filters for selected chats
                await self.configure_user_filters()
            else:
                print("\n⚠️ No chats selected")
                
        except Exception as e:
            print(f"\n❌ Error configuring channels: {str(e)}")
            print("Please try again")

    async def view_settings(self):
        """View current settings"""
        print("\n📊 Current Configuration")
        print("=" * 50)
        
        if self.source_chats:
            print(f"\nMonitored Chats: {len(self.source_chats)}")
            for chat_id in self.source_chats:
                try:
                    entity = await self.client.get_entity(int(chat_id))
                    chat_name = entity.title if hasattr(entity, 'title') else str(chat_id)
                    if str(chat_id) in self.filtered_users:
                        user_count = len(self.filtered_users[str(chat_id)])
                        print(f"✓ {chat_name}: Monitoring {user_count} specific users")
                    else:
                        print(f"✓ {chat_name}: Monitoring all users")
                except:
                    print(f"✓ Chat {chat_id}: Configuration saved")
        else:
            print("\nNo channels configured")
            
        print(f"\nTarget Chat: {TARGET_CHAT}")
        input("\nPress Enter to continue...")

    async def manage_keyword_filters(self):
        """Manage keyword filters"""
        while True:
            print("\n🔍 Keyword Filter Management")
            print("=" * 50)
            
            current_blacklist = self.config.get('blacklisted_keywords', [])
            current_whitelist = self.config.get('whitelisted_keywords', [])
            
            print("\n📊 Current Status:")
            print("--------------------------------------------------")
            print("⚫ Blacklist:", ", ".join(current_blacklist) if current_blacklist else "Empty")
            print("⚪ Whitelist:", ", ".join(current_whitelist) if current_whitelist else "Empty")
            
            print("\n📝 Options:")
            print("--------------------------------------------------")
            print("Blacklist Management:")
            print("  1. View blacklist")
            print("  2. Add to blacklist")
            print("  3. Remove from blacklist")
            print("  4. Clear blacklist")
            
            print("\nWhitelist Management:")
            print("  5. View whitelist")
            print("  6. Add to whitelist")
            print("  7. Remove from whitelist")
            print("  8. Clear whitelist")
            
            print("\nGeneral:")
            print("  9. Clear all filters")
            print("  0. Back to main menu")
            
            choice = input("\nEnter your choice (0-9): ").strip()
            
            try:
                if choice == "0":
                    break
                    
                elif choice in ["1", "5"]:  # View lists
                    target_list = current_blacklist if choice == "1" else current_whitelist
                    list_name = "Blacklist" if choice == "1" else "Whitelist"
                    print(f"\nCurrent {list_name}:")
                    if target_list:
                        for i, word in enumerate(target_list, 1):
                            print(f"{i}. {word}")
                    else:
                        print("Empty")
                    input("\nPress Enter to continue...")
                    
                elif choice in ["2", "6"]:  # Add to lists
                    target_list = current_blacklist if choice == "2" else current_whitelist
                    list_name = "blacklist" if choice == "2" else "whitelist"
                    word = input(f"\nEnter word to {list_name}: ").strip().lower()
                    if word:
                        if word in target_list:
                            print(f"'{word}' already in {list_name}")
                        else:
                            target_list.append(word)
                            print(f"Added '{word}' to {list_name}")
                            
                elif choice in ["3", "7"]:  # Remove from lists
                    target_list = current_blacklist if choice == "3" else current_whitelist
                    list_name = "blacklist" if choice == "3" else "whitelist"
                    if target_list:
                        print(f"\nSelect word to remove from {list_name}:")
                        for i, word in enumerate(target_list, 1):
                            print(f"{i}. {word}")
                        try:
                            idx = int(input("\nEnter number: ")) - 1
                            if 0 <= idx < len(target_list):
                                removed = target_list.pop(idx)
                                print(f"Removed '{removed}'")
                            else:
                                print("Invalid number")
                        except ValueError:
                            print("Please enter a valid number")
                    else:
                        print(f"No words in {list_name}")
                        
                elif choice in ["4", "8"]:  # Clear lists
                    target_list = current_blacklist if choice == "4" else current_whitelist
                    list_name = "blacklist" if choice == "4" else "whitelist"
                    if target_list:
                        if input(f"\nClear entire {list_name}? (y/n): ").lower() == 'y':
                            target_list.clear()
                            print(f"{list_name.capitalize()} cleared")
                    else:
                        print(f"{list_name.capitalize()} is already empty")
                        
                elif choice == "9":  # Clear all
                    if current_blacklist or current_whitelist:
                        if input("\nClear ALL filters? (y/n): ").lower() == 'y':
                            current_blacklist.clear()
                            current_whitelist.clear()
                            print("All filters cleared")
                    else:
                        print("No filters to clear")
                        
                else:
                    print("Invalid choice")
                    
            except Exception as e:
                print(f"Error: {str(e)}")
                
            self.config['blacklisted_keywords'] = current_blacklist
            self.config['whitelisted_keywords'] = current_whitelist
            self.save_config()

    async def check_message_content(self, message) -> bool:
        """Check if message matches filters"""
        if not message.message:
            return True
            
        message_text = message.message.lower()
        blacklisted_keywords = self.config.get('blacklisted_keywords', [])
        whitelisted_keywords = self.config.get('whitelisted_keywords', [])
        
        # First check whitelist if it's not empty
        if whitelisted_keywords:
            # If whitelist exists, message must match at least one whitelist keyword
            whitelist_match = False
            for keyword in whitelisted_keywords:
                if keyword in message_text:
                    whitelist_match = True
                    logging.info(f"✅ Message matched whitelist keyword: {keyword}")
                    break
            if not whitelist_match:
                logging.info("❌ Message did not match any whitelist keywords")
                return False
        
        # Then check blacklist
        for keyword in blacklisted_keywords:
            if keyword in message_text:
                logging.info(f"❌ Message contains blacklisted keyword: {keyword}")
                return False
                
        return True

    async def handle_new_message(self, event):
        """Process new messages from monitored chats"""
        try:
            # Get the message
            message = event.message
            
            # Skip if message is None
            if not message:
                return
                
            # Check if message is from a monitored chat
            chat_id = str(message.chat_id)
            if int(chat_id) not in self.source_chats:
                return
                
            # Log message receipt for debugging
            try:
                chat = await self.client.get_entity(message.chat_id)
                sender = await self.client.get_entity(message.sender_id) if message.sender_id else None
                sender_name = None
                
                if sender:
                    if hasattr(sender, 'username') and sender.username:
                        sender_name = f"@{sender.username}"
                    elif hasattr(sender, 'title'):  # It's a channel
                        sender_name = f"Channel: {sender.title}"
                    elif hasattr(sender, 'first_name'):  # It's a user
                        sender_name = sender.first_name
                    else:
                        sender_name = f"ID: {message.sender_id}"
                
                logging.info(
                    f"\nReceived message from {chat.title}\n"
                    f"From: {sender_name or 'Unknown'}\n"
                    f"Message: {message.message[:100]}..."
                )
            except Exception as e:
                logging.error(f"Error logging message details: {e}")
                
            # Check user filters
            if chat_id in self.filtered_users and message.sender_id not in self.filtered_users[chat_id]:
                logging.info("Message filtered: User not in monitored list")
                return
                
            # Check for blacklisted keywords
            if not await self.check_message_content(message):
                logging.info("Message filtered: Contains blacklisted keyword")
                return
                
            # Process message content
            content_type, ca = await self.process_message_content(message)
            if not ca:
                logging.info("No CA found in message")
                return
                
            # Skip if already processed
            if ca in self.processed_tokens:
                print(f"⏩ Skipping duplicate token: {ca}")
                return
                
            self.processed_tokens.append(ca)
            self.save_processed_tokens()
            
            # Try to forward the message
            try:
                await message.forward_to(TARGET_CHAT)
                print(f"✅ Forwarded new token: {ca}")
                logging.info(f"Successfully forwarded CA: {ca}")
                self.forwarded_count += 1
            except Exception as forward_error:
                # If forwarding fails due to protection, send as new message
                if "protected chat" in str(forward_error):
                    try:
                        # Create a formatted message with source info
                        source_info = f"Source: {chat.title}"
                        if sender_name:
                            source_info += f" | From: {sender_name}"
                            
                        formatted_message = (
                            f"🔔 New Token Detected\n\n"
                            f"💎 CA: `{ca}`\n\n"
                            f"🔍 {source_info}\n\n"
                            f"Quick Links:\n"
                            f"• Birdeye: https://birdeye.so/token/{ca}\n"
                            f"• Solscan: https://solscan.io/token/{ca}\n"
                            f"• Jupiter: https://jup.ag/swap/SOL-{ca}"
                        )
                        
                        await self.client.send_message(TARGET_CHAT, formatted_message, parse_mode='markdown')
                        print(f"✅ Sent new token message: {ca}")
                        logging.info(f"Successfully sent CA as new message: {ca}")
                        self.forwarded_count += 1
                    except Exception as send_error:
                        print(f"❌ Error sending message: {str(send_error)}")
                        logging.error(f"Error sending message: {str(send_error)}")
                else:
                    print(f"❌ Error forwarding message: {str(forward_error)}")
                    logging.error(f"Error forwarding message: {str(forward_error)}")
            
            self.processed_count += 1
            
        except Exception as e:
            logging.error(f"Error handling message: {str(e)}")
            logging.exception("Full traceback:")

    async def forward_message(self, message, contract_address, content_type="text"):
        """Forward contract address to target chat"""
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

            # Resolve target chat
            try:
                target_entity = None
                
                # Method 1: Try with @ prefix
                if not target_entity:
                    try:
                        target_entity = await self.client.get_entity(f"@{TARGET_CHAT}")
                        logging.info("Resolved target chat using @ prefix")
                    except Exception as e:
                        logging.debug(f"Failed to resolve with @ prefix: {e}")

                # Method 2: Try as channel ID
                if not target_entity and TARGET_CHAT.replace('-', '').isdigit():
                    try:
                        chat_id = int(TARGET_CHAT) if TARGET_CHAT.startswith('-') else int(f"-100{TARGET_CHAT}")
                        target_entity = await self.client.get_entity(chat_id)
                        logging.info("Resolved target chat using ID")
                    except Exception as e:
                        logging.debug(f"Failed to resolve as channel ID: {e}")

                # Method 3: Try direct string
                if not target_entity:
                    try:
                        target_entity = await self.client.get_entity(TARGET_CHAT)
                        logging.info("Resolved target chat using direct string")
                    except Exception as e:
                        logging.debug(f"Failed to resolve as direct string: {e}")

                if target_entity:
                    await self.client.send_message(
                        target_entity,
                        contract_address
                    )
                    logging.info(f"Successfully forwarded CA to {TARGET_CHAT}")
                else:
                    raise ValueError(f"Could not resolve target chat: {TARGET_CHAT}")

            except Exception as e:
                logging.error(f"Error resolving target chat: {str(e)}")
                logging.error(f"Target chat value: {TARGET_CHAT}")
                raise

        except Exception as e:
            logging.error(f"Error forwarding message: {str(e)}")
            # Don't raise here to continue processing other messages

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

    def load_processed_tokens(self) -> list:
        tokens_file = BASE_DIR / 'processed_tokens.json'
        if tokens_file.exists():
            try:
                return json.loads(tokens_file.read_text())
            except Exception as e:
                logging.error(f"Error loading processed tokens: {str(e)}")
        return []

    def save_processed_tokens(self):
        try:
            tokens_file = BASE_DIR / 'processed_tokens.json'
            tokens_file.write_text(json.dumps(self.processed_tokens, indent=4))
        except Exception as e:
            logging.error(f"Error saving processed tokens: {str(e)}")

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
                    f"* Messages Processed: {self.processed_count}\n"
                    f"* Tokens Forwarded: {self.forwarded_count}\n"
                    f"* Unique Tokens: {len(self.processed_tokens)}\n"
                    f"* Uptime: {hours}h {minutes}m\n"
                    f"* Monitoring: {len(self.source_chats)} chats"
                )
                
                await asyncio.sleep(3600)  # Check every hour
            except Exception as e:
                logging.error(f"Health monitor error: {e}")
                await asyncio.sleep(60)  # Wait before retry

    async def run(self):
        try:
            started = await self.start()
            if started:
                print("\n🤖 Bot is running!")
                print("Press Ctrl+C to stop at any time.")
        except KeyboardInterrupt:
            logging.info("Bot stopped by user.")
        finally:
            self.save_processed_tokens()
            await self.client.disconnect()

    async def verify_access(self):
        """Verify user has access through referral link"""
        try:
            if self.config.get('verified', False):
                print("✅ Access previously verified")
                return True
                
            print("\n🔍 Checking Telegram connection...")
            await self.client.connect()
            
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
            
            # Try primary bot first
            verified = await self._try_verify_bot(PRIMARY_BOT['username'], PRIMARY_BOT['ref'])
            if verified:
                return True
            
            # If primary fails, try backup bot
            if not verified:
                print("\n⚠️ Primary bot not started. Trying backup bot...")
                verified = await self._try_verify_bot(BACKUP_BOT['username'], BACKUP_BOT['ref'])
                if verified:
                    return True
            
            # If both fail, show both options to user
            print("\n❌ Bot verification needed")
            print("\nPlease start one of these bots:")
            print(f"1. Primary Bot: https://t.me/{PRIMARY_BOT['username']}?start={PRIMARY_BOT['ref']}")
            print(f"2. Backup Bot: https://t.me/{BACKUP_BOT['username']}?start={BACKUP_BOT['ref']}")
            print("\nSteps:")
            print("1. Click either link above")
            print("2. Click 'Start' in the bot chat")
            print("3. Press Enter here after clicking Start")
            input()
            
            # Check both bots again
            verified = await self._try_verify_bot(PRIMARY_BOT['username'], PRIMARY_BOT['ref'])
            if not verified:
                verified = await self._try_verify_bot(BACKUP_BOT['username'], BACKUP_BOT['ref'])
            
            if verified:
                return True
            
            print("\n❌ Please start one of the bots first:")
            print(f"1. Primary: https://t.me/{PRIMARY_BOT['username']}?start={PRIMARY_BOT['ref']}")
            print(f"2. Backup: https://t.me/{BACKUP_BOT['username']}?start={BACKUP_BOT['ref']}")
            return False
            
        except Exception as e:
            print(f"\n❌ Connection error: {str(e)}")
            print("\nPlease check:")
            print("1. Your internet connection")
            print("2. Your API credentials in .env file")
            return False

    async def _try_verify_bot(self, bot_username: str, ref_code: str) -> bool:
        """Try to verify with a specific bot - just check if they've started it"""
        try:
            bot_entity = await self.client.get_input_entity(bot_username)
            print(f"✓ Found @{bot_username}")
            
            # If we can get the bot entity and any message history, they've started it
            try:
                async for message in self.client.iter_messages(bot_entity, limit=1):
                    print(f"✅ Verified with @{bot_username}!")
                    self.config['verified'] = True
                    self.save_config()
                    return True
            except:
                pass
                
            return False
            
        except Exception as e:
            if "BOT_ALREADY_STARTED" in str(e):
                print(f"✅ Already started @{bot_username}!")
                self.config['verified'] = True
                self.save_config()
                return True
            return False

    async def configure_user_filters(self):
        """Configure user filters for selected chats"""
        print("\n👥 User Filter Setup")
        print("=" * 50)
        print(f"Setting up filters for {len(self.source_chats)} selected chats...")
        
        for i, chat_id in enumerate(self.source_chats, 1):
            # Get chat name from dialogs
            chat_name = None
            try:
                entity = await self.client.get_entity(chat_id)
                chat_name = entity.title
            except:
                chat_name = str(chat_id)
            
            print(f"\n🔍 Chat {i} of {len(self.source_chats)}")
            print(f"Channel: {chat_name}")
            print(f"Chat ID: {chat_id}")
            print("=" * 50)
            
            filtered_users = await self.display_user_filter_menu(chat_id)
            if filtered_users:
                self.filtered_users[str(chat_id)] = filtered_users
                print(f"✅ User filter set for {chat_name}")
            else:
                print(f"👥 Monitoring all users in {chat_name}")
            
            if i < len(self.source_chats):
                proceed = input("\nPress Enter to configure next chat (or 'q' to skip remaining): ")
                if proceed.lower() == 'q':
                    print("\n⏩ Skipping remaining chat configurations...")
                    break
        
        # Show summary
        print("\n📊 Configuration Summary")
        print("=" * 50)
        for chat_id in self.source_chats:
            try:
                entity = await self.client.get_entity(chat_id)
                chat_name = entity.title
                if str(chat_id) in self.filtered_users:
                    user_count = len(self.filtered_users[str(chat_id)])
                    print(f"✓ {chat_name}: Monitoring {user_count} specific users")
                else:
                    print(f"✓ {chat_name}: Monitoring all users")
            except:
                print(f"✓ Chat {chat_id}: Configuration saved")

async def main():
    """Main entry point"""
    print("👋 Welcome to Simple Solana Listener!")
    print("\n📁 Initializing Solana CA Listener...")
    print("=" * 50)
    
    try:
        print("\n🔄 Running startup checks...")
        print("=" * 50)
        bot = SimpleSolListener()
        
        print("\n📊 Startup Summary")
        print("=" * 50)
        print("✓ Environment variables loaded")
        print("✓ Configuration files initialized")
        print("✓ Directories created")
        print("✓ Session loaded")
        print(f"✓ Monitoring {len(bot.source_chats)} chats")
        print(f"✓ Target chat: {TARGET_CHAT}")
        print("=" * 50)
        
        await bot.run()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 