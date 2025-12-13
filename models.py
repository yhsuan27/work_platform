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

    # 評價關聯設定
    given_ratings = relationship("Rating", foreign_keys="Rating.rater_id", back_populates="rater")
    received_ratings = relationship("Rating", foreign_keys="Rating.rated_user_id", back_populates="rated_user")

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

    ratings = relationship("Rating", back_populates="project")

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

    # work_platform/work_platform/models.py (新增在檔案末尾)

# work_platform/work_platform/models.py (新增在檔案末尾)

# 評價資料表
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