from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import schemas, crud, models

router = APIRouter(prefix="/projects", tags=["專案管理"])

@router.post("/", response_model=schemas.Project)
def create_project(
    project: schemas.ProjectCreate,
    client_id: int,  # 簡化版：直接傳入使用者ID
    db: Session = Depends(get_db)
):
    """建立專案（委託人）"""
    return crud.create_project(db, project, client_id)

@router.get("/", response_model=List[schemas.Project])
def get_all_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """查詢所有開放專案（接案人）"""
    return crud.get_projects(db, skip, limit)

@router.get("/{project_id}", response_model=schemas.Project)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """查看單一專案詳情"""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    return project

@router.put("/{project_id}", response_model=schemas.Project)
def update_project(
    project_id: int,
    project_update: schemas.ProjectUpdate,
    db: Session = Depends(get_db)
):
    """修改專案（委託人）"""
    project = crud.update_project(db, project_id, project_update)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    return project

@router.get("/user/{user_id}", response_model=List[schemas.Project])
def get_user_projects(user_id: int, db: Session = Depends(get_db)):
    """取得使用者的歷史專案列表"""
    return crud.get_user_projects(db, user_id)

@router.post("/{project_id}/select-contractor", response_model=schemas.Project)
def select_contractor(
    project_id: int,
    contractor_id: int,
    db: Session = Depends(get_db)
):
    """選擇接案人（委託人）"""
    project = crud.select_contractor(db, project_id, contractor_id)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    return project

@router.post("/{project_id}/submit", response_model=schemas.Project)
def submit_project(
    project_id: int,
    submission: schemas.ProjectSubmit,
    db: Session = Depends(get_db)
):
    """提交結案檔案（接案人）"""
    project = crud.submit_project(db, project_id, submission.submission_file_url)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    return project

@router.post("/{project_id}/accept", response_model=schemas.Project)
def accept_project(project_id: int, db: Session = Depends(get_db)):
    if crud.has_open_issues(db, project_id): # 新增
        raise HTTPException(status_code=400, detail="仍有未處理的 issue，無法結案")
    """接受結案（委託人）"""
    project = crud.accept_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    return project

@router.post("/{project_id}/reject", response_model=schemas.Project)
def reject_project(
    project_id: int,
    rejection: schemas.ProjectReject,
    db: Session = Depends(get_db)
):
    """退件（委託人）"""
    project = crud.reject_project(db, project_id, rejection.rejection_reason)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    return project

# ==================== 提案相關 ====================

@router.post("/{project_id}/proposals", response_model=schemas.Proposal)
def create_proposal(
    project_id: int,
    proposal: schemas.ProposalCreate,
    contractor_id: int,  # 簡化版：直接傳入接案人ID
    db: Session = Depends(get_db)
):
    """提出承包意願（接案人）"""
    proposal.project_id = project_id
    return crud.create_proposal(db, proposal, contractor_id)

@router.get("/{project_id}/proposals", response_model=List[schemas.Proposal])
def get_proposals(project_id: int, db: Session = Depends(get_db)):
    """查看專案的所有提案（委託人）"""
    return crud.get_project_proposals(db, project_id)

# ==================== Issue相關 ====================(新增)
@router.post("/{project_id}/issues", response_model=schemas.Issue)
def create_issue(
    project_id: int,
    issue: schemas.IssueCreate,
    creator_id: int,              
    db: Session = Depends(get_db)
):
    db_issue = crud.create_issue(db, project_id, creator_id, issue)
    if not db_issue:
        raise HTTPException(status_code=400, detail="無法建立 issue（專案不存在或狀態不允許）")
    return db_issue

# 列出專案的所有 Issue
@router.get("/{project_id}/issues", response_model=List[schemas.Issue])
def get_issues(project_id: int, db: Session = Depends(get_db)):
    return crud.get_project_issues(db, project_id)

# 甲乙雙方在 Issue 底下留言
@router.post("/{project_id}/issues/{issue_id}/comments", response_model=schemas.IssueComment)
def create_issue_comment(
    project_id: int,
    issue_id: int,
    comment: schemas.IssueCommentCreate,
    sender_id: int,
    db: Session = Depends(get_db)
):
    db_comment = crud.create_issue_comment(db, issue_id, sender_id, comment.content)
    if not db_comment:
        raise HTTPException(status_code=404, detail="Issue 不存在")
    return db_comment

# 取得 Issue 底下所有留言
@router.get("/{project_id}/issues/{issue_id}/comments", response_model=List[schemas.IssueComment])
def get_issue_comments(project_id: int, issue_id: int, db: Session = Depends(get_db)):
    return crud.get_issue_comments(db, issue_id)

# 甲方將 Issue 設為已處理完成
@router.post("/{project_id}/issues/{issue_id}/resolve", response_model=schemas.Issue)
def resolve_issue(
    project_id: int,
    issue_id: int,
    resolver_id: int,
    db: Session = Depends(get_db)
):
    db_issue = crud.resolve_issue(db, issue_id, resolver_id)
    if not db_issue:
        raise HTTPException(status_code=400, detail="無法將 issue 設為已完成（權限或資料錯誤）")
    return db_issue