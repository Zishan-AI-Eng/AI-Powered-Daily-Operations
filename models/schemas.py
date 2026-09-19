from pydantic import BaseModel , Field
from typing import Optional , TypedDict

class Candidates(BaseModel):
    name: str = Field(..., description="Name of the candidate")
    email: Optional[str] = Field(None, description="Email of the candidate")
    phone_number: Optional[str] = Field(None, description="Phone number of the candidate")
    contact_owner: Optional[str] = Field(None, description="Owner of the contact")
    primary_company: Optional[str] = Field(None, description="Primary company of the candidate")
    lead_status: Optional[str] = Field(None, description="Lead status of the candidate")
    created_date: Optional[str] = Field(None, description="Creation date of the candidate")
    last_activity_date: Optional[str] = Field(None, description="Last activity date of the candidate")
    
class Companies(BaseModel):
    name: str = Field(..., description="Name of the company")
    owner: Optional[str] = Field(None, description="Owner of the company")
    phone_number: Optional[str] = Field(None, description="Phone number of the company")
    city: Optional[str] = Field(None, description="City of the company")
    country: Optional[str] = Field(None, description="Country of the company")
    industry: Optional[str] = Field(None, description="Industry of the company")
    last_activity_date: Optional[str] = Field(None, description="Last activity date of the company")
    created_date: Optional[str] = Field(None, description="Creation date of the company")


class JobDeal(BaseModel):
    id: str
    job_title: str
    stage: str

class NormalizedCRMData(BaseModel):
    candidates: list[Candidates]
    companies: list[Companies]
    jobs: list[JobDeal]
