from flask import Blueprint, request, jsonify

from database import applications_collection, programs_collection

admission_routes = Blueprint("admission_routes", __name__)


@admission_routes.route("/eligibility-check", methods=["POST"])
def check_eligibility():
    data = request.get_json(silent=True) or {}

    stream = (data.get("stream") or "").strip()
    marks = data.get("marks")

    if not stream or marks is None:
        return jsonify({"error": "stream and marks required"}), 400

    if stream.lower() == "mpc" and float(marks) >= 60:
        result = "You are eligible for B.Tech programs."
    else:
        result = "You may not meet the eligibility criteria."

    return jsonify({"eligibility": result})


@admission_routes.route("/programs", methods=["GET"])
def programs():
    search = (request.args.get("search") or "").strip()

    query = {}
    if search:
        query = {
            "$or": [
                {"name": {"$regex": search, "$options": "i"}},
                {"department": {"$regex": search, "$options": "i"}},
                {"degree": {"$regex": search, "$options": "i"}},
            ]
        }

    try:
        rows = list(
            programs_collection.find(
                query,
                {
                    "_id": 0,
                    "name": 1,
                    "degree": 1,
                    "department": 1,
                    "duration_years": 1,
                    "intake": 1,
                    "eligibility_summary": 1,
                },
            ).sort("name", 1)
        )

        if rows:
            return jsonify({"items": rows})

        return jsonify(
            {
                "items": [
                    {
                        "name": "B.Tech Computer Science and Engineering",
                        "degree": "B.Tech",
                        "department": "Computer Science",
                        "duration_years": 4,
                        "intake": 240,
                        "eligibility_summary": "10+2 with MPC and qualifying entrance exam score.",
                    },
                    {
                        "name": "B.Tech Information Technology",
                        "degree": "B.Tech",
                        "department": "Information Technology",
                        "duration_years": 4,
                        "intake": 180,
                        "eligibility_summary": "10+2 with MPC and qualifying entrance exam score.",
                    },
                ],
                "source": "fallback",
            }
        )
    except Exception as e:
        return jsonify({"error": "Failed to fetch programs", "details": str(e)}), 503


@admission_routes.route("/application-status/<registration>", methods=["GET"])
def application_status(registration):
    application = applications_collection.find_one({"registration_number": registration})

    if not application:
        return jsonify({"status": "Application not found"})

    return jsonify(
        {
            "status": application.get("status"),
            "application_id": application.get("application_id"),
            "registration_number": application.get("registration_number"),
            "program": application.get("program"),
            "last_updated": application.get("last_updated"),
        }
    )
