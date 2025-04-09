import requests
import json
from typing import Union, List, Optional

def send_expo_notification(
    to: Union[str, List[str]],
    title: Optional[str] = None,
    body: Optional[str] = None,
    data: Optional[dict] = None,
    ttl: Optional[int] = None,
    expiration: Optional[int] = None,
    priority: Optional[str] = None, 
    subtitle: Optional[str] = None,
    sound: Optional[Union[str, None]] = None,
    badge: Optional[int] = None,
    interruptionLevel: Optional[str] = None,
    channelId: Optional[str] = None,
    icon: Optional[str] = None,
    richContent: Optional[dict] = None,
    categoryId: Optional[str] = None,
    mutableContent: Optional[bool] = None,
    _contentAvailable: Optional[bool] = None
):
    url = "https://exp.host/--/api/v2/push/send"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "to": to,
        "title": title,
        "body": body,
        "data": data or {},
        "ttl": ttl,
        "expiration": expiration,
        "priority": priority,
        "subtitle": subtitle,
        "sound": sound,
        "badge": badge,
        "interruptionLevel": interruptionLevel,
        "channelId": channelId,
        "icon": icon,
        "richContent": richContent,
        "categoryId": categoryId,
        "mutableContent": mutableContent,
        "_contentAvailable": _contentAvailable
    }

    payload = {k: v for k, v in payload.items() if v is not None}

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print("✅ Notification sent:", response.json())
        return response.json()
    except requests.exceptions.RequestException as e:
        print("❌ Error sending notification:", e)
        print("🔁 Response content:", response.text if response else "No response")
        return None
