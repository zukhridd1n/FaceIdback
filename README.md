# Face ID Auth API

FastAPI backend: registratsiya vaqtida ism, telefon raqam, parol va rasm qabul qiladi. Login telefon raqam, parol va yangi rasm orqali bo'ladi. Yangi rasm registratsiyada saqlangan yuz vektori bilan solishtiriladi.

## Ishga tushirish

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API hujjatlari:

```text
http://127.0.0.1:8000/docs
```

## Docker bilan ishga tushirish

Docker Compose orqali:

```bash
docker compose up --build
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

To'xtatish:

```bash
docker compose down
```

Ma'lumotlar `faceid-data` Docker volume ichida saqlanadi. JWT secretni productionda o'zgartiring:

```bash
JWT_SECRET=strong-secret docker compose up --build
```

## Endpointlar

### Registratsiya

`POST /api/auth/register`

`multipart/form-data`:

- `name`
- `phone`
- `password`
- `image`

Rasm `JPG` yoki `PNG` bo'lishi kerak va unda bitta yuz aniq ko'rinishi kerak.

### Login: telefon raqam va parol

`POST /api/auth/login/password`

`multipart/form-data`:

- `phone`
- `password`

### Login: Face ID

`POST /api/auth/login/face`

`multipart/form-data`:

- `image`

### Face ID mosligini tekshirish

`POST /api/face/verify`

`multipart/form-data`:

- `user_id`
- `image`

Javob:

```json
{
  "user_id": 1,
  "matched": true,
  "distance": 0.21,
  "similarity_percent": 79.0
}
```

Uchala auth endpoint ham muvaffaqiyatli javobda `access_token` va `user` qaytaradi.

Eslatma: bu lokal OpenCV asosidagi Face ID tekshiruvi. Bank yoki yuqori xavfsizlik talab qiladigan tizimlarda ArcFace/InsightFace kabi model yoki maxsus biometrik servis ishlatish kerak.

## Profile CRUD

Bu endpointlar `Authorization: Bearer <token>` bilan ishlaydi.

### Profilni olish

`GET /api/profile`

### Profilni yangilash

`PATCH /api/profile`

`multipart/form-data` ichida quyidagilar ixtiyoriy:

- `name`
- `phone`
- `password`
- `image`

`image` yuborilsa, foydalanuvchining Face ID rasmi ham yangilanadi.

### Profilni o'chirish

`DELETE /api/profile`
