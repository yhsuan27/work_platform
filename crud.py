from sqlalchemy.orm import Session
from sqlalchemy import or_, func
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
        # 直接存 'client' / 'contractor'，Enum 會接受
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
        status=models.ProjectStatus.OPEN,
        deadline=project.deadline
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def get_project(db: Session, project_id: int):
    """取得單一專案"""
    return db.query(models.Project).filter(models.Project.id == project_id).first()


def get_projects(db: Session, skip: int = 0, limit: int = 100):
    """
    取得所有開放專案（接案人）
    - 只回傳 status=OPEN 且 deadline 未過期（或沒設定）的專案
    """
    now = datetime.utcnow()
    return (
        db.query(models.Project)
        .filter(
            models.Project.status == models.ProjectStatus.OPEN,
            # deadline 為空 或 deadline > 現在
            or_(models.Project.deadline.is_(None),
                models.Project.deadline > now)
        )
        .order_by(models.Project.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_user_projects(db: Session, user_id: int):
    """取得使用者的專案"""
    return db.query(models.Project).filter(
        or_(
            models.Project.client_id == user_id,
            models.Project.contractor_id == user_id
        )
    ).order_by(models.Project.created_at.desc()).all()


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
    db_project = get_project(db, project_id)
    if not db_project:
        return None

    db_project.status = models.ProjectStatus.SUBMITTED
    db_project.updated_at = datetime.utcnow()

    add_submission_version(db, project_id, file_url)

    db.commit()
    db.refresh(db_project)
    return db_project


def accept_project(db: Session, project_id: int):
    """接受結案"""
    db_project = get_project(db, project_id)
    if db_project:
        db_project.status = models.ProjectStatus.COMPLETED
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
        db.commit()
        db.refresh(db_project)
    return db_project


# ==================== Proposal CRUD ====================

def create_proposal(db: Session, proposal: schemas.ProposalCreate, contractor_id: int):
    """建立提案（不含檔案）"""
    db_proposal = models.Proposal(
        project_id=proposal.project_id,
        contractor_id=contractor_id,
        price=proposal.price,
        description=proposal.description,
    )
    db.add(db_proposal)
    db.commit()
    db.refresh(db_proposal)
    return db_proposal


def add_proposal_file(
    db: Session,
    proposal_id: int,
    original_filename: str,
    stored_path: str,
):
    """提案 PDF 檔案版本紀錄"""
    last = (
        db.query(models.ProposalFile)
        .filter(models.ProposalFile.proposal_id == proposal_id)
        .order_by(models.ProposalFile.version.desc())
        .first()
    )
    next_ver = 1 if not last else last.version + 1

    db_file = models.ProposalFile(
        proposal_id=proposal_id,
        version=next_ver,
        original_filename=original_filename,
        stored_path=stored_path,
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file


def get_project_proposals(db: Session, project_id: int):
    """取得專案的所有提案"""
    return db.query(models.Proposal).filter(
        models.Proposal.project_id == project_id
    ).all()


def get_proposal_files(db: Session, proposal_id: int):
    """取得某提案所有 PDF 檔案版本"""
    return (
        db.query(models.ProposalFile)
        .filter(models.ProposalFile.proposal_id == proposal_id)
        .order_by(models.ProposalFile.version)
        .all()
    )


# crud.py 末端附近

def is_project_open_for_bidding(project: models.Project) -> bool:
    """
    檢查專案是否仍可投標
    - 狀態必須是 OPEN
    - 若有設定 deadline，現在時間 > deadline 就視為已截止
    """
    if project.status != models.ProjectStatus.OPEN:
        return False

    # deadline 沒設就當成不限時
    if project.deadline is None:
        return True

    # 用「本機時間」來比，跟你在瀏覽器看到的時間一致
    now = datetime.now()
    return project.deadline > now


# ==================== Message CRUD ====================

def create_message(db: Session, project_id: int, sender_id: int, content: str):
    """建立訊息"""
    db_message = models.Message(
        project_id=project_id,
        sender_id=sender_id,
        content=content,
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message


def get_project_messages(db: Session, project_id: int):
    """取得專案的所有訊息"""
    return (
        db.query(models.Message)
        .filter(models.Message.project_id == project_id)
        .order_by(models.Message.created_at)
        .all()
    )

# ==================== Submission Version CRUD ====================

def add_submission_version(db: Session, project_id: int, submit_url: str):
    """新增一個結案版本紀錄（v1, v2, v3...）"""
    last = (
        db.query(models.SubmissionVersion)
        .filter(models.SubmissionVersion.project_id == project_id)
        .order_by(models.SubmissionVersion.version.desc())
        .first()
    )
    new_version = 1 if last is None else last.version + 1

    ver = models.SubmissionVersion(
        project_id=project_id,
        version=new_version,
        submit_url=submit_url,
    )
    db.add(ver)
    db.commit()
    db.refresh(ver)
    return ver


def get_submission_versions(db: Session, project_id: int):
    """查詢某專案所有結案版本（依版本號升冪）"""
    return (
        db.query(models.SubmissionVersion)
        .filter(models.SubmissionVersion.project_id == project_id)
        .order_by(models.SubmissionVersion.version.asc())
        .all()
    )

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

# ==================== Rating CRUD ====================

def create_rating(db: Session, project_id: int, rater_id: int, rated_user_id: int, rating: schemas.RatingCreate):
    """建立評價"""
    rating_data = rating.dict(exclude_unset=True)
    # 移除重複的 ID 參數
    rating_data.pop('rater_id', None)
    rating_data.pop('rated_user_id', None)
    
    db_rating = models.Rating(
        rater_id=rater_id,
        project_id=project_id,
        rated_user_id=rated_user_id,
        **rating_data 
    )
    db.add(db_rating)
    db.commit()
    db.refresh(db_rating)
    return db_rating

def get_average_rating(db: Session, user_id: int):
    """取得使用者收到的綜合平均評價"""
    ratings = db.query(models.Rating).filter(models.Rating.rated_user_id == user_id).all()
    
    if not ratings:
        return {"average_score": 0.0, "total_ratings": 0}

    total_score_sum = 0.0
    total_items_count = 0

    for r in ratings:
        scores = [
            r.cooperation_attitude,
            r.output_quality,
            r.execution_efficiency,
            r.demand_reasonableness,
            r.acceptance_difficulty
        ]
        valid_scores = [s for s in scores if s is not None]
        
        if valid_scores:
            total_score_sum += sum(valid_scores) / len(valid_scores)
            total_items_count += 1

    final_average = total_score_sum / total_items_count if total_items_count > 0 else 0.0

    return {
        "average_score": round(final_average, 1),
        "total_ratings": len(ratings)
    }

def has_user_rated_project(db: Session, project_id: int, rater_id: int, rated_user_id: int):
    """檢查評價者是否已經對該專案的該使用者評分"""
    return db.query(models.Rating).filter(
        models.Rating.project_id == project_id,
        models.Rating.rater_id == rater_id,
        models.Rating.rated_user_id == rated_user_id
    ).first()

# --- 新增的查詢與更新功能 ---

def get_rating_by_ids(db: Session, project_id: int, rater_id: int):
    """根據專案ID和評價者ID取得評價"""
    return db.query(models.Rating).filter(
        models.Rating.project_id == project_id,
        models.Rating.rater_id == rater_id
    ).first()

def update_rating(db: Session, project_id: int, rater_id: int, rating_update: schemas.RatingCreate):
    """更新已存在的評價"""
    db_rating = get_rating_by_ids(db, project_id, rater_id)
    if db_rating:
        update_data = rating_update.dict(exclude_unset=True)
        update_data.pop('rater_id', None)
        update_data.pop('rated_user_id', None)
        
        for key, value in update_data.items():
            setattr(db_rating, key, value)
            
        db.commit()
        db.refresh(db_rating)
    return db_rating

# 新增：取得文字評論列表
def get_user_reviews(db: Session, user_id: int):
    """取得特定使用者收到的所有評價列表 (包含評論內容)"""
    return db.query(models.Rating).filter(
        models.Rating.rated_user_id == user_id
    ).order_by(models.Rating.created_at.desc()).all()
