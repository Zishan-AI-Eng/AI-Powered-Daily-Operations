import requests
from dotenv import load_dotenv
import os
from models.schemas import Candidates, Companies, JobDeal, NormalizedCRMData
from utils.logger import get_logger

load_dotenv()  # Load environment variables from .env file

logger = get_logger(__name__)

HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY")
headers = {
    "Authorization": f"Bearer {HUBSPOT_API_KEY}",
    'Content-Type': 'application/json'
}



def fetch_and_normalize_crm_data() -> NormalizedCRMData:
    """Takes the data from HubSpot API and normalizes it into a structured format."""
    
    raw_contacts = fetch_raw_contacts()
    raw_deals = fetch_raw_deals()
    
    normalized_candidates = []
    normalized_jobs = []
    
    for contact in raw_contacts.get('results', []):
        props = contact.get('properties', {})
        
        full_name = f"{props.get('firstname', '')} {props.get('lastname', '')}".strip()
        if not full_name:
            full_name = "Unknown Name"
            
        candidate_obj = Candidates(
            id=contact.get('id', ''),
            name=full_name,
            email=props.get('email'),
            phone_number=props.get('phone'),
            contact_owner=props.get('hubspot_owner_id'),
            primary_company=props.get('company'),
            lead_status=props.get('hs_lead_status'),
            created_date=props.get('createdate'),
            last_activity_date=props.get('lastmodifieddate')
        )
        normalized_candidates.append(candidate_obj)
        
    for deal in raw_deals.get('results', []):
            props = deal.get('properties', {})
             
            job_obj = JobDeal(
                id=deal.get('id'),
                job_title=props.get('dealname', 'No Name'),
                stage=props.get('dealstage', 'Unknown')
                
            )
            normalized_jobs.append(job_obj)
            

    return NormalizedCRMData(
        candidates=normalized_candidates,
        companies=[],  # Placeholder for companies, can be populated similarly if needed
        jobs=normalized_jobs
    )
            
        
def fetch_raw_contacts():
    """Fetches raw contact data from HubSpot API."""
    contacts_url = 'https://api.hubapi.com/crm/v3/objects/contacts?limit=10'
    try:
        response = requests.get(contacts_url, headers=headers, timeout=30)
        response.raise_for_status()  # Raise an error for bad responses
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error("Contacts fetch failed: %s", e)
        return {"results": []}
    
    
    
def fetch_raw_deals():
    """Fetches raw deal data from HubSpot API."""
    deals_url = "https://api.hubapi.com/crm/v3/objects/deals?limit=10"
    try:
        response = requests.get(deals_url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error("Deals fetch failed: %s", e)
        return {"results": []}
    


def update_hubspot_contact(contact_id: str, properties: dict) -> bool:
    """HubSpot API ko PATCH request bhej kar contact update karta hai."""
    
    url = f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}"
    headers = {
        "Authorization": f"Bearer {HUBSPOT_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # HubSpot API properties ko ek specific JSON format mein mangta hai
    payload = {
        "properties": properties
    }
    
    try:
        logger.debug(f"Sending PATCH request to HubSpot for Contact ID: {contact_id}")
        response = requests.patch(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            logger.info(f"Successfully updated Contact ID {contact_id} in HubSpot.")
            return True
        else:
            logger.error(f"HubSpot API Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Exception during HubSpot API call: {e}")
        return False


def update_hubspot_deal(deal_id: str, properties: dict) -> bool:
    """Update a HubSpot deal and return whether the provider accepted it."""
    url = f"https://api.hubapi.com/crm/v3/objects/deals/{deal_id}"
    payload = {"properties": properties}

    try:
        logger.debug("Sending PATCH request to HubSpot for Deal ID: %s", deal_id)
        response = requests.patch(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            logger.info("Successfully updated Deal ID %s in HubSpot.", deal_id)
            return True
        logger.error("HubSpot deal update failed: %s - %s", response.status_code, response.text)
        return False
    except requests.exceptions.RequestException as exc:
        logger.error("Exception during HubSpot deal update: %s", exc)
        return False