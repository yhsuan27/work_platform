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


# ==================== User ====================

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 關聯
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


# ==================== Project ====================

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
    submission_file_url = Column(String(500), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    deadline = Column(DateTime, nullable=True)  # ★ 限時競標截止時間
    
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

    # ★ 一個專案有多個「結案」版本
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

    # ★ 一個提案可以有多個 PDF 版本
    files = relationship(
        "ProposalFile",
        back_populates="proposal",
        order_by="ProposalFile.version",
        cascade="all, delete-orphan"
    )


# ★ 新增：提案 PDF 檔案版本（限時競標用）

class ProposalFile(Base):
    __tablename__ = "proposal_files"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("proposals.id"), nullable=False)
    original_filename = Column(String(255), nullable=False)   # 上傳時的檔名
    stored_path = Column(String(500), nullable=False)         # 儲存在 static/proposals/... 的路徑
    version = Column(Integer, nullable=False)                 # v1, v2, v3 ...
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    proposal = relationship("Proposal", back_populates="files")


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


# ★ 新增：結案版本歷史（結案退件 / 重送用）

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

    # ★★ 關鍵：補上這個
    project = relationship(
        "Project",
        back_populates="submission_versions"
    )
