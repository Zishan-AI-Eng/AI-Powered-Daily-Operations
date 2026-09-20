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
    "Content-Type": "application/json",
}

HUBSPOT_BASE_URL = "https://api.hubapi.com"
READ_TIMEOUT_SECONDS = 30

EXPLORER_PROPERTIES = {
    "contacts": [
        "firstname",
        "lastname",
        "email",
        "phone",
        "hs_lead_status",
        "hubspot_owner_id",
    ],
    "companies": [
        "name",
        "domain",
        "industry",
        "city",
        "phone",
        "hubspot_owner_id",
    ],
    "deals": [
        "dealname",
        "amount",
        "dealstage",
        "closedate",
        "hubspot_owner_id",
    ],
}


def _hubspot_error(resource: str, response: requests.Response) -> str:
    """Convert an HTTP failure into a concise, agent-safe error message."""
    if response.status_code == 401:
        reason = "authentication failed"
    elif response.status_code == 403:
        reason = "permission denied"
    elif response.status_code == 404:
        reason = "resource not found"
    elif response.status_code == 429:
        reason = "rate limit reached"
    elif response.status_code >= 500:
        reason = "HubSpot service unavailable"
    else:
        reason = f"HTTP {response.status_code}"

    logger.error("HubSpot %s request failed: %s (%s)", resource, response.status_code, reason)
    return f"ERROR: Unable to fetch HubSpot {resource}; {reason}."


def _request_records(
    object_type: str,
    properties: list[str],
    limit: int,
    query: str | None = None,
) -> list[dict] | str:
    """Fetch and minimize HubSpot object records before they reach the agent."""
    if not HUBSPOT_API_KEY:
        logger.error("HubSpot API key is not configured")
        return "ERROR: HubSpot integration is not configured."

    try:
        if query:
            url = f"{HUBSPOT_BASE_URL}/crm/v3/objects/{object_type}/search"
            payload = {
                "query": query,
                "limit": limit,
                "properties": properties,
            }
            response = requests.post(url, headers=headers, json=payload, timeout=READ_TIMEOUT_SECONDS)
        else:
            url = f"{HUBSPOT_BASE_URL}/crm/v3/objects/{object_type}"
            response = requests.get(
                url,
                headers=headers,
                params={"limit": limit, "properties": properties},
                timeout=READ_TIMEOUT_SECONDS,
            )

        if not response.ok:
            return _hubspot_error(object_type, response)

        results = response.json().get("results", [])
        return [
            {
                "id": record.get("id"),
                **{
                    property_name: record.get("properties", {}).get(property_name)
                    for property_name in properties
                    if record.get("properties", {}).get(property_name) is not None
                },
            }
            for record in results[:limit]
        ]
    except requests.exceptions.Timeout:
        logger.error("HubSpot %s request timed out", object_type)
        return f"ERROR: HubSpot {object_type} request timed out."
    except requests.exceptions.RequestException as exc:
        logger.error("HubSpot %s request failed: %s", object_type, exc)
        return f"ERROR: Unable to reach HubSpot for {object_type}."
    except (TypeError, ValueError) as exc:
        logger.error("HubSpot %s response could not be parsed: %s", object_type, exc)
        return f"ERROR: HubSpot returned an invalid {object_type} response."


def list_hubspot_contacts(limit: int = 10, query: str | None = None) -> list[dict] | str:
    """Fetch compact contact records from HubSpot."""
    return _request_records(
        "contacts",
        ["firstname", "lastname", "email", "phone", "hubspot_owner_id", "hs_lead_status"],
        limit,
        query,
    )


def list_hubspot_companies(limit: int = 10, query: str | None = None) -> list[dict] | str:
    """Fetch compact company records from HubSpot."""
    return _request_records(
        "companies",
        ["name", "phone", "city", "country", "industry", "hubspot_owner_id"],
        limit,
        query,
    )


def list_hubspot_deals(limit: int = 10, query: str | None = None) -> list[dict] | str:
    """Fetch compact deal records from HubSpot."""
    return _request_records(
        "deals",
        ["dealname", "dealstage", "amount", "hubspot_owner_id", "closedate"],
        limit,
        query,
    )


def list_hubspot_tasks(limit: int = 10, query: str | None = None) -> list[dict] | str:
    """Fetch compact task records from HubSpot."""
    return _request_records(
        "tasks",
        ["hs_task_subject", "hs_task_status", "hs_task_priority", "hs_timestamp", "hubspot_owner_id"],
        limit,
        query,
    )


def _map_explorer_record(record: dict, properties: list[str]) -> dict:
    """Map a HubSpot record to the exact bounded explorer contract."""
    record_properties = record.get("properties", {})
    return {
        "id": record.get("id"),
        **{property_name: record_properties.get(property_name) for property_name in properties},
    }


def _fetch_explorer_records(
    object_type: str,
    properties: list[str],
    page: int,
    limit: int,
    search: str | None = None,
    stage: str | None = None,
) -> dict | str:
    """Fetch one frontend page while following HubSpot cursor pagination."""
    if not HUBSPOT_API_KEY:
        logger.error("HubSpot API key is not configured")
        return "ERROR: HubSpot integration is not configured."

    start_index = (page - 1) * limit
    requested_end = start_index + limit
    records: list[dict] = []
    after: str | None = None
    total: int | None = None

    try:
        while len(records) < requested_end:
            if search or stage:
                url = f"{HUBSPOT_BASE_URL}/crm/v3/objects/{object_type}/search"
                filters = []
                if stage:
                    filters.append({
                        "filters": [{"propertyName": "dealstage", "operator": "EQ", "value": stage}]
                    })
                payload = {
                    "limit": min(limit, 100),
                    "properties": properties,
                    "query": search or "",
                    "filterGroups": filters,
                }
                if after is not None:
                    payload["after"] = after
                response = requests.post(
                    url, headers=headers, json=payload, timeout=READ_TIMEOUT_SECONDS
                )
            else:
                url = f"{HUBSPOT_BASE_URL}/crm/v3/objects/{object_type}"
                params = {"limit": min(limit, 100), "properties": properties}
                if after is not None:
                    params["after"] = after
                response = requests.get(
                    url, headers=headers, params=params, timeout=READ_TIMEOUT_SECONDS
                )

            if not response.ok:
                return _hubspot_error(object_type, response)

            payload = response.json()
            batch = payload.get("results", [])
            records.extend(batch)
            if isinstance(payload.get("total"), int):
                total = payload["total"]

            next_after = payload.get("paging", {}).get("next", {}).get("after")
            if not next_after or not batch:
                break
            after = str(next_after)

        items = [_map_explorer_record(record, properties) for record in records[start_index:requested_end]]
        return {"items": items, "total": total if total is not None else len(records)}
    except requests.exceptions.Timeout:
        logger.error("HubSpot %s explorer request timed out", object_type)
        return f"ERROR: HubSpot {object_type} request timed out."
    except requests.exceptions.RequestException as exc:
        logger.error("HubSpot %s explorer request failed: %s", object_type, exc)
        return f"ERROR: Unable to reach HubSpot for {object_type}."
    except (TypeError, ValueError) as exc:
        logger.error("HubSpot %s explorer response could not be parsed: %s", object_type, exc)
        return f"ERROR: HubSpot returned an invalid {object_type} response."


def fetch_explorer_candidates(page: int, limit: int, search: str | None = None) -> dict | str:
    """Fetch the paginated candidate contract for the dashboard."""
    return _fetch_explorer_records("contacts", EXPLORER_PROPERTIES["contacts"], page, limit, search=search)


def fetch_explorer_candidate(candidate_id: str) -> dict | str:
    """Fetch one candidate by HubSpot contact ID for the dashboard."""
    if not HUBSPOT_API_KEY:
        return "ERROR: HubSpot integration is not configured."
    try:
        response = requests.get(
            f"{HUBSPOT_BASE_URL}/crm/v3/objects/contacts/{candidate_id}",
            headers=headers,
            params={"properties": EXPLORER_PROPERTIES["contacts"]},
            timeout=READ_TIMEOUT_SECONDS,
        )
        if not response.ok:
            return _hubspot_error("contact", response)
        return _map_explorer_record(response.json(), EXPLORER_PROPERTIES["contacts"])
    except requests.exceptions.Timeout:
        return "ERROR: HubSpot contact request timed out."
    except requests.exceptions.RequestException as exc:
        logger.error("HubSpot contact lookup failed: %s", exc)
        return "ERROR: Unable to reach HubSpot for contact."
    except (TypeError, ValueError):
        return "ERROR: HubSpot returned an invalid contact response."


def fetch_explorer_companies(page: int, limit: int, search: str | None = None) -> dict | str:
    """Fetch the paginated company contract for the dashboard."""
    return _fetch_explorer_records("companies", EXPLORER_PROPERTIES["companies"], page, limit, search=search)


def fetch_explorer_deals(page: int, limit: int, stage: str | None = None) -> dict | str:
    """Fetch the paginated deal contract for the dashboard."""
    return _fetch_explorer_records("deals", EXPLORER_PROPERTIES["deals"], page, limit, stage=stage)



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