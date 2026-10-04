from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from typing import Optional

from app.core.errors import AppError
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
    Submits a public contact form inquiry and dispatches notification to configured provider.
    Returns HTTP 200 ONLY when email delivery succeeds.
    Returns HTTP 503 / 502 with truthful error details if provider is unconfigured or fails.
    """
    contact_data = ContactInquiryPayload(
        name=payload.name,
        email=str(payload.email),
        institution=payload.institution,
        message=payload.message,
    )
    result = send_contact_inquiry(contact_data)
    if not result.success:
        if result.status == "unconfigured":
            raise AppError(
                code="EMAIL_SERVICE_UNCONFIGURED",
                message=result.message,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        else:
            raise AppError(
                code="EMAIL_DELIVERY_FAILED",
                message=result.message,
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

    return result
