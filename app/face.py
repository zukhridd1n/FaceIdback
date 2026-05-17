import json
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
from fastapi import HTTPException, UploadFile, status

from app.config import FACE_DISTANCE_TOLERANCE, MAX_UPLOAD_SIZE, UPLOAD_DIR


ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
FACE_SIZE = (128, 128)


async def save_upload(file: UploadFile) -> Path:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rasm formati JPG, PNG yoki WEBP bo'lishi kerak.",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rasm hajmi 5MB dan oshmasligi kerak.",
        )

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / f"{uuid4().hex}{suffix}"
    path.write_bytes(content)
    return path


def extract_face_encoding(image_path: Path) -> list[float]:
    image_bytes = np.frombuffer(image_path.read_bytes(), dtype=np.uint8)
    image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rasmni o'qib bo'lmadi.",
        )

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    detector = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80),
    )

    if len(faces) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rasmda yuz topilmadi.",
        )

    if len(faces) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rasmda faqat bitta yuz bo'lishi kerak.",
        )

    x, y, w, h = faces[0]
    face = gray[y : y + h, x : x + w]
    face = cv2.resize(face, FACE_SIZE)
    face = cv2.equalizeHist(face)
    face = face.astype(np.float32) / 255.0
    face = (face - float(face.mean())) / (float(face.std()) + 1e-6)
    return face.flatten().tolist()


def encode_face_json(encoding: list[float]) -> str:
    return json.dumps(encoding)


def decode_face_json(value: str) -> list[float]:
    return json.loads(value)


def is_same_face(known_encoding: list[float], candidate_encoding: list[float]) -> tuple[bool, float]:
    known = np.asarray(known_encoding, dtype=np.float32)
    candidate = np.asarray(candidate_encoding, dtype=np.float32)
    denominator = float(np.linalg.norm(known) * np.linalg.norm(candidate))
    if denominator == 0:
        return False, 1.0

    similarity = float(np.dot(known, candidate) / denominator)
    distance = 1.0 - similarity
    return bool(distance <= FACE_DISTANCE_TOLERANCE), float(distance)
