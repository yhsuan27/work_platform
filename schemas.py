from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from models import UserRole, ProjectStatus, IssueStatus 

# ==================== User Schemas ====================

class UserBase(BaseModel):
    username: str
    email: EmailStr
    # 前端傳 'client' / 'contractor'，先用 str 接就好
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

# ==================== Issue Schemas (需放在 Project 之前) ====================

class IssueBase(BaseModel):
    title: str
    description: Optional[str] = None

class IssueCreate(IssueBase):
    pass

class Issue(IssueBase):
    id: int
    project_id: int
    status: IssueStatus
    created_by_id: int
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class IssueCommentCreate(BaseModel):
    content: str

class IssueComment(BaseModel):
    id: int
    issue_id: int
    sender_id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

# ==================== Project Schemas ====================

class ProjectBase(BaseModel):
    title: str
    description: str
    budget: Optional[float] = None
    # ★ 新增：委託截止時間（可選）
    deadline: Optional[datetime] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    budget: Optional[float] = None
    status: Optional[ProjectStatus] = None
    deadline: Optional[datetime] = None

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
    issues: List[Issue] = []    # 這裡就可以正常使用 Issue 了

    class Config:
        from_attributes = True

# ==================== Proposal File Schemas（檔案版本） ====================

class ProposalFile(BaseModel):
    id: int
    proposal_id: int
    version: int
    original_filename: str
    stored_path: str
    uploaded_at: datetime

    class Config:
        from_attributes = True

# ==================== Proposal Schemas ====================

class ProposalBase(BaseModel):
    price: float
    description: Optional[str] = None

class ProposalCreate(ProposalBase):
    project_id: int
    # 提案時實際的 PDF 檔會用 UploadFile 接，不會用 schema

class Proposal(ProposalBase):
    id: int
    project_id: int
    contractor_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ProposalWithContractor(Proposal):
    contractor: User
    # ★ 新增：對應到 models.Proposal.files
    files: List[ProposalFile] = []

    class Config:
        from_attributes = True

# ==================== Submission Version Schemas ====================

class SubmissionVersion(BaseModel):
    id: int
    project_id: int
    version: int
    submit_url: str
    uploaded_at: datetime # 這裡對應 models 的 created_at

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
    rater_id: int           # 評價者 ID
    rated_user_id: int      # 被評價者 ID

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