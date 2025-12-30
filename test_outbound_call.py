#!/usr/bin/env python3
"""
Test script for making outbound calls to gyms.
Usage: python test_outbound_call.py +14155551234 "Example BJJ Gym"
"""
import requests
import sys
import time
import urllib3

# Disable SSL warnings for self-signed certs in dev
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://bidetking.ddns.net"  # Production k8s deployment
VERIFY_SSL = False  # Set to True in production with valid cert

def make_call(phone_number: str, gym_name: str = None):
    """Initiate an outbound call."""
    print(f"📞 Initiating call to {phone_number}" + (f" ({gym_name})" if gym_name else ""))
    
    payload = {
        "phone_number": phone_number,
        "gym_name": gym_name,
        "country": "US",
        "timezone": "America/Los_Angeles",
        "preferred_language": "en"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/v1/calls", json=payload, verify=VERIFY_SSL)
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Call initiated successfully!")
        print(f"   Call ID: {data['call_id']}")
        print(f"   Twilio SID: {data['twilio_call_sid']}")
        print(f"   Status: {data['status']}")
        print(f"   Created: {data['created_at']}")
        
        return data['call_id']
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        print(f"   Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def check_call_status(call_id: str):
    """Check the status of a call."""
    try:
        response = requests.get(f"{BASE_URL}/v1/calls/{call_id}", verify=VERIFY_SSL)
        response.raise_for_status()
        
        data = response.json()
        print(f"\n📊 Call Status for {call_id}:")
        print(f"   Status: {data['status']}")
        print(f"   Twilio SID: {data['twilio_call_sid']}")
        print(f"   Phone: {data['request']['phone_number']}")
        if 'last_updated' in data:
            print(f"   Last Updated: {data['last_updated']}")
        
        return data
        
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_outbound_call.py <phone_number> [gym_name]")
        print("Example: python test_outbound_call.py +14155551234 'Example Gym'")
        sys.exit(1)
    
    phone_number = sys.argv[1]
    gym_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Make the call
    call_id = make_call(phone_number, gym_name)
    
    if call_id:
        print("\n⏳ Waiting 3 seconds to check status...")
        time.sleep(3)
        check_call_status(call_id)
        
        print("\n💡 Tip: Watch your uvicorn logs to see the call progress!")
        print("   When answered, you'll see: 'Twilio voice webhook called'")
        print("   Then: 'Twilio Media Stream WebSocket connected'")

