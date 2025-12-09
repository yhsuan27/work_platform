from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
import models, schemas
from auth_utils import get_password_hash, verify_password

# ==================== User CRUD ====================

def create_user(db: Session, user: schemas.UserCreate):
    """建立使用者"""
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_username(db: Session, username: str):
    """根據帳號查詢使用者"""
    return db.query(models.User).filter(models.User.username == username).first()

def authenticate_user(db: Session, username: str, password: str):
    """驗證使用者登入"""
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

# ==================== Project CRUD ====================

def create_project(db: Session, project: schemas.ProjectCreate, client_id: int):
    """建立專案"""
    db_project = models.Project(
        title=project.title,
        description=project.description,
        budget=project.budget,
        client_id=client_id,
        status=models.ProjectStatus.OPEN  # 確保是 OPEN 不是 DRAFT
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

def get_project(db: Session, project_id: int):
    """取得單一專案"""
    return db.query(models.Project).filter(models.Project.id == project_id).first()

def get_projects(db: Session, skip: int = 0, limit: int = 100):
    """取得所有開放專案"""
    return db.query(models.Project).filter(
        models.Project.status == models.ProjectStatus.OPEN
    ).offset(skip).limit(limit).all()

def get_user_projects(db: Session, user_id: int):
    """取得使用者的專案（委託的或接的）"""
    return db.query(models.Project).filter(
        or_(models.Project.client_id == user_id, 
            models.Project.contractor_id == user_id)
    ).all()

def update_project(db: Session, project_id: int, project_update: schemas.ProjectUpdate):
    """更新專案"""
    db_project = get_project(db, project_id)
    if db_project:
        for key, value in project_update.dict(exclude_unset=True).items():
            setattr(db_project, key, value)
        db.commit()
        db.refresh(db_project)
    return db_project

def select_contractor(db: Session, project_id: int, contractor_id: int):
    """選擇接案人"""
    db_project = get_project(db, project_id)
    if db_project:
        db_project.contractor_id = contractor_id
        db_project.status = models.ProjectStatus.IN_PROGRESS
        db.commit()
        db.refresh(db_project)
    return db_project

def submit_project(db: Session, project_id: int, file_url: str):
    """提交結案"""
    db_project = get_project(db, project_id)
    if db_project:
        db_project.submission_file_url = file_url
        db_project.status = models.ProjectStatus.SUBMITTED
        db.commit()
        db.refresh(db_project)
    return db_project

def accept_project(db: Session, project_id: int):
    """接受結案"""
    db_project = get_project(db, project_id)
    if db_project:
        db_project.status = models.ProjectStatus.COMPLETED
        from datetime import datetime
        db_project.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(db_project)
    return db_project

def reject_project(db: Session, project_id: int, reason: str):
    """退件"""
    db_project = get_project(db, project_id)
    if db_project:
        db_project.status = models.ProjectStatus.REJECTED
        db_project.rejection_reason = reason
        db_project.submission_file_url = None
        db.commit()
        db.refresh(db_project)
    return db_project

# ==================== Proposal CRUD ====================

def create_proposal(db: Session, proposal: schemas.ProposalCreate, contractor_id: int):
    """建立提案"""
    db_proposal = models.Proposal(
        project_id=proposal.project_id,
        contractor_id=contractor_id,
        price=proposal.price,
        description=proposal.description
    )
    db.add(db_proposal)
    db.commit()
    db.refresh(db_proposal)
    return db_proposal

def get_project_proposals(db: Session, project_id: int):
    """取得專案的所有提案"""
    return db.query(models.Proposal).filter(
        models.Proposal.project_id == project_id
    ).all()

# ==================== Message CRUD ====================

def create_message(db: Session, project_id: int, sender_id: int, content: str):
    """建立訊息"""
    db_message = models.Message(
        project_id=project_id,
        sender_id=sender_id,
        content=content
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def get_project_messages(db: Session, project_id: int):
    """取得專案的所有訊息"""
    return db.query(models.Message).filter(
        models.Message.project_id == project_id
    ).order_by(models.Message.created_at).all()

# ==================== Issue CRUD ====================(新增)

def create_issue(db: Session, project_id: int, creator_id: int, issue_in: schemas.IssueCreate):
    """建立一筆 Issue（通常由委託方在專案已提交結案後建立）"""
    project = get_project(db, project_id)
    if not project:
        return None

    # 可以依需求限制只有 SUBMITTED 狀態才能建立 issue
    if project.status != models.ProjectStatus.SUBMITTED:
        return None

    db_issue = models.Issue(
        project_id=project_id,
        title=issue_in.title,
        description=issue_in.description,
        created_by_id=creator_id,
    )
    db.add(db_issue)
    db.commit()
    db.refresh(db_issue)
    return db_issue


def get_project_issues(db: Session, project_id: int):
    """取得某專案底下的所有 Issues"""
    return (
        db.query(models.Issue)
        .filter(models.Issue.project_id == project_id)
        .order_by(models.Issue.created_at)
        .all()
    )


def create_issue_comment(db: Session, issue_id: int, sender_id: int, content: str):
    """在 Issue 底下新增留言"""
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()
    if not issue:
        return None

    db_comment = models.IssueComment(
        issue_id=issue_id,
        sender_id=sender_id,
        content=content,
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment


def get_issue_comments(db: Session, issue_id: int):
    """取得 Issue 底下所有留言"""
    return (
        db.query(models.IssueComment)
        .filter(models.IssueComment.issue_id == issue_id)
        .order_by(models.IssueComment.created_at)
        .all()
    )


def resolve_issue(db: Session, issue_id: int, resolver_id: int):
    """由委託方將 Issue 設為已處理完成"""
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()
    if not issue:
        return None

    project = issue.project
    if project.client_id != resolver_id:
        # 只有該專案的委託人可以結束 Issue
        return None

    issue.status = models.IssueStatus.RESOLVED
    issue.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(issue)
    return issue


def has_open_issues(db: Session, project_id: int) -> bool:
    """檢查某專案是否仍有未處理的 Issue"""
    return (
        db.query(models.Issue)
        .filter(
            models.Issue.project_id == project_id,
            models.Issue.status == models.IssueStatus.OPEN,
        )
        .count()
        > 0
    )