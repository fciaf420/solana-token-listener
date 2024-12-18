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
        self.GECKO_BASE_URL = "https://api.geckoterminal.com/api/v2"
        self.notification_target = notification_target  # Where to send notifications ('me' for Saved Messages)
        
        # Initialize tracked_tokens.json if it doesn't exist
        self.tokens_file = Path('tracked_tokens.json')
        if not self.tokens_file.exists():
            print("✨ Creating tracked tokens file...")
            self.save_tracked_tokens()
            print("✓ tracked_tokens.json created")
        
        self.load_tracked_tokens()
        
        # Rate limiting
        self.RATE_LIMIT_CALLS = 30
        self.RATE_LIMIT_WINDOW = 60  # seconds
        self.MIN_CHECK_INTERVAL = 60  # Minimum time between checks for each token (cache time)
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
                url = f"{self.GECKO_BASE_URL}/networks/solana/tokens/{address}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        mcap = float(data['data']['attributes'].get('market_cap_usd', 0))
                        return mcap
                    return None
            except Exception as e:
                logging.error(f"Error fetching market cap for {address}: {str(e)}")
                return None

    async def process_token(self, address: str, current_time: float):
        """Process a single token"""
        info = self.tracked_tokens[address]
        
        # Skip if checked too recently
        if current_time - info.get('last_check', 0) < self.MIN_CHECK_INTERVAL:
            return
            
        current_mcap = await self.get_current_mcap(address)
        if current_mcap:
            info['last_check'] = current_time
            multiple = current_mcap / info['initial_mcap']
            last_notified = info['last_notified_multiple']
            
            # Get the current whole number multiple
            current_whole_multiple = int(multiple)
            
            # Notify if we've hit a new whole number multiple above the last notification
            if current_whole_multiple > last_notified:
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

    async def check_and_notify_multipliers(self):
        while True:
            try:
                current_time = time.time()
                num_tokens = len(self.tracked_tokens)
                
                if num_tokens == 0:
                    await asyncio.sleep(20)
                    continue
                
                # Calculate optimal batch size and delay
                # We want to spread our rate limit across all tokens while respecting cache time
                calls_per_check = 1  # Each token needs 1 API call
                total_calls_needed = num_tokens * calls_per_check
                
                # Calculate how many complete checks we can do in a rate limit window
                max_checks_per_window = self.RATE_LIMIT_CALLS // total_calls_needed
                
                if max_checks_per_window == 0:
                    # If we can't check all tokens in one window, we need to batch them
                    batch_size = self.RATE_LIMIT_CALLS // 2  # Use half our rate limit per batch
                    delay = self.RATE_LIMIT_WINDOW / 2  # Split window in half
                else:
                    # We can check all tokens multiple times per window
                    batch_size = num_tokens
                    delay = self.RATE_LIMIT_WINDOW / max_checks_per_window
                
                # Get next batch of tokens to process
                batch = self.get_next_batch(batch_size)
                
                # Process batch
                for address in batch:
                    try:
                        await self.process_token(address, current_time)
                    except Exception as e:
                        logging.error(f"Error processing token {address}: {str(e)}")
                
                # Log batch processing info
                logging.info(
                    f"Processed batch of {len(batch)} tokens. "
                    f"Total tokens: {num_tokens}. "
                    f"Batch size: {batch_size}. "
                    f"Delay: {delay:.1f}s"
                )
                
                # Wait before next batch
                await asyncio.sleep(delay)
                
            except Exception as e:
                logging.error(f"Error in check_and_notify_multipliers: {str(e)}")
                await asyncio.sleep(20)