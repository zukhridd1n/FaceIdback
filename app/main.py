from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.db import Base, engine, get_db
from app.face import (
    decode_face_json,
    encode_face_json,
    extract_face_encoding,
    is_same_face,
    save_upload,
)
from app.models import User
from app.schemas import AuthResponse, FaceVerifyResponse, MessageResponse, UserOut
from app.security import create_access_token, decode_access_token, hash_password, verify_password


Base.metadata.create_all(bind=engine)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Face ID Auth API",
    openapi_tags=[
        {"name": "Register", "description": "Yangi foydalanuvchini rasm bilan ro'yxatdan o'tkazish."},
        {"name": "Login Password", "description": "Telefon raqam va parol orqali login."},
        {"name": "Login Face ID", "description": "Rasm orqali Face ID login."},
        {"name": "Face Verify", "description": "Berilgan user rasmi bilan yangi rasm mosligini tekshirish."},
        {"name": "JWT", "description": "Bearer JWT token orqali himoyalangan endpointlar."},
        {"name": "Profile CRUD", "description": "JWT token orqali profilni ko'rish, yangilash va o'chirish."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
bearer_scheme = HTTPBearer()


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        name=user.name,
        phone=user.phone,
        image_url=f"/uploads/{Path(user.image_path).name}",
        created_at=user.created_at,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    user_id = decode_access_token(credentials.credentials)
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token egasi topilmadi.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def similarity_percent(distance: float) -> float:
    percent = max(0.0, min(100.0, (1.0 - distance) * 100.0))
    return round(percent, 2)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post(
    "/api/auth/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Register"],
    summary="Registratsiya",
)
async def register(
    name: str = Form(..., min_length=2, max_length=100),
    phone: str = Form(..., min_length=5, max_length=32),
    password: str = Form(..., min_length=6, max_length=128),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    existing_user = db.query(User).filter(User.phone == phone).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu telefon raqam oldin ro'yxatdan o'tgan.",
        )

    image_path = await save_upload(image)
    face_encoding = extract_face_encoding(image_path)

    user = User(
        name=name.strip(),
        phone=phone.strip(),
        password_hash=hash_password(password),
        face_encoding=encode_face_json(face_encoding),
        image_path=str(image_path),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return AuthResponse(access_token=create_access_token(user.id), user=user_out(user))


@app.post(
    "/api/auth/login/password",
    response_model=AuthResponse,
    tags=["Login Password"],
    summary="Telefon raqam va parol bilan login",
)
async def login_with_password(
    phone: str = Form(..., min_length=5, max_length=32),
    password: str = Form(..., min_length=6, max_length=128),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.phone == phone.strip()).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telefon raqam yoki parol noto'g'ri.",
        )

    return AuthResponse(access_token=create_access_token(user.id), user=user_out(user))


@app.post(
    "/api/auth/login/face",
    response_model=AuthResponse,
    tags=["Login Face ID"],
    summary="Face ID bilan login",
)
async def login_with_face(
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    login_image_path = await save_upload(image)
    candidate_encoding = extract_face_encoding(login_image_path)

    best_user: User | None = None
    best_distance: float | None = None

    users = db.query(User).all()
    for user in users:
        matched, distance = is_same_face(decode_face_json(user.face_encoding), candidate_encoding)
        if matched and (best_distance is None or distance < best_distance):
            best_user = user
            best_distance = distance

    if best_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Face ID mos kelmadi.",
        )

    return AuthResponse(access_token=create_access_token(best_user.id), user=user_out(best_user))


@app.post(
    "/api/face/verify",
    response_model=FaceVerifyResponse,
    tags=["Face Verify"],
    summary="Face ID mosligini tekshirish",
)
async def verify_face(
    user_id: int = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foydalanuvchi topilmadi.",
        )

    image_path = await save_upload(image)
    candidate_encoding = extract_face_encoding(image_path)
    matched, distance = is_same_face(decode_face_json(user.face_encoding), candidate_encoding)

    return FaceVerifyResponse(
        user_id=user.id,
        matched=matched,
        distance=distance,
        similarity_percent=similarity_percent(distance),
    )


@app.get(
    "/api/auth/me",
    response_model=UserOut,
    tags=["JWT"],
    summary="JWT token orqali profilni olish",
)
def me(current_user: User = Depends(get_current_user)):
    return user_out(current_user)


@app.get(
    "/api/profile",
    response_model=UserOut,
    tags=["Profile CRUD"],
    summary="Profilni olish",
)
def get_profile(current_user: User = Depends(get_current_user)):
    return user_out(current_user)


@app.patch(
    "/api/profile",
    response_model=UserOut,
    tags=["Profile CRUD"],
    summary="Profilni yangilash",
)
async def update_profile(
    name: str | None = Form(None, min_length=2, max_length=100),
    phone: str | None = Form(None, min_length=5, max_length=32),
    password: str | None = Form(None, min_length=6, max_length=128),
    image: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if phone is not None:
        clean_phone = phone.strip()
        existing_user = (
            db.query(User)
            .filter(User.phone == clean_phone, User.id != current_user.id)
            .first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu telefon raqam boshqa foydalanuvchida bor.",
            )
        current_user.phone = clean_phone

    if name is not None:
        current_user.name = name.strip()

    if password is not None:
        current_user.password_hash = hash_password(password)

    if image is not None:
        image_path = await save_upload(image)
        face_encoding = extract_face_encoding(image_path)
        current_user.image_path = str(image_path)
        current_user.face_encoding = encode_face_json(face_encoding)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return user_out(current_user)


@app.delete(
    "/api/profile",
    response_model=MessageResponse,
    tags=["Profile CRUD"],
    summary="Profilni o'chirish",
)
def delete_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    image_path = Path(current_user.image_path)
    db.delete(current_user)
    db.commit()

    if image_path.exists():
        image_path.unlink(missing_ok=True)

    return MessageResponse(message="Profil o'chirildi.")
