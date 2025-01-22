from pydantic import BaseModel, Field, validator
from datetime import date
import re

class TestModel(BaseModel):
    phone_nr: str = Field(..., example="+34674766354")
    date_field: date = Field(..., example="2025-04-27")

    @validator('phone_nr')
    def validate_phone_nr(cls, v):
        pattern = re.compile(r'^\+\d{10,15}$')
        if not pattern.match(v):
            raise ValueError('Invalid phone number format. It should start with + followed by 10-15 digits.')
        return v

if __name__ == "__main__":
    m = TestModel(phone_nr="+34674766354", date_field="2025-04-27")
    print(m)