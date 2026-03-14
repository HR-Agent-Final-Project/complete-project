from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional

class EmployeeRegisterRequest(BaseModel):
    """
    Only HR Manager (level 3) or Admin (level 4) can use this.
    Creates a new employee account.
    """
    first_name      : str
    last_name       : str
    personal_email  : EmailStr
    phone_number    : Optional[str] = None
    department_id   : Optional[int] = None
    role_id         : Optional[int] = None
    employment_type : str = "full_time"
    base_salary     : Optional[float] = None
    language_pref   : str = "en"

    class Config:
        json_schema_extra = {
            "example": {
                "first_name":      "Kaveen",
                "last_name":       "Deshapriya",
                "personal_email":  "kaveen@company.com",
                "phone_number":    "0771234567",
                "department_id":   1,
                "role_id":         1,
                "employment_type": "full_time",
                "base_salary":     150000,
                "language_pref":   "en"
            }
        }


class EmployeeRegisterResponse(BaseModel):
    """Returned after successful registration."""
    message         : str
    employee_id     : int
    employee_number : str
    full_name       : str
    email           : str
    temp_password   : str    # Temporary password — employee must change on first login
    department      : Optional[str] = None
    role            : Optional[str] = None


class SetPasswordRequest(BaseModel):
    """
    Employee uses this to set their own password on first login.
    Replaces the temporary password given by HR.
    """
    temp_password    : str
    new_password     : str
    confirm_password : str

    @field_validator("confirm_password")
    def passwords_match(cls, v, info):
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match.")
        return v

    @field_validator("new_password")
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number.")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "temp_password":    "TempPass123",
                "new_password":     "MyNewPass@456",
                "confirm_password": "MyNewPass@456"
            }
        }


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    class Config:
        json_schema_extra = {
            "example": {"email": "kaveen@company.com"}
        }


class ResetPasswordRequest(BaseModel):
    reset_token      : str
    new_password     : str
    confirm_password : str

    @field_validator("confirm_password")
    def passwords_match(cls, v, info):
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match.")
        return v


class SelfRegisterRequest(BaseModel):
    """
    HR Admin or Management staff self-registration.
    Account is created as inactive — requires approval from hr.agent.automation@gmail.com.
    """
    first_name      : str
    last_name       : str
    personal_email  : EmailStr
    password        : str
    confirm_password: str
    requested_role  : str   # 'hr_admin' or 'management'
    phone_number    : Optional[str] = None

    @field_validator("confirm_password")
    def passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match.")
        return v

    @field_validator("password")
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number.")
        return v

    @field_validator("requested_role")
    def valid_role(cls, v):
        if v not in ("hr_admin", "management"):
            raise ValueError("requested_role must be 'hr_admin' or 'management'.")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "first_name":      "Dilani",
                "last_name":       "Fernando",
                "personal_email":  "dilani@example.com",
                "password":        "Secure@123",
                "confirm_password":"Secure@123",
                "requested_role":  "hr_admin",
                "phone_number":    "0771234567"
            }
        }


class SelfRegisterResponse(BaseModel):
    message: str


class LoginRequest(BaseModel):
    identifier: str   # Employee ID (e.g. IT0001) or personal email
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "identifier": "IT0001",
                "password": "Admin@123"
            }
        }


class FirebaseTokenRequest(BaseModel):
    id_token: str

    class Config:
        json_schema_extra = {
            "example": {
                "id_token": "eyJhbGciOiJSUzI1NiIs..."
            }
        }


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    employee_id: int
    employee_name: str
    email: str
    access_level: int
    department: Optional[str] = None
    role: Optional[str] = None
    profile_photo: Optional[str] = None
    must_change_password: bool = False   # True on first ever login (temp password)


class MessageResponse(BaseModel):
    message: str