import asyncio
import re
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
import logging
from typing import List, Dict
import json
import os
import base64
from openai import AsyncOpenAI
import aiohttp
import io
import time
import platform
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config.env')

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

# Telegram credentials from environment variables
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
TARGET_CHAT = os.getenv('TARGET_CHAT')

# Validate required environment variables
if not all([API_ID, API_HASH, TARGET_CHAT]):
    raise ValueError(
        "Please set the following required variables in config.env file:\n"
        "- API_ID\n"
        "- API_HASH\n"
        "- TARGET_CHAT (channel where tokens will be forwarded)"
    )

# Referral settings
REQUIRED_REF = 'r-forza222'
BOT_USERNAME = 'odysseus_trojanbot'

# Config file - use platform-agnostic path
CONFIG_FILE = str(Path('.') / 'sol_listener_config.json')

# Temp directory for downloaded images - use platform-agnostic path
TEMP_DIR = str(Path('.') / 'temp_images')
os.makedirs(TEMP_DIR, exist_ok=True)

class SimpleSolListener:
    def __init__(self):
        self.config = self.load_config()
        session = StringSession(self.config.get('session_string', ''))
        self.client = TelegramClient(session, API_ID, API_HASH)
        
        # Add token tracking
        self.processed_tokens = self.load_processed_tokens()
        self.start_time = time.time()
        
        # Initialize OpenAI client if API key is available
        self.openai_api_key = os.getenv('OPENAI_API_KEY') or self.config.get('openai_api_key')
        self.openai_client = None
        if self.openai_api_key:
            self.openai_client = AsyncOpenAI(api_key=self.openai_api_key)
            logging.info("OpenAI client initialized - Image analysis enabled")
        else:
            logging.info("OpenAI API key not provided - Image analysis disabled")
            
        self.processed_count = 0
        self.forwarded_count = 0
        self.source_chats = []
        self.filtered_users = {}
        self.dialogs_cache: Dict[int, str] = {}
        self.authorized = False

    def load_config(self) -> dict:
        config_path = Path(CONFIG_FILE)
        if config_path.exists():
            try:
                with config_path.open('r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error loading config: {str(e)}")
        return {
            'source_chats': [],
            'filtered_users': {},
            'session_string': None,
            'openai_api_key': None
        }

    def save_config(self):
        try:
            if not self.config.get('session_string'):
                self.config['session_string'] = self.client.session.save()
            self.config['source_chats'] = self.source_chats
            self.config['filtered_users'] = self.filtered_users
            config_path = Path(CONFIG_FILE)
            with config_path.open('w', encoding='utf-8') as f:
                json.dump(self.config, f)
        except Exception as e:
            logging.error(f"Error saving config: {str(e)}")

    async def encode_image_to_base64(self, image_path: str) -> str:
        """Convert image to base64 string"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    async def analyze_image_with_gpt4(self, image_path: str) -> str:
        """Analyze image using GPT-4O"""
        if not self.openai_client:
            logging.debug("Image analysis skipped - OpenAI API key not configured")
            return ""
            
        try:
            base64_image = await self.encode_image_to_base64(image_path)
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Please analyze this image and extract any Solana contract addresses. "
                                       "A Solana address is typically 32-44 characters long and uses base58 characters "
                                       "(1-9 and A-H, J-N, P-Z, a-k, m-z). Look for any text that matches this pattern."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            text = response.choices[0].message.content
            logging.info(f"GPT-4O Analysis: {text}")
            return text
            
        except Exception as e:
            logging.error(f"Error analyzing image with GPT-4O: {str(e)}")
            return ""

    async def download_media_message(self, message) -> str:
        """Download media message and return path"""
        try:
            if message.media:
                file_path = os.path.join(TEMP_DIR, f"temp_{message.id}.jpg")
                await message.download_media(file_path)
                return file_path
        except Exception as e:
            logging.error(f"Error downloading media: {str(e)}")
        return None

    async def extract_ca_from_text(self, text: str) -> str:
        """Extract Solana CA from text"""
        if not text:
            return None
        ca_match = re.search(r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b', text)
        return ca_match.group(0) if ca_match else None

    async def cleanup_temp_file(self, file_path: str):
        """Clean up temporary files"""
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logging.error(f"Error cleaning up file {file_path}: {str(e)}")

    async def process_message_content(self, message) -> tuple[str, str]:
        """Process different types of message content"""
        content_type = "text"
        ca = None
        
        try:
            if isinstance(message.media, (types.MessageMediaPhoto, types.MessageMediaDocument)):
                # Skip image analysis if OpenAI is not configured
                if not self.openai_client:
                    logging.debug("Skipping image analysis - OpenAI not configured")
                    if message.message:  # Still check for text in media messages
                        logging.info(f"Received message: {message.message}")
                        ca = await self.extract_ca_from_text(message.message)
                        if ca:
                            logging.info(f"Checking text for CA: {message.message}")
                            logging.info(f"Found CA: {ca}")
                    return "media_skipped", ca
                
                content_type = "photo" if isinstance(message.media, types.MessageMediaPhoto) else "document"
                if isinstance(message.media, types.MessageMediaDocument) and not message.media.document.mime_type.startswith('image/'):
                    return content_type, None
                
                file_path = await self.download_media_message(message)
                if file_path:
                    text = await self.analyze_image_with_gpt4(file_path)
                    if text:
                        logging.info(f"Received image text: {text}")
                        ca = await self.extract_ca_from_text(text)
                        if ca:
                            logging.info(f"Checking image text for CA: {text}")
                            logging.info(f"Found CA: {ca}")
                    await self.cleanup_temp_file(file_path)
            
            elif message.message:  # Text message
                logging.info(f"Received message: {message.message}")
                ca = await self.extract_ca_from_text(message.message)
                if ca:
                    logging.info(f"Checking text for CA: {message.message}")
                    logging.info(f"Found CA: {ca}")
        
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
                print("❌ Please enter valid numbers separated by commas")
        
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
                    print(" No users found in recent messages")
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
                        print("❌ Please enter valid numbers")
                
                return selected_users if selected_users else None
                
            except Exception as e:
                logging.error(f"Error loading users: {e}")
                return None
        
        return None  # Monitor all users

    async def check_referral(self) -> bool:
        """Check if the user joined through the correct referral link"""
        try:
            print("\n🔍 Checking Telegram connection...")
            
            # First verify we can connect to Telegram
            try:
                await self.client.connect()
                print("✅ Successfully connected to Telegram")
            except Exception as e:
                print("\n❌ Failed to connect to Telegram!")
                print("Please check:")
                print("1. You have created config.env file")
                print("2. Your API_ID and API_HASH are correct in config.env")
                print("3. Your internet connection is working")
                print(f"\nError details: {str(e)}")
                return False

            print("\n🔍 Verifying referral...")
            # Get bot's chat history to check start parameter
            try:
                async for message in self.client.iter_messages(BOT_USERNAME, limit=1):
                    if message and message.message:
                        # Check if the start command contains our referral code
                        if f"start={REQUIRED_REF}" in message.message:
                            print("✅ Referral verified successfully!")
                            return True
                
                print("\n❌ Referral verification failed!")
                print("Please make sure to:")
                print(f"1. Join the bot using this link: https://t.me/{BOT_USERNAME}?start={REQUIRED_REF}")
                print("2. Start the bot by clicking 'Start' or sending /start")
                return False
                
            except Exception as e:
                print("\n❌ Error checking referral!")
                print("Please make sure you've:")
                print(f"1. Joined the bot: https://t.me/{BOT_USERNAME}?start={REQUIRED_REF}")
                print("2. Started a chat with the bot")
                print(f"\nError details: {str(e)}")
                return False
            
        except Exception as e:
            print(f"\n❌ Unexpected error during verification: {str(e)}")
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

    async def start(self):
        """Start the bot with menu selection"""
        print("\n📋 Checking setup...")
        
        # Check if config.env exists
        if not os.path.exists('config.env'):
            print("\n❌ config.env file not found!")
            print("\nRequired Steps:")
            print("1. Rename or copy config.env.sample to config.env:")
            print("   Windows: copy config.env.sample config.env")
            print("   Linux/Mac: cp config.env.sample config.env")
            print("\n2. Edit config.env with your credentials:")
            print("   - API_ID (from https://my.telegram.org/apps)")
            print("   - API_HASH (from https://my.telegram.org/apps)")
            return False
            
        # Check if required credentials are set
        if not all([API_ID, API_HASH]):
            print("\n❌ Missing API credentials in config.env!")
            print("\nPlease edit config.env and set:")
            print("- API_ID (from https://my.telegram.org/apps)")
            print("- API_HASH (from https://my.telegram.org/apps)")
            return False

        # First check referral
        print("\n🔍 Verifying access...")
        self.authorized = await self.check_referral()
        if not self.authorized:
            return False

        # Continue with normal startup if authorized
        if not self.openai_api_key:
            print("\n⚠️ OpenAI API key not provided - Image analysis will be disabled")
            print("You can add it later in config.env if needed")

        try:
            await self.client.start()
        except Exception as e:
            print("\n❌ Failed to start the bot!")
            print("Please check:")
            print("1. Your API credentials are correct")
            print("2. You have internet connection")
            print(f"\nError details: {str(e)}")
            return False

        # Setup target chat if not configured
        if not TARGET_CHAT:
            print("\n⚠️ Target chat not configured!")
            target_chat = await self.setup_target_chat()
            if not await self.verify_target_chat(target_chat):
                print("\n❌ Target chat setup failed!")
                print("Please try again with a different channel")
                return False
            
            # Update config.env with the new target chat
            config_path = Path('config.env')
            config_content = config_path.read_text()
            if 'TARGET_CHAT=' in config_content:
                config_content = re.sub(r'TARGET_CHAT=.*\n', f'TARGET_CHAT={target_chat}\n', config_content)
            else:
                config_content += f'\nTARGET_CHAT={target_chat}\n'
            config_path.write_text(config_content)
            print("\n✅ Target chat configured and saved to config.env!")
            
            # Update global variable
            global TARGET_CHAT
            TARGET_CHAT = target_chat
        else:
            # Verify existing target chat
            if not await self.verify_target_chat(TARGET_CHAT):
                return False

        self.save_config()
        
        # Load previous configuration or select new chats
        if self.config.get('source_chats'):
            print("\n📋 Previously monitored chats found!")
            print("1. Continue with previous selection")
            print("2. Select new chats")
            if input("\nEnter choice (1-2): ") == "1":
                self.source_chats = self.config['source_chats']
                self.filtered_users = self.config.get('filtered_users', {})
            else:
                self.source_chats = await self.display_chat_selection()
        else:
            self.source_chats = await self.display_chat_selection()
        
        if not self.source_chats:
            logging.info("No chats selected. Bot startup cancelled.")
            return False
            
        # Set up user filters for each chat
        print("\n User Filter Setup")
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
        
        self.save_config()
        
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
        
        logging.info(f"Starting Solana CA Listener for {len(self.source_chats)} chats")
        
        @self.client.on(events.NewMessage(chats=self.source_chats))
        async def handle_new_message(event):
            try:
                # Check user filter
                chat_id = str(event.chat_id)
                if chat_id in self.filtered_users:
                    if event.sender_id not in self.filtered_users[chat_id]:
                        return
                
                self.processed_count += 1
                
                # Process message content
                content_type, ca = await self.process_message_content(event.message)
                
                if ca:
                    # Check if token was already processed
                    if await self.is_token_processed(ca):
                        logging.info(f"Skipping duplicate token: {ca}")
                        return
                    
                    logging.info(f"Found new Solana CA in {content_type}: {ca}")
                    await self.forward_message(event.message, ca, content_type)
                    await self.add_processed_token(ca)
                    self.forwarded_count += 1
                
                if self.processed_count % 10 == 0:
                    logging.info(f"Stats - Processed: {self.processed_count}, "
                               f"Forwarded: {self.forwarded_count}")
                    
            except Exception as e:
                logging.error(f"Error processing message: {str(e)}")
        
        return True

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
            await self.client.send_message(
                TARGET_CHAT,
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

    def load_processed_tokens(self) -> set:
        """Load previously processed tokens"""
        tokens_path = Path('processed_tokens.json')
        try:
            if tokens_path.exists():
                with tokens_path.open('r', encoding='utf-8') as f:
                    return set(json.load(f))
        except Exception as e:
            logging.error(f"Error loading processed tokens: {e}")
        return set()

    def save_processed_tokens(self):
        """Save processed tokens to file"""
        tokens_path = Path('processed_tokens.json')
        try:
            with tokens_path.open('w', encoding='utf-8') as f:
                json.dump(list(self.processed_tokens), f)
        except Exception as e:
            logging.error(f"Error saving processed tokens: {e}")

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
                print("\n��� Bot startup cancelled. Please make sure you:")
                print(f"1. Join using the correct referral link: https://t.me/{BOT_USERNAME}?start={REQUIRED_REF}")
                print("2. Have valid API credentials in your config.env file")
        except KeyboardInterrupt:
            logging.info("Bot stopped by user.")
        finally:
            self.save_processed_tokens()
            await self.client.disconnect()

async def main():
    bot = SimpleSolListener()
    await bot.run()

if __name__ == "__main__":
    print("🤖 Welcome to Simple Solana Listener!")
    asyncio.run(main()) 