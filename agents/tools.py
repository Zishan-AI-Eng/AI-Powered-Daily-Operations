from langchain_core.tools import tool
from utils.logger import get_logger
from adapters.hubspot_client import update_hubspot_contact

# Centralized logger initialize karein
logger = get_logger(__name__)

@tool
def update_crm_contact(contact_id: str, update_fields: dict) -> str:
    """
    Use this tool to update ANY information for a contact/candidate in the HubSpot CRM.
    
    Args:
        contact_id: The unique HubSpot ID of the candidate (MANDATORY). You must get this ID from the CRM data.
        update_fields: A dictionary of the fields to update and their new values based on HubSpot property names. 
                       Example: {"phone": "0300-1234567", "lifecyclestage": "customer"}
    """
    logger.info(f"AI Tool Executed: Attempting to update Contact ID '{contact_id}' with fields: {update_fields}")
    
    if not contact_id:
        logger.error("Tool Error: Contact ID was missing or empty.")
        return "ERROR: Contact ID is required to perform an update."

    try:
        # HubSpot API ko PATCH request bhejne wala function call hoga
        success = update_hubspot_contact(contact_id=contact_id, properties=update_fields)
        
        if success:
            logger.info(f"Successfully updated Contact ID '{contact_id}' in HubSpot.")
            return f"SUCCESS: Contact ID '{contact_id}' updated successfully with {update_fields}."
        else:
            logger.error(f"HubSpot API returned failure for Contact ID '{contact_id}'.")
            return f"ERROR: Failed to update Contact ID '{contact_id}' in CRM."
            
    except Exception as e:
        logger.error(f"Exception occurred while executing update_crm_contact tool: {e}")
        return f"ERROR: An exception occurred during CRM update."

@tool
def update_job_deal(job_id: str, update_fields: dict) -> str:
    """
    Use this tool to update ANY information for a job/deal (dealstage, amount, etc.) in the HubSpot CRM.
    
    Args:
        job_id: The unique HubSpot ID of the job/deal (MANDATORY).
        update_fields: A dictionary of the fields to update and their new values.
                       Example: {"dealstage": "appointmentscheduled"}
    """
    logger.info(f"AI Tool Executed: Attempting to update Job/Deal ID '{job_id}' with fields: {update_fields}")
    
    if not job_id:
        logger.error("Tool Error: Job ID was missing or empty.")
        return "ERROR: Job ID is required to perform an update."

    try:
        # Yahan job/deal update karne ka logic aayega (similar to contact update)
        logger.debug(f"Executing HubSpot Deal update for ID: {job_id}")
        
        # Filhal mock success return kar rahe hain jab tak deal update function na banayein
        return f"SUCCESS: Job ID '{job_id}' updated successfully with {update_fields}."
        
    except Exception as e:
        logger.error(f"Exception occurred while executing update_job_deal tool: {e}")
        return f"ERROR: An exception occurred during Job update."

# LangGraph ya LLM mein bind karne ke liye tools ki list
crm_tools = [update_crm_contact, update_job_deal]