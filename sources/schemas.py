from pydantic import BaseModel, EmailStr
from typing import Optional, List
from enum import Enum
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase): # user/repo ,  auth/routes
    password: str

class SummaryType(str, Enum):
    SHORT = "short"
    DETAILED = "detailed"

class SummaryRequest(BaseModel):
    summary_type: SummaryType = SummaryType.SHORT

class SummaryBase(BaseModel):
    content: str

#class SummaryResponse(BaseModel): # MAY BE NOT USED 
#    summary: str

class SummaryDisplay(SummaryBase):
    id: int
    document_id: int
    summary_type: str
    content: str
    audio_path: Optional[str] = None

    class Config:
        orm_mode = True

class ReportType(str, Enum):
    FORMAL = "formal"
    ACADEMIC = "academic"
    BUSINESS_INSIGHTS = "business_insights"
    RISK_ANALYSIS = "risk_analysis"

class ReportRequest(BaseModel):
    report_type: ReportType = ReportType.FORMAL

class ReportDisplay(BaseModel):
    id: int
    content: str
    report_type: str
    document_id: int
    
    class Config:
        orm_mode = True

class ChatHistoryBase(BaseModel):
    question: str
    answer: str

class ChatHistoryDisplay(ChatHistoryBase):
    id: int
    timestamp: datetime
    
    class Config:
        orm_mode = True


class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str

class DocumentBase(BaseModel):
    id: int
    filename: str
    status: str
    file_type: Optional[str] = None

class DocumentDisplay(DocumentBase):
    content: Optional[str] = None 
    summaries: List[SummaryDisplay] = []
    reports: List[ReportDisplay] = []
    chat_histories: List[ChatHistoryDisplay] = []
    
    class Config:
        orm_mode = True

class UserPublic(BaseModel): #  user/routes
    id: int
    username: str
    email: EmailStr
    is_verified: bool
    documents: List[DocumentBase] = [] 

    class Config:
        orm_mode = True

class SignupResponse(BaseModel): # auth/routes
    message: str
    details: UserPublic

class Login(BaseModel): # auth/routes
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginResponse(Token): # auth/routes
    access_token: str
    token_type: str
    refresh_token: str

class ChangePassword(BaseModel): # user/repo ,  user/routes
    current_password: str
    new_password: str

class ResetPassword(BaseModel): # auth/routes
    new_password: str
    
class EmailOnly(BaseModel): # auth/routes
    email: EmailStr

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None

class UserDeleteConfirmation(BaseModel):
    password: str

class ContactForm(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str
