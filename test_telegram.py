"""
Test script for Telegram notifications.
"""
import os
from dotenv import load_dotenv
from src.notifications.telegram_notifier import TelegramNotifier
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_telegram():
    # Load environment variables
    load_dotenv()
    
    # Get Telegram credentials
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    print(f"Using Bot Token: {bot_token}")
    print(f"Using Chat ID: {chat_id}")
    
    # Initialize notifier
    notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
    
    # Test will be performed automatically in __init__
    
if __name__ == "__main__":
    test_telegram() 