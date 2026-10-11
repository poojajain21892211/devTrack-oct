import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import (
    Reporter,
    Issue,
    CriticalIssue,
    LowPriorityIssue,
)


# =====================================================
# REPORTER JSON HELPERS
# =====================================================

def read_reporters():
    try:
        with open("reporters.json", "r") as file:
            return json.load(file)

    except FileNotFoundError:
        return []

    except json.JSONDecodeError:
        raise ValueError(
            "reporters.json contains invalid JSON"
        )


def write_reporters(reporters):
    with open("reporters.json", "w") as file:
        json.dump(reporters, file, indent=4)


# =====================================================
# REPORTER API
# =====================================================

@csrf_exempt
def reporters_view(request):

    # -------------------------------------------------
    # POST /api/reporters/
    # -------------------------------------------------

    if request.method == "POST":

        try:
            data = json.loads(request.body)

        except json.JSONDecodeError:
            return JsonResponse(
                {"error": "Invalid JSON"},
                status=400
            )

        if not isinstance(data, dict):
            return JsonResponse(
                {"error": "Request body must be a JSON object"},
                status=400
            )

        required_fields = [
            "id",
            "name",
            "email",
            "team"
        ]

        for field in required_fields:
            if field not in data:
                return JsonResponse(
                    {"error": f"{field} is required"},
                    status=400
                )

        if not isinstance(data["id"], int):
            return JsonResponse(
                {"error": "Reporter ID must be an integer"},
                status=400
            )

        if not isinstance(data["name"], str):
            return JsonResponse(
                {"error": "Name must be a string"},
                status=400
            )

        if not isinstance(data["email"], str):
            return JsonResponse(
                {"error": "Email must be a string"},
                status=400
            )

        if not isinstance(data["team"], str):
            return JsonResponse(
                {"error": "Team must be a string"},
                status=400
            )

        reporter = Reporter(
            data["id"],
            data["name"].strip(),
            data["email"].strip(),
            data["team"].strip()
        )

        try:
            reporter.validate()

        except ValueError as error:
            return JsonResponse(
                {"error": str(error)},
                status=400
            )

        if not reporter.team:
            return JsonResponse(
                {"error": "Team cannot be empty"},
                status=400
            )

        try:
            reporters = read_reporters()

        except ValueError as error:
            return JsonResponse(
                {"error": str(error)},
                status=500
            )

        # Duplicate ID
        if any(
            item.get("id") == reporter.id
            for item in reporters
        ):
            return JsonResponse(
                {"error": "Reporter ID already exists"},
                status=400
            )

        # Duplicate email
        if any(
            str(item.get("email", "")).strip().lower()
            == reporter.email.lower()
            for item in reporters
        ):
            return JsonResponse(
                {"error": "Reporter email already exists"},
                status=400
            )

        reporter_data = reporter.to_dict()

        reporters.append(reporter_data)

        try:
            write_reporters(reporters)

        except OSError:
            return JsonResponse(
                {"error": "Unable to save reporter data"},
                status=500
            )

        return JsonResponse(
            reporter_data,
            status=201
        )

    # -------------------------------------------------
    # GET /api/reporters/
    # GET /api/reporters/?id=1
    # GET /api/reporters/?email=...
    # -------------------------------------------------

    if request.method == "GET":

        try:
            reporters = read_reporters()

        except ValueError as error:
            return JsonResponse(
                {"error": str(error)},
                status=500
            )

        reporter_id = request.GET.get("id")
        reporter_email = request.GET.get("email")

        # GET Reporter by ID
        if reporter_id is not None:

            try:
                reporter_id = int(reporter_id)

            except ValueError:
                return JsonResponse(
                    {"error": "Reporter ID must be an integer"},
                    status=400
                )

            for reporter in reporters:

                if reporter.get("id") == reporter_id:
                    return JsonResponse(
                        reporter,
                        status=200
                    )

            return JsonResponse(
                {"error": "Reporter not found"},
                status=404
            )

        # Optional GET Reporter by email
        if reporter_email is not None:

            reporter_email = (
                reporter_email
                .strip()
                .lower()
            )

            if not reporter_email:
                return JsonResponse(
                    {"error": "Email cannot be empty"},
                    status=400
                )

            for reporter in reporters:

                stored_email = str(
                    reporter.get(
                        "email",
                        ""
                    )
                ).strip().lower()

                if stored_email == reporter_email:
                    return JsonResponse(
                        reporter,
                        status=200
                    )

            return JsonResponse(
                {"error": "Reporter not found"},
                status=404
            )

        # GET all Reporters
        return JsonResponse(
            reporters,
            safe=False,
            status=200
        )

    return JsonResponse(
        {"error": "Method not allowed"},
        status=405
    )


# =====================================================
# ISSUE JSON HELPERS
# =====================================================

def read_issues():
    try:
        with open("issues.json", "r") as file:
            return json.load(file)

    except FileNotFoundError:
        return []

    except json.JSONDecodeError:
        raise ValueError(
            "issues.json contains invalid JSON"
        )


def write_issues(issues):
    with open("issues.json", "w") as file:
        json.dump(issues, file, indent=4)


# =====================================================
# ISSUE API
# =====================================================

@csrf_exempt
def issues_view(request):

    # -------------------------------------------------
    # POST /api/issues/
    # -------------------------------------------------

    if request.method == "POST":

        try:
            data = json.loads(request.body)

        except json.JSONDecodeError:
            return JsonResponse(
                {"error": "Invalid JSON"},
                status=400
            )

        if not isinstance(data, dict):
            return JsonResponse(
                {"error": "Request body must be a JSON object"},
                status=400
            )

        required_fields = [
            "id",
            "title",
            "description",
            "status",
            "priority",
            "reporter_id"
        ]

        for field in required_fields:

            if field not in data:
                return JsonResponse(
                    {"error": f"{field} is required"},
                    status=400
                )

        # -------------------------------------------------
        # Type validation
        # -------------------------------------------------

        if not isinstance(data["id"], int):
            return JsonResponse(
                {"error": "Issue ID must be an integer"},
                status=400
            )

        if not isinstance(data["reporter_id"], int):
            return JsonResponse(
                {"error": "Reporter ID must be an integer"},
                status=400
            )

        if not isinstance(data["title"], str):
            return JsonResponse(
                {"error": "Title must be a string"},
                status=400
            )

        if not isinstance(data["description"], str):
            return JsonResponse(
                {"error": "Description must be a string"},
                status=400
            )

        if not isinstance(data["status"], str):
            return JsonResponse(
                {"error": "Status must be a string"},
                status=400
            )

        if not isinstance(data["priority"], str):
            return JsonResponse(
                {"error": "Priority must be a string"},
                status=400
            )

        # Normalize strings
        title = data["title"].strip()

        description = (
            data["description"]
            .strip()
        )

        status = (
            data["status"]
            .strip()
            .lower()
        )

        priority = (
            data["priority"]
            .strip()
            .lower()
        )

        # -------------------------------------------------
        # Validate Reporter relationship
        # -------------------------------------------------

        try:
            reporters = read_reporters()

        except ValueError as error:
            return JsonResponse(
                {"error": str(error)},
                status=500
            )

        reporter_exists = any(
            reporter.get("id")
            == data["reporter_id"]

            for reporter
            in reporters
        )

        if not reporter_exists:
            return JsonResponse(
                {"error": "Reporter not found"},
                status=400
            )

        # -------------------------------------------------
        # Instantiate appropriate Issue subclass
        # -------------------------------------------------

        issue_arguments = {
            "id": data["id"],
            "title": title,
            "description": description,
            "status": status,
            "priority": priority,
            "reporter_id": data["reporter_id"]
        }

        if priority == "critical":

            issue = CriticalIssue(
                **issue_arguments
            )

        elif priority == "low":

            issue = LowPriorityIssue(
                **issue_arguments
            )

        else:

            issue = Issue(
                **issue_arguments
            )

        # -------------------------------------------------
        # OOP validation
        # -------------------------------------------------

        try:
            issue.validate()

        except ValueError as error:
            return JsonResponse(
                {"error": str(error)},
                status=400
            )

        # -------------------------------------------------
        # Read existing Issues
        # -------------------------------------------------

        try:
            issues = read_issues()

        except ValueError as error:
            return JsonResponse(
                {"error": str(error)},
                status=500
            )

        # Duplicate ID validation
        if any(
            existing_issue.get("id")
            == issue.id

            for existing_issue
            in issues
        ):
            return JsonResponse(
                {"error": "Issue ID already exists"},
                status=400
            )

        # BaseEntity.to_dict()
        issue_data = issue.to_dict()

        # Save
        issues.append(
            issue_data
        )

        try:
            write_issues(issues)

        except OSError:
            return JsonResponse(
                {"error": "Unable to save issue data"},
                status=500
            )

        # -------------------------------------------------
        # Polymorphism
        # -------------------------------------------------

        response_data = issue_data.copy()

        response_data["message"] = (
            issue.describe()
        )

        return JsonResponse(
            response_data,
            status=201
        )

    # -------------------------------------------------
    # GET /api/issues/
    # GET /api/issues/?id=1
    # GET /api/issues/?status=open
    # -------------------------------------------------

    if request.method == "GET":

        try:
            issues = read_issues()

        except ValueError as error:
            return JsonResponse(
                {"error": str(error)},
                status=500
            )

        issue_id = request.GET.get(
            "id"
        )

        status_filter = request.GET.get(
            "status"
        )

        # Prevent ambiguous filtering
        if (
            issue_id is not None
            and status_filter is not None
        ):
            return JsonResponse(
                {
                    "error":
                    "Use either id or status, not both"
                },
                status=400
            )

        # -------------------------------------------------
        # GET Issue by ID
        # -------------------------------------------------

        if issue_id is not None:

            try:
                issue_id = int(
                    issue_id
                )

            except ValueError:
                return JsonResponse(
                    {"error": "Issue ID must be an integer"},
                    status=400
                )

            for issue in issues:

                if issue.get("id") == issue_id:

                    return JsonResponse(
                        issue,
                        status=200
                    )

            return JsonResponse(
                {"error": "Issue not found"},
                status=404
            )

        # -------------------------------------------------
        # GET Issues by status
        # -------------------------------------------------

        if status_filter is not None:

            status_filter = (
                status_filter
                .strip()
                .lower()
            )

            allowed_statuses = [
                "open",
                "in_progress",
                "resolved",
                "closed"
            ]

            if (
                status_filter
                not in allowed_statuses
            ):
                return JsonResponse(
                    {"error": "Invalid status"},
                    status=400
                )

            filtered_issues = [
                issue

                for issue
                in issues

                if str(
                    issue.get(
                        "status",
                        ""
                    )
                ).strip().lower()
                == status_filter
            ]

            return JsonResponse(
                filtered_issues,
                safe=False,
                status=200
            )

        # -------------------------------------------------
        # GET all Issues
        # -------------------------------------------------

        return JsonResponse(
            issues,
            safe=False,
            status=200
        )

    # -------------------------------------------------
    # Unsupported HTTP method
    # -------------------------------------------------

    return JsonResponse(
        {"error": "Method not allowed"},
        status=405
    )