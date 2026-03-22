from flask import Blueprint, jsonify

from database import hostel_info_collection, transport_schedules_collection, campus_navigation_collection

campus_routes = Blueprint("campus_routes", __name__)


@campus_routes.route("/hostel-info", methods=["GET"])
def hostel_info():
    try:
        rows = list(
            hostel_info_collection.find(
                {},
                {"_id": 0, "hostel_name": 1, "type": 1, "capacity": 1, "fee_per_year": 1, "facilities": 1},
            )
        )
        if rows:
            return jsonify({"items": rows})

        return jsonify(
            {
                "items": [
                    {
                        "hostel_name": "Central Boys Hostel",
                        "type": "Boys",
                        "capacity": 600,
                        "fee_per_year": 90000,
                        "facilities": ["Wi-Fi", "Mess", "Laundry", "Reading Room"],
                    }
                ],
                "source": "fallback",
            }
        )
    except Exception as e:
        return jsonify({"error": "Failed to fetch hostel info", "details": str(e)}), 503


@campus_routes.route("/transport-schedules", methods=["GET"])
def transport_schedules():
    try:
        rows = list(
            transport_schedules_collection.find(
                {},
                {"_id": 0, "route_name": 1, "pickup_points": 1, "departure_time": 1, "arrival_time": 1, "bus_no": 1},
            ).sort("route_name", 1)
        )
        if rows:
            return jsonify({"items": rows})

        return jsonify(
            {
                "items": [
                    {
                        "route_name": "City Center to Campus",
                        "pickup_points": ["Main Bus Stand", "Railway Station", "Market Circle"],
                        "departure_time": "07:15",
                        "arrival_time": "08:05",
                        "bus_no": "VU-12",
                    }
                ],
                "source": "fallback",
            }
        )
    except Exception as e:
        return jsonify({"error": "Failed to fetch transport schedules", "details": str(e)}), 503


@campus_routes.route("/campus-navigation", methods=["GET"])
def campus_navigation():
    try:
        rows = list(
            campus_navigation_collection.find(
                {},
                {"_id": 0, "from": 1, "to": 1, "route_steps": 1, "approx_minutes": 1},
            )
        )
        if rows:
            return jsonify({"items": rows})

        return jsonify(
            {
                "items": [
                    {
                        "from": "Main Gate",
                        "to": "CSE Block",
                        "route_steps": ["Walk straight for 250m", "Turn left at Admin Block", "Second building on right"],
                        "approx_minutes": 6,
                    }
                ],
                "source": "fallback",
            }
        )
    except Exception as e:
        return jsonify({"error": "Failed to fetch campus navigation info", "details": str(e)}), 503
