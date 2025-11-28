from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from models import UserRole, ProjectStatus

# ==================== User Schemas ====================

class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class User(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

# ==================== Project Schemas ====================

class ProjectBase(BaseModel):
    title: str
    description: str
    budget: Optional[float] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    budget: Optional[float] = None
    status: Optional[ProjectStatus] = None

class ProjectSubmit(BaseModel):
    submission_file_url: str

class ProjectReject(BaseModel):
    rejection_reason: str

class Project(ProjectBase):
    id: int
    status: ProjectStatus
    client_id: int
    contractor_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    submission_file_url: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    class Config:
        from_attributes = True

class ProjectWithDetails(Project):
    client: User
    contractor: Optional[User] = None
    
    class Config:
        from_attributes = True

# ==================== Proposal Schemas ====================

class ProposalBase(BaseModel):
    price: float
    description: Optional[str] = None

class ProposalCreate(ProposalBase):
    project_id: int

class Proposal(ProposalBase):
    id: int
    project_id: int
    contractor_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ProposalWithContractor(Proposal):
    contractor: User
    
    class Config:
        from_attributes = True

# ==================== Message Schemas ====================

class MessageCreate(BaseModel):
    content: str

class Message(BaseModel):
    id: int
    project_id: int
    sender_id: int
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class MessageWithSender(Message):
    sender: User
    
    class Config:
        from_attributes = True