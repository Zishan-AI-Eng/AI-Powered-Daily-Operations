from dotenv import load_dotenv
import requests
import os



env = load_dotenv()
HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY")

if not HUBSPOT_API_KEY:
    raise ValueError("HUBSPOT_API_KEY is not set in the environment variables.")


headers ={
    "Authorization": f"Bearer {HUBSPOT_API_KEY}",
    'Content-Type': 'application/json'
}

def fetch_crm_data():
    
    print("\n")
    print("Fetching data from HubSpot API...")
    
    contacts_url = 'https://api.hubapi.com/crm/v3/objects/contacts?limit=10'
    try:
        response = requests.get(contacts_url, headers=headers, timeout=30)
        response.raise_for_status()  # Raise an error for bad responses
        contacts_data = response.json()
        
        print("="*40 + "\n")
            
        
        print("--- CANDIDATES (CONTACTS) ---")
        for contact in contacts_data.get('results', []):
            props = contact.get('properties', {})
            print(f"ID: {contact.get('id')} | Name: {props.get('firstname', '')} {props.get('lastname', '')}")
    except requests.exceptions.RequestException as e:
        print(f"Contacts Fetch Error: {e}")
        
    print("\n" + "="*40 + "\n")

    deals_url = "https://api.hubapi.com/crm/v3/objects/deals?limit=10"
    try:
        response = requests.get(deals_url, headers=headers, timeout=30)
        response.raise_for_status()
        deals_data = response.json()
        
        print("--- JOBS (DEALS) ---")
        for deal in deals_data.get('results', []):
            props = deal.get('properties', {})
            print(f"ID: {deal.get('id')} | Deal Name: {props.get('dealname', 'No Name')} | Stage: {props.get('dealstage', 'Unknown')}")
    except requests.exceptions.RequestException as e:
        print(f"Deals Fetch Error: {e}")




if __name__ == "__main__":
    fetch_crm_data()