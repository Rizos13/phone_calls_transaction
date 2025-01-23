from pydantic import BaseModel, Field, ConfigDict
from datetime import date

class ContactCreate(BaseModel):
    phone_nr: str = Field(..., example="+34674766354")
    contact_name: str = Field(..., example="Nik Jonas")

class Contact(BaseModel):
    phone_nr: str
    contact_name: str

    model_config = ConfigDict(from_attributes=True)

class CallCreate(BaseModel):
    phone_nr: str = Field(..., example="+34674766354")
    call_date: date = Field(..., example="2025-04-27")
    hour: int = Field(..., ge=0, le=23, example=14)
    minute: int = Field(..., ge=0, le=59, example=30)
    duration_seconds: int = Field(..., ge=0, example=300)

class Call(BaseModel):
    call_id: int
    phone_nr: str
    call_date: date
    hour: int
    minute: int
    duration_seconds: int

    model_config = ConfigDict(from_attributes=True)

