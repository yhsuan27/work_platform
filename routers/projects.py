# routers/projects.py
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
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


# ==================== 專案相關 ====================

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
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
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

    orig_name = file.filename or "file"
    suffix = Path(orig_name).suffix
    unique_name = f"{project_id}_{uuid4().hex}{suffix}"
    save_path = SUBMISSION_UPLOAD_DIR / unique_name

    file_bytes = await file.read()
    with open(save_path, "wb") as f:
        f.write(file_bytes)

    submit_url = f"/static/submissions/{unique_name}"

    project = crud.submit_project(db, project_id, submit_url)
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
    db: Session = Depends(get_db),
):
    """退件（委託人）"""
    project = crud.reject_project(db, project_id, rejection.rejection_reason)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")
    return project


@router.get("/{project_id}/submission-files")
def get_submission_files(project_id: int, db: Session = Depends(get_db)):
    """
    舊需求：查看某專案所有結案版本（網址）
    如果之後沒用到，可以不呼叫這支 API
    """
    files = crud.get_submission_files(db, project_id)
    return [
        {
            "id": f.id,
            "version": f.version,
            "file_url": f.file_url,
            "uploaded_at": f.uploaded_at,
        }
        for f in files
    ]


# ==================== 提案相關（限時競標 + PDF 上傳） ====================

@router.post("/{project_id}/proposals")
async def create_proposal(
    project_id: int,
    contractor_id: int,
    price: float = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    提出承包意願（接案人）
    1. 檢查專案是否還在截止時間內（限時競標）
    2. 必須上傳 PDF 檔案
    3. 檔名做處理，不覆蓋舊檔（用 uuid 產生唯一檔名）
    4. 檔案版本寫入 ProposalFile
    """
    # 1️⃣ 確認專案存在
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="專案不存在")

    # 2️⃣ 檢查是否仍可投標
    if not crud.is_project_open_for_bidding(project):
        raise HTTPException(status_code=400, detail="此專案已截止或不可投標")

    # 3️⃣ 檢查檔案格式（只能 pdf）
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="僅接受 PDF 檔案")

    # 4️⃣ 先建立 Proposal（不含檔案）
    proposal_data = schemas.ProposalCreate(
        project_id=project_id,
        price=price,
        description=description,
    )
    db_proposal = crud.create_proposal(db, proposal_data, contractor_id)

    # 5️⃣ 產生不會重複的檔名
    ext = ".pdf"
    unique_name = f"{db_proposal.id}_{uuid4().hex}{ext}"
    save_path = PROPOSAL_UPLOAD_DIR / unique_name

    # 6️⃣ 實際寫檔
    file_bytes = await file.read()
    with open(save_path, "wb") as f:
        f.write(file_bytes)

    # 7️⃣ 建立 ProposalFile 記錄
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
        }
    )


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


@router.get("/{project_id}/submissions")
def get_project_submissions(project_id: int, db: Session = Depends(get_db)):
    """
    取得某專案所有歷史結案版本
    回傳格式：
    [
      {"version": 1, "submit_url": "...", "created_at": "..."},
      ...
    ]
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
