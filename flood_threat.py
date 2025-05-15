from whatsapp_messaging_api import send_flood_alert
import logging
import sys

# Set default encoding to utf-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def is_flood_threat(flood_hazard_index):
    # Threshold value that indicates an imminent flood threat
    # This threshold can be adjusted based on specific requirements
    FLOOD_THREAT_THRESHOLD = 0.7
    
    return flood_hazard_index >= FLOOD_THREAT_THRESHOLD

def alert_on_flood_threat(flood_hazard_index, group_id=None, phone_number=None, should_notify=True):

    is_threat = is_flood_threat(flood_hazard_index)
    alert_status = None
    
    if is_threat:
        print(f"Imminent flood threat detected! Index: {flood_hazard_index}")
        
        if should_notify and (group_id or phone_number):
            logger.info(f"Sending WhatsApp alert for flood threat with index: {flood_hazard_index}")
            alert_status = send_flood_alert(flood_hazard_index, group_id, phone_number)
            
            if alert_status["status"] == "success":
                logger.info("Alert sent successfully")
            else:
                logger.error(f"Failed to send alert: {alert_status['message']}")
    else:
        print(f"No imminent flood threat. Index: {flood_hazard_index}")
    
    return is_threat, alert_status

if __name__ == "__main__":
    # Example usage
    test_indices = [0.2, 0.6, 0.7, 0.8, 0.95]
    
    # Set your WhatsApp group ID or phone number here
    # Example group_id: "AbCdEfGhIjKlMnOp"
    # Example phone_number: "+1234567890" (with country code)
    group_id =  'FAXzTqYTt4zF2h6OuVeUck' # Replace with your group ID
    phone_number = '+3139336782' # Replace with your phone number
    
    print("Running flood threat detection with WhatsApp alerts...")
    
    for index in test_indices:
        # Set should_notify=False to disable actual WhatsApp messages during testing
        is_threat, alert_status = alert_on_flood_threat(
            index, 
            group_id=group_id, 
            phone_number=phone_number, 
            should_notify=True  # Set to True to enable actual notifications
        )
        
        if is_threat:
            print("Alert status:", "Not sent (notifications disabled)" if alert_status is None else alert_status)