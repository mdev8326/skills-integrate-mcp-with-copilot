# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities
- Institution-scoped tenant filtering using request headers
- Audit logging for critical activity mutations

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get activities visible to the request institution                   |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up for an activity in your institution                         |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student from an institution-scoped activity        |
| PATCH  | `/activities/{activity_name}/capacity?max_participants=25`       | Update capacity (admin/superadmin only)                            |
| GET    | `/audit-logs`                                                     | Read audit logs (admin/superadmin only)                            |

## Tenant Context Headers

All API calls accept these headers for tenant and actor context propagation:

- `x-institution-id` (default: `mergington-high`)
- `x-user-id` (default: `anonymous`)
- `x-user-role` (default: `guardian`; accepted: guardian, teacher, admin, superadmin)

If an activity exists in another institution, the API returns `404 Activity not found` to prevent cross-tenant data leakage.

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data and audit logs are stored in memory, which means they reset when the server restarts.
