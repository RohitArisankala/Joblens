#!/usr/bin/env python3
"""
JobLens Backend API Testing Suite
Tests all backend APIs comprehensively including authentication, user management, 
student/recruiter profiles, courses, jobs, and applications.
"""

import requests
import json
import time
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')

# Configuration
BASE_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://joblens.preview.emergentagent.com')
API_URL = f"{BASE_URL}/api"

class JobLensAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.tokens = {}  # Store tokens for different users
        self.users = {}   # Store user data
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, message: str, details: Any = None):
        """Log test results"""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'details': details
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def make_request(self, method: str, endpoint: str, data: Dict = None, token: str = None) -> requests.Response:
        """Make HTTP request with optional authentication"""
        url = f"{API_URL}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'
            
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers, params=data)
            elif method.upper() == 'POST':
                response = self.session.post(url, headers=headers, json=data)
            elif method.upper() == 'PUT':
                response = self.session.put(url, headers=headers, json=data)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            return response
        except Exception as e:
            print(f"Request failed: {e}")
            raise
    
    def test_api_health(self):
        """Test if API is accessible"""
        try:
            response = self.make_request('GET', '/')
            if response.status_code == 200:
                self.log_test("API Health Check", True, "API is accessible")
                return True
            else:
                self.log_test("API Health Check", False, f"API returned status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("API Health Check", False, f"API not accessible: {str(e)}")
            return False
    
    def test_user_registration(self):
        """Test user registration for different roles"""
        test_users = [
            {
                "email": "alice.student@university.edu",
                "password": "SecurePass123!",
                "name": "Alice Johnson",
                "role": "student"
            },
            {
                "email": "bob.recruiter@techcorp.com", 
                "password": "RecruiterPass456!",
                "name": "Bob Smith",
                "role": "recruiter"
            },
            {
                "email": "admin@joblens.com",
                "password": "AdminPass789!",
                "name": "Admin User",
                "role": "admin"
            }
        ]
        
        for user_data in test_users:
            try:
                response = self.make_request('POST', '/auth/register', user_data)
                
                if response.status_code == 200:
                    data = response.json()
                    if all(key in data for key in ['access_token', 'user_role', 'user_id']):
                        self.tokens[user_data['role']] = data['access_token']
                        self.users[user_data['role']] = {
                            'user_id': data['user_id'],
                            'email': user_data['email'],
                            'name': user_data['name']
                        }
                        self.log_test(f"User Registration ({user_data['role']})", True, 
                                    f"Successfully registered {user_data['name']}")
                    else:
                        self.log_test(f"User Registration ({user_data['role']})", False, 
                                    "Missing required fields in response", data)
                else:
                    self.log_test(f"User Registration ({user_data['role']})", False, 
                                f"Registration failed with status {response.status_code}", 
                                response.text)
            except Exception as e:
                self.log_test(f"User Registration ({user_data['role']})", False, 
                            f"Registration error: {str(e)}")
    
    def test_user_login(self):
        """Test user login functionality"""
        login_data = [
            {"email": "alice.student@university.edu", "password": "SecurePass123!", "role": "student"},
            {"email": "bob.recruiter@techcorp.com", "password": "RecruiterPass456!", "role": "recruiter"}
        ]
        
        for login in login_data:
            try:
                response = self.make_request('POST', '/auth/login', {
                    'email': login['email'],
                    'password': login['password']
                })
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('user_role') == login['role']:
                        self.log_test(f"User Login ({login['role']})", True, 
                                    f"Successfully logged in as {login['role']}")
                    else:
                        self.log_test(f"User Login ({login['role']})", False, 
                                    f"Role mismatch: expected {login['role']}, got {data.get('user_role')}")
                else:
                    self.log_test(f"User Login ({login['role']})", False, 
                                f"Login failed with status {response.status_code}", response.text)
            except Exception as e:
                self.log_test(f"User Login ({login['role']})", False, f"Login error: {str(e)}")
    
    def test_invalid_login(self):
        """Test login with invalid credentials"""
        try:
            response = self.make_request('POST', '/auth/login', {
                'email': 'nonexistent@test.com',
                'password': 'wrongpassword'
            })
            
            if response.status_code == 401:
                self.log_test("Invalid Login Test", True, "Correctly rejected invalid credentials")
            else:
                self.log_test("Invalid Login Test", False, 
                            f"Expected 401, got {response.status_code}")
        except Exception as e:
            self.log_test("Invalid Login Test", False, f"Error: {str(e)}")
    
    def test_student_profile_creation(self):
        """Test student profile creation"""
        if 'student' not in self.tokens:
            self.log_test("Student Profile Creation", False, "No student token available")
            return
            
        profile_data = {
            "college": "Stanford University",
            "branch": "Computer Science",
            "year_of_passout": 2025,
            "phone": "+1-555-0123"
        }
        
        try:
            response = self.make_request('POST', '/students/profile', 
                                      profile_data, self.tokens['student'])
            
            if response.status_code == 200:
                self.log_test("Student Profile Creation", True, "Student profile created successfully")
            else:
                self.log_test("Student Profile Creation", False, 
                            f"Profile creation failed with status {response.status_code}", 
                            response.text)
        except Exception as e:
            self.log_test("Student Profile Creation", False, f"Error: {str(e)}")
    
    def test_student_profile_retrieval(self):
        """Test student profile retrieval"""
        if 'student' not in self.tokens:
            self.log_test("Student Profile Retrieval", False, "No student token available")
            return
            
        try:
            response = self.make_request('GET', '/students/profile', 
                                      token=self.tokens['student'])
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['name', 'email', 'college', 'branch', 'year_of_passout']
                if all(field in data for field in required_fields):
                    self.log_test("Student Profile Retrieval", True, 
                                "Successfully retrieved student profile")
                else:
                    missing = [f for f in required_fields if f not in data]
                    self.log_test("Student Profile Retrieval", False, 
                                f"Missing fields: {missing}", data)
            else:
                self.log_test("Student Profile Retrieval", False, 
                            f"Profile retrieval failed with status {response.status_code}", 
                            response.text)
        except Exception as e:
            self.log_test("Student Profile Retrieval", False, f"Error: {str(e)}")
    
    def test_skill_completion(self):
        """Test skill completion functionality"""
        if 'student' not in self.tokens:
            self.log_test("Skill Completion", False, "No student token available")
            return
            
        skills_to_complete = ["Python", "SQL", "Communication"]
        
        for skill in skills_to_complete:
            try:
                response = self.make_request('POST', f'/students/complete-skill/{skill}', 
                                          token=self.tokens['student'])
                
                if response.status_code == 200:
                    self.log_test(f"Skill Completion ({skill})", True, 
                                f"Successfully completed {skill} skill")
                else:
                    self.log_test(f"Skill Completion ({skill})", False, 
                                f"Skill completion failed with status {response.status_code}", 
                                response.text)
            except Exception as e:
                self.log_test(f"Skill Completion ({skill})", False, f"Error: {str(e)}")
    
    def test_recruiter_profile_creation(self):
        """Test recruiter profile creation"""
        if 'recruiter' not in self.tokens:
            self.log_test("Recruiter Profile Creation", False, "No recruiter token available")
            return
            
        profile_data = {
            "company": "TechCorp Solutions",
            "position": "Senior Technical Recruiter",
            "phone": "+1-555-0456"
        }
        
        try:
            response = self.make_request('POST', '/recruiters/profile', 
                                      profile_data, self.tokens['recruiter'])
            
            if response.status_code == 200:
                self.log_test("Recruiter Profile Creation", True, "Recruiter profile created successfully")
            else:
                self.log_test("Recruiter Profile Creation", False, 
                            f"Profile creation failed with status {response.status_code}", 
                            response.text)
        except Exception as e:
            self.log_test("Recruiter Profile Creation", False, f"Error: {str(e)}")
    
    def test_recruiter_profile_retrieval(self):
        """Test recruiter profile retrieval"""
        if 'recruiter' not in self.tokens:
            self.log_test("Recruiter Profile Retrieval", False, "No recruiter token available")
            return
            
        try:
            response = self.make_request('GET', '/recruiters/profile', 
                                      token=self.tokens['recruiter'])
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['name', 'email', 'company', 'position']
                if all(field in data for field in required_fields):
                    self.log_test("Recruiter Profile Retrieval", True, 
                                "Successfully retrieved recruiter profile")
                else:
                    missing = [f for f in required_fields if f not in data]
                    self.log_test("Recruiter Profile Retrieval", False, 
                                f"Missing fields: {missing}", data)
            else:
                self.log_test("Recruiter Profile Retrieval", False, 
                            f"Profile retrieval failed with status {response.status_code}", 
                            response.text)
        except Exception as e:
            self.log_test("Recruiter Profile Retrieval", False, f"Error: {str(e)}")
    
    def test_student_search(self):
        """Test student search functionality"""
        if 'recruiter' not in self.tokens:
            self.log_test("Student Search", False, "No recruiter token available")
            return
            
        search_queries = [
            {"college": "Stanford"},
            {"year_of_passout": 2025},
            {"skills": ["Python", "SQL"]},
            {}  # Empty search to get all students
        ]
        
        for i, search_data in enumerate(search_queries):
            try:
                response = self.make_request('POST', '/recruiters/search-students', 
                                          search_data, self.tokens['recruiter'])
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        self.log_test(f"Student Search {i+1}", True, 
                                    f"Search returned {len(data)} students")
                    else:
                        self.log_test(f"Student Search {i+1}", False, 
                                    "Search did not return a list", data)
                else:
                    self.log_test(f"Student Search {i+1}", False, 
                                f"Search failed with status {response.status_code}", 
                                response.text)
            except Exception as e:
                self.log_test(f"Student Search {i+1}", False, f"Error: {str(e)}")
    
    def test_course_management(self):
        """Test course listing and initialization"""
        # First initialize default courses as admin
        if 'admin' in self.tokens:
            try:
                response = self.make_request('POST', '/admin/init-data', 
                                          token=self.tokens['admin'])
                if response.status_code == 200:
                    self.log_test("Course Initialization", True, "Default courses initialized")
                else:
                    self.log_test("Course Initialization", False, 
                                f"Initialization failed with status {response.status_code}")
            except Exception as e:
                self.log_test("Course Initialization", False, f"Error: {str(e)}")
        
        # Test course listing (public endpoint)
        try:
            response = self.make_request('GET', '/courses')
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    course_skills = [course.get('skill_name') for course in data]
                    expected_skills = ['Resume Building', 'Aptitude', 'Python', 'SQL', 'Communication']
                    if all(skill in course_skills for skill in expected_skills):
                        self.log_test("Course Listing", True, 
                                    f"Successfully retrieved {len(data)} courses")
                    else:
                        self.log_test("Course Listing", False, 
                                    f"Missing expected courses. Found: {course_skills}")
                else:
                    self.log_test("Course Listing", False, "No courses found or invalid format")
            else:
                self.log_test("Course Listing", False, 
                            f"Course listing failed with status {response.status_code}")
        except Exception as e:
            self.log_test("Course Listing", False, f"Error: {str(e)}")
    
    def test_job_management(self):
        """Test job posting and listing"""
        if 'recruiter' not in self.tokens:
            self.log_test("Job Management", False, "No recruiter token available")
            return
            
        # Test job posting
        job_data = {
            "title": "Software Engineering Intern",
            "company": "TechCorp Solutions",
            "location": "San Francisco, CA",
            "description": "Join our team as a software engineering intern and work on cutting-edge projects.",
            "job_type": "internship",
            "required_skills": ["Python", "SQL", "Communication"],
            "year_level": "3rd",
            "salary": "$25/hour"
        }
        
        job_id = None
        try:
            response = self.make_request('POST', '/jobs', job_data, self.tokens['recruiter'])
            
            if response.status_code == 200:
                data = response.json()
                job_id = data.get('job_id')
                self.log_test("Job Posting", True, "Successfully posted job")
            else:
                self.log_test("Job Posting", False, 
                            f"Job posting failed with status {response.status_code}", 
                            response.text)
        except Exception as e:
            self.log_test("Job Posting", False, f"Error: {str(e)}")
        
        # Test job listing
        try:
            response = self.make_request('GET', '/jobs')
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    self.log_test("Job Listing", True, f"Successfully retrieved {len(data)} jobs")
                else:
                    self.log_test("Job Listing", False, "No jobs found")
            else:
                self.log_test("Job Listing", False, 
                            f"Job listing failed with status {response.status_code}")
        except Exception as e:
            self.log_test("Job Listing", False, f"Error: {str(e)}")
        
        return job_id
    
    def test_job_application(self, job_id: str = None):
        """Test job application functionality"""
        if 'student' not in self.tokens:
            self.log_test("Job Application", False, "No student token available")
            return
            
        if not job_id:
            # Get a job ID from job listing
            try:
                response = self.make_request('GET', '/jobs')
                if response.status_code == 200:
                    jobs = response.json()
                    if jobs:
                        job_id = jobs[0]['id']
                    else:
                        self.log_test("Job Application", False, "No jobs available to apply to")
                        return
                else:
                    self.log_test("Job Application", False, "Could not retrieve jobs for application test")
                    return
            except Exception as e:
                self.log_test("Job Application", False, f"Error retrieving jobs: {str(e)}")
                return
        
        # Apply to job
        try:
            response = self.make_request('POST', f'/jobs/{job_id}/apply', 
                                      token=self.tokens['student'])
            
            if response.status_code == 200:
                self.log_test("Job Application", True, "Successfully applied to job")
            else:
                self.log_test("Job Application", False, 
                            f"Job application failed with status {response.status_code}", 
                            response.text)
        except Exception as e:
            self.log_test("Job Application", False, f"Error: {str(e)}")
    
    def test_application_tracking(self):
        """Test application tracking for students"""
        if 'student' not in self.tokens:
            self.log_test("Application Tracking", False, "No student token available")
            return
            
        try:
            response = self.make_request('GET', '/students/applications', 
                                      token=self.tokens['student'])
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Application Tracking", True, 
                                f"Successfully retrieved {len(data)} applications")
                else:
                    self.log_test("Application Tracking", False, 
                                "Applications endpoint did not return a list")
            else:
                self.log_test("Application Tracking", False, 
                            f"Application tracking failed with status {response.status_code}")
        except Exception as e:
            self.log_test("Application Tracking", False, f"Error: {str(e)}")
    
    def test_authentication_protection(self):
        """Test that protected endpoints require authentication"""
        protected_endpoints = [
            ('GET', '/students/profile'),
            ('GET', '/recruiters/profile'),
            ('POST', '/students/complete-skill/Python'),
            ('POST', '/jobs')
        ]
        
        for method, endpoint in protected_endpoints:
            try:
                response = self.make_request(method, endpoint)  # No token
                
                if response.status_code == 401:
                    self.log_test(f"Auth Protection ({method} {endpoint})", True, 
                                "Correctly rejected unauthenticated request")
                else:
                    self.log_test(f"Auth Protection ({method} {endpoint})", False, 
                                f"Expected 401, got {response.status_code}")
            except Exception as e:
                self.log_test(f"Auth Protection ({method} {endpoint})", False, f"Error: {str(e)}")
    
    def test_admin_authentication(self):
        """Test admin user registration and login"""
        # Admin registration should already be done in test_user_registration
        if 'admin' not in self.tokens:
            self.log_test("Admin Authentication", False, "Admin user not registered")
            return
            
        # Test admin login
        try:
            response = self.make_request('POST', '/auth/login', {
                'email': 'admin@joblens.com',
                'password': 'AdminPass789!'
            })
            
            if response.status_code == 200:
                data = response.json()
                if data.get('user_role') == 'admin':
                    self.log_test("Admin Authentication", True, "Admin login successful")
                else:
                    self.log_test("Admin Authentication", False, 
                                f"Role mismatch: expected admin, got {data.get('user_role')}")
            else:
                self.log_test("Admin Authentication", False, 
                            f"Admin login failed with status {response.status_code}")
        except Exception as e:
            self.log_test("Admin Authentication", False, f"Error: {str(e)}")
    
    def test_admin_data_initialization(self):
        """Test admin data initialization endpoint"""
        if 'admin' not in self.tokens:
            self.log_test("Admin Data Initialization", False, "No admin token available")
            return
            
        try:
            response = self.make_request('POST', '/admin/init-data', 
                                      token=self.tokens['admin'])
            
            if response.status_code == 200:
                self.log_test("Admin Data Initialization", True, 
                            "Default data initialized successfully")
            else:
                self.log_test("Admin Data Initialization", False, 
                            f"Data initialization failed with status {response.status_code}", 
                            response.text)
        except Exception as e:
            self.log_test("Admin Data Initialization", False, f"Error: {str(e)}")
    
    def test_admin_course_management(self):
        """Test admin course CRUD operations"""
        if 'admin' not in self.tokens:
            self.log_test("Admin Course Management", False, "No admin token available")
            return
        
        course_id = None
        
        # Test adding a new course
        new_course = {
            "title": "Advanced JavaScript",
            "description": "Master advanced JavaScript concepts and frameworks",
            "price": 750.0,
            "duration": "4-5 hours",
            "skill_name": "Advanced JavaScript"
        }
        
        try:
            response = self.make_request('POST', '/admin/courses', 
                                      new_course, self.tokens['admin'])
            
            if response.status_code == 200:
                data = response.json()
                course_id = data.get('course_id')
                self.log_test("Admin Add Course", True, "Successfully added new course")
            else:
                self.log_test("Admin Add Course", False, 
                            f"Course addition failed with status {response.status_code}", 
                            response.text)
        except Exception as e:
            self.log_test("Admin Add Course", False, f"Error: {str(e)}")
        
        # Test updating a course (if we have a course_id)
        if course_id:
            updated_course = {
                "title": "Advanced JavaScript & React",
                "description": "Master advanced JavaScript concepts, React, and modern frameworks",
                "price": 850.0
            }
            
            try:
                response = self.make_request('PUT', f'/admin/courses/{course_id}', 
                                          updated_course, self.tokens['admin'])
                
                if response.status_code == 200:
                    self.log_test("Admin Update Course", True, "Successfully updated course")
                else:
                    self.log_test("Admin Update Course", False, 
                                f"Course update failed with status {response.status_code}", 
                                response.text)
            except Exception as e:
                self.log_test("Admin Update Course", False, f"Error: {str(e)}")
        
        # Test deleting a course (if we have a course_id)
        if course_id:
            try:
                response = self.make_request('DELETE', f'/admin/courses/{course_id}', 
                                          token=self.tokens['admin'])
                
                if response.status_code == 200:
                    self.log_test("Admin Delete Course", True, "Successfully deleted course")
                else:
                    self.log_test("Admin Delete Course", False, 
                                f"Course deletion failed with status {response.status_code}", 
                                response.text)
            except Exception as e:
                self.log_test("Admin Delete Course", False, f"Error: {str(e)}")
    
    def test_admin_job_management(self):
        """Test admin job management operations"""
        if 'admin' not in self.tokens:
            self.log_test("Admin Job Management", False, "No admin token available")
            return
        
        # First, get a job ID to delete (from existing jobs)
        job_id = None
        try:
            response = self.make_request('GET', '/jobs')
            if response.status_code == 200:
                jobs = response.json()
                if jobs:
                    job_id = jobs[0]['id']
            
            if not job_id:
                # Create a job first for testing deletion
                job_data = {
                    "title": "Test Job for Deletion",
                    "company": "Test Company",
                    "location": "Test Location",
                    "description": "This job is created for testing admin deletion functionality",
                    "job_type": "internship",
                    "required_skills": ["Python"],
                    "year_level": "3rd",
                    "salary": "$20/hour"
                }
                
                response = self.make_request('POST', '/jobs', job_data, self.tokens['admin'])
                if response.status_code == 200:
                    job_id = response.json().get('job_id')
        except Exception as e:
            self.log_test("Admin Job Management Setup", False, f"Error setting up job: {str(e)}")
        
        # Test deleting a job
        if job_id:
            try:
                response = self.make_request('DELETE', f'/admin/jobs/{job_id}', 
                                          token=self.tokens['admin'])
                
                if response.status_code == 200:
                    self.log_test("Admin Delete Job", True, "Successfully deleted job")
                else:
                    self.log_test("Admin Delete Job", False, 
                                f"Job deletion failed with status {response.status_code}", 
                                response.text)
            except Exception as e:
                self.log_test("Admin Delete Job", False, f"Error: {str(e)}")
        else:
            self.log_test("Admin Delete Job", False, "No job available for deletion test")
    
    def test_admin_user_management(self):
        """Test admin user management operations"""
        if 'admin' not in self.tokens:
            self.log_test("Admin User Management", False, "No admin token available")
            return
        
        # Test getting all users
        try:
            response = self.make_request('GET', '/admin/users', 
                                      token=self.tokens['admin'])
            
            if response.status_code == 200:
                data = response.json()
                if all(key in data for key in ['users', 'students', 'recruiters']):
                    total_users = len(data['users'])
                    total_students = len(data['students'])
                    total_recruiters = len(data['recruiters'])
                    self.log_test("Admin Get All Users", True, 
                                f"Retrieved {total_users} users, {total_students} students, {total_recruiters} recruiters")
                else:
                    self.log_test("Admin Get All Users", False, 
                                "Missing required sections in response", data)
            else:
                self.log_test("Admin Get All Users", False, 
                            f"User retrieval failed with status {response.status_code}", 
                            response.text)
        except Exception as e:
            self.log_test("Admin Get All Users", False, f"Error: {str(e)}")
        
        # Test user verification
        user_id_to_verify = None
        if 'recruiter' in self.users:
            user_id_to_verify = self.users['recruiter']['user_id']
        
        if user_id_to_verify:
            try:
                response = self.make_request('PUT', f'/admin/users/{user_id_to_verify}/verify', 
                                          token=self.tokens['admin'])
                
                if response.status_code == 200:
                    self.log_test("Admin Verify User", True, "Successfully verified user")
                else:
                    self.log_test("Admin Verify User", False, 
                                f"User verification failed with status {response.status_code}", 
                                response.text)
            except Exception as e:
                self.log_test("Admin Verify User", False, f"Error: {str(e)}")
        else:
            self.log_test("Admin Verify User", False, "No user available for verification test")
    
    def test_admin_analytics(self):
        """Test admin analytics endpoint"""
        if 'admin' not in self.tokens:
            self.log_test("Admin Analytics", False, "No admin token available")
            return
        
        try:
            response = self.make_request('GET', '/admin/analytics', 
                                      token=self.tokens['admin'])
            
            if response.status_code == 200:
                data = response.json()
                if 'stats' in data and 'recent_activity' in data:
                    stats = data['stats']
                    required_stats = ['total_users', 'total_students', 'total_recruiters', 
                                    'total_courses', 'total_jobs', 'total_applications']
                    
                    if all(stat in stats for stat in required_stats):
                        self.log_test("Admin Analytics", True, 
                                    f"Analytics retrieved successfully with {len(stats)} stats")
                    else:
                        missing_stats = [s for s in required_stats if s not in stats]
                        self.log_test("Admin Analytics", False, 
                                    f"Missing stats: {missing_stats}", data)
                else:
                    self.log_test("Admin Analytics", False, 
                                "Missing required sections in analytics response", data)
            else:
                self.log_test("Admin Analytics", False, 
                            f"Analytics retrieval failed with status {response.status_code}", 
                            response.text)
        except Exception as e:
            self.log_test("Admin Analytics", False, f"Error: {str(e)}")
    
    def test_admin_access_control(self):
        """Test that admin endpoints reject non-admin users"""
        admin_endpoints = [
            ('POST', '/admin/init-data'),
            ('POST', '/admin/courses'),
            ('GET', '/admin/users'),
            ('GET', '/admin/analytics')
        ]
        
        # Test with student token
        if 'student' in self.tokens:
            for method, endpoint in admin_endpoints:
                try:
                    response = self.make_request(method, endpoint, 
                                              token=self.tokens['student'])
                    
                    if response.status_code == 403:
                        self.log_test(f"Admin Access Control ({method} {endpoint})", True, 
                                    "Correctly rejected non-admin user")
                    else:
                        self.log_test(f"Admin Access Control ({method} {endpoint})", False, 
                                    f"Expected 403, got {response.status_code}")
                except Exception as e:
                    self.log_test(f"Admin Access Control ({method} {endpoint})", False, 
                                f"Error: {str(e)}")
        else:
            self.log_test("Admin Access Control", False, "No student token available for testing")
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting JobLens Backend API Tests")
        print("=" * 50)
        
        # Basic connectivity
        if not self.test_api_health():
            print("❌ API is not accessible. Stopping tests.")
            return
        
        # Authentication tests
        print("\n🔐 Testing Authentication...")
        self.test_user_registration()
        self.test_user_login()
        self.test_invalid_login()
        self.test_authentication_protection()
        
        # Student functionality tests
        print("\n👨‍🎓 Testing Student Features...")
        self.test_student_profile_creation()
        self.test_student_profile_retrieval()
        self.test_skill_completion()
        
        # Recruiter functionality tests
        print("\n👔 Testing Recruiter Features...")
        self.test_recruiter_profile_creation()
        self.test_recruiter_profile_retrieval()
        self.test_student_search()
        
        # Course management tests
        print("\n📚 Testing Course Management...")
        self.test_course_management()
        
        # Job and application tests
        print("\n💼 Testing Job Management...")
        job_id = self.test_job_management()
        self.test_job_application(job_id)
        self.test_application_tracking()
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results if result['success'])
        failed = len(self.test_results) - passed
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/len(self.test_results)*100):.1f}%")
        
        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  • {result['test']}: {result['message']}")
        
        print("\n" + "=" * 50)

if __name__ == "__main__":
    tester = JobLensAPITester()
    tester.run_all_tests()