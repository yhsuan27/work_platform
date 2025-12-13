from pydantic import BaseModel, EmailStr,Field
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

# work_platform/work_platform/schemas.py (新增在檔案末尾)

# ==================== Rating Schemas ====================

class RatingBase(BaseModel):
    # 共同維度
    cooperation_attitude: float = Field(..., ge=1.0, le=5.0) 
    comment: Optional[str] = None
    
    # 委託人受評維度
    demand_reasonableness: Optional[float] = Field(None, ge=1.0, le=5.0)
    acceptance_difficulty: Optional[float] = Field(None, ge=1.0, le=5.0)
    
    # 接案人受評維度
    output_quality: Optional[float] = Field(None, ge=1.0, le=5.0)
    execution_efficiency: Optional[float] = Field(None, ge=1.0, le=5.0)

class RatingCreate(RatingBase):
    rater_id: int          # 評價者 ID (新增至 Body)
    rated_user_id: int     # 被評價者 ID (新增至 Body)

class Rating(RatingBase):
    id: int
    rater_id: int
    project_id: int
    rated_user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class AvgRating(BaseModel):
    """用於顯示平均評價的 Schema"""
    average_score: float
    total_ratings: int