from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# 載入 .env 檔案
load_dotenv()

# 從環境變數讀取資料庫連線字串
DATABASE_URL = os.getenv("DATABASE_URL")

# 建立資料庫引擎
engine = create_engine(DATABASE_URL)

# 建立 Session 類別
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 建立 Base 類別（所有 model 都會繼承這個）
Base = declarative_base()

# 取得資料庫連線的函式（依賴注入用）
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()