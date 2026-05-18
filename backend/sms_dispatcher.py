"""
Layer 4: SMS Dispatcher
Bilingual SMS alert generation & delivery logic
"""

from datetime import datetime

def generate_sms_alert(cell_id, sm_value, alert_type, crop="maize", language="english"):
    """
    Generate SMS alert message (≤160 characters for standard SMS).

    Inputs:
    - cell_id: Grid cell identifier (e.g., "L01")
    - sm_value: Soil moisture value (m³/m³)
    - alert_type: "drought_critical", "irrigation_needed", etc.
    - crop: Crop type (maize, wheat, sorghum)
    - language: "english" or "tshivenda" or "sepedi"

    Returns:
    - SMS message string (≤160 chars)
    """

    # Bilingual SMS templates (from Maryline's thesis, Table 19)
    templates = {
        "english": {
            "drought_critical": f"⚠️ {cell_id}: URGENT - Severe drought. SM={sm_value:.2f}. Irrigate immediately. Forecast: Low rain.",
            "irrigation_needed": f"⚠️ {cell_id}: {crop.title()} needs water. SM={sm_value:.2f}. Plan irrigation in 2 days.",
            "rainfall_deficit": f"⚠️ {cell_id}: Low rainfall (7d < 20mm). Monitor {crop.title()}.",
        },
        "tshivenda": {
            "drought_critical": f"vha songo shelesa {cell_id}: VWC={sm_value:.2f}. Tshifhinga tsha u sheledza zwino.",
            "irrigation_needed": f"vha songo shelesa {cell_id}: {crop.title()} a a dzhamela mwenya. Tshinela nga 25 mm.",
            "rainfall_deficit": f"vha songo shelesa {cell_id}: Mualo wa 7 duvha < 20mm. Gumula.",
        },
        "sepedi": {
            "drought_critical": f"Tshwereng: {cell_id}: VWC={sm_value:.2f}. Thela gape jwale.",
            "irrigation_needed": f"Tshwereng: {cell_id}: {crop.title()} a nyarega metsi. Thela ka 2 letsatsi.",
            "rainfall_deficit": f"Tshwereng: {cell_id}: Pula (7d < 20mm). Lekantswe {crop.title()}.",
        },
    }

    # Get template
    if language in templates and alert_type in templates[language]:
        msg = templates[language][alert_type]
    else:
        msg = f"Alert: {cell_id} {alert_type} (SM={sm_value:.2f})"

    # Ensure ≤160 chars
    msg = msg[:160]

    return msg

def dispatch_sms(phone_number, message, gateway="twilio"):
    """
    Dispatch SMS via gateway.

    Inputs:
    - phone_number: Target farmer's phone (e.g., "+27123456789")
    - message: SMS content (≤160 chars)
    - gateway: "twilio" (international), "afrimotech" (local SA), or "mock"

    Returns:
    - status: "sent", "pending", or "failed"
    """

    # In production, use Twilio SDK:
    # from twilio.rest import Client
    # client = Client(ACCOUNT_SID, AUTH_TOKEN)
    # message = client.messages.create(
    #     body=message,
    #     from_="+1234567890",
    #     to=phone_number
    # )

    # For demo: mock dispatch
    dispatch_record = {
        "phone": phone_number,
        "message": message,
        "gateway": gateway,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "pending",  # Would be "sent" after real API call
        "message_id": f"msg_{int(datetime.utcnow().timestamp())}",
    }

    return dispatch_record

def get_alert_log(alerts):
    """
    Generate SMS alert log from triggered alerts.
    Outputs: List of SMS messages ready for dispatch.
    """

    sms_log = []

    for alert in alerts:
        # Map to farmer details (mock - in production: lookup from DB)
        farmer_phone = "+27123456789"  # Mock phone
        crop = "maize"  # Mock crop

        # Generate SMS
        sms_msg = generate_sms_alert(
            cell_id=alert["cell_id"],
            sm_value=alert["sm_value"],
            alert_type=alert["alert_type"],
            crop=crop,
            language="english"  # Could be "tshivenda" or "sepedi"
        )

        # Dispatch (mock)
        dispatch = dispatch_sms(farmer_phone, sms_msg, gateway="twilio")

        sms_log.append({
            "cell_id": alert["cell_id"],
            "farmer_phone": farmer_phone,
            "crop": crop,
            "sms_message": sms_msg,
            "timestamp": alert["timestamp"],
            "status": dispatch["status"],
        })

    return sms_log

def generate_csv_export(alerts, start_date=None, end_date=None):
    """
    Export alerts to CSV for DALRRD reports.
    """

    import csv
    from io import StringIO

    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["date", "cell_id", "crop", "sm_value", "alert_type", "severity", "action"]
    )
    writer.writeheader()

    for alert in alerts:
        writer.writerow({
            "date": alert.get("timestamp", ""),
            "cell_id": alert.get("cell_id", ""),
            "crop": "maize",  # Mock
            "sm_value": f"{alert.get('sm_value', 0):.3f}",
            "alert_type": alert.get("alert_type", ""),
            "severity": alert.get("severity", ""),
            "action": f"Irrigate {alert.get('cell_id', '')} in 2 days",
        })

    return output.getvalue()
