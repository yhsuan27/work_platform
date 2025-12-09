from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from database import Base

# 定義使用者角色的列舉
class UserRole(str, enum.Enum):
    CLIENT = "client"          # 委託人
    CONTRACTOR = "contractor"  # 接案人

# 定義專案狀態的列舉
class ProjectStatus(str, enum.Enum):
    DRAFT = "draft"               # 草稿
    OPEN = "open"                 # 開放接案
    IN_PROGRESS = "in_progress"   # 進行中
    SUBMITTED = "submitted"       # 已提交結案
    COMPLETED = "completed"       # 已完成
    REJECTED = "rejected"         # 已退件

class IssueStatus(str, enum.Enum): #新增
    OPEN = "open"          # 尚待處理
    RESOLVED = "resolved"  # 已處理完成

# 使用者資料表
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 關聯設定
    created_projects = relationship("Project", back_populates="client", foreign_keys="Project.client_id")
    contracted_projects = relationship("Project", back_populates="contractor", foreign_keys="Project.contractor_id")
    proposals = relationship("Proposal", back_populates="contractor")
    messages = relationship("Message", back_populates="sender")

# 專案資料表
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
    
    # 關聯設定
    client = relationship("User", back_populates="created_projects", foreign_keys=[client_id])
    contractor = relationship("User", back_populates="contracted_projects", foreign_keys=[contractor_id])
    proposals = relationship("Proposal", back_populates="project")
    messages = relationship("Message", back_populates="project")
    issues = relationship("Issue", back_populates="project", cascade="all, delete-orphan") #新增

# 提案資料表（接案人的報價）
class Proposal(Base):
    __tablename__ = "proposals"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    contractor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    price = Column(Float, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 關聯設定
    project = relationship("Project", back_populates="proposals")
    contractor = relationship("User", back_populates="proposals")

class Issue(Base): #新增
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

class IssueComment(Base): #新增
    __tablename__ = "issue_comments"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    issue = relationship("Issue", back_populates="comments")
    sender = relationship("User")


# 訊息資料表（溝通用）
class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 關聯設定
    project = relationship("Project", back_populates="messages")
    sender = relationship("User", back_populates="messages")