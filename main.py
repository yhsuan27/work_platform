from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import engine, Base
import models
from routers import auth, projects  # 移除 communications

# 建立所有資料表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="工作委託平台 API",
    description="支援委託人發案與接案人承接的平台",
    version="1.0.0"
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載靜態檔案
app.mount("/static", StaticFiles(directory="static"), name="static")

# 引入路由
app.include_router(auth.router)
app.include_router(projects.router)
# app.include_router(communications.router)  # 註解掉或刪除

@app.get("/")
def root():
    return {
        "message": "工作委託平台 API 運作正常！",
        "web_ui": "http://127.0.0.1:8080/static/index.html",
        "docs": "http://127.0.0.1:8080/docs",
        "功能": {
            "身份驗證": "/auth",
            "專案管理": "/projects"
        }
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "database": "connected"}