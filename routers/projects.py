from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import schemas, crud, models

router = APIRouter(prefix="/projects", tags=["專案管理"])

# ==================== 專案基本 CRUD ====================

@router.post("/", response_model=schemas.Project)
def create_project(project: schemas.ProjectCreate, client_id: int, db: Session = Depends(get_db)):
    """建立專案"""
    return crud.create_project(db, project, client_id)

@router.get("/", response_model=List[schemas.Project])
def get_all_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """查詢所有開放專案"""
    return crud.get_projects(db, skip, limit)

@router.get("/{project_id}", response_model=schemas.Project)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """查看單一專案詳情"""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    return project

@router.put("/{project_id}", response_model=schemas.Project)
def update_project(project_id: int, project_update: schemas.ProjectUpdate, db: Session = Depends(get_db)):
    """修改專案"""
    project = crud.update_project(db, project_id, project_update)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    return project

@router.get("/user/{user_id}", response_model=List[schemas.Project])
def get_user_projects(user_id: int, db: Session = Depends(get_db)):
    """取得使用者的歷史專案列表"""
    return crud.get_user_projects(db, user_id)

# ==================== 專案流程 (選擇、提交、驗收) ====================

@router.post("/{project_id}/select-contractor", response_model=schemas.Project)
def select_contractor(project_id: int, contractor_id: int, db: Session = Depends(get_db)):
    """選擇接案人"""
    project = crud.select_contractor(db, project_id, contractor_id)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    return project

@router.post("/{project_id}/submit", response_model=schemas.Project)
def submit_project(project_id: int, submission: schemas.ProjectSubmit, db: Session = Depends(get_db)):
    """提交結案檔案"""
    project = crud.submit_project(db, project_id, submission.submission_file_url)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    return project

@router.post("/{project_id}/accept", response_model=schemas.Project)
def accept_project(project_id: int, db: Session = Depends(get_db)):
    """接受結案"""
    project = crud.accept_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    return project

@router.post("/{project_id}/reject", response_model=schemas.Project)
def reject_project(project_id: int, rejection: schemas.ProjectReject, db: Session = Depends(get_db)):
    """退件"""
    project = crud.reject_project(db, project_id, rejection.rejection_reason)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    return project

# ==================== 提案相關 ====================

@router.post("/{project_id}/proposals", response_model=schemas.Proposal)
def create_proposal(project_id: int, proposal: schemas.ProposalCreate, contractor_id: int, db: Session = Depends(get_db)):
    """提出承包意願"""
    proposal.project_id = project_id
    return crud.create_proposal(db, proposal, contractor_id)

@router.get("/{project_id}/proposals", response_model=List[schemas.Proposal])
def get_proposals(project_id: int, db: Session = Depends(get_db)):
    """查看專案的所有提案"""
    return crud.get_project_proposals(db, project_id)

# ==================== 評價相關 ====================

@router.post("/{project_id}/rate", response_model=schemas.Rating)
def rate_user(project_id: int, rating: schemas.RatingCreate, db: Session = Depends(get_db)):
    """提交評價"""
    rater_id = rating.rater_id
    rated_user_id = rating.rated_user_id
    
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")

    if project.status != models.ProjectStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="專案未完成，無法評價")
        
    if rater_id not in [project.client_id, project.contractor_id]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="非專案參與者無法評價")

    if (rated_user_id not in [project.client_id, project.contractor_id] or rated_user_id == rater_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="評價對象必須是專案的另一方")
        
    if crud.has_user_rated_project(db, project_id, rater_id, rated_user_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="您已對該使用者完成評價")

    return crud.create_rating(db, project_id, rater_id, rated_user_id, rating)

@router.get("/{project_id}/rate", response_model=schemas.Rating)
def get_rating(project_id: int, rater_id: int, db: Session = Depends(get_db)):
    """查詢單一評價 (用於前端判斷)"""
    rating = crud.get_rating_by_ids(db, project_id, rater_id)
    if not rating:
        raise HTTPException(status_code=404, detail="尚未評價")
    return rating

@router.put("/{project_id}/rate", response_model=schemas.Rating)
def update_existing_rating(project_id: int, rating_update: schemas.RatingCreate, db: Session = Depends(get_db)):
    """修改評價"""
    rater_id = rating_update.rater_id
    db_rating = crud.get_rating_by_ids(db, project_id, rater_id)
    if not db_rating:
        raise HTTPException(status_code=404, detail="找不到要修改的評價")
    return crud.update_rating(db, project_id, rater_id, rating_update)

@router.get("/user/{user_id}/average-rating", response_model=schemas.AvgRating)
def get_user_average_rating(user_id: int, db: Session = Depends(get_db)):
    """取得平均評價"""
    return crud.get_average_rating(db, user_id)

@router.get("/user/{user_id}/reviews", response_model=List[schemas.Rating])
def get_user_reviews(user_id: int, db: Session = Depends(get_db)):
    """取得詳細評論列表"""
    return crud.get_user_reviews(db, user_id)