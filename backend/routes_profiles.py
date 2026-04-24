import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db, CompanyProfile, JobPost, SeekerProfile, User
from auth import get_current_user

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
MAX_CV_SIZE = 500 * 1024 * 1024  # 500 MB

router = APIRouter(prefix="/profiles", tags=["profiles"])


class CompanyProfileIn(BaseModel):
    name: str
    industry: Optional[str] = None
    description: Optional[str] = None


class JobPostIn(BaseModel):
    title: str
    description: Optional[str] = None
    required_skills: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None


class SeekerProfileIn(BaseModel):
    full_name: str
    title: Optional[str] = None
    bio: Optional[str] = None
    skills: Optional[str] = None
    experience_years: Optional[int] = None
    location: Optional[str] = None
    desired_role: Optional[str] = None
    education: Optional[str] = None


# ---- Company profile (one per company) ----

@router.post("/company")
def upsert_company(body: CompanyProfileIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "company":
        raise HTTPException(status_code=403, detail="Only companies can set company profiles")
    profile = db.query(CompanyProfile).filter(CompanyProfile.user_id == user.id).first()
    if profile:
        for k, v in body.dict().items():
            setattr(profile, k, v)
    else:
        profile = CompanyProfile(user_id=user.id, **body.dict())
        db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


# ---- Job posts (many per company) ----

@router.get("/company/posts")
def list_posts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "company":
        raise HTTPException(status_code=403, detail="Companies only")
    return db.query(JobPost).filter(JobPost.user_id == user.id).order_by(JobPost.created_at.desc()).all()


@router.post("/company/posts")
def create_post(body: JobPostIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "company":
        raise HTTPException(status_code=403, detail="Companies only")
    post = JobPost(user_id=user.id, **body.dict())
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.put("/company/posts/{post_id}")
def update_post(post_id: int, body: JobPostIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    post = db.query(JobPost).filter(JobPost.id == post_id, JobPost.user_id == user.id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    for k, v in body.dict().items():
        setattr(post, k, v)
    db.commit()
    db.refresh(post)
    return post


@router.delete("/company/posts/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    post = db.query(JobPost).filter(JobPost.id == post_id, JobPost.user_id == user.id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(post)
    db.commit()
    return {"ok": True}


# ---- Seeker profile ----

@router.post("/seeker")
def upsert_seeker(body: SeekerProfileIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "seeker":
        raise HTTPException(status_code=403, detail="Only seekers can set seeker profiles")
    profile = db.query(SeekerProfile).filter(SeekerProfile.user_id == user.id).first()
    if profile:
        for k, v in body.dict().items():
            setattr(profile, k, v)
    else:
        profile = SeekerProfile(user_id=user.id, **body.dict())
        db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/me")
def get_my_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == "company":
        return db.query(CompanyProfile).filter(CompanyProfile.user_id == user.id).first()
    return db.query(SeekerProfile).filter(SeekerProfile.user_id == user.id).first()


@router.post("/seeker/cv")
async def upload_cv(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "seeker":
        raise HTTPException(status_code=403, detail="Only seekers can upload a CV")
    # read in chunks to enforce size limit without loading everything into memory
    contents = b""
    while chunk := await file.read(1024 * 1024):
        contents += chunk
        if len(contents) > MAX_CV_SIZE:
            raise HTTPException(status_code=413, detail="CV file exceeds 500 MB limit")
    ext = os.path.splitext(file.filename or "")[1].lower() or ".pdf"
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(contents)
    profile = db.query(SeekerProfile).filter(SeekerProfile.user_id == user.id).first()
    if not profile:
        # auto-create a minimal profile so CV can be attached before the form is filled
        profile = SeekerProfile(user_id=user.id, full_name="")
        db.add(profile)
        db.flush()
    # delete old CV file if present
    if profile.cv_filename:
        old = os.path.join(UPLOAD_DIR, profile.cv_filename)
        if os.path.exists(old):
            os.remove(old)
    profile.cv_filename = filename
    db.commit()
    return {"filename": filename}


@router.get("/seeker/{user_id}/cv")
def download_cv(user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # seeker can download their own; companies can download any seeker's CV
    if user.role == "seeker" and user.id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    profile = db.query(SeekerProfile).filter(SeekerProfile.user_id == user_id).first()
    if not profile or not profile.cv_filename:
        raise HTTPException(status_code=404, detail="No CV uploaded")
    path = os.path.join(UPLOAD_DIR, profile.cv_filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="CV file not found")
    display_name = f"{profile.full_name.replace(' ', '_')}_CV{os.path.splitext(profile.cv_filename)[1]}"
    return FileResponse(path, filename=display_name, media_type="application/octet-stream")
