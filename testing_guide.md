# Flood Threat Detection & WhatsApp Alert System - Testing Guide

This guide provides step-by-step instructions for testing the flood threat detection system with WhatsApp notifications.

## Prerequisites

1. **Python Environment Setup**
   - Ensure Python 3.8+ is installed
   - Install required packages:
     ```
     pip install flask pywhatkit
     ```
   - If you encounter version compatibility issues, try specifying a specific pywhatkit version:
     ```
     pip install pywhatkit==5.4 flask
     ```

2. **WhatsApp Web Access**
   - A WhatsApp account with an active phone number
   - WhatsApp Web access (you will need to scan QR code during testing)
   - A browser installed on your system

## Testing the Components

### 1. Testing Flood Threat Detection (Without Notifications)

This test verifies the core threat detection logic without sending actual WhatsApp messages.

1. Open a terminal and navigate to the project directory:
   ```
   cd /path/to/igs
   ```

2. Run the flood threat detection script with notifications disabled:
   ```
   python flood_threat.py
   ```

3. Expected output:
   - You should see results for each test index (0.2, 0.6, 0.7, 0.8, 0.95)
   - Indices below 0.7 should show "No imminent flood threat"
   - Indices 0.7 and above should show "Imminent flood threat detected!"
   - All notifications should be disabled by default

### 2. Testing WhatsApp API Standalone

This test verifies the WhatsApp messaging API works independently.

1. Edit the `whatsapp_messaging_api.py` file:
   - Uncomment the test line at the bottom of the file
   - Replace "Your_Group_ID_Here" with your actual WhatsApp group ID, or
   - Add a phone number test by uncommenting and modifying:
     ```python
     # send_flood_alert(0.85, phone_number="+1234567890")  # Replace with your number
     ```

2. Run the WhatsApp API script:
   ```
   python whatsapp_messaging_api.py
   ```

3. Expected behavior:
   - A browser window will open with WhatsApp Web
   - If not already logged in, you'll need to scan the QR code
   - After approximately 2 minutes, the message will be sent
   - Check your WhatsApp to confirm message delivery

### 3. Testing Flask API Endpoints

This test verifies the REST API for sending alerts.

1. Start the Flask server:
   ```
   python whatsapp_messaging_api.py
   ```
   - Uncomment the `app.run(debug=True, port=5000)` line first

2. In a separate terminal, send a test request to the API:
   ```
   curl -X POST http://localhost:5000/send_alert \
     -H "Content-Type: application/json" \
     -d '{"phone_number":"+1234567890", "message":"Test flood alert", "hazard_index":0.85}'
   ```
   - Replace "+1234567890" with your phone number
   - Alternatively, use a tool like Postman to send the request

3. Expected behavior:
   - API should return a success response
   - Message should be sent to WhatsApp after ~2 minutes

### 4. Testing Integrated System

This test verifies the complete end-to-end functionality.

1. Edit `flood_threat.py`:
   - Add your WhatsApp group ID or phone number:
     ```python
     group_id = "YourGroupIDHere"  # or leave as None if using phone_number
     phone_number = "+1234567890"  # or leave as None if using group_id
     ```
   - Change `should_notify=False` to `should_notify=True`

2. Run the flood threat detection script:
   ```
   python flood_threat.py
   ```

3. Expected behavior:
   - Detections should work as in Test 1
   - WhatsApp messages should be sent for indices ≥ 0.7
   - Logs should show successful message sending

## Troubleshooting

### Common Issues

1. **WhatsApp Web Login Problems**
   - Ensure your phone has an active internet connection
   - Try logging into WhatsApp Web manually first
   - Check that your WhatsApp account is active

2. **Message Not Sending**
   - PyWhatKit requires a 2-minute buffer for scheduling messages
   - Ensure your browser window isn't minimized during sending
   - Check the console for any error messages

3. **Browser Issues**
   - PyWhatKit works best with Chrome or Firefox
   - Ensure you have a default browser set
   - Try manually specifying the browser path in PyWhatKit settings

4. **Phone Number Format**
   - Always include the country code (e.g., "+1" for US)
   - Don't include spaces or special characters

### Advanced Configuration

For fine-tuning the system, you can modify:

1. **Flood Threat Threshold**
   - Edit `FLOOD_THREAT_THRESHOLD` in `flood_threat.py` (default: 0.7)

2. **PyWhatKit Settings**
   - Adjust `wait_time` in `setup_whatsapp_config()` to change wait duration
   - Set `close_tab=False` to keep browser open after sending

## Security Considerations

- Never commit WhatsApp group IDs or phone numbers to version control
- Consider environment variables for sensitive information in production
- When running as a service, use headless browser mode or Twilio API instead

## Alternative APIs

For production use, consider these alternatives to PyWhatKit:

1. **Twilio API for WhatsApp**: More reliable and officially supported
2. **Selenium-based solutions**: More customizable but require more setup