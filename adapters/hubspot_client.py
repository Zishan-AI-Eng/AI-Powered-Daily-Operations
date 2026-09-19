import requests 
from dotenv import load_dotenv
import os 


from models.schemas import Candidates, Companies, JobDeal, NormalizedCRMData

load_dotenv()  # Load environment variables from .env file


HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY")
headers ={
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
        print(f"Contacts Fetch Error: {e}")
        return {}
    
    
    
def fetch_raw_deals():
    """Fetches raw deal data from HubSpot API."""
    deals_url = "https://api.hubapi.com/crm/v3/objects/deals?limit=10"
    try:
        response = requests.get(deals_url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Deals Fetch Error: {e}")
        return {}
    
    
    
    # Testing ke liye script run karein
if __name__ == "__main__":
    clean_data = fetch_and_normalize_crm_data()
    print(clean_data.model_dump_json(indent=2)) # Pydantic model ko JSON format me print karein