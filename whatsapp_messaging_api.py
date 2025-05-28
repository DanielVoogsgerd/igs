from flask import Flask, request, jsonify
import pywhatkit
import time
import datetime
import logging
import sys
import os
import webbrowser
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Public exports
__all__ = ['send_flood_alert', 'send_whatsapp_message']

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set default encoding to utf-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Flask app
app = Flask(__name__)

# Global settings
PROFILE_DIR = "./whatsapp_persistent_profile"
HAS_AUTHENTICATED = False
WAIT_TIME = 30


def send_whatsapp_message(phone_number, message, group_id=None):

    full_message = f"⚠️ IMPORTANT MESSAGE ⚠️\n\n{message}"

    result = _send_with_browser(phone_number, full_message, group_id)
    if result["status"] == "success":
        return result
    

    logger.info("Browser method failed, trying fallback method...")
    return _open_whatsapp_directly(phone_number, full_message, group_id)


def _send_with_browser(phone_number, message, group_id=None):

    global HAS_AUTHENTICATED
    
    try:
        # Setup browser
        chrome_options = Options()
        
        # Create profile directory if it doesn't exist
        if not os.path.exists(PROFILE_DIR):
            os.makedirs(PROFILE_DIR, exist_ok=True)
        
        # Use persistent profile to maintain login session
        chrome_options.add_argument(f"--user-data-dir={PROFILE_DIR}")
        
        # Launch browser
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            # Start at WhatsApp Web home
            driver.get("https://web.whatsapp.com/")
            
            # Show QR code scan instructions if first time
            if not HAS_AUTHENTICATED:
                print("\n" + "="*60)
                print("PLEASE SCAN QR CODE IN BROWSER WINDOW")
                print("You only need to do this once")
                print("="*60 + "\n")
            

            try:
                WebDriverWait(driver, WAIT_TIME).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='3']"))
                )
                HAS_AUTHENTICATED = True
                logger.info("Authentication successful")
            except TimeoutException:
                logger.warning("Authentication timed out - waiting for QR code scan")
                # Wait longer in case user is scanning QR code
                WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='3']"))
                )
                HAS_AUTHENTICATED = True
            
            # Navigate to specific chat
            if group_id:
                driver.get(f"https://web.whatsapp.com/accept?code={group_id}")
            else:
                formatted_phone = phone_number.replace("+", "").replace(" ", "")
                driver.get(f"https://web.whatsapp.com/send?phone={formatted_phone}")
            
            # Wait for chat to load
            logger.info("Waiting for chat to load...")
            time.sleep(5)
            
            # Check for and click join button if present
            try:
                join_buttons = driver.find_elements(By.XPATH, "//div[contains(text(), 'Join') or contains(text(), 'join')]")
                if join_buttons:
                    logger.info("Found join button, clicking...")
                    join_buttons[0].click()
                    time.sleep(3)
            except Exception as e:
                logger.info(f"No join button found or couldn't click: {e}")
            
            # Find text input box
            input_box = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='10']"))
            )
            
            # Input message
            input_box.clear()
            
            # Send in chunks to avoid issues
            for chunk in [message[i:i+20] for i in range(0, len(message), 20)]:
                input_box.send_keys(chunk)
                time.sleep(0.2)
            
            # Send message
            time.sleep(1)
            input_box.send_keys(Keys.ENTER)
            
            # Take screenshot for debugging
            try:
                screenshot_path = "whatsapp_debug.png"
                driver.save_screenshot(screenshot_path)
                logger.info(f"Saved screenshot to {screenshot_path}")
            except Exception:
                pass
            
            logger.info("Message sent successfully")
            time.sleep(3)
            return {"status": "success", "message": "Message sent successfully"}
            
        finally:
            # Clean up
            driver.quit()
    
    except Exception as e:
        logger.error(f"Error using browser method: {e}")
        return {"status": "error", "message": str(e)}


def _open_whatsapp_directly(phone_number, message, group_id=None):
    """Simple method to open WhatsApp Web and guide user to send message manually"""
    try:
        # Configure pywhatkit
        try:
            pywhatkit.config.wait_time = 15
            pywhatkit.config.close_tab = False
        except AttributeError:
            try:
                pywhatkit.settings.wait_time = 15
                pywhatkit.settings.close_tab = False
            except AttributeError:
                logger.warning("Could not configure pywhatkit")
        
        # Calculate time (1 minute from now)
        now = datetime.datetime.now()
        hour, minute = now.hour, (now.minute + 1) % 60
        if now.minute == 59:
            hour = (hour + 1) % 24
        
        # Show instructions
        print("\n" + "="*60)
        print("MANUAL ACTION REQUIRED:")
        print("1. A browser will open to WhatsApp Web")
        print("2. Scan QR code with your phone if prompted")
        print("3. The message should be sent automatically")
        print("4. If not, copy and paste this message:")
        print("-"*40)
        print(message)
        print("-"*40)
        print("="*60 + "\n")
        
        # Try pywhatkit's methods
        if group_id:
            # Open directly to group
            webbrowser.open(f"https://web.whatsapp.com/accept?code={group_id}")
            time.sleep(2)
            
            # Try pywhatkit as backup
            try:
                pywhatkit.sendwhatmsg_to_group(group_id, message, hour, minute, wait_time=15)
                return {"status": "success", "message": "Message sent via pywhatkit"}
            except Exception as e:
                logger.warning(f"Pywhatkit group message failed: {e}")
                return {"status": "partial", "message": "WhatsApp Web opened for manual sending"}
        else:
            # For individual messages
            formatted_phone = phone_number.replace("+", "").replace(" ", "")
            try:
                pywhatkit.sendwhatmsg(formatted_phone, message, hour, minute, wait_time=15)
                return {"status": "success", "message": "Message sent via pywhatkit"}
            except Exception as e:
                logger.warning(f"Pywhatkit message failed: {e}")
                webbrowser.open(f"https://web.whatsapp.com/send?phone={formatted_phone}")
                return {"status": "partial", "message": "WhatsApp Web opened for manual sending"}
    
    except Exception as e:
        logger.error(f"Error opening WhatsApp Web: {e}")
        return {"status": "error", "message": str(e)}


def send_flood_alert(hazard_index, group_id=None, phone_number=None, affected_regions=None, language='en'):

    if not group_id and not phone_number:
        logger.error("Either group_id or phone_number must be provided")
        return {"status": "error", "message": "Either group_id or phone_number must be provided"}
    
    # Import translation function here to avoid circular imports
    from flood_threat import format_alert_message

    message = format_alert_message(hazard_index, affected_regions, language)

    logger.info(f"Sending flood alert with hazard index {hazard_index:.2f} for regions: {affected_regions or 'Unknown'} in {language}")
    
    # Send the message
    return send_whatsapp_message(phone_number, message, group_id)


@app.route('/send_alert', methods=['POST'])
def send_alert():
    """API endpoint to send an alert message"""
    data = request.json
    
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400
    
    message = data.get('message')
    if not message:
        return jsonify({"status": "error", "message": "No message provided"}), 400
    
    phone_number = data.get('phone_number')
    group_id = data.get('group_id')
    
    if not phone_number and not group_id:
        return jsonify({"status": "error", "message": "Either phone_number or group_id must be provided"}), 400

    hazard_index = data.get('hazard_index')
    if hazard_index:
        logger.info(f"Sending alert for hazard index: {hazard_index}")
    
    # Send the message
    result = send_whatsapp_message(phone_number, message, group_id)
    
    if result["status"] == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 500


if __name__ == "__main__":
    # For testing purposes
    print("Starting WhatsApp Messaging API")
    # Test direct message sending
    result = send_flood_alert(0.85, group_id="FAXzTqYTt4zF2h6OuVeUck")
    print(f"Result: {result}")
    # Flask server:
    # app.run(debug=True, port=5000)