import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'faceid.db'}")

JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))

FACE_DISTANCE_TOLERANCE = float(os.getenv("FACE_DISTANCE_TOLERANCE", "0.38"))
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", str(5 * 1024 * 1024)))
