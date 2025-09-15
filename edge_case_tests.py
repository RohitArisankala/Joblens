#!/usr/bin/env python3
"""
JobLens Backend Edge Case Tests
Tests edge cases and error conditions
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')

BASE_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://joblens.preview.emergentagent.com')
API_URL = f"{BASE_URL}/api"

def test_duplicate_registration():
    """Test duplicate email registration"""
    user_data = {
        "email": "duplicate@test.com",
        "password": "TestPass123!",
        "name": "Test User",
        "role": "student"
    }
    
    # First registration
    response1 = requests.post(f"{API_URL}/auth/register", json=user_data)
    print(f"First registration: {response1.status_code}")
    
    # Duplicate registration
    response2 = requests.post(f"{API_URL}/auth/register", json=user_data)
    print(f"Duplicate registration: {response2.status_code}")
    
    if response2.status_code == 400:
        print("✅ PASS: Duplicate registration correctly rejected")
    else:
        print(f"❌ FAIL: Expected 400, got {response2.status_code}")

def test_duplicate_profile_creation():
    """Test duplicate profile creation"""
    # Register and login as student
    user_data = {
        "email": "profile.test@university.edu",
        "password": "TestPass123!",
        "name": "Profile Test",
        "role": "student"
    }
    
    reg_response = requests.post(f"{API_URL}/auth/register", json=user_data)
    if reg_response.status_code != 200:
        print("❌ FAIL: Could not register user for profile test")
        return
    
    token = reg_response.json()['access_token']
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    profile_data = {
        "college": "Test University",
        "branch": "Computer Science",
        "year_of_passout": 2025
    }
    
    # First profile creation
    response1 = requests.post(f"{API_URL}/students/profile", json=profile_data, headers=headers)
    print(f"First profile creation: {response1.status_code}")
    
    # Duplicate profile creation
    response2 = requests.post(f"{API_URL}/students/profile", json=profile_data, headers=headers)
    print(f"Duplicate profile creation: {response2.status_code}")
    
    if response2.status_code == 400:
        print("✅ PASS: Duplicate profile creation correctly rejected")
    else:
        print(f"❌ FAIL: Expected 400, got {response2.status_code}")

def test_duplicate_job_application():
    """Test duplicate job application"""
    # Register student and recruiter
    student_data = {
        "email": "job.student@university.edu",
        "password": "TestPass123!",
        "name": "Job Student",
        "role": "student"
    }
    
    recruiter_data = {
        "email": "job.recruiter@company.com",
        "password": "TestPass123!",
        "name": "Job Recruiter",
        "role": "recruiter"
    }
    
    # Register users
    student_reg = requests.post(f"{API_URL}/auth/register", json=student_data)
    recruiter_reg = requests.post(f"{API_URL}/auth/register", json=recruiter_data)
    
    if student_reg.status_code != 200 or recruiter_reg.status_code != 200:
        print("❌ FAIL: Could not register users for job application test")
        return
    
    student_token = student_reg.json()['access_token']
    recruiter_token = recruiter_reg.json()['access_token']
    
    student_headers = {'Authorization': f'Bearer {student_token}', 'Content-Type': 'application/json'}
    recruiter_headers = {'Authorization': f'Bearer {recruiter_token}', 'Content-Type': 'application/json'}
    
    # Create student profile
    profile_data = {
        "college": "Test University",
        "branch": "Computer Science", 
        "year_of_passout": 2025
    }
    requests.post(f"{API_URL}/students/profile", json=profile_data, headers=student_headers)
    
    # Create recruiter profile
    recruiter_profile = {
        "company": "Test Company",
        "position": "Recruiter"
    }
    requests.post(f"{API_URL}/recruiters/profile", json=recruiter_profile, headers=recruiter_headers)
    
    # Post a job
    job_data = {
        "title": "Test Job",
        "company": "Test Company",
        "location": "Test Location",
        "description": "Test Description",
        "job_type": "internship",
        "required_skills": ["Python"],
        "year_level": "3rd"
    }
    
    job_response = requests.post(f"{API_URL}/jobs", json=job_data, headers=recruiter_headers)
    if job_response.status_code != 200:
        print("❌ FAIL: Could not create job for application test")
        return
    
    job_id = job_response.json()['job_id']
    
    # First application
    response1 = requests.post(f"{API_URL}/jobs/{job_id}/apply", headers=student_headers)
    print(f"First job application: {response1.status_code}")
    
    # Duplicate application
    response2 = requests.post(f"{API_URL}/jobs/{job_id}/apply", headers=student_headers)
    print(f"Duplicate job application: {response2.status_code}")
    
    if response2.status_code == 400:
        print("✅ PASS: Duplicate job application correctly rejected")
    else:
        print(f"❌ FAIL: Expected 400, got {response2.status_code}")

def test_nonexistent_job_application():
    """Test applying to non-existent job"""
    # Use existing student token from previous tests
    user_data = {
        "email": "nonexist.student@university.edu",
        "password": "TestPass123!",
        "name": "Nonexist Student",
        "role": "student"
    }
    
    reg_response = requests.post(f"{API_URL}/auth/register", json=user_data)
    if reg_response.status_code != 200:
        print("❌ FAIL: Could not register user for nonexistent job test")
        return
    
    token = reg_response.json()['access_token']
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    # Create student profile
    profile_data = {
        "college": "Test University",
        "branch": "Computer Science",
        "year_of_passout": 2025
    }
    requests.post(f"{API_URL}/students/profile", json=profile_data, headers=headers)
    
    # Apply to non-existent job
    fake_job_id = "00000000-0000-0000-0000-000000000000"
    response = requests.post(f"{API_URL}/jobs/{fake_job_id}/apply", headers=headers)
    
    print(f"Apply to nonexistent job: {response.status_code}")
    
    if response.status_code == 404:
        print("✅ PASS: Nonexistent job application correctly rejected")
    else:
        print(f"❌ FAIL: Expected 404, got {response.status_code}")

if __name__ == "__main__":
    print("🧪 Running Edge Case Tests")
    print("=" * 30)
    
    test_duplicate_registration()
    print()
    test_duplicate_profile_creation()
    print()
    test_duplicate_job_application()
    print()
    test_nonexistent_job_application()
    
    print("\n" + "=" * 30)
    print("Edge case tests completed!")