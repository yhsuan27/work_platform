from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from models import UserRole, ProjectStatus

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

# ==================== Project Schemas ====================

class ProjectBase(BaseModel):
    title: str
    description: str
    budget: Optional[float] = None
    # ★ 新增：委託截止時間（可選）
    deadline: Optional[datetime] = None

class ProjectCreate(ProjectBase):
    # 之後前端在建立專案時要一併送出 deadline
    pass

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    budget: Optional[float] = None
    status: Optional[ProjectStatus] = None
    # 也允許更新截止時間
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

# 如果之後想回傳「直接可下載的網址」，可以再加一個包含 download_url 的 schema

# ==================== Proposal Schemas ====================

class ProposalBase(BaseModel):
    price: float
    description: Optional[str] = None

class ProposalCreate(ProposalBase):
    project_id: int
    # 提案時實際的 PDF 檔會用 UploadFile 接，不會用 schema，
    # 所以這裡先不用放檔案欄位

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
    uploaded_at: datetime

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
