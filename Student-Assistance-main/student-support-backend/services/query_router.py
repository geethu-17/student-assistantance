import re

from database import (
    applications_collection,
    academic_calendar_collection,
    course_registration_collection,
    credit_requirements_collection,
    loan_assistance_collection,
    programs_collection,
    fee_structure_collection,
    scholarships_collection,
    transport_schedules_collection,
    campus_navigation_collection,
    stress_resources_collection,
)


def _route_result(handled=False, response=None, matched=None, matched_intent=None, match_source=None):
    return {
        "handled": handled,
        "response": response,
        "matched": matched,
        "matched_intent": matched_intent,
        "match_source": match_source,
    }


def _extract_application_id(message_text):
    match = re.search(r"\bapp[\w-]*\b", message_text or "", re.IGNORECASE)
    if not match:
        return None
    return match.group(0).upper()


def _get_application_for_user(user_identifier, message_text):
    user_identifier = (user_identifier or "").strip()
    app_id = _extract_application_id(message_text)

    selectors = []
    if app_id:
        selectors.append({"application_id": app_id})
    if user_identifier:
        selectors.extend(
            [
                {"registration_number": user_identifier},
                {"email": user_identifier.lower()},
            ]
        )

    if not selectors:
        return None

    return applications_collection.find_one({"$or": selectors}, {"_id": 0})


def try_handle_functional_query(message_en, user_identifier="guest"):
    text = (message_en or "").lower()

    if "eligibility check" in text or "eligibility" in text:
        return _route_result(
            True,
            "For eligibility, please share your stream and marks. Example: stream MPC, marks 78.",
            True,
            "eligibility_checks",
            "functional_rule",
        )

    if "course registration guidance" in text or "course registration" in text:
        rows = list(
            course_registration_collection.find(
                {},
                {"_id": 0, "title": 1, "steps": 1, "required_documents": 1, "contacts": 1},
            ).limit(2)
        )
        if rows:
            first = rows[0]
            steps = " -> ".join(first.get("steps") or [])
            docs = ", ".join(first.get("required_documents") or [])
            contacts = ", ".join(first.get("contacts") or [])
            response = (
                f"{first.get('title', 'Course registration guidance')}:\n"
                f"Steps: {steps or '-'}\n"
                f"Required documents: {docs or '-'}\n"
                f"Contact: {contacts or '-'}"
            )
            return _route_result(True, response, True, "course_registration_guidance", "functional_rule_db")
        return _route_result(
            True,
            "Course registration guidance is being updated. Please contact academic office.",
            False,
            "course_registration_guidance",
            "functional_rule_missing_data",
        )

    if "academic calendar" in text:
        events = list(academic_calendar_collection.find({}, {"_id": 0, "event": 1, "date": 1}).sort("date", 1).limit(5))
        if events:
            lines = [f"{row.get('date', '-')}: {row.get('event', '-')}" for row in events]
            return _route_result(
                True,
                "Academic calendar highlights:\n" + "\n".join(lines),
                True,
                "academic_calendar_information",
                "functional_rule_db",
            )
        return _route_result(
            True,
            "Academic calendar is currently being updated.",
            False,
            "academic_calendar_information",
            "functional_rule_missing_data",
        )

    if "application status" in text or "track application" in text:
        app_status = _get_application_for_user(user_identifier, text)
        if app_status:
            response = (
                f"Application status: {app_status.get('status', 'Unknown')}.\n"
                f"Application ID: {app_status.get('application_id', '-')}\n"
                f"Program: {app_status.get('program', '-')}\n"
                f"Last updated: {app_status.get('last_updated', '-')}"
            )
            return _route_result(True, response, True, "application_tracking", "functional_rule_db")
        return _route_result(
            True,
            "I could not find your application record yet. Please share your registration number or application ID (example: APP2026-0012).",
            False,
            "application_tracking",
            "functional_rule_missing_data",
        )

    if "program information" in text or "available programs" in text or "courses offered" in text:
        rows = list(
            programs_collection.find(
                {},
                {"_id": 0, "name": 1, "degree": 1, "duration_years": 1, "intake": 1},
            ).limit(5)
        )
        if rows:
            lines = [
                f"{row.get('name')} ({row.get('degree', '-')}, {row.get('duration_years', '-')} years, intake {row.get('intake', '-')})"
                for row in rows
            ]
            return _route_result(True, "Programs snapshot:\n" + "\n".join(lines), True, "program_information", "functional_rule_db")
        return _route_result(
            True,
            "Program catalog is being updated. Please ask the admissions office for detailed intake and eligibility.",
            False,
            "program_information",
            "functional_rule_missing_data",
        )

    if "credit requirement" in text or "required credits" in text or "credit query" in text:
        reqs = list(
            credit_requirements_collection.find(
                {},
                {"_id": 0, "program": 1, "semester": 1, "required_credits": 1},
            ).limit(4)
        )
        if reqs:
            lines = [
                f"{row.get('program')} Sem {row.get('semester')}: {row.get('required_credits')} credits"
                for row in reqs
            ]
            return _route_result(
                True,
                "Credit requirements snapshot:\n" + "\n".join(lines) + "\nUse your registration number for exact pending credits.",
                True,
                "credit_requirement_queries",
                "functional_rule_db",
            )
        return _route_result(
            True,
            "Credit requirement data is being updated. Please contact academics office with your program and semester.",
            False,
            "credit_requirement_queries",
            "functional_rule_missing_data",
        )

    if "fee" in text or "tuition" in text:
        fee_row = fee_structure_collection.find_one(
            {},
            {"_id": 0, "program": 1, "tuition_fee": 1, "hostel_fee": 1, "other_charges": 1, "currency": 1},
        )
        if fee_row:
            response = (
                f"Fee details for {fee_row.get('program', 'program')}:\n"
                f"Tuition: {fee_row.get('tuition_fee', '-')}\n"
                f"Hostel: {fee_row.get('hostel_fee', '-')}\n"
                f"Other charges: {fee_row.get('other_charges', '-')}\n"
                f"Currency: {fee_row.get('currency', 'INR')}"
            )
            return _route_result(True, response, True, "fee_payment_information", "functional_rule_db")
        return _route_result(
            True,
            "Fee structure is currently being updated. Please contact finance office for latest payable amount and due dates.",
            False,
            "fee_payment_information",
            "functional_rule_missing_data",
        )

    if "scholarship" in text:
        scholarship = scholarships_collection.find_one(
            {},
            {"_id": 0, "name": 1, "criteria": 1, "benefit": 1, "deadline": 1, "link": 1},
        )
        if scholarship:
            response = (
                f"{scholarship.get('name', 'Scholarship')}:\n"
                f"Criteria: {scholarship.get('criteria', '-')}\n"
                f"Benefit: {scholarship.get('benefit', '-')}\n"
                f"Deadline: {scholarship.get('deadline', '-')}\n"
                f"More info: {scholarship.get('link', '-')}"
            )
            return _route_result(True, response, True, "scholarship_guidance", "functional_rule_db")
        return _route_result(
            True,
            "Scholarship details are being updated. Please check with scholarship cell for latest criteria and deadlines.",
            False,
            "scholarship_guidance",
            "functional_rule_missing_data",
        )

    if "loan" in text or "education loan" in text or "loan assistance" in text:
        loan_info = loan_assistance_collection.find_one(
            {},
            {"_id": 0, "description": 1, "required_documents": 1, "contact": 1, "link": 1},
        )
        if loan_info:
            docs = ", ".join(loan_info.get("required_documents") or [])
            response = (
                f"{loan_info.get('description', 'Loan assistance details are available.')}\n"
                f"Required documents: {docs or 'Contact office for document list'}.\n"
                f"Contact: {loan_info.get('contact', 'finance office')}.\n"
                f"More info: {loan_info.get('link', '-')}"
            )
            return _route_result(True, response, True, "loan_assistance_information", "functional_rule_db")
        return _route_result(
            True,
            "You can apply for education loan support using admission letter, fee structure, ID/address proof, and mark sheets. Please contact the finance office for the latest process.",
            True,
            "loan_assistance_information",
            "functional_rule_fallback",
        )

    if "transport" in text or "bus schedule" in text:
        transport = transport_schedules_collection.find_one(
            {},
            {"_id": 0, "route_name": 1, "departure_time": 1, "arrival_time": 1, "pickup_points": 1, "bus_no": 1},
        )
        if transport:
            points = ", ".join(transport.get("pickup_points") or [])
            response = (
                f"Transport route: {transport.get('route_name', '-')}\n"
                f"Bus: {transport.get('bus_no', '-')}\n"
                f"Departure: {transport.get('departure_time', '-')}, Arrival: {transport.get('arrival_time', '-')}\n"
                f"Pickup points: {points or '-'}"
            )
            return _route_result(True, response, True, "transportation_schedules", "functional_rule_db")
        return _route_result(
            True,
            "Transportation schedule is being updated. Please check the transport office notice.",
            False,
            "transportation_schedules",
            "functional_rule_missing_data",
        )

    if "campus navigation" in text or "how to reach" in text or "where is" in text:
        nav = campus_navigation_collection.find_one(
            {},
            {"_id": 0, "from": 1, "to": 1, "route_steps": 1, "approx_minutes": 1},
        )
        if nav:
            steps = " -> ".join(nav.get("route_steps") or [])
            response = (
                f"Route from {nav.get('from', 'start')} to {nav.get('to', 'destination')}:\n"
                f"{steps or 'Follow campus signage'}\n"
                f"Approx time: {nav.get('approx_minutes', '-')} minutes"
            )
            return _route_result(True, response, True, "campus_navigation", "functional_rule_db")
        return _route_result(
            True,
            "Campus navigation info is being updated. Please ask at help desk near main gate.",
            False,
            "campus_navigation",
            "functional_rule_missing_data",
        )

    if "stress" in text or "anxiety" in text or "mental health" in text:
        resource = stress_resources_collection.find_one(
            {},
            {"_id": 0, "title": 1, "description": 1, "contact": 1, "link": 1},
        )
        if resource:
            response = (
                f"{resource.get('title', 'Stress support resource')}:\n"
                f"{resource.get('description', '-')}\n"
                f"Contact: {resource.get('contact', 'counseling center')}\n"
                f"Link: {resource.get('link', '-')}"
            )
            return _route_result(True, response, True, "stress_management_resources", "functional_rule_db")
        return _route_result(
            True,
            "For stress support, take a short break, practice controlled breathing, and contact the campus counseling center. If urgent, please reach emergency support immediately.",
            True,
            "stress_management_resources",
            "functional_rule_fallback",
        )

    return _route_result()
