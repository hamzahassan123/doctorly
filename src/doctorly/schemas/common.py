from pydantic import BaseModel, ConfigDict


class ApiSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid", #strict guard (against melicious code)
        from_attributes=True, # converts sqlachemy object into pydantic object
        str_strip_whitespace=True,
    )
"""
1. data validation class (api data)
2. ya class har API Contract i.e. schema between frontend and backend(DTO - data transfer object) main use hote hai
3. if you are sending or recieving data from frontend to backend
or har attribute apna kaam in ya out hoty wqakt karta hai"""

class ErrorResponse(ApiSchema):
    code: str
    message: str
    request_id: str | None = None

#Yeh class tab use hoti hai jab API mein koi error aa jaye
