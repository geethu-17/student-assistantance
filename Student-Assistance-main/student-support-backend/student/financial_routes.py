from flask import Blueprint, jsonify, request
from database import loan_assistance_collection, fee_structure_collection, scholarships_collection

financial_routes = Blueprint("financial_routes", __name__)


@financial_routes.route("/fees", methods=["GET"])
def fee_info():
    program = (request.args.get("program") or "").strip()

    query = {}
    if program:
        query["program"] = {"$regex": f"^{program}$", "$options": "i"}

    try:
        rows = list(
            fee_structure_collection.find(
                query,
                {"_id": 0, "program": 1, "tuition_fee": 1, "hostel_fee": 1, "other_charges": 1, "currency": 1},
            )
        )

        if rows:
            return jsonify({"items": rows})

        return jsonify(
            {
                "items": [
                    {
                        "program": "B.Tech CSE",
                        "tuition_fee": 220000,
                        "hostel_fee": 90000,
                        "other_charges": 15000,
                        "currency": "INR",
                    }
                ],
                "source": "fallback",
            }
        )
    except Exception as e:
        return jsonify({"error": "Failed to fetch fee info", "details": str(e)}), 503


@financial_routes.route("/scholarships", methods=["GET"])
def scholarships():
    try:
        rows = list(
            scholarships_collection.find(
                {},
                {"_id": 0, "name": 1, "criteria": 1, "benefit": 1, "deadline": 1, "link": 1},
            )
        )

        if rows:
            return jsonify({"items": rows})

        return jsonify(
            {
                "items": [
                    {
                        "name": "Merit Scholarship",
                        "criteria": "Minimum 85% in qualifying exam",
                        "benefit": "Up to 25% tuition fee waiver",
                        "deadline": "2026-06-30",
                        "link": "https://example.edu/scholarships",
                    }
                ],
                "source": "fallback",
            }
        )
    except Exception as e:
        return jsonify({"error": "Failed to fetch scholarships", "details": str(e)}), 503


@financial_routes.route("/loan-assistance", methods=["GET"])
def loan_assistance():
    try:
        rows = list(
            loan_assistance_collection.find(
                {},
                {"_id": 0, "title": 1, "description": 1, "required_documents": 1, "contact": 1, "link": 1},
            )
        )

        if rows:
            return jsonify({"items": rows})

        fallback = {
            "items": [
                {
                    "title": "Education Loan Support",
                    "description": "Students can apply through partner banks with admission proof and fee structure.",
                    "required_documents": [
                        "Admission letter",
                        "Fee structure",
                        "ID proof",
                        "Address proof",
                        "Academic mark sheets",
                    ],
                    "contact": "finance.office@university.edu",
                    "link": "https://example.edu/loan-assistance",
                }
            ],
            "source": "fallback",
        }
        return jsonify(fallback)
    except Exception as e:
        return jsonify({"error": "Failed to fetch loan assistance info", "details": str(e)}), 503
