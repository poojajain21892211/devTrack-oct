# DevTrack | Engineering Issue Tracking API

DevTrack is a lightweight Django backend for recording engineering issues and the reporters who raise them. The project is intentionally small in scope, with the focus on clean domain modelling, predictable API behaviour, validation, and a clear one-to-many relationship between reporters and issues.

## Architecture at a Glance

```text
Client / Postman
      |
      v
Django URL Routing
      |
      v
API Views
  |       |
  |       +--> Request parsing / HTTP responses
  |       +--> JSON read / write
  |
  v
Domain Objects
  |-- Reporter
  |-- Issue
      |-- CriticalIssue
      |-- LowPriorityIssue
  |
  v
JSON Persistence
  |-- reporters.json
  +-- issues.json
```

The application separates domain behaviour from HTTP handling. Entity validation and issue-specific behaviour live in `issues/models.py`, while `issues/views.py` coordinates requests, responses, lookups, and JSON persistence.

## Core Capabilities

- Register reporters with a unique ID and contact information
- File multiple issues against the same reporter
- Retrieve all reporters or locate a reporter by ID
- Retrieve all issues or locate a specific issue by ID
- Filter issues by workflow status
- Validate issue title, status, priority, and reporter reference
- Produce priority-specific descriptions through inheritance and method overriding
- Persist Reporter and Issue records in separate JSON files

## Domain Model

### Reporter

A Reporter represents the engineer or user who raises an issue.

| Field | Purpose |
|---|---|
| `id` | Unique reporter identifier |
| `name` | Full name |
| `email` | Contact email |
| `team` | Team such as frontend, backend, or devops |

### Issue

An Issue represents a bug or engineering task.

| Field | Purpose |
|---|---|
| `id` | Unique issue identifier |
| `title` | Short summary |
| `description` | Detailed context |
| `status` | Current workflow state |
| `priority` | Business/engineering urgency |
| `reporter_id` | Reporter who filed the issue |
| `created_at` | Creation timestamp |

Supported statuses:

```text
open
in_progress
resolved
closed
```

Supported priorities:

```text
low
medium
high
critical
```

## Object-Oriented Design

### Shared entity contract

`BaseEntity` acts as the common abstraction for the domain objects. It requires derived entities to implement `validate()` and provides `to_dict()` for converting an object into a JSON-friendly dictionary.

```text
BaseEntity
   |
   +-- Reporter
   |
   +-- Issue
         |
         +-- CriticalIssue
         |
         +-- LowPriorityIssue
```

`Issue.describe()` provides the default description for medium and high priority issues. `CriticalIssue` and `LowPriorityIssue` override the same method to provide behaviour appropriate to their priority.

This keeps the API call simple:

```python
message = issue.describe()
```

The concrete Issue object determines which description is returned.

## Design Decisions

### 1. Keep the Reporter-Issue relationship on the Issue side

I modelled the relationship by storing `reporter_id` inside each Issue. Reporter does not maintain a separate collection of Issue IDs.

```text
Reporter #7
   |
   +-- Issue #101
   +-- Issue #102
   +-- Issue #103
```

This gives the relationship a single direction and supports the required one-to-many model naturally. Before an Issue is persisted, the API verifies that its `reporter_id` references an existing Reporter.

Keeping the reference in one place also avoids duplicated relationship state. If both Reporter and Issue maintained the association, creating an Issue would require two records to remain synchronized.

### 2. Keep domain validation with the domain objects

Validation that describes what makes a Reporter or Issue valid belongs to the entity itself. For that reason, `validate()` is implemented by `Reporter` and `Issue` in `models.py` rather than placing every business rule directly in the Django views.

This creates a clearer responsibility boundary:

```text
models.py
    Domain structure
    Validation rules
    Priority-specific behaviour

views.py
    HTTP request handling
    Query parameters
    Error responses
    JSON persistence

urls.py
    Endpoint routing
```

The result is easier to reason about because HTTP concerns and domain rules are not treated as the same responsibility.

## Data Persistence

DevTrack stores data in two independent JSON files:

```text
reporters.json
issues.json
```

An empty store contains:

```json
[]
```

The relationship between the files is maintained by `reporter_id` on each Issue.

## API Contract

Local base URL:

```text
http://127.0.0.1:8000/api/
```

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/reporters/` | Create a reporter |
| GET | `/api/reporters/` | Retrieve all reporters |
| GET | `/api/reporters/?id=1` | Retrieve one reporter by ID |
| POST | `/api/issues/` | Create an issue |
| GET | `/api/issues/` | Retrieve all issues |
| GET | `/api/issues/?id=1` | Retrieve one issue by ID |
| GET | `/api/issues/?status=open` | Filter issues by status |

## API Examples

The samples below intentionally use different engineering scenarios to demonstrate the API behaviour.

### Example 1: Create a Reporter

**Request**

```text
POST /api/reporters/
```

```json
{
    "id": 7,
    "name": "Aarav Menon",
    "email": "aarav.menon@example.com",
    "team": "platform"
}
```

A successful request returns `201 Created` with the stored Reporter data.

### Example 2: Create a Critical Issue

Scenario: a production checkout service is returning errors.

```text
POST /api/issues/
```

```json
{
    "id": 101,
    "title": "Checkout API returns 500 for card payments",
    "description": "Payment requests fail when customers submit card details during checkout.",
    "status": "open",
    "priority": "critical",
    "reporter_id": 7
}
```

The response includes the CriticalIssue description:

```json
{
    "id": 101,
    "title": "Checkout API returns 500 for card payments",
    "description": "Payment requests fail when customers submit card details during checkout.",
    "status": "open",
    "priority": "critical",
    "reporter_id": 7,
    "created_at": "<generated at runtime>",
    "message": "[URGENT] Checkout API returns 500 for card payments — needs immediate attention"
}
```

### Example 3: Create a Low-Priority Issue

Scenario: a small UI inconsistency is discovered in an internal dashboard.

```json
{
    "id": 102,
    "title": "Dashboard filter labels are misaligned",
    "description": "Filter labels shift slightly when the browser width is reduced.",
    "status": "open",
    "priority": "low",
    "reporter_id": 7
}
```

Its response message is produced by `LowPriorityIssue.describe()`:

```text
Dashboard filter labels are misaligned — low priority, handle when free
```

### Example 4: Create a High-Priority Issue

Scenario: an authentication problem affects some users but does not require the CriticalIssue subclass.

```json
{
    "id": 103,
    "title": "Session expires during long-running report export",
    "description": "Users are redirected to login when a large report export takes several minutes.",
    "status": "in_progress",
    "priority": "high",
    "reporter_id": 7
}
```

High and medium priorities use the base `Issue` implementation, so the description follows:

```text
Session expires during long-running report export [high]
```

### Example 5: Retrieve One Issue

```text
GET /api/issues/?id=101
```

If the Issue exists, the API returns the matching record with `200 OK`.

If it does not exist:

```json
{
    "error": "Issue not found"
}
```

with `404 Not Found`.

### Example 6: Filter Issues by Status

```text
GET /api/issues/?status=in_progress
```

Only Issues with `in_progress` status are returned.

## Validation Examples

### Empty Issue title

```json
{
    "id": 104,
    "title": "",
    "description": "Verifying title validation.",
    "status": "open",
    "priority": "medium",
    "reporter_id": 7
}
```

Expected response:

```json
{
    "error": "Title cannot be empty"
}
```

Status: `400 Bad Request`

### Invalid priority

```json
{
    "id": 105,
    "title": "Search results load slowly",
    "description": "Used to verify priority validation.",
    "status": "open",
    "priority": "urgent",
    "reporter_id": 7
}
```

Expected result: `400 Bad Request` because `urgent` is not one of the supported priorities.

### Unknown Reporter

```json
{
    "id": 106,
    "title": "Notification preferences are not retained",
    "description": "Used to verify Reporter reference validation.",
    "status": "open",
    "priority": "medium",
    "reporter_id": 999
}
```

The request is rejected because the referenced Reporter does not exist.

## HTTP Response Behaviour

| Status | Meaning in DevTrack |
|---|---|
| `200 OK` | Successful retrieval |
| `201 Created` | Reporter or Issue created successfully |
| `400 Bad Request` | Request or domain validation failed |
| `404 Not Found` | Requested Reporter or Issue was not found |
| `405 Method Not Allowed` | HTTP method is not supported by the endpoint |
| `500 Internal Server Error` | JSON persistence could not be processed safely |

## Project Structure

```text
devTrack/
├── manage.py
├── reporters.json
├── issues.json
├── requirements.txt
├── README.md
├── devtrack/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
└── issues/
    ├── models.py
    ├── views.py
    ├── urls.py
    └── migrations/
```

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/poojajain21892211/devTrack-oct/
cd devTrack
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate it

Windows Command Prompt:

```cmd
venv\Scripts\activate
```

Windows PowerShell:

```powershell
venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 5. Apply Django migrations

```bash
python manage.py migrate
```

### 6. Validate the Django configuration

```bash
python manage.py check
```

### 7. Start the application

```bash
python manage.py runserver
```

The local API is available at:

```text
http://127.0.0.1:8000/api/
```

## Postman Verification

The required endpoints are exercised from Postman. For submission evidence, the README includes one successful request and one validation failure.

### Successful Critical Issue Creation

Issue Creation API Test: Successfully creates a high-priority issue associated with Reporter 7 and returns the issue description through the custom describe() behavior.

<img width="536" height="409" alt="image" src="https://github.com/user-attachments/assets/81870b94-83a9-498c-a4cd-5db667851a30" />


### Validation Failure

This test demonstrates the domain validation path for an empty Issue title and the `400 Bad Request` response.

<img width="533" height="411" alt="image" src="https://github.com/user-attachments/assets/9ad86ff9-44aa-4a2c-9ebe-2cd5c5936bb5" />



