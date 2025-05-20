from flask import Flask, request, jsonify
import logging
import sys
import requests
import time

# Set default encoding to utf-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global variable to store the bot token
BOT_TOKEN = 'place token here'

def setup_telegram_config(token):

    global BOT_TOKEN
    BOT_TOKEN = token
    
    # Verify that the token works by making a simple API call
    try:
        response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe")
        response.raise_for_status()
        bot_info = response.json()
        
        if bot_info.get("ok"):
            logger.info(f"Telegram bot configured successfully: @{bot_info['result']['username']}")
            return True
        else:
            logger.error(f"Failed to configure Telegram bot: {bot_info.get('description', 'Unknown error')}")
            return False
    except Exception as e:
        logger.error(f"Error setting up Telegram bot: {str(e)}")
        return False

def send_telegram_message(chat_id, message):

    if not BOT_TOKEN:
        error_msg = "Telegram bot not configured. Call setup_telegram_config first."
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}
    
    try:
        logger.info(f"Sending message to chat_id {chat_id}")
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"  # Supports HTML formatting in messages
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        
        if result.get("ok"):
            logger.info(f"Message sent successfully to chat_id {chat_id}")
            return {"status": "success", "message": "Message sent successfully", "message_id": result["result"]["message_id"]}
        else:
            error_msg = f"Failed to send message: {result.get('description', 'Unknown error')}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
    
    except Exception as e:
        error_msg = f"Error sending Telegram message: {str(e)}"
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
    
    chat_id = data.get('chat_id')
    if not chat_id:
        return jsonify({"status": "error", "message": "No chat_id provided"}), 400
    

    hazard_index = data.get('hazard_index')
    if hazard_index:
        logger.info(f"Sending alert for hazard index: {hazard_index}")
    
    # Send the message
    result = send_telegram_message(chat_id, message)
    
    if result["status"] == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 500

def send_flood_alert(hazard_index, chat_id, affected_regions=None, language='en'):

    ##Send a specific flood alert message with the hazard index and affected regions.


    if not chat_id:
        logger.error("chat_id must be provided")
        return {"status": "error", "message": "chat_id must be provided"}

    from flood_threat import translate_message, format_alert_message

    templates = {
        'alert_title': translate_message("FLOOD ALERT!", language),
        'threat_detected': translate_message("Imminent flood threat detected with hazard index of", language),
        'affected_regions': translate_message("Affected regions", language),
        'take_precautions': translate_message("Please take necessary precautions immediately.", language),
    }
    

    regions_text = f"\n\n<b>{templates['affected_regions']}:</b> {affected_regions}" if affected_regions else ""
    
    message = f"<b>🚨 {templates['alert_title']}</b>\n\n{templates['threat_detected']} <b>{hazard_index:.2f}</b>.{regions_text}\n\n{templates['take_precautions']}"
    
    # Log the alert
    logger.info(f"Sending flood alert with hazard index {hazard_index:.2f} for regions: {affected_regions or 'Unknown'} in {language}")
    
    # Send the message
    return send_telegram_message(chat_id, message)

if __name__ == "__main__":
    # For testing purposes
    print("Starting Telegram Messaging API")
    # Uncomment to test sending a message:
    setup_telegram_config("YOUR_BOT_TOKEN_HERE")
    send_flood_alert(0.85, "YOUR_CHAT_ID_HERE")
    # Or to run the Flask server:
    app.run(debug=True, port=5001)  # Using port 5001 to avoid conflict with WhatsApp API