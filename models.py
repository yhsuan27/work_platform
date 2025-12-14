from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy.sql import func 
import enum
from database import Base

# ==================== Enum 定義 ====================

class UserRole(str, enum.Enum):
    CLIENT = "client"          # 委託人
    CONTRACTOR = "contractor"  # 接案人

class ProjectStatus(str, enum.Enum):
    DRAFT = "draft"               # 草稿
    OPEN = "open"                 # 開放接案
    IN_PROGRESS = "in_progress"   # 進行中
    SUBMITTED = "submitted"       # 已提交結案
    COMPLETED = "completed"       # 已完成
    REJECTED = "rejected"         # 已退件

class IssueStatus(str, enum.Enum): 
    OPEN = "open"           # 尚待處理
    RESOLVED = "resolved"   # 已處理完成

# ==================== User (使用者) ====================

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 專案關聯
    created_projects = relationship(
        "Project",
        back_populates="client",
        foreign_keys="Project.client_id"
    )
    contracted_projects = relationship(
        "Project",
        back_populates="contractor",
        foreign_keys="Project.contractor_id"
    )
    proposals = relationship("Proposal", back_populates="contractor")
    messages = relationship("Message", back_populates="sender")

    # 評價關聯設定 (來自 main 分支)
    given_ratings = relationship("Rating", foreign_keys="Rating.rater_id", back_populates="rater")
    received_ratings = relationship("Rating", foreign_keys="Rating.rated_user_id", back_populates="rated_user")


# ==================== Project (專案) ====================

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    budget = Column(Float)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.DRAFT)
    
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    contractor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # 結案相關
    submission_file_url = Column(String(500), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # ★ 限時競標截止時間 (來自 feature 分支)
    deadline = Column(DateTime, nullable=True)  
    
    # 關聯
    client = relationship(
        "User",
        back_populates="created_projects",
        foreign_keys=[client_id]
    )
    contractor = relationship(
        "User",
        back_populates="contracted_projects",
        foreign_keys=[contractor_id]
    )
    proposals = relationship("Proposal", back_populates="project")
    messages = relationship("Message", back_populates="project")
    
    # 新增關聯 (來自 main 分支)
    issues = relationship("Issue", back_populates="project", cascade="all, delete-orphan") 
    ratings = relationship("Rating", back_populates="project")

    # ★ 一個專案有多個「結案」版本 (來自 feature 分支)
    submission_versions = relationship(
        "SubmissionVersion",
        back_populates="project",
        order_by="SubmissionVersion.version",
        cascade="all, delete-orphan"
    )


# ==================== Proposal（報價提案） ====================

class Proposal(Base):
    __tablename__ = "proposals"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    contractor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    price = Column(Float, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 關聯
    project = relationship("Project", back_populates="proposals")
    contractor = relationship("User", back_populates="proposals")

    # ★ 一個提案可以有多個 PDF 版本 (來自 feature 分支)
    files = relationship(
        "ProposalFile",
        back_populates="proposal",
        order_by="ProposalFile.version",
        cascade="all, delete-orphan"
    )


# ==================== ProposalFile (提案 PDF 版本) ====================
# (來自 feature 分支)

class ProposalFile(Base):
    __tablename__ = "proposal_files"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("proposals.id"), nullable=False)
    original_filename = Column(String(255), nullable=False)   # 上傳時的檔名
    stored_path = Column(String(500), nullable=False)         # 儲存在 static/proposals/... 的路徑
    version = Column(Integer, nullable=False)                 # v1, v2, v3 ...
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    proposal = relationship("Proposal", back_populates="files")


# ==================== Issue (待處理事項) ====================
# (來自 main 分支)

class Issue(Base): 
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(IssueStatus), default=IssueStatus.OPEN)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="issues")
    created_by = relationship("User")
    comments = relationship("IssueComment", back_populates="issue", cascade="all, delete-orphan")


class IssueComment(Base): 
    __tablename__ = "issue_comments"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    issue = relationship("Issue", back_populates="comments")
    sender = relationship("User")


# ==================== Message（溝通訊息） ====================

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="messages")
    sender = relationship("User", back_populates="messages")


# ==================== SubmissionVersion (結案版本歷史) ====================
# (來自 feature 分支)

class SubmissionVersion(Base):
    __tablename__ = "submission_versions"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version = Column(Integer, nullable=False)
    submit_url = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship(
        "Project",
        back_populates="submission_versions"
    )


# ==================== Rating (評價) ====================
# (來自 main 分支)

class Rating(Base):
    __tablename__ = "ratings"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 評價者ID (誰給出的評價)
    rater_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # 被評價的專案ID (針對哪個專案)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    # 被評價者ID (誰收到的評價)
    rated_user_id = Column(Integer, ForeignKey("users.id"), nullable=False) 
    
    # 評價維度 (1-5 星，使用 Float 儲存 1.0-5.0 分)
    cooperation_attitude = Column(Float, nullable=False) # 合作態度
    
    # 委託人受評維度 (Rater is Contractor, Rated is Client)
    demand_reasonableness = Column(Float, nullable=True) # 需求合理性
    acceptance_difficulty = Column(Float, nullable=True) # 驗收難度
    
    # 接案人受評維度 (Rater is Client, Rated is Contractor)
    output_quality = Column(Float, nullable=True)       # 產出品質
    execution_efficiency = Column(Float, nullable=True) # 執行效率
    
    # 總體質性評論
    comment = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 關聯設定
    rater = relationship("User", foreign_keys=[rater_id], back_populates="given_ratings")
    rated_user = relationship("User", foreign_keys=[rated_user_id], back_populates="received_ratings")
    project = relationship("Project", back_populates="ratings")