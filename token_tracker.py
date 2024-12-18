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

class TokenTracker:
    def __init__(self, telegram_client, notification_target: str = 'me'):
        self.tracked_tokens = {}  # {token_address: {initial_mcap, name, symbol, last_notified_multiple}}
        self.client = telegram_client
        self.JUPITER_BASE_URL = "https://api.jup.ag/price/v2"
        self.notification_target = notification_target  # Where to send notifications ('me' for Saved Messages)
        
        # Initialize tracked_tokens.json if it doesn't exist
        self.tokens_file = Path('tracked_tokens.json')
        if not self.tokens_file.exists():
            print("✨ Creating tracked tokens file...")
            self.save_tracked_tokens()
            print("✓ tracked_tokens.json created")
        
        self.load_tracked_tokens()
        
        # Rate limiting for Jupiter API (600 requests per minute)
        self.RATE_LIMIT_CALLS = 600
        self.RATE_LIMIT_WINDOW = 60  # seconds
        self.MIN_CHECK_INTERVAL = 60  # Minimum time between checks for each token
        self.api_call_times = []
        
        # Batch processing
        self.current_batch_index = 0

    def load_tracked_tokens(self):
        """Load tracked tokens from JSON file"""
        try:
            with open(self.tokens_file, 'r') as f:
                self.tracked_tokens = json.load(f)
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

    async def add_token(self, address: str, name: str, initial_mcap: float):
        if address not in self.tracked_tokens:
            self.tracked_tokens[address] = {
                'initial_mcap': initial_mcap,
                'name': name,
                'last_notified_multiple': 0,  # Start at 0 to catch the 1x
                'added_at': datetime.now().isoformat(),
                'last_check': 0  # Track when we last checked this token
            }
            self.save_tracked_tokens()
            logging.info(f"Started tracking {name} ({address}) with initial mcap: ${initial_mcap:,.2f}")

    def remove_token(self, address: str):
        if address in self.tracked_tokens:
            token_info = self.tracked_tokens.pop(address)
            self.save_tracked_tokens()
            logging.info(f"Stopped tracking {token_info['name']} ({address})")

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

    async def process_token(self, address: str, current_time: float):
        """Process a single token"""
        info = self.tracked_tokens[address]
        
        # Skip if checked too recently
        if current_time - info.get('last_check', 0) < self.MIN_CHECK_INTERVAL:
            return
            
        # Get current market cap from Jupiter API
        current_mcap = await self.get_current_mcap(address)
        if current_mcap is not None:
            info['last_check'] = current_time
            multiple = current_mcap / info['initial_mcap']
            last_notified = info['last_notified_multiple']
            
            # Log the check for debugging
            logging.info(f"Token: {info['name']} ({address})")
            logging.info(f"Initial MCap: ${info['initial_mcap']:,.2f}")
            logging.info(f"Current MCap: ${current_mcap:,.2f}")
            logging.info(f"Multiple: {multiple:.2f}x")
            
            # Get the current whole number multiple
            current_whole_multiple = int(multiple)
            
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
                    f"  • Current: ${current_mcap:,.2f}\n"
                    f"  • Change: +${current_mcap - info['initial_mcap']:,.2f}\n\n"
                    f"⏱ Time since entry: {int(hours)}h {int((hours % 1) * 60)}m\n\n"
                    f"🔗 Quick Links:\n"
                    f"• Birdeye: https://birdeye.so/token/{address}\n"
                    f"• DexScreener: https://dexscreener.com/solana/{address}\n"
                    f"• Solscan: https://solscan.io/token/{address}"
                )
                await self.client.send_message(self.notification_target, message)
                self.tracked_tokens[address]['last_notified_multiple'] = current_whole_multiple
                self.save_tracked_tokens()
        else:
            # Log failed check attempt
            info['last_check'] = current_time  # Still update last check to prevent spam
            info['failed_checks'] = info.get('failed_checks', 0) + 1
            
            # Only notify after 5 consecutive failures
            if info['failed_checks'] >= 5:
                info['failed_checks'] = 0  # Reset counter
                logging.error(f"❌ Failed to get market cap for {info['name']} ({address}) after 5 attempts")
            
            self.save_tracked_tokens()

    async def check_and_notify_multipliers(self):
        """Check token market caps and notify on multipliers"""
        error_notification_threshold = 5  # Only notify after this many errors
        error_count_total = 0  # Track total errors across checks
        
        while True:
            try:
                current_time = time.time()
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