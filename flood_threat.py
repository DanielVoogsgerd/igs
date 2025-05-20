from whatsapp_messaging_api import send_flood_alert as send_whatsapp_alert
from telegram_messaging_api import setup_telegram_config, send_flood_alert as send_telegram_alert
import logging
import sys
import gettext
import os

# Only import these when needed (not during testing)
def import_spatial_libraries():
    import geopandas as gpd
    import numpy as np
    from areas import map_grid_cells_to_areas
    return gpd, np, map_grid_cells_to_areas

# Set up internationalization
gettext.bindtextdomain('flood_alerts', './locale')
gettext.textdomain('flood_alerts')

# Create translation functions
_ = gettext.gettext  # Standard translation function

# Indonesian translations dictionary as a fallback
INDONESIAN_TRANSLATIONS = {
    "FLOOD ALERT!": "PERINGATAN BANJIR!",
    "Imminent flood threat detected with hazard index of": "Ancaman banjir terdeteksi dengan indeks bahaya",
    "Affected regions": "Wilayah yang terkena dampak",
    "Please take necessary precautions immediately.": "Harap segera mengambil tindakan pencegahan yang diperlukan.",
    "PLEASE DO NOT TOUCH YOUR COMPUTER WHILE THIS MESSAGE IS BEING SENT": "MOHON JANGAN SENTUH KOMPUTER ANDA SELAMA PESAN INI SEDANG DIKIRIM", 
    "You must scan the QR code when WhatsApp Web opens.": "Anda harus memindai kode QR ketika WhatsApp Web terbuka.",
    "No specific regions affected": "Tidak ada wilayah tertentu yang terkena dampak",
    "Unknown regions": "Wilayah tidak diketahui",
    "Unable to determine affected regions": "Tidak dapat menentukan wilayah yang terkena dampak"
}

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

def get_affected_regions(raster_data=None):
    """Get the affected regions from raster data
    
    If no raster data is provided, returns a default message.
    """
    if raster_data is None:
        return "Unknown regions"
    
    try:
        # Import spatial libraries only when needed
        gpd, np, map_grid_cells_to_areas = import_spatial_libraries()
        
        # Convert raster data to GeoDataFrame
        raster_gdf = raster_data.to_gdf()
        # Filter for values above threshold
        THRESHOLD_VALUE = 32
        raster_gdf_filtered = raster_gdf[raster_gdf["value"] >= THRESHOLD_VALUE]
        
        if raster_gdf_filtered.empty:
            return "No specific regions affected"
        
        # Map grid cells to administrative areas
        affected_areas = map_grid_cells_to_areas(raster_gdf_filtered)
        
        if affected_areas.empty:
            return "No specific regions affected"
        
        # Get the names of affected regions (level 3 administrative divisions)
        region_names = affected_areas["NAME_3"].unique().tolist()
        regions_text = ", ".join(sorted(region_names))
        
        return regions_text
    except Exception as e:
        logger.error(f"Error getting affected regions: {e}")
        return "Unable to determine affected regions"

def translate_message(message, lang='en'):
    """
    Translate a message to the specified language.
    
    Args:
        message (str): The message to translate
        lang (str): The language code ('en' for English, 'id' for Indonesian)
        
    Returns:
        str: The translated message
    """
    if lang == 'en' or not message:
        return message
        
    if lang == 'id':
        # Try using gettext first
        try:
            # Set the locale for Indonesian
            lang_env = gettext.translation('flood_alerts', localedir='./locale', languages=['id'])
            lang_env.install()
            _ = lang_env.gettext
            translated = _(message)
            # If no translation found (returned unchanged), use our fallback dictionary
            if translated == message and message in INDONESIAN_TRANSLATIONS:
                return INDONESIAN_TRANSLATIONS[message]
            return translated
        except FileNotFoundError:
            # If no translation files found, use our fallback dictionary
            if message in INDONESIAN_TRANSLATIONS:
                return INDONESIAN_TRANSLATIONS[message]
            
            # For sentences not directly in our dictionary, try to translate phrases
            for english, indonesian in INDONESIAN_TRANSLATIONS.items():
                if english in message:
                    message = message.replace(english, indonesian)
            return message
    
    # Return original message if language not supported
    return message


def get_message_template(lang='en'):
    """
    Get message templates in the specified language.
    
    Args:
        lang (str): The language code ('en' for English, 'id' for Indonesian)
        
    Returns:
        dict: Message templates in the specified language
    """
    templates = {
        'alert_title': translate_message("FLOOD ALERT!", lang),
        'threat_detected': translate_message("Imminent flood threat detected with hazard index of", lang),
        'affected_regions': translate_message("Affected regions", lang),
        'take_precautions': translate_message("Please take necessary precautions immediately.", lang),
        'warning_message': translate_message("PLEASE DO NOT TOUCH YOUR COMPUTER WHILE THIS MESSAGE IS BEING SENT", lang),
        'instruction_message': translate_message("You must scan the QR code when WhatsApp Web opens.", lang),
    }
    return templates


def format_alert_message(flood_hazard_index, affected_regions=None, lang='en'):
    """
    Format an alert message in the specified language.
    
    Args:
        flood_hazard_index (float): The hazard index value
        affected_regions (str, optional): String of affected region names
        lang (str): The language code ('en' for English, 'id' for Indonesian)
        
    Returns:
        str: Formatted alert message in the specified language
    """
    templates = get_message_template(lang)
    
    # Create the message
    regions_text = "\n{}: {}".format(
        templates['affected_regions'], 
        affected_regions if affected_regions else translate_message("No specific regions affected", lang)
    )
    
    message = "{0}\n{1} {2:.2f}.{3}\n{4}".format(
        templates['alert_title'],
        templates['threat_detected'],
        flood_hazard_index,
        regions_text,
        templates['take_precautions']
    )
    
    return message


def alert_on_flood_threat(flood_hazard_index, whatsapp_group_id=None, whatsapp_phone_number=None, telegram_chat_id=None, 
                      should_notify=True, raster_data=None, use_whatsapp=True, use_telegram=True, 
                      use_whatsapp_fallback_only=False, language='en'):
    """
    Send flood threat alerts based on the hazard index.
    
    Args:
        flood_hazard_index (float): The hazard index value (0-1)
        whatsapp_group_id (str, optional): WhatsApp group ID to send the alert to
        whatsapp_phone_number (str, optional): WhatsApp phone number to send the alert to
        telegram_chat_id (str, optional): Telegram chat ID to send the alert to
        should_notify (bool): Whether notifications should be sent at all
        raster_data: Raster data containing flood information for region detection
        use_whatsapp (bool): Whether to use WhatsApp notifications
        use_telegram (bool): Whether to use Telegram notifications
        use_whatsapp_fallback_only (bool): If True, only use the fallback (pywhatkit) method for WhatsApp
        
    Returns:
        tuple: (is_threat, alert_statuses)
            is_threat (bool): Whether a flood threat was detected
            alert_statuses (dict): Status information for each messaging platform
    """
    is_threat = is_flood_threat(flood_hazard_index)
    whatsapp_alert_status = None
    telegram_alert_status = None
    
    # Get affected regions
    affected_regions = get_affected_regions(raster_data)
    
    if is_threat:
        title = translate_message("Imminent flood threat detected!", language)
        regions_label = translate_message("Affected regions", language)
        print(f"{title} Index: {flood_hazard_index}")
        print(f"{regions_label}: {affected_regions}")
        
        # Format the alert message based on the specified language
        alert_message = format_alert_message(flood_hazard_index, affected_regions, language)
        
        if should_notify:
            # Send WhatsApp alert if enabled and recipients specified
            if use_whatsapp and (whatsapp_group_id or whatsapp_phone_number):
                logger.info(f"Sending WhatsApp alert for flood threat with index: {flood_hazard_index} in regions: {affected_regions}")
                
                if use_whatsapp_fallback_only:
                    # Import directly here to avoid circular imports
                    from whatsapp_messaging_api import send_whatsapp_message_pywhatkit
                    
                    # Add warning message in the specified language
                    templates = get_message_template(language)
                    warning_message = templates['warning_message'] + "\n"
                    instruction_message = templates['instruction_message'] + "\n\n"
                    full_message = warning_message + instruction_message + alert_message
                    
                    whatsapp_alert_status = send_whatsapp_message_pywhatkit(whatsapp_phone_number, full_message, whatsapp_group_id)
                else:
                    # Use the regular method which tries headless first, then fallback
                    whatsapp_alert_status = send_whatsapp_alert(flood_hazard_index, whatsapp_group_id, whatsapp_phone_number, affected_regions, language)
                
                if whatsapp_alert_status["status"] == "success":
                    logger.info("WhatsApp alert sent successfully")
                else:
                    logger.error(f"Failed to send WhatsApp alert: {whatsapp_alert_status['message']}")
            
            # Send Telegram alert if enabled and recipient specified
            if use_telegram and telegram_chat_id:
                logger.info(f"Sending Telegram alert for flood threat with index: {flood_hazard_index} in regions: {affected_regions}")
                telegram_alert_status = send_telegram_alert(flood_hazard_index, telegram_chat_id, affected_regions, language)
                
                if telegram_alert_status["status"] == "success":
                    logger.info("Telegram alert sent successfully")
                else:
                    logger.error(f"Failed to send Telegram alert: {telegram_alert_status['message']}")
    else:
        print(f"No imminent flood threat. Index: {flood_hazard_index}")
    
    return is_threat, {"whatsapp": whatsapp_alert_status, "telegram": telegram_alert_status}

if __name__ == "__main__":
    # Example usage
    import argparse
    
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='Flood threat detection and alert system')
    parser.add_argument('--whatsapp', action='store_true', help='Enable WhatsApp notifications')
    parser.add_argument('--telegram', action='store_true', help='Enable Telegram notifications')
    parser.add_argument('--fallback-only', action='store_true', help='Use only WhatsApp fallback (pywhatkit) method')
    parser.add_argument('--dry-run', action='store_true', help='Run without sending actual notifications')
    parser.add_argument('--threshold', type=float, default=0.7, help='Flood threat threshold (0-1)')
    parser.add_argument('--language', '-l', choices=['en', 'id'], default='en', 
                        help='Message language (en=English, id=Indonesian)')
    
    args = parser.parse_args()
    
    # If no platforms specified, default to both
    if not (args.whatsapp or args.telegram):
        args.whatsapp = True
        args.telegram = True
        
    # Show language selection
    language_name = "English" if args.language == "en" else "Indonesian (Bahasa Indonesia)"
    
    # Set your WhatsApp group ID or phone number here
    # Example group_id: "AbCdEfGhIjKlMnOp"
    # Example phone_number: "+1234567890" (with country code)
    whatsapp_group_id = ''  # Replace with your WhatsApp group ID
    whatsapp_phone_number = ''  # Replace with your WhatsApp phone number
    
    # Set your Telegram channel or chat ID
    telegram_chat_id = '@fewsbandungML'  # The Telegram channel provided
    
    # Mock data for testing without spatial libraries
    class MockRaster:
        def __init__(self):
            pass
            
        def to_gdf(self):
            # This will not be called during testing as we'll catch the import error
            pass
    
    mock_regions = [
        "Bandung", "Cimahi", "Garut", "Sumedang", "Cianjur"
    ]
    
    # Override get_affected_regions for testing
    original_get_affected_regions = get_affected_regions
    def mock_get_affected_regions(raster_data=None):
        # Simply return some test regions
        import random
        # Return 1-3 random regions for testing
        num_regions = random.randint(1, 3)
        selected_regions = random.sample(mock_regions, num_regions)
        return ", ".join(selected_regions)
    
    # Replace with mock function for testing
    get_affected_regions = mock_get_affected_regions
    
    # Display configuration
    print("\n" + "="*60)
    print("FLOOD THREAT DETECTION AND ALERT SYSTEM")
    print("="*60)
    print(f"WhatsApp notifications: {'Enabled (fallback only)' if args.whatsapp and args.fallback_only else 'Enabled' if args.whatsapp else 'Disabled'}")
    print(f"Telegram notifications: {'Enabled' if args.telegram else 'Disabled'}")
    print(f"Notification mode: {'DRY RUN (no actual messages)' if args.dry_run else 'LIVE (real messages will be sent)'}")
    print(f"Flood threat threshold: {args.threshold}")
    print(f"Message language: {language_name}")
    print("This is a test run with simulated region data\n")
    
    # Test indices - include the threshold to ensure at least one alert is triggered
    test_indices = [0.2, 0.5, args.threshold, args.threshold + 0.1, 0.95]
    
    for index in test_indices:
        print(f"\nTesting with hazard index: {index}")
        mock_raster = MockRaster()
        
        # Determine if we should send notifications
        should_notify = not args.dry_run
        
        is_threat, alert_status = alert_on_flood_threat(
            index, 
            whatsapp_group_id=whatsapp_group_id if args.whatsapp else None, 
            whatsapp_phone_number=whatsapp_phone_number if args.whatsapp else None,
            telegram_chat_id=telegram_chat_id if args.telegram else None,
            should_notify=should_notify,
            raster_data=mock_raster,
            use_whatsapp=args.whatsapp,
            use_telegram=args.telegram,
            use_whatsapp_fallback_only=args.fallback_only,
            language=args.language
        )
        
        if is_threat:
            print("WhatsApp alert status:", "Not sent (notifications disabled)" if alert_status["whatsapp"] is None else alert_status["whatsapp"])
            print("Telegram alert status:", "Not sent (notifications disabled)" if alert_status["telegram"] is None else alert_status["telegram"])
        
    print("\nTest run completed.\n")