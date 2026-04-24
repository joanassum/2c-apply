from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///./jobsite.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "company" or "seeker"
    created_at = Column(DateTime, default=datetime.utcnow)

    company_profile = relationship("CompanyProfile", back_populates="user", uselist=False)
    job_posts = relationship("JobPost", back_populates="user")
    seeker_profile = relationship("SeekerProfile", back_populates="user", uselist=False)


class CompanyProfile(Base):
    __tablename__ = "company_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    name = Column(String, nullable=False)
    industry = Column(String)
    description = Column(Text)

    user = relationship("User", back_populates="company_profile")


class JobPost(Base):
    __tablename__ = "job_posts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    required_skills = Column(Text)
    location = Column(String)
    salary_range = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="job_posts")
    matches = relationship("Match", back_populates="job_post", cascade="all, delete-orphan")


class SeekerProfile(Base):
    __tablename__ = "seeker_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    full_name = Column(String, nullable=False)
    title = Column(String)
    bio = Column(Text)
    skills = Column(Text)
    experience_years = Column(Integer)
    location = Column(String)
    desired_role = Column(Text)
    education = Column(String)
    cv_filename = Column(String, nullable=True)

    user = relationship("User", back_populates="seeker_profile")


class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True, index=True)
    job_post_id = Column(Integer, ForeignKey("job_posts.id"), nullable=False)
    seeker_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    score = Column(Float)
    reasoning = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    job_post = relationship("JobPost", back_populates="matches")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
