from flask import Flask, request, jsonify
import pywhatkit
import time
import datetime
import logging
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# Set default encoding to utf-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

def setup_whatsapp_config(wait_time=15, close_tab=True):

    # PyWhatKit updated its API - different ways to set config depending on version
    try:
        # Try new API style first
        pywhatkit.config.wait_time = wait_time
        pywhatkit.config.close_tab = close_tab
    except AttributeError:
        try:
            # Try old API style
            pywhatkit.settings.wait_time = wait_time
            pywhatkit.settings.close_tab = close_tab
        except AttributeError:
            # If both fail, log the issue but continue
            logger.warning("Unable to configure PyWhatKit settings - using defaults")
    
    logger.info("WhatsApp configuration set up successfully")

def send_whatsapp_message(phone_number, message, group_id=None):
    """
    Send a WhatsApp message using headless Chrome browser.
    
    Args:
        phone_number: The recipient's phone number (with country code)
        message: The message content
        group_id: Optional group ID for group messages
    
    Returns:
        Dictionary with status and message
    """
    try:
        # Configure Chrome options for headless mode
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")  # Use new headless mode
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Set user agent to avoid detection as a bot
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
        chrome_options.add_argument(f'user-agent={user_agent}')
        
        # Generate a unique profile directory for each session to avoid conflicts
        import uuid
        profile_dir = f"./whatsapp_profile_{uuid.uuid4().hex[:8]}"
        chrome_options.add_argument(f"--user-data-dir={profile_dir}")
        
        logger.info("Initializing Chrome driver in headless mode")
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            # Import wait utilities for more robust element detection
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException, NoSuchElementException
            
            if group_id:
                # Send message to a group using direct web URL
                logger.info(f"Sending message to group {group_id} using headless browser")
                web_url = f"https://web.whatsapp.com/accept?code={group_id}"
                driver.get(web_url)
                
                logger.info("Waiting for WhatsApp Web to load")
                # Use a single loaded condition for the chat page
                try:
                    WebDriverWait(driver, 60).until(
                        EC.visibility_of_any_elements_located((By.CSS_SELECTOR, "[contenteditable='true']"))
                    )
                    logger.info("WhatsApp Web loaded successfully")
                except TimeoutException:
                    logger.error("Timed out waiting for WhatsApp Web to load")
                    # If we can't find the input field, try directly sending the message via URL
                    driver.get(f"https://web.whatsapp.com/accept?code={group_id}&text={message}")
                    time.sleep(20)  # Give extra time for WhatsApp to load with the message
                    # Try to press Enter
                    driver.find_element(By.CSS_SELECTOR, "body").send_keys(Keys.ENTER)
                    time.sleep(3)  # Wait for message to send
                    return {"status": "success", "message": f"Message sent to group {group_id} via direct URL"}
                
                # Try multiple selector strategies to find the input field
                text_box = None
                selectors = [
                    (By.CSS_SELECTOR, "[contenteditable='true']"),
                    (By.CSS_SELECTOR, "div[role='textbox']"),
                    (By.CSS_SELECTOR, "div[data-testid='conversation-compose-box-input']"),
                    (By.CSS_SELECTOR, "footer div.selectable-text"),
                    (By.XPATH, "//div[contains(@class, 'selectable-text')]")
                ]
                
                for selector_type, selector in selectors:
                    try:
                        text_box = driver.find_element(selector_type, selector)
                        logger.info(f"Found input field using {selector_type}: {selector}")
                        break
                    except NoSuchElementException:
                        continue
                
                if text_box:
                    # Send message using JavaScript to ensure it works in headless mode
                    driver.execute_script(f"arguments[0].innerHTML = '{message}'", text_box)
                    text_box.send_keys(Keys.ENTER)
                    logger.info(f"Message entered and sent to group {group_id}")
                    time.sleep(3)  # Wait for message to send
                    return {"status": "success", "message": f"Message sent to group {group_id} using headless browser"}
                else:
                    raise Exception("Could not find message input field using any selector strategy")
            else:
                # Send message to an individual
                logger.info(f"Sending message to {phone_number} using headless browser")
                formatted_phone = phone_number.replace("+", "").replace(" ", "")
                
                # Include the message directly in the URL for easier sending
                web_url = f"https://web.whatsapp.com/send?phone={formatted_phone}&text={message}"
                driver.get(web_url)
                
                # Wait for the page to load
                logger.info("Waiting for WhatsApp Web to load")
                try:
                    # Wait for either the message input field or the send button to appear
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                    )
                    logger.info("WhatsApp Web page loaded")
                    
                    # Try to press Enter to send the pre-filled message
                    driver.find_element(By.CSS_SELECTOR, "body").send_keys(Keys.ENTER)
                    logger.info("Enter key sent to body")
                    time.sleep(3)  # Wait for message to send
                    
                    return {"status": "success", "message": f"Message sent to {phone_number} using headless browser"}
                except TimeoutException:
                    logger.error("Timed out waiting for WhatsApp Web to load")
                    raise Exception("Timed out waiting for WhatsApp Web to load")
        finally:
            # Always close the driver
            driver.quit()
            
            # Clean up the temporary profile directory
            import shutil
            try:
                shutil.rmtree(profile_dir, ignore_errors=True)
                logger.info(f"Cleaned up temporary profile directory: {profile_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up profile directory: {str(e)}")
    
    except Exception as e:
        error_msg = f"Error sending WhatsApp message: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}

# Flask routes
@app.route('/send_alert', methods=['POST'])
def send_alert():

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
    
    # Optional hazard index for logging
    hazard_index = data.get('hazard_index')
    if hazard_index:
        logger.info(f"Sending alert for hazard index: {hazard_index}")
    
    # Configure settings
    setup_whatsapp_config()
    
    # Send the message
    result = send_whatsapp_message(phone_number, message, group_id)
    
    if result["status"] == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 500

def send_flood_alert(hazard_index, group_id=None, phone_number=None):
    """
    Send a flood alert to a WhatsApp group or individual.
    
    Args:
        hazard_index: The flood hazard index value
        group_id: Optional WhatsApp group ID
        phone_number: Optional recipient phone number
        
    Returns:
        Dictionary with status and message
    """
    if not group_id and not phone_number:
        logger.error("Either group_id or phone_number must be provided")
        return {"status": "error", "message": "Either group_id or phone_number must be provided"}
    
    message = f"FLOOD ALERT!\nImminent flood threat detected with hazard index of {hazard_index:.2f}.\nPlease take necessary precautions immediately."
    
    # Log the alert
    logger.info(f"Sending flood alert with hazard index {hazard_index:.2f}")
    
    # Send the message using the headless implementation
    return send_whatsapp_message(phone_number, message, group_id)

if __name__ == "__main__":
    # For testing purposes
    print("Starting WhatsApp Messaging API")
    # Uncomment to test sending a message:
    # send_flood_alert(0.85, group_id="Your_Group_ID_Here")
    # Or to run the Flask server:
    app.run(debug=True, port=5000)