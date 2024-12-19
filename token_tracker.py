import aiohttp
import asyncio
import json
from datetime import datetime
import logging
from typing import Dict, Optional, List
import time
import math
import os
from pathlib import Path
import re

class TokenTracker:
    def __init__(self, telegram_client, notification_target: str = 'me'):
        # Configure logging to be less verbose
        logging.getLogger().setLevel(logging.WARNING)  # Set default level to WARNING
        self.tracked_tokens = {}  # {token_address: {initial_mcap, name, symbol, last_notified_multiple}}
        self.sold_tokens = set()  # Keep track of tokens that were sold
        self.client = telegram_client
        self.JUPITER_BASE_URL = "https://api.jup.ag/price/v2"
        self.notification_target = notification_target  # Where to send notifications ('me' for Saved Messages)
        self.target_chat = os.getenv('TARGET_CHAT')  # Chat to monitor for buy/sell messages
        
        # Initialize tracked_tokens.json and sold_tokens.json
        self.tokens_file = Path('tracked_tokens.json')
        self.sold_tokens_file = Path('sold_tokens.json')
        
        if not self.tokens_file.exists():
            print("✨ Creating tracked tokens file...")
            self.save_tracked_tokens()
            print("✓ tracked_tokens.json created")
            
        if not self.sold_tokens_file.exists():
            print("✨ Creating sold tokens file...")
            self.save_sold_tokens()
            print("✓ sold_tokens.json created")
        
        self.load_tracked_tokens()
        self.load_sold_tokens()
        
        # Rate limiting for Jupiter API (600 requests per minute)
        self.RATE_LIMIT_CALLS = 600
        self.RATE_LIMIT_WINDOW = 60  # seconds
        self.MIN_CHECK_INTERVAL = 60  # Minimum time between checks for each token
        self.api_call_times = []
        
        # Batch processing
        self.current_batch_index = 0
        
        # Buy/Sell indicators
        self.buy_indicators = [
            "buy $", "buy success",  # Exact matches from target chat
            "🟢 buy success",        # With emoji
            "fetched quote",         # Part of buy process
            "⇄",                     # Swap indicator
            "balance: ",             # Part of buy message
            "price: $"               # Part of buy message
        ]
        
        self.sell_indicators = [
            "🟢 sell success",         # Main sell indicator from target chat
            "sell $",                  # Start of sell message
            "⇄",                       # Swap indicator
            "price impact:",           # Part of sell process
            "fetched quote (raydiumamm)",  # Quote indicator
            "balance:",                # Balance check
            "view on solscan"          # Transaction confirmation
        ]

    async def initialize(self):
        """Run initial cleanup after client is connected"""
        await self.initial_cleanup()

    def load_tracked_tokens(self):
        """Load tracked tokens from JSON file"""
        try:
            with open(self.tokens_file, 'r') as f:
                self.tracked_tokens = json.load(f)
            
            # Migrate old format tokens to new format
            for address, info in self.tracked_tokens.items():
                if isinstance(info.get('last_check'), (int, float)):
                    old_timestamp = info['last_check']
                    info['last_check'] = {
                        'time': old_timestamp,
                        'time_readable': self.format_timestamp(old_timestamp),
                        'time_ago': self.format_time_ago(old_timestamp),
                        'mcap': info['initial_mcap'],  # Use initial mcap as placeholder
                        'multiple': 1.0  # Reset multiple
                    }
                    self.save_tracked_tokens()  # Save the migrated data
            
            logging.info(f"Loaded {len(self.tracked_tokens)} tracked tokens")
        except FileNotFoundError:
            self.tracked_tokens = {}
            logging.info("No tracked tokens file found, starting fresh")
        except json.JSONDecodeError:
            self.tracked_tokens = {}
            logging.warning("Tracked tokens file was corrupted, starting fresh")

    def save_tracked_tokens(self):
        """Save tracked tokens to JSON file"""
        try:
            with open(self.tokens_file, 'w') as f:
                json.dump(self.tracked_tokens, f, indent=2)
            logging.info(f"Saved {len(self.tracked_tokens)} tracked tokens")
        except Exception as e:
            logging.error(f"Error saving tracked tokens: {str(e)}")

    def load_sold_tokens(self):
        """Load sold tokens from JSON file"""
        try:
            with open(self.sold_tokens_file, 'r') as f:
                self.sold_tokens = set(json.load(f))
            logging.info(f"Loaded {len(self.sold_tokens)} sold tokens")
        except FileNotFoundError:
            self.sold_tokens = set()
            logging.info("No sold tokens file found, starting fresh")
        except json.JSONDecodeError:
            self.sold_tokens = set()
            logging.warning("Sold tokens file was corrupted, starting fresh")

    def save_sold_tokens(self):
        """Save sold tokens to JSON file"""
        try:
            with open(self.sold_tokens_file, 'w') as f:
                json.dump(list(self.sold_tokens), f, indent=2)
            logging.info(f"Saved {len(self.sold_tokens)} sold tokens")
        except Exception as e:
            logging.error(f"Error saving sold tokens: {str(e)}")

    async def add_token(self, address: str, name: str, initial_mcap: float):
        if address not in self.tracked_tokens:
            now = time.time()
            self.tracked_tokens[address] = {
                'initial_mcap': initial_mcap,
                'name': name,
                'last_notified_multiple': 0,  # Start at 0 to catch the 1x
                'added_at': datetime.now().isoformat(),
                'last_check': {
                    'time': now,
                    'time_readable': self.format_timestamp(now),
                    'time_ago': 'just now',
                    'mcap': initial_mcap,
                    'multiple': 1.0
                },
                'failed_checks': 0
            }
            self.save_tracked_tokens()
            logging.info(f"Started tracking {name} ({address}) with initial mcap: ${initial_mcap:,.2f}")

    def remove_token(self, address: str):
        if address in self.tracked_tokens:
            token_info = self.tracked_tokens.pop(address)
            self.sold_tokens.add(address)  # Add to sold tokens set
            self.save_tracked_tokens()
            self.save_sold_tokens()
            logging.info(f"Stopped tracking {token_info['name']} ({address}) and added to sold tokens")

    def get_next_batch(self, batch_size: int) -> List[str]:
        """Get the next batch of tokens to check"""
        tokens = list(self.tracked_tokens.keys())
        if not tokens:
            return []
            
        # Calculate start index for this batch
        start_idx = self.current_batch_index
        # Update the index for next time
        self.current_batch_index = (self.current_batch_index + batch_size) % len(tokens)
        
        # Handle wrap-around
        if start_idx + batch_size > len(tokens):
            return tokens[start_idx:] + tokens[:batch_size - (len(tokens) - start_idx)]
        else:
            return tokens[start_idx:start_idx + batch_size]

    async def wait_for_rate_limit(self):
        """Implement token bucket rate limiting"""
        current_time = time.time()
        
        # Remove API calls outside the current window
        self.api_call_times = [t for t in self.api_call_times if current_time - t < self.RATE_LIMIT_WINDOW]
        
        # If we've hit the rate limit, wait
        if len(self.api_call_times) >= self.RATE_LIMIT_CALLS:
            wait_time = self.api_call_times[0] + self.RATE_LIMIT_WINDOW - current_time
            if wait_time > 0:
                logging.info(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
                # Recursive call to ensure we're now under the limit
                await self.wait_for_rate_limit()
        
        # Add this call to our window
        self.api_call_times.append(current_time)

    async def get_current_mcap(self, address: str) -> Optional[float]:
        await self.wait_for_rate_limit()
        
        async with aiohttp.ClientSession() as session:
            try:
                # Get price in USDC
                url = f"{self.JUPITER_BASE_URL}?ids={address}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and isinstance(data, dict) and 'data' in data:
                            token_data = data['data'].get(address)
                            if token_data and 'price' in token_data:
                                price = float(token_data['price'])
                                
                                # Get token supply from Solana RPC
                                supply_url = "https://api.mainnet-beta.solana.com"
                                supply_payload = {
                                    "jsonrpc": "2.0",
                                    "id": 1,
                                    "method": "getTokenSupply",
                                    "params": [address]
                                }
                                async with session.post(supply_url, json=supply_payload) as supply_response:
                                    if supply_response.status == 200:
                                        supply_data = await supply_response.json()
                                        if supply_data and 'result' in supply_data:
                                            supply = float(supply_data['result']['value']['amount']) / 10 ** supply_data['result']['value']['decimals']
                                            mcap = price * supply
                                            logging.info(f"Got market cap for {address}: ${mcap:,.2f} (price: ${price}, supply: {supply:,.0f})")
                                            return mcap
                                    
                                    error_msg = f"❌ Could not fetch token supply for {address}"
                                    logging.error(error_msg)
                                    return None
                            
                        error_msg = f"❌ No price data found for token {address} in Jupiter API response"
                        logging.error(error_msg)
                        return None
                    else:
                        error_msg = f"❌ Jupiter API Error ({response.status}): Could not fetch price for {address}"
                        logging.error(error_msg)
                        return None
            except Exception as e:
                error_msg = f"❌ Network Error: Could not fetch price/mcap for {address}\nError: {str(e)}"
                logging.error(error_msg)
                return None

    def format_timestamp(self, timestamp: float) -> str:
        """Convert Unix timestamp to readable format"""
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def format_time_ago(self, timestamp: float) -> str:
        """Convert Unix timestamp to '5 minutes ago' format"""
        now = time.time()
        diff = now - timestamp
        
        if diff < 60:
            return "just now"
        elif diff < 3600:
            minutes = int(diff / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff < 86400:
            hours = int(diff / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(diff / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"

    async def process_token(self, address: str, current_time: float):
        """Process a single token"""
        info = self.tracked_tokens[address]
        
        # Get fresh timestamp for this check
        check_time = time.time()
        
        # Handle old format last_check (migration)
        if isinstance(info.get('last_check'), (int, float)):
            info['last_check'] = {
                'time': info['last_check'],
                'time_readable': self.format_timestamp(info['last_check']),
                'time_ago': self.format_time_ago(info['last_check']),
                'mcap': info['initial_mcap'],
                'multiple': 1.0
            }
            self.save_tracked_tokens()
        
        # Skip if checked too recently
        if check_time - info['last_check']['time'] < self.MIN_CHECK_INTERVAL:
            return
            
        # Get current market cap from Jupiter API
        current_mcap = await self.get_current_mcap(address)
        if current_mcap is not None:
            # Calculate multiple
            multiple = current_mcap / info['initial_mcap']
            
            # Update last check data
            check_time = time.time()
            info['last_check'] = {
                'time': check_time,
                'time_readable': self.format_timestamp(check_time),
                'time_ago': self.format_time_ago(check_time),
                'mcap': current_mcap,
                'multiple': multiple
            }
            info['failed_checks'] = 0
            self.save_tracked_tokens()
            
            # Only log significant changes (more than 10% change in multiple)
            last_multiple = info.get('last_logged_multiple', multiple)
            if abs(multiple - last_multiple) > 0.1:
                logging.warning(f"📊 {info['name']} ({address[:6]}...): {multiple:.2f}x | MCap: ${current_mcap:,.2f}")
                info['last_logged_multiple'] = multiple
            
            # Get the current whole number multiple
            current_whole_multiple = int(multiple)
            last_notified = info['last_notified_multiple']
            
            # Only notify if we've hit a new whole number multiple above 1x
            if current_whole_multiple > max(1, last_notified):
                # Calculate time since entry
                entry_time = datetime.fromisoformat(info['added_at'])
                time_since_entry = datetime.now() - entry_time
                hours = time_since_entry.total_seconds() / 3600
                
                message = (
                    f"💰 Token Multiple Alert 💰\n\n"
                    f"🪙 Token: {info['name']}\n"
                    f"🎯 Multiple: {current_whole_multiple}x\n\n"
                    f"📊 Market Cap:\n"
                    f"  • Initial: ${info['initial_mcap']:,.2f}\n"
                    f"   Current: ${current_mcap:,.2f}\n"
                    f"  • Change: +${current_mcap - info['initial_mcap']:,.2f}\n\n"
                    f"⏱ Time since entry: {int(hours)}h {int((hours % 1) * 60)}m\n\n"
                    f"Quick Links:\n"
                    f"• Birdeye: https://birdeye.so/token/{address}\n"
                    f"• DexScreener: https://dexscreener.com/solana/{address}\n"
                    f"• Solscan: https://solscan.io/token/{address}"
                )
                await self.client.send_message(self.notification_target, message)
                self.tracked_tokens[address]['last_notified_multiple'] = current_whole_multiple
                self.save_tracked_tokens()
                logging.warning(f"🎯 Sent {current_whole_multiple}x notification for {info['name']}")
        else:
            # Log failed check attempt
            info['failed_checks'] = info.get('failed_checks', 0) + 1
            self.save_tracked_tokens()
            
            # Only notify after 5 consecutive failures
            if info['failed_checks'] >= 5:
                info['failed_checks'] = 0  # Reset counter
                logging.error(f"❌ Failed to get market cap for {info['name']} ({address}) after 5 attempts")

    async def check_and_notify_multipliers(self):
        """Check token market caps and notify on multipliers"""
        error_notification_threshold = 5  # Only notify after this many errors
        error_count_total = 0  # Track total errors across checks
        last_cleanup_check = 0  # Track when we last did a cleanup check
        last_catchup_check = 0  # Track when we last did a catchup check
        
        while True:
            try:
                current_time = time.time()
                
                # Run cleanup check every hour
                if current_time - last_cleanup_check >= 3600:  # 3600 seconds = 1 hour
                    await self.cleanup_check()
                    last_cleanup_check = current_time
                
                # Run catchup check every 15 minutes
                if current_time - last_catchup_check >= 900:  # 900 seconds = 15 minutes
                    await self.catchup_check()
                    last_catchup_check = current_time
                
                num_tokens = len(self.tracked_tokens)
                
                if num_tokens == 0:
                    await asyncio.sleep(60)  # Sleep for a minute if no tokens
                    continue
                
                # Process all tokens at once, since we're only checking once per minute
                batch = list(self.tracked_tokens.keys())
                
                success_count = 0
                error_count = 0
                
                # Process batch
                for address in batch:
                    try:
                        await self.process_token(address, current_time)
                        success_count += 1
                        error_count_total = 0  # Reset total error count on success
                    except Exception as e:
                        error_count += 1
                        error_count_total += 1
                        logging.error(f"Error processing token {address}: {str(e)}")
                
                # Log processing info
                logging.info(
                    f"Processed {len(batch)} tokens "
                    f"(Success: {success_count}, Errors: {error_count}). "
                    f"Next check in 60 seconds."
                )
                
                # Only notify if we've hit the error threshold
                if error_count_total >= error_notification_threshold:
                    await self.client.send_message(
                        self.notification_target,
                        f"⚠️ Market Cap Check Issues\n\n"
                        f"Multiple errors occurred while checking market caps.\n"
                        f"This might indicate API issues or network problems.\n\n"
                        f"Will continue checking every minute."
                    )
                    error_count_total = 0  # Reset after notification
                
                # Wait a full minute before next check
                await asyncio.sleep(60)
                
            except Exception as e:
                error_msg = f"Error in market cap checker: {str(e)}"
                logging.error(error_msg)
                error_count_total += 1
                
                # Only notify on persistent errors
                if error_count_total >= error_notification_threshold:
                    await self.client.send_message(
                        self.notification_target,
                        f"⚠️ Market Cap Checker Error\n\n"
                        f"Multiple errors occurred. This might indicate a serious issue.\n"
                        f"Will continue retrying every minute."
                    )
                    error_count_total = 0  # Reset after notification
                
                await asyncio.sleep(60)  # Still wait a minute on error

    async def initial_cleanup(self):
        """Run cleanup and catchup checks on startup with extended message history"""
        try:
            initial_token_count = len(self.tracked_tokens)
            
            # Run extended cleanup check with logging
            logging.warning(f"Starting initial cleanup check with {initial_token_count} tokens...")
            await self.cleanup_check(initial_run=True)
            after_cleanup_count = len(self.tracked_tokens)
            removed_count = initial_token_count - after_cleanup_count
            logging.warning(f"Initial cleanup removed {removed_count} tokens, {after_cleanup_count} remaining.")
            
            # Run extended catchup check
            await self.catchup_check(initial_run=True)
            final_token_count = len(self.tracked_tokens)
            added_count = final_token_count - after_cleanup_count
            
            print("\n📊 Initial Token Check Summary")
            print("==================================================")
            print(f"Initial tokens: {initial_token_count}")
            print(f"🗑️ Removed tokens: {removed_count}")
            print(f"✨ Added tokens: {added_count}")
            print(f"📈 Now tracking {final_token_count} tokens")
            
            # Show current multiples
            if final_token_count > 0:
                print("\n📈 Current Token Status:")
                for address, info in self.tracked_tokens.items():
                    multiple = info['last_check']['multiple']
                    print(f"• {info['name']}: {multiple:.2f}x (${info['last_check']['mcap']:,.2f})")
            print("==================================================\n")
            
        except Exception as e:
            logging.error(f"Error during initial startup checks: {str(e)}")

    async def cleanup_check(self, initial_run: bool = False):
        """Check target chat history for sell messages to cleanup tracked tokens"""
        try:
            if not self.target_chat:
                logging.error("❌ No target chat configured for cleanup check")
                return
                
            current_tracked = set(self.tracked_tokens.keys())
            if not current_tracked:
                return
                
            cleanup_count = 0
            messages_checked = 0
            message_limit = 1000 if initial_run else 100  # Increased limit for initial run
            
            logging.warning(f"🔍 Starting cleanup check in {self.target_chat} for {len(current_tracked)} tokens...")
            
            # Get messages in chronological order
            messages = []
            async for message in self.client.iter_messages(self.target_chat, limit=message_limit, reverse=True):
                messages.append(message)
            
            # Process messages chronologically
            for message in messages:
                if not message or not message.message:
                    continue
                
                text = message.message.lower()
                ca = await self.extract_ca_from_message(message.message)
                if ca and ca in current_tracked:
                    # Check for sell indicators with more detailed logging
                    for indicator in self.sell_indicators:
                        if indicator.lower() in text:
                            logging.warning(f"Found sell indicator '{indicator}' for {ca} in message: {text[:100]}...")
                            self.remove_token(ca)
                            cleanup_count += 1
                            current_tracked.remove(ca)
                            break
                    
                    if not current_tracked:  # If no more tokens to check
                        break
            
            if cleanup_count > 0:
                logging.warning(f"🧹 Cleanup check completed. Removed {cleanup_count} tokens.")
            else:
                logging.warning(f"🔍 Cleanup check completed. No tokens removed after checking {len(messages)} messages.")
            
        except Exception as e:
            logging.error(f"Error during cleanup check: {str(e)}")

    async def catchup_check(self, initial_run: bool = False):
        """Scan recent messages for any buy/sell signals we might have missed"""
        try:
            if not self.target_chat:
                logging.error("❌ No target chat configured for catchup check")
                return
                
            tokens_added = 0
            tokens_removed = 0
            
            temp_tracked = {}  # Tokens bought but not yet sold
            temp_sold = set()  # Tokens that were sold
            
            message_limit = 300 if initial_run else 200
            
            logging.warning(f"🔍 Starting catchup check in {self.target_chat}...")
            
            # Get messages in chronological order
            messages = []
            async for message in self.client.iter_messages(self.target_chat, limit=message_limit, reverse=True):
                messages.append(message)
            
            # Process messages chronologically
            for message in messages:
                if not message or not message.message:
                    continue
                
                text = message.message.lower()
                ca = await self.extract_ca_from_message(message.message)
                if not ca:
                    continue
                
                # Check for sell signals first
                if any(indicator.lower() in text for indicator in self.sell_indicators):
                    if ca in temp_tracked:
                        del temp_tracked[ca]
                        temp_sold.add(ca)
                        tokens_removed += 1
                        logging.warning(f"Found sell signal for {ca} in catchup check")
                    if ca in self.tracked_tokens:
                        self.remove_token(ca)
                        tokens_removed += 1
                        logging.warning(f"Removed tracked token {ca} due to sell signal")
                
                # Then check for buy signals
                elif any(indicator.lower() in text for indicator in self.buy_indicators):
                    # Only process if not sold and not already tracked
                    if ca not in temp_sold and ca not in self.sold_tokens and ca not in temp_tracked and ca not in self.tracked_tokens:
                        # Get initial market cap
                        initial_mcap = await self.get_current_mcap(ca)
                        if initial_mcap:
                            # Try to extract name from message
                            name_match = re.search(r'(?i)(?:' + '|'.join(self.buy_indicators) + r')\s+(?:into\s+)?(\w+)', text)
                            name = name_match.group(1).upper() if name_match else ca[:6]
                            
                            temp_tracked[ca] = {
                                'name': name,
                                'initial_mcap': initial_mcap,
                                'message': message.message
                            }
                            tokens_added += 1
                            logging.warning(f"Found new token {name} ({ca}) in catchup check")
            
            # Add remaining temp tracked tokens to actual tracking
            for ca, info in temp_tracked.items():
                await self.add_token(ca, info['name'], info['initial_mcap'])
            
            if tokens_added > 0 or tokens_removed > 0:
                logging.warning(f"Catchup check completed. Added {tokens_added} tokens, Removed {tokens_removed} tokens.")
            else:
                logging.warning(f"Catchup check completed. No changes after checking {len(messages)} messages.")
            
        except Exception as e:
            logging.error(f"Error during catchup check: {str(e)}")

    async def extract_ca_from_message(self, text: str) -> Optional[str]:
        """Extract contract address from message text"""
        if not text:
            return None
            
        # Common Solana link patterns - prioritize tokens in links
        link_patterns = [
            r'dexscreener\.com/solana/([1-9A-HJ-NP-Za-km-z]{32,44})',
            r'birdeye\.so/token/([1-9A-HJ-NP-Za-km-z]{32,44})',
            r'solscan\.io/token/([1-9A-HJ-NP-Za-km-z]{32,44})',
            r'jup\.ag/swap/[^-]+-([1-9A-HJ-NP-Za-km-z]{32,44})'
        ]
        
        # First try to find token in links
        for pattern in link_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        # Look for token addresses in buy/sell messages
        buy_sell_patterns = [
            r'buy\s+\$\w+\s*[-—]\s*\([^)]+\)\s*[📈•🫧]*\s*([1-9A-HJ-NP-Za-km-z]{32,44})',  # Buy message format
            r'sell\s+\$\w+\s*[-—]\s*\([^)]+\)\s*[📈•🫧]*\s*([1-9A-HJ-NP-Za-km-z]{32,44})',  # Sell message format
            r'balance:\s*[\d.]+ \w+\s*[-—]\s*w\d+.*\nprice:\s*\$[\d.]+\s*[-—]\s*liq:\s*\$[\d.k]+\s*[-—]\s*mc:\s*\$[\d.k]+.*\n.*([1-9A-HJ-NP-Za-km-z]{32,44})',  # Price/MC format
            r'fetched quote.*\n.*⇄.*\n.*\n.*([1-9A-HJ-NP-Za-km-z]{32,44})',  # Quote format
            r'🟢\s*sell\s*success.*view\s*on\s*solscan.*tx/[^)]+\).*([1-9A-HJ-NP-Za-km-z]{32,44})'  # Sell success format
        ]
        
        for pattern in buy_sell_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                return match.group(1)
        
        # If no matches found in structured formats, look for explicitly marked tokens
        explicit_patterns = [
            r'token:\s*([1-9A-HJ-NP-Za-km-z]{32,44})\b',
            r'ca:\s*([1-9A-HJ-NP-Za-km-z]{32,44})\b',
            r'contract:\s*([1-9A-HJ-NP-Za-km-z]{32,44})\b'
        ]
        
        for pattern in explicit_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

    async def handle_sell_message(self, message: str, ca: str):
        """Handle a sell message in real-time"""
        try:
            if ca in self.tracked_tokens:
                token_name = self.tracked_tokens[ca]['name']
                text = message.lower()
                # Check if it's really a sell message
                if any(indicator in text for indicator in self.sell_indicators):
                    self.remove_token(ca)
                    
                    # Send notification about stopping tracking
                    await self.client.send_message(
                        self.notification_target,
                        f"🛑 Stopped Tracking Token\n\n"
                        f"Token: {token_name}\n"
                        f"Reason: Sell message detected"
                    )
        except Exception as e:
            logging.error(f"Error handling sell message: {str(e)}")