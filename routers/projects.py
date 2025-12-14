# routers/projects.py
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path
from uuid import uuid4

from database import get_db
import schemas, crud
import models

router = APIRouter(prefix="/projects", tags=["專案管理"])

# === 檔案上傳設定 ===
BASE_DIR = Path(__file__).resolve().parent.parent

# 提案 PDF 上傳資料夾
PROPOSAL_UPLOAD_DIR = BASE_DIR / "static" / "proposals"
PROPOSAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 結案檔案上傳資料夾（任何副檔名都可以）
SUBMISSION_UPLOAD_DIR = BASE_DIR / "static" / "submissions"
SUBMISSION_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ==================== 專案基本 CRUD ====================

@router.post("/", response_model=schemas.Project)
def create_project(
    project: schemas.ProjectCreate,
    client_id: int,
    db: Session = Depends(get_db),
):
    """建立專案（委託人）"""
    return crud.create_project(db, project, client_id)


@router.get("/", response_model=List[schemas.Project])
def get_all_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    查詢所有開放專案（接案人）
    - 只會回傳 status=OPEN 且未過截止時間的專案（crud 有處理）
    """
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
    db: Session = Depends(get_db),
):
    """
    修改專案（委託人）
    - 可更新 title / description / budget / status / deadline
    """
    project = crud.update_project(db, project_id, project_update)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    return project


@router.get("/user/{user_id}", response_model=List[schemas.Project])
def get_user_projects(user_id: int, db: Session = Depends(get_db)):
    """取得使用者的歷史專案列表（委託 或 接案）"""
    return crud.get_user_projects(db, user_id)


# ==================== 專案流程 (選擇、提交、驗收) ====================

@router.post("/{project_id}/select-contractor", response_model=schemas.Project)
def select_contractor(
    project_id: int,
    contractor_id: int,
    db: Session = Depends(get_db),
):
    """截止後，委託人選擇接案人"""
    project = crud.select_contractor(db, project_id, contractor_id)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    return project


# === 接案人上傳「結案檔案」，任何副檔名都可以 ===
@router.post("/{project_id}/submit", response_model=schemas.Project)
async def submit_project(
    project_id: int,
    file: UploadFile = File(None), # 這裡為了相容性，先允許 None，但邏輯上要有檔案
    submission_file_url: Optional[str] = Form(None), # 為了相容舊版純網址上傳
    db: Session = Depends(get_db),
):
    """
    提交結案檔案
    - 支援舊版純網址 (submission_file_url)
    - 支援新版檔案上傳 (file)
    """
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")

    # 只允許「進行中」或「被退件」的專案上傳結案
    if project.status not in (
        models.ProjectStatus.IN_PROGRESS,
        models.ProjectStatus.REJECTED,
    ):
        raise HTTPException(
            status_code=400,
            detail="目前狀態不可上傳結案"
        )

    final_url = ""

    # 如果有上傳實體檔案
    if file:
        orig_name = file.filename or "file"
        suffix = Path(orig_name).suffix
        unique_name = f"{project_id}_{uuid4().hex}{suffix}"
        save_path = SUBMISSION_UPLOAD_DIR / unique_name

        file_bytes = await file.read()
        with open(save_path, "wb") as f:
            f.write(file_bytes)
        
        final_url = f"/static/submissions/{unique_name}"
    
    # 如果沒檔案但有網址（舊版相容）
    elif submission_file_url:
        final_url = submission_file_url
    
    else:
         raise HTTPException(status_code=400, detail="請上傳檔案或提供連結")

    # 寫入資料庫 (crud 裡面會處理版本控制)
    project = crud.submit_project(db, project_id, final_url)
    return project


@router.post("/{project_id}/accept", response_model=schemas.Project)
def accept_project(project_id: int, db: Session = Depends(get_db)):
    """接受結案（委託人）"""
    # 檢查是否有未解決的 Issue (來自 main 分支的邏輯)
    if crud.has_open_issues(db, project_id):
        raise HTTPException(status_code=400, detail="仍有未處理的 issue，無法結案")

    project = crud.accept_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    return project


@router.post("/{project_id}/reject", response_model=schemas.Project)
def reject_project(
    project_id: int,
    rejection: schemas.ProjectReject,
    db: Session = Depends(get_db),
):
    """退件（委託人）"""
    project = crud.reject_project(db, project_id, rejection.rejection_reason)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    return project


@router.get("/{project_id}/submissions")
def get_project_submissions(project_id: int, db: Session = Depends(get_db)):
    """
    取得某專案所有歷史結案版本
    """
    versions = crud.get_submission_versions(db, project_id)
    return [
        {
            "version": v.version,
            "submit_url": v.submit_url,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


# ==================== 提案相關（限時競標 + PDF 上傳） ====================

@router.post("/{project_id}/proposals")
async def create_proposal(
    project_id: int,
    contractor_id: int,
    price: float = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(None), # 允許不傳檔（相容舊版）
    db: Session = Depends(get_db),
):
    """
    提出承包意願（接案人）
    - 如果有上傳 file，則走 PDF 流程 (feature 分支)
    - 如果沒上傳 file，則走簡易流程 (main 分支)
    """
    # 1️⃣ 確認專案存在
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")

    # 2️⃣ 檢查是否仍可投標 (feature 分支邏輯)
    if not crud.is_project_open_for_bidding(project):
        raise HTTPException(status_code=400, detail="此專案已截止或不可投標")

    # 3️⃣ 建立基本 Proposal
    proposal_data = schemas.ProposalCreate(
        project_id=project_id,
        price=price,
        description=description,
    )
    db_proposal = crud.create_proposal(db, proposal_data, contractor_id)

    # 4️⃣ 如果有檔案，處理 PDF 上傳
    if file:
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="僅接受 PDF 檔案")

        # 產生檔名
        ext = ".pdf"
        unique_name = f"{db_proposal.id}_{uuid4().hex}{ext}"
        save_path = PROPOSAL_UPLOAD_DIR / unique_name

        # 寫檔
        file_bytes = await file.read()
        with open(save_path, "wb") as f:
            f.write(file_bytes)

        # 寫入 ProposalFile 記錄
        crud.add_proposal_file(
            db=db,
            proposal_id=db_proposal.id,
            original_filename=file.filename,
            stored_path=str(save_path.relative_to(BASE_DIR)),
        )
        
        return JSONResponse(
            {
                "message": "提案已送出，PDF 已上傳",
                "proposal_id": db_proposal.id,
                "price": price,
                "description": description
            }
        )

    # 如果沒檔案，直接回傳 proposal 物件
    return db_proposal


@router.get("/{project_id}/proposals", response_model=List[schemas.Proposal])
def get_proposals(project_id: int, db: Session = Depends(get_db)):
    """查看專案的所有提案（委託人）"""
    return crud.get_project_proposals(db, project_id)


@router.get("/proposals/{proposal_id}/files")
def get_proposal_files(proposal_id: int, db: Session = Depends(get_db)):
    """
    查看某一提案的所有歷史檔案版本（PDF）
    """
    files = crud.get_proposal_files(db, proposal_id)
    result = []
    for f in files:
        download_url = "/" + str(f.stored_path).replace("\\", "/")
        result.append(
            {
                "id": f.id,
                "version": f.version,
                "original_filename": f.original_filename,
                "uploaded_at": f.uploaded_at,
                "download_url": download_url,
            }
        )
    return result


# ==================== Issue 相關 (來自 main 分支) ====================

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


# ==================== 評價相關 (來自 main 分支) ====================

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