from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from typing import Optional

from app.services.email_service import ContactInquiryPayload, EmailDeliveryResult, send_contact_inquiry

router = APIRouter(prefix="/contact", tags=["Contact"])


class ContactInquiryRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    institution: Optional[str] = Field(None, max_length=200)
    message: str = Field(..., min_length=10, max_length=5000)


@router.post("", response_model=EmailDeliveryResult, status_code=status.HTTP_200_OK)
async def submit_contact_inquiry(payload: ContactInquiryRequest) -> EmailDeliveryResult:
    """
    Submits a public contact form inquiry and dispatches notification to karnan284858@gmail.com.
    """
    contact_data = ContactInquiryPayload(
        name=payload.name,
        email=str(payload.email),
        institution=payload.institution,
        message=payload.message,
    )
    return send_contact_inquiry(contact_data)
