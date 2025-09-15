from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Union
import uuid
from datetime import datetime, timedelta, timezone
import jwt
import bcrypt
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Create the main app without a prefix
app = FastAPI(title="JobLens API", description="Connecting students with recruiters through verified skills")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Enums
class UserRole(str, Enum):
    STUDENT = "student"
    RECRUITER = "recruiter"
    ADMIN = "admin"

class JobType(str, Enum):
    INTERNSHIP = "internship"
    FULLTIME = "fulltime"

class YearLevel(str, Enum):
    FIRST = "1st"
    SECOND = "2nd"
    THIRD = "3rd"
    FINAL = "final"

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    password_hash: str
    role: UserRole
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_verified: bool = False

class Student(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    college: str
    branch: str
    year_of_passout: int
    completed_skills: List[str] = []
    phone: Optional[str] = None
    
class Recruiter(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    company: str
    position: str
    phone: Optional[str] = None
    is_verified: bool = False

class Course(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    price: float = 500.0
    duration: str = "2-3 hours"
    skill_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Job(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    company: str
    location: str
    description: str
    job_type: JobType
    required_skills: List[str] = []
    year_level: Optional[YearLevel] = None  # for internships
    experience_level: Optional[str] = None  # fresher/experienced for fulltime
    salary: Optional[str] = None
    posted_by: str  # recruiter id
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Application(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    job_id: str
    status: str = "applied"
    applied_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Request/Response Models
class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: UserRole

class StudentCreate(BaseModel):
    college: str
    branch: str
    year_of_passout: int
    phone: Optional[str] = None

class RecruiterCreate(BaseModel):
    company: str
    position: str
    phone: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_role: str
    user_id: str

class JobCreate(BaseModel):
    title: str
    company: str
    location: str
    description: str
    job_type: JobType
    required_skills: List[str] = []
    year_level: Optional[YearLevel] = None
    experience_level: Optional[str] = None
    salary: Optional[str] = None

class StudentSearch(BaseModel):
    college: Optional[str] = None
    year_of_passout: Optional[int] = None
    skills: Optional[List[str]] = None

# Utility Functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(user_id: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        role = payload.get("role")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return {"user_id": user_id, "role": role}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

# Routes
@api_router.get("/")
async def root():
    return {"message": "JobLens API - Connecting talent with opportunity"}

# Authentication Routes
@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed_password = hash_password(user_data.password)
    user = User(
        email=user_data.email,
        password_hash=hashed_password,
        role=user_data.role,
        name=user_data.name
    )
    
    await db.users.insert_one(user.dict())
    
    # Create JWT token
    token = create_jwt_token(user.id, user.role.value)
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_role=user.role.value,
        user_id=user.id
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(login_data: LoginRequest):
    # Find user
    user_doc = await db.users.find_one({"email": login_data.email})
    if not user_doc or not verify_password(login_data.password, user_doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user = User(**user_doc)
    token = create_jwt_token(user.id, user.role.value)
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_role=user.role.value,
        user_id=user.id
    )

# Student Routes
@api_router.post("/students/profile")
async def create_student_profile(student_data: StudentCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can create student profiles")
    
    # Check if profile already exists
    existing_profile = await db.students.find_one({"user_id": current_user["user_id"]})
    if existing_profile:
        raise HTTPException(status_code=400, detail="Student profile already exists")
    
    student = Student(
        user_id=current_user["user_id"],
        **student_data.dict()
    )
    
    await db.students.insert_one(student.dict())
    return {"message": "Student profile created successfully"}

@api_router.get("/students/profile")
async def get_student_profile(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Access denied")
    
    student_doc = await db.students.find_one({"user_id": current_user["user_id"]})
    if not student_doc:
        raise HTTPException(status_code=404, detail="Student profile not found")
    
    user_doc = await db.users.find_one({"id": current_user["user_id"]})
    student = Student(**student_doc)
    user = User(**user_doc)
    
    return {
        "id": student.id,
        "name": user.name,
        "email": user.email,
        "college": student.college,
        "branch": student.branch,
        "year_of_passout": student.year_of_passout,
        "completed_skills": student.completed_skills,
        "phone": student.phone
    }

@api_router.post("/students/complete-skill/{skill_name}")
async def complete_skill(skill_name: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update student's completed skills
    result = await db.students.update_one(
        {"user_id": current_user["user_id"]},
        {"$addToSet": {"completed_skills": skill_name}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Student profile not found or skill already completed")
    
    return {"message": f"Skill '{skill_name}' completed successfully"}

# Recruiter Routes
@api_router.post("/recruiters/profile")
async def create_recruiter_profile(recruiter_data: RecruiterCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can create recruiter profiles")
    
    existing_profile = await db.recruiters.find_one({"user_id": current_user["user_id"]})
    if existing_profile:
        raise HTTPException(status_code=400, detail="Recruiter profile already exists")
    
    recruiter = Recruiter(
        user_id=current_user["user_id"],
        **recruiter_data.dict()
    )
    
    await db.recruiters.insert_one(recruiter.dict())
    return {"message": "Recruiter profile created successfully"}

@api_router.get("/recruiters/profile")
async def get_recruiter_profile(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "recruiter":
        raise HTTPException(status_code=403, detail="Access denied")
    
    recruiter_doc = await db.recruiters.find_one({"user_id": current_user["user_id"]})
    if not recruiter_doc:
        raise HTTPException(status_code=404, detail="Recruiter profile not found")
    
    user_doc = await db.users.find_one({"id": current_user["user_id"]})
    recruiter = Recruiter(**recruiter_doc)
    user = User(**user_doc)
    
    return {
        "id": recruiter.id,
        "name": user.name,
        "email": user.email,
        "company": recruiter.company,
        "position": recruiter.position,
        "phone": recruiter.phone,
        "is_verified": recruiter.is_verified
    }

@api_router.post("/recruiters/search-students")
async def search_students(search_data: StudentSearch, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "recruiter":
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Build search query
    query = {}
    if search_data.college:
        query["college"] = {"$regex": search_data.college, "$options": "i"}
    if search_data.year_of_passout:
        query["year_of_passout"] = search_data.year_of_passout
    if search_data.skills:
        query["completed_skills"] = {"$in": search_data.skills}
    
    students = await db.students.find(query).to_list(100)
    
    # Get user details and rank by skills
    result = []
    for student_doc in students:
        user_doc = await db.users.find_one({"id": student_doc["user_id"]})
        if user_doc:
            result.append({
                "id": student_doc["id"],
                "name": user_doc["name"],
                "email": user_doc["email"],
                "college": student_doc["college"],
                "branch": student_doc["branch"],
                "year_of_passout": student_doc["year_of_passout"],
                "completed_skills": student_doc["completed_skills"],
                "skill_count": len(student_doc["completed_skills"])
            })
    
    # Sort by skill count (more skills = higher ranking)
    result.sort(key=lambda x: x["skill_count"], reverse=True)
    return result

# Course Routes
@api_router.get("/courses")
async def get_courses():
    courses = await db.courses.find().to_list(100)
    return [Course(**course) for course in courses]

# Job Routes
@api_router.post("/jobs")
async def create_job(job_data: JobCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["recruiter", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    job = Job(
        posted_by=current_user["user_id"],
        **job_data.dict()
    )
    
    await db.jobs.insert_one(job.dict())
    return {"message": "Job posted successfully", "job_id": job.id}

@api_router.get("/jobs")
async def get_jobs(job_type: Optional[JobType] = None, year_level: Optional[YearLevel] = None, experience_level: Optional[str] = None):
    query = {}
    if job_type:
        query["job_type"] = job_type
    if year_level:
        query["year_level"] = year_level
    if experience_level:
        query["experience_level"] = experience_level
    
    jobs = await db.jobs.find(query).sort("created_at", -1).to_list(100)
    return [Job(**job) for job in jobs]

@api_router.post("/jobs/{job_id}/apply")
async def apply_to_job(job_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can apply to jobs")
    
    # Check if job exists
    job = await db.jobs.find_one({"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if already applied
    existing_application = await db.applications.find_one({"student_id": current_user["user_id"], "job_id": job_id})
    if existing_application:
        raise HTTPException(status_code=400, detail="Already applied to this job")
    
    application = Application(
        student_id=current_user["user_id"],
        job_id=job_id
    )
    
    await db.applications.insert_one(application.dict())
    return {"message": "Application submitted successfully"}

@api_router.get("/students/applications")
async def get_student_applications(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Access denied")
    
    applications = await db.applications.find({"student_id": current_user["user_id"]}).to_list(100)
    
    result = []
    for app in applications:
        job = await db.jobs.find_one({"id": app["job_id"]})
        if job:
            result.append({
                "application_id": app["id"],
                "job_title": job["title"],
                "company": job["company"],
                "location": job["location"],
                "status": app["status"],
                "applied_at": app["applied_at"]
            })
    
    return result

# Initialize default data
@api_router.post("/admin/init-data")
async def initialize_default_data(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Default courses
    default_courses = [
        {"title": "Resume Building", "description": "Learn to create professional resumes that get noticed", "skill_name": "Resume Building"},
        {"title": "Aptitude Prep", "description": "Master quantitative and logical reasoning skills", "skill_name": "Aptitude"},
        {"title": "Python Basics", "description": "Learn Python programming from scratch", "skill_name": "Python"},
        {"title": "SQL Basics", "description": "Master database querying with SQL", "skill_name": "SQL"},
        {"title": "Communication Skills", "description": "Enhance your professional communication abilities", "skill_name": "Communication"}
    ]
    
    for course_data in default_courses:
        existing = await db.courses.find_one({"skill_name": course_data["skill_name"]})
        if not existing:
            course = Course(**course_data)
            await db.courses.insert_one(course.dict())
    
    # Add some default jobs if none exist
    job_count = await db.jobs.count_documents({})
    if job_count == 0:
        default_jobs = [
            {
                "title": "Frontend Developer Intern",
                "company": "TechCorp Inc",
                "location": "Bangalore, India",
                "description": "Build responsive web applications using React and modern frontend technologies",
                "job_type": "internship",
                "required_skills": ["Python", "SQL", "Communication"],
                "year_level": "3rd",
                "salary": "₹15,000/month",
                "posted_by": current_user["user_id"]
            },
            {
                "title": "Software Engineer",
                "company": "StartupXYZ",
                "location": "Mumbai, India", 
                "description": "Full-stack development role working on cutting-edge products",
                "job_type": "fulltime",
                "required_skills": ["Python", "SQL"],
                "experience_level": "fresher",
                "salary": "₹6-8 LPA",
                "posted_by": current_user["user_id"]
            }
        ]
        
        for job_data in default_jobs:
            job = Job(**job_data)
            await db.jobs.insert_one(job.dict())
    
    return {"message": "Default data initialized successfully"}

# Admin Course Management
@api_router.post("/admin/courses")
async def add_course(course_data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    course = Course(**course_data)
    await db.courses.insert_one(course.dict())
    return {"message": "Course added successfully", "course_id": course.id}

@api_router.put("/admin/courses/{course_id}")
async def update_course(course_id: str, course_data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.courses.update_one(
        {"id": course_id},
        {"$set": course_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return {"message": "Course updated successfully"}

@api_router.delete("/admin/courses/{course_id}")
async def delete_course(course_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.courses.delete_one({"id": course_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return {"message": "Course deleted successfully"}

# Admin Job Management
@api_router.delete("/admin/jobs/{job_id}")
async def delete_job(job_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.jobs.delete_one({"id": job_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"message": "Job deleted successfully"}

# Admin User Management
@api_router.get("/admin/users")
async def get_all_users(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = await db.users.find().to_list(1000)
    students = await db.students.find().to_list(1000)
    recruiters = await db.recruiters.find().to_list(1000)
    
    result = {
        "users": [],
        "students": [],
        "recruiters": []
    }
    
    for user in users:
        result["users"].append({
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "created_at": user["created_at"],
            "is_verified": user.get("is_verified", False)
        })
    
    for student in students:
        user_data = next((u for u in users if u["id"] == student["user_id"]), None)
        if user_data:
            result["students"].append({
                "id": student["id"],
                "name": user_data["name"],
                "email": user_data["email"],
                "college": student["college"],
                "branch": student["branch"],
                "year_of_passout": student["year_of_passout"],
                "completed_skills": student["completed_skills"],
                "skill_count": len(student["completed_skills"])
            })
    
    for recruiter in recruiters:
        user_data = next((u for u in users if u["id"] == recruiter["user_id"]), None)
        if user_data:
            result["recruiters"].append({
                "id": recruiter["id"],
                "name": user_data["name"],
                "email": user_data["email"],
                "company": recruiter["company"],
                "position": recruiter["position"],
                "is_verified": recruiter["is_verified"]
            })
    
    return result

@api_router.put("/admin/users/{user_id}/verify")
async def verify_user(user_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Update user verification status
    user_result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_verified": True}}
    )
    
    # Also update recruiter verification if it's a recruiter
    await db.recruiters.update_one(
        {"user_id": user_id},
        {"$set": {"is_verified": True}}
    )
    
    if user_result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User verified successfully"}

# Admin Analytics
@api_router.get("/admin/analytics")
async def get_analytics(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get counts
    total_users = await db.users.count_documents({})
    total_students = await db.students.count_documents({})
    total_recruiters = await db.recruiters.count_documents({})
    total_courses = await db.courses.count_documents({})
    total_jobs = await db.jobs.count_documents({})
    total_applications = await db.applications.count_documents({})
    
    # Get recent activity (mock data for now)
    recent_activity = [
        {"type": "registration", "message": "New student registered", "timestamp": datetime.now(timezone.utc)},
        {"type": "skill", "message": "Course completed: Python Basics", "timestamp": datetime.now(timezone.utc)},
        {"type": "job", "message": "New job posted: Frontend Developer", "timestamp": datetime.now(timezone.utc)}
    ]
    
    return {
        "stats": {
            "total_users": total_users,
            "total_students": total_students,
            "total_recruiters": total_recruiters,
            "total_courses": total_courses,
            "total_jobs": total_jobs,
            "total_applications": total_applications
        },
        "recent_activity": recent_activity
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()