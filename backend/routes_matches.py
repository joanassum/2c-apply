from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, CompanyProfile, JobPost, SeekerProfile, Match, User
from auth import get_current_user

router = APIRouter(prefix="/matches", tags=["matches"])


@router.post("/run")
def run_matching(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from matching import match_post_to_seekers, match_seeker_to_posts

    if user.role == "company":
        posts = db.query(JobPost).filter(JobPost.user_id == user.id).all()
        if not posts:
            raise HTTPException(status_code=400, detail="Create at least one job post first")
        seekers = db.query(SeekerProfile).all()
        if not seekers:
            raise HTTPException(status_code=400, detail="No job seekers registered yet")
        company = db.query(CompanyProfile).filter(CompanyProfile.user_id == user.id).first()
        company_name = company.name if company else "Company"
        total = 0
        for post in posts:
            results = match_post_to_seekers(post, company_name, seekers)
            db.query(Match).filter(Match.job_post_id == post.id).delete()
            for r in results:
                db.add(Match(job_post_id=post.id, seeker_user_id=r["seeker_user_id"],
                             score=r["score"], reasoning=r["reasoning"]))
            total += len(results)
        db.commit()
        return {"matched": total}

    else:
        seeker = db.query(SeekerProfile).filter(SeekerProfile.user_id == user.id).first()
        if not seeker:
            raise HTTPException(status_code=400, detail="Complete your profile first")
        posts = db.query(JobPost).all()
        if not posts:
            raise HTTPException(status_code=400, detail="No job posts available yet")
        company_names = {}
        for post in posts:
            cp = db.query(CompanyProfile).filter(CompanyProfile.user_id == post.user_id).first()
            company_names[post.id] = cp.name if cp else "Unknown"
        posts_with_company = [(p, company_names[p.id]) for p in posts]
        results = match_seeker_to_posts(seeker, posts_with_company)
        # clear old matches for this seeker
        old_post_ids = [p.id for p in posts]
        db.query(Match).filter(
            Match.seeker_user_id == user.id,
            Match.job_post_id.in_(old_post_ids)
        ).delete(synchronize_session=False)
        for r in results:
            db.add(Match(job_post_id=r["job_post_id"], seeker_user_id=user.id,
                         score=r["score"], reasoning=r["reasoning"]))
        db.commit()
        return {"matched": len(results)}


@router.get("/")
def get_matches(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == "company":
        posts = db.query(JobPost).filter(JobPost.user_id == user.id).all()
        result = []
        for post in posts:
            matches = db.query(Match).filter(Match.job_post_id == post.id).order_by(Match.score.desc()).all()
            for m in matches:
                seeker = db.query(SeekerProfile).filter(SeekerProfile.user_id == m.seeker_user_id).first()
                result.append({
                    "match_id": m.id,
                    "score": m.score,
                    "reasoning": m.reasoning,
                    "job_post": {"id": post.id, "title": post.title},
                    "seeker": {
                        "user_id": m.seeker_user_id,
                        "full_name": seeker.full_name if seeker else "Unknown",
                        "title": seeker.title if seeker else "",
                        "skills": seeker.skills if seeker else "",
                        "location": seeker.location if seeker else "",
                        "experience_years": seeker.experience_years if seeker else 0,
                        "desired_role": seeker.desired_role if seeker else "",
                        "cv_filename": seeker.cv_filename if seeker else None,
                    }
                })
        result.sort(key=lambda x: x["score"], reverse=True)
        return result

    else:
        matches = db.query(Match).filter(Match.seeker_user_id == user.id).order_by(Match.score.desc()).all()
        result = []
        for m in matches:
            post = db.query(JobPost).filter(JobPost.id == m.job_post_id).first()
            if not post:
                continue
            company = db.query(CompanyProfile).filter(CompanyProfile.user_id == post.user_id).first()
            result.append({
                "match_id": m.id,
                "score": m.score,
                "reasoning": m.reasoning,
                "company": {
                    "user_id": post.user_id,
                    "name": company.name if company else "Unknown",
                    "industry": company.industry if company else "",
                    "job_title": post.title,
                    "location": post.location or "",
                    "salary_range": post.salary_range or "",
                    "job_description": post.description or "",
                }
            })
        return result
