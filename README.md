# Niva AI - API Documentation

This document provides comprehensive API documentation for the Niva AI application, designed for frontend developers to integrate with the backend services.

## Base URL
```
http://localhost:8000/api/v1
```

or

```
http://3.66.219.6:8000/api/v1/
```

## Authentication
Most endpoints require authentication using token-based authentication. Include the token in the Authorization header:
```
Authorization: Token <your_token_here>
```

---

## Table of Contents

1. [Authentication APIs](#authentication-apis)
2. [Course Management APIs](#course-management-apis)
3. [Agent Memory APIs](#agent-memory-apis)
4. [Agent APIs](#agent-apis)
5. [Daily.co Integration APIs](#dailyco-integration-apis)
6. [Entrypoint APIs](#entrypoint-apis)
7. [Test APIs](#test-apis)
8. [Pipecat Agent APIs](#pipecat-agent-apis)

---

## Authentication APIs

### Register User
**POST** `/auth/register/`

Creates a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "role_type": "user"  // or "admin"
}
```

**Response:**
```json
{
  "message": "User created successfully.",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "user@example.com",
    "role": "User"
  }
}
```

**Status Codes:**
- `200` - Success
- `400` - Bad Request (validation errors, email already exists)

---

### Login
**POST** `/auth/login/`

Authenticates a user and returns an access token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "token": "your_access_token_here"
}
```

**Status Codes:**
- `200` - Success
- `400` - Bad Request (invalid credentials)
- `404` - User not found

---

## Course Management APIs

### Create Course
**POST** `/course/create/`

Creates a new course with an associated agent.

**Request Body:**
```json
{
  "name": "Python Programming Course",
  "description": "Learn Python from basics to advanced",
  "is_active": true,
  "passing_score": 70.00,
  "max_score": 100.00,
  "syllabus": "Course syllabus content",
  "instructions": "Course instructions",
  "evaluation_criteria": "Evaluation criteria"
}
```

**Response:**
```json
{
  "message": "Course and associated agent created successfully",
  "course": {
    "id": "uuid",
    "name": "Python Programming Course",
    "description": "Learn Python from basics to advanced",
    "is_active": true,
    "passing_score": "70.00",
    "max_score": "100.00",
    "syllabus": "Course syllabus content",
    "instructions": "Course instructions",
    "evaluation_criteria": "Evaluation criteria",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "agents": [
      {
        "id": "uuid",
        "name": "Python Course Agent",
        "is_active": true,
        "language": "en",
        "agent_type": "course_agent"
      }
    ]
  }
}
```

---

### Get Course
**POST** `/course/get/`

Retrieves a specific course by ID.

**Request Body:**
```json
{
  "course_id": "uuid"
}
```

**Response:**
```json
{
  "course": {
    "id": "uuid",
    "name": "Python Programming Course",
    "description": "Learn Python from basics to advanced",
    "is_active": true,
    "passing_score": "70.00",
    "max_score": "100.00",
    "syllabus": "Course syllabus content",
    "instructions": "Course instructions",
    "evaluation_criteria": "Evaluation criteria",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "agents": [...]
  }
}
```

**Status Codes:**
- `200` - Success
- `400` - Bad Request
- `404` - Course not found

---

### Get All Courses
**POST** `/course/all/`

Retrieves all courses with optional filtering.

**Request Body:**
```json
{
  "is_active": true  // optional
}
```

**Response:**
```json
{
  "courses": [
    {
      "id": "uuid",
      "name": "Python Programming Course",
      "description": "Learn Python from basics to advanced",
      "is_active": true,
      "passing_score": "70.00",
      "max_score": "100.00",
      "syllabus": "Course syllabus content",
      "instructions": "Course instructions",
      "evaluation_criteria": "Evaluation criteria",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

### Update Course
**POST** `/course/update/`

Updates an existing course.

**Request Body:**
```json
{
  "course_id": "uuid",
  "name": "Updated Course Name",  // optional
  "description": "Updated description",  // optional
  "is_active": false,  // optional
  "passing_score": 80.00,  // optional
  "max_score": 100.00,  // optional
  "syllabus": "Updated syllabus",  // optional
  "instructions": "Updated instructions",  // optional
  "evaluation_criteria": "Updated criteria"  // optional
}
```

**Response:**
```json
{
  "message": "Course updated successfully",
  "course": {
    "id": "uuid",
    "name": "Updated Course Name",
    "description": "Updated description",
    "is_active": false,
    "passing_score": "80.00",
    "max_score": "100.00",
    "syllabus": "Updated syllabus",
    "instructions": "Updated instructions",
    "evaluation_criteria": "Updated criteria",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
  }
}
```

**Status Codes:**
- `200` - Success
- `400` - Bad Request
- `404` - Course not found

---

### Delete Course
**POST** `/course/delete/`

Deletes a course.

**Request Body:**
```json
{
  "course_id": "uuid"
}
```

**Response:**
```json
{
  "message": "Course deleted successfully"
}
```

**Status Codes:**
- `200` - Success
- `400` - Bad Request
- `404` - Course not found

---

## Agent Memory APIs

### Add Memory
**POST** `/agent-memory/{course_id}/add-memory/`

Adds memory (document or website) to a course.

**Request Body (Multipart Form Data):**
```
type: "document" or "website"
name: "Memory Name"
file: <file> (required for document type)
url: "https://example.com" (required for website type)
```

**Response:**
```json
{
  "message": "Document uploaded and processed successfully",
  "file_path": "/path/to/uploaded/file.pdf"
}
```

**Status Codes:**
- `200` - Success
- `400` - Bad Request (missing file/URL, invalid type)
- `403` - Course not active

---

### Delete Memory
**DELETE** `/agent-memory/{course_id}/delete-memory/{memory_id}/`

Deletes a specific memory.

**Response:**
```
Status: 204 No Content
```

**Status Codes:**
- `204` - Success
- `404` - Memory not found

---

### Get Memory Content
**GET** `/agent-memory/{course_id}/memory/{memory_id}/content/`

Retrieves the content of a specific memory with pagination.

**Query Parameters:**
- `limit` - Number of items per page (default: 20)
- `offset` - Number of items to skip (default: 0)

**Response:**
```json
{
  "count": 10,
  "next": "http://api/v1/agent-memory/course_id/memory/memory_id/content/?limit=20&offset=20",
  "previous": null,
  "results": [
    {
      "content": "Document chunk content...",
      "chunk_index": 0,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

**Status Codes:**
- `200` - Success
- `403` - Course not active
- `404` - Memory not found

---

### Get Memory Summary
**GET** `/agent-memory/{course_id}/memory/{memory_id}/summary/`

Retrieves summary information about a specific memory.

**Response:**
```json
{
  "memory_id": "uuid",
  "name": "Memory Name",
  "type": "document",
  "url": "/path/to/file.pdf",
  "course_id": "uuid",
  "course_name": "Course Name",
  "chunk_count": 5,
  "total_content_length": 1500,
  "preview": "First 500 characters of content...",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**Status Codes:**
- `200` - Success
- `403` - Course not active
- `404` - Memory not found

---

## Agent APIs

### Process Post Call Data
**POST** `/agent/process-post-call-data/`

Processes data after a call has ended.

**Request Body:**
```json
{
  "call_id": "call_123",
  "session_id": "session_456",
  "course_id": "uuid",
  "agent_id": "uuid"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Post-call data processed successfully"
}
```

**Status Codes:**
- `200` - Success
- `400` - Bad Request (missing required fields)
- `500` - Internal Server Error

---

### Get Call Processor Status
**GET** `/agent/processor-status/`

Retrieves call processing statistics and system status.

**Response:**
```json
{
  "status": "healthy",
  "statistics": {
    "total_calls": 150,
    "calls_last_24h": 25,
    "calls_with_recordings": 140,
    "calls_with_customers": 120,
    "recording_success_rate": 93.33
  },
  "services": {
    "gcp_storage": "operational",
    "database": "operational",
    "customer_processor": "operational"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Status Codes:**
- `200` - Success
- `500` - Internal Server Error

---

## Daily.co Integration APIs

### Daily Webhook
**POST** `/daily/webhooks/daily/`

Handles Daily.co webhook events (room creation, participant events, recording events).

**Request Body:**
```json
{
  "type": "room.created",
  "data": {
    "room": {
      "name": "room_name"
    },
    "participant": {
      "user_id": "user_123"
    },
    "recording": {
      "id": "recording_123",
      "download_link": "https://example.com/recording.mp4"
    }
  }
}
```

**Response:**
```
Status: 200 OK
```

**Status Codes:**
- `200` - Success
- `400` - Bad Request (invalid JSON)
- `500` - Internal Server Error

---

### Get Call Recording
**GET** `/daily/calls/{daily_call_id}/recording/`

Retrieves recording information for a specific Daily call.

**Response:**
```json
{
  "call_id": "uuid",
  "call_sid": "call_sid_123",
  "recording_data": {
    "id": "recording_123",
    "download_link": "https://example.com/recording.mp4"
  },
  "course_id": "uuid",
  "course_name": "Course Name",
  "student_id": "uuid",
  "student_name": "John Doe"
}
```

**Status Codes:**
- `200` - Success
- `404` - Call not found
- `500` - Internal Server Error

---

### Create Daily Room
**POST** `/daily/rooms/`

Creates a new Daily.co room.

**Request Body:**
```json
{
  "room_name": "my-room",
  "privacy": "private",
  "exp_time": 3600,
  "enable_chat": false,
  "enable_sip": true,
  "sip_display_name": "SIP Participant",
  "sip_video": false
}
```

**Response:**
```json
{
  "name": "my-room",
  "url": "https://example.daily.co/my-room",
  "token": "room_token_here",
  "sip_endpoint": "sip@example.com"
}
```

**Status Codes:**
- `201` - Created
- `500` - Internal Server Error

---

### Create and Save Room
**POST** `/daily/rooms/create-and-save/`

Creates a Daily.co room and saves call information to database.

**Request Body:**
```json
{
  "caller_phone_number": "+1234567890",
  "course_id": "uuid",
  "agent_id": "uuid",
  "call_sid": "call_sid_123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Room created and saved successfully",
  "daily_call_id": "uuid",
  "room": {
    "name": "room_name",
    "url": "https://example.daily.co/room_name",
    "token": "room_token_here"
  },
  "call": {
    "id": "uuid",
    "call_sid": "call_sid_123",
    "daily_room_token": "room_token_here"
  },
  "course_id": "uuid",
  "course_name": "Course Name"
}
```

**Status Codes:**
- `201` - Created
- `400` - Bad Request (missing required fields, invalid course reference)
- `500` - Internal Server Error

---

## Entrypoint APIs

### Entrypoint Voice API
**POST** `/initiate/entrypoint/`

Handles inbound calls and initiates voice conversations.

**Request Body:**
```json
{
  "course_id": "uuid",
  "agent_id": "uuid"  // optional, will use first active agent if not provided
}
```

**Response:**
```json
{
  "success": true,
  "sip_endpoint": "sip@example.com",
  "daily_call_id": "uuid",
  "agent_result": {...},
  "room_url": "https://example.daily.co/room_name",
  "token": "room_token_here",
  "course_name": "Course Name",
  "agent_name": "Agent Name"
}
```

**Status Codes:**
- `200` - Success
- `400` - Bad Request (invalid course/agent, validation errors)
- `500` - Internal Server Error

---

## Test APIs

### Test Voice Call
**POST** `/test/voice-call/`

Test endpoint to manually trigger a voice call.

**Request Body:**
```json
{
  "phone_number": "+1234567890",
  "daily_call_id": "test_call_123",
  "daily_room_url": "https://test.daily.co/test-room",
  "sip_endpoint": "test@sip.example.com",
  "course_id": "test_course_123",
  "agent_id": "test_agent_456",
  "token": "test_daily_token_123",
  "twilio_data": {
    "test": true,
    "call_sid": "test_sid"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Test voice call initiated",
  "request_data": {...},
  "response": {...}
}
```

---

### Test Health Check
**GET** `/test/health/`

Test endpoint to check system health.

**Response:**
```json
{
  "success": true,
  "health_check": {...}
}
```

---

### Test Active Calls
**GET** `/test/active-calls/`

Test endpoint to get active calls.

**Response:**
```json
{
  "success": true,
  "active_calls": [...]
}
```

---

### Test Stop Call
**POST** `/test/stop-call/`

Test endpoint to stop a specific call.

**Request Body:**
```json
{
  "session_id": "session_123"
}
```

**Response:**
```json
{
  "success": true,
  "stop_call_result": {...}
}
```

---

## Pipecat Agent APIs

### Health Check
**GET** `/pipecat/health/`

Checks the health of Pipecat agents.

**Response:**
```json
{
  "status": "healthy",
  "message": "Pipecat agents are functioning correctly",
  "agent_types": ["inbound", "outbound"],
  "components": {
    "registry": "ok",
    "flow_config": "ok",
    "transcript": "ok",
    "audiobuffer": "ok"
  }
}
```

**Status Codes:**
- `200` - Success
- `500` - Internal Server Error

---

### Handle Voice Call
**POST** `/pipecat/voice-call/`

Processes voice call requests from niva_app.

**Request Body:**
```json
{
  "daily_call_id": "uuid",
  "daily_room_url": "https://example.daily.co/room",
  "sip_endpoint": "sip@example.com",
  "token": "room_token_here",
  "course_id": "uuid",
  "agent_id": "uuid",
  "location_id": "location_123",
  "phone_number": "+1234567890",
  "twilio_data": {
    "from": "+1234567890",
    "to": "+0987654321",
    "callsid": "call_sid_123"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Voice call processed successfully",
  "session_id": "session_123"
}
```

**Status Codes:**
- `200` - Success
- `400` - Bad Request (missing required fields)
- `500` - Internal Server Error

---

### Get Active Calls
**GET** `/pipecat/active-calls/`

Retrieves all active voice calls.

**Response:**
```json
{
  "success": true,
  "active_calls": 3,
  "calls": [
    {
      "session_id": "session_123",
      "status": "active",
      "course_id": "uuid",
      "agent_id": "uuid",
      "phone_number": "+1234567890"
    }
  ]
}
```

---

### Stop Voice Call
**POST** `/pipecat/stop-call/`

Stops a specific voice call.

**Request Body:**
```json
{
  "session_id": "session_123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Call stopped",
  "session_id": "session_123"
}
```

**Status Codes:**
- `200` - Success
- `400` - Bad Request (missing session_id)
- `500` - Internal Server Error

---

**Student API Endpoints**

All student APIs are available at: `http://your-domain.com/api/v1/student/`

### **1. Create Student**
**Endpoint:** `POST /api/v1/student/create/`

**Request Body:**
```json
{
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "1234567890",
    "email": "john.doe@example.com",
    "gender": "MALE",
    "date_of_birth": "1990-01-15",
    "course_ids": ["course-uuid-1", "course-uuid-2"]
}
```

**Response:**
```json
{
    "message": "Student created successfully",
    "student": {
        "id": "student-uuid",
        "first_name": "John",
        "last_name": "Doe",
        "gender": "MALE",
        "date_of_birth": "1990-01-15",
        "email": "john.doe@example.com",
        "phone_number": "+1234567890",
        "created_at": "2025-09-17T10:30:00Z",
        "updated_at": "2025-09-17T10:30:00Z",
        "courses": [...]
    }
}
```

### **2. Get Student**
**Endpoint:** `POST /api/v1/student/get/`

**Request Body:**
```json
{
    "student_id": "student-uuid"
}
```

### **3. Get All Students**
**Endpoint:** `POST /api/v1/student/all/`

**Request Body (optional filters):**
```json
{
    "course_id": "course-uuid",
    "phone_number": "+1234567890",
    "email": "john.doe@example.com"
}
```

### **4. Update Student**
**Endpoint:** `POST /api/v1/student/update/`

**Request Body:**
```json
{
    "student_id": "student-uuid",
    "first_name": "John Updated",
    "phone_number": "9876543210",
    "course_ids": ["new-course-uuid"]
}
```

### **5. Delete Student**
**Endpoint:** `POST /api/v1/student/delete/`

**Request Body:**
```json
{
    "student_id": "student-uuid"
}
```

# **Feedback**

#### 1. **Get Specific Feedback**
- **Endpoint:** `GET /api/v1/feedback/get/`
- **Purpose:** Retrieve a specific feedback by ID
- **Parameters:** `feedback_id` (UUID)

#### 2. **Get Student Feedbacks**
- **Endpoint:** `GET /api/v1/feedback/student/`
- **Purpose:** Get all feedbacks for a specific student
- **Parameters:** 
  - `student_id` (UUID, required)
  - `limit` (integer, optional, default: 10, max: 100)
  - `offset` (integer, optional, default: 0)

#### 3. **Get Agent Feedbacks**
- **Endpoint:** `GET /api/v1/feedback/agent/`
- **Purpose:** Get all feedbacks for a specific agent
- **Parameters:**
  - `agent_id` (UUID, required)
  - `limit` (integer, optional, default: 10, max: 100)
  - `offset` (integer, optional, default: 0)

#### 4. **Get Course Feedbacks**
- **Endpoint:** `GET /api/v1/feedback/course/`
- **Purpose:** Get all feedbacks for students in a specific course
- **Parameters:**
  - `course_id` (UUID, required)
  - `limit` (integer, optional, default: 10, max: 100)
  - `offset` (integer, optional, default: 0)

#### 5. **Get All Feedbacks (with filtering)**
- **Endpoint:** `GET /api/v1/feedback/all/`
- **Purpose:** Get all feedbacks with optional filtering and statistics
- **Parameters:**
  - `student_id` (UUID, optional)
  - `agent_id` (UUID, optional)
  - `course_id` (UUID, optional)
  - `min_rating` (integer, optional, 1-10)
  - `max_rating` (integer, optional, 1-10)
  - `limit` (integer, optional, default: 10, max: 100)
  - `offset` (integer, optional, default: 0)
  - `ordering` (string, optional, default: '-created_at')

#### 6. **Get Feedback Statistics**
- **Endpoint:** `GET /api/v1/feedback/statistics/`
- **Purpose:** Get comprehensive feedback statistics
- **Parameters:**
  - `student_id` (UUID, optional)
  - `agent_id` (UUID, optional)
  - `course_id` (UUID, optional)