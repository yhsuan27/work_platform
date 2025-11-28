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