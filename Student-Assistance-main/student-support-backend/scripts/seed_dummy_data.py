from datetime import datetime
from pathlib import Path
import sys

# Allow running this file directly.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import (  # noqa: E402
    applications_collection,
    programs_collection,
    course_registration_collection,
    academic_calendar_collection,
    credit_requirements_collection,
    student_credits_collection,
    fee_structure_collection,
    scholarships_collection,
    loan_assistance_collection,
    hostel_info_collection,
    transport_schedules_collection,
    campus_navigation_collection,
    stress_resources_collection,
    counseling_slots_collection,
    counseling_collection,
)


def upsert_many(collection, rows, unique_keys):
    for row in rows:
        filt = {k: row[k] for k in unique_keys}
        collection.replace_one(filt, row, upsert=True)


def main():
    now = datetime.utcnow().isoformat()

    applications = [
        {
            "registration_number": "22BCS1234",
            "email": "rahul@example.com",
            "application_id": "APP2026-0012",
            "program": "B.Tech CSE",
            "status": "Under Review",
            "last_updated": "2026-03-19",
        },
        {
            "registration_number": "22BIT1111",
            "email": "anita@example.com",
            "application_id": "APP2026-0048",
            "program": "B.Tech IT",
            "status": "Documents Verified",
            "last_updated": "2026-03-18",
        },
        {
            "registration_number": "22ECE0009",
            "email": "vijay@example.com",
            "application_id": "APP2026-0101",
            "program": "B.Tech ECE",
            "status": "Accepted",
            "last_updated": "2026-03-17",
        },
    ]

    programs = [
        {
            "name": "B.Tech Computer Science and Engineering",
            "degree": "B.Tech",
            "department": "Computer Science",
            "duration_years": 4,
            "intake": 240,
            "eligibility_summary": "10+2 with MPC and qualifying entrance score.",
        },
        {
            "name": "B.Tech Information Technology",
            "degree": "B.Tech",
            "department": "Information Technology",
            "duration_years": 4,
            "intake": 180,
            "eligibility_summary": "10+2 with MPC and qualifying entrance score.",
        },
        {
            "name": "B.Tech Electronics and Communication Engineering",
            "degree": "B.Tech",
            "department": "ECE",
            "duration_years": 4,
            "intake": 180,
            "eligibility_summary": "10+2 with MPC and qualifying entrance score.",
        },
    ]

    course_registration_guidance = [
        {
            "title": "Semester Course Registration",
            "steps": [
                "Login to student portal",
                "Select offered courses",
                "Check prerequisites and credit limit",
                "Submit for advisor approval",
            ],
            "required_documents": ["Previous semester marksheet", "Fee receipt"],
            "contacts": ["academic.office@university.edu", "+91-9000000001"],
        }
    ]

    academic_calendar = [
        {"event": "Odd Semester Start", "date": "2026-07-01"},
        {"event": "Mid Semester Exams", "date": "2026-09-10"},
        {"event": "End Semester Exams", "date": "2026-11-20"},
    ]

    credit_requirements = [
        {"program": "B.Tech CSE", "semester": "1", "required_credits": 20, "notes": "Core + Labs"},
        {"program": "B.Tech CSE", "semester": "2", "required_credits": 22, "notes": "Core + Skill"},
        {"program": "B.Tech IT", "semester": "1", "required_credits": 20, "notes": "Core + Labs"},
    ]

    student_credits = [
        {"registration_number": "22BCS1234", "program": "B.Tech CSE", "semester": "2", "earned_credits": 18},
        {"registration_number": "22BIT1111", "program": "B.Tech IT", "semester": "1", "earned_credits": 19},
    ]

    fee_structure = [
        {
            "program": "B.Tech CSE",
            "tuition_fee": 220000,
            "hostel_fee": 90000,
            "other_charges": 15000,
            "currency": "INR",
        },
        {
            "program": "B.Tech IT",
            "tuition_fee": 210000,
            "hostel_fee": 90000,
            "other_charges": 14000,
            "currency": "INR",
        },
    ]

    scholarships = [
        {
            "name": "Merit Scholarship",
            "criteria": "Minimum 85% in qualifying exam",
            "benefit": "Up to 25% tuition fee waiver",
            "deadline": "2026-06-30",
            "link": "https://example.edu/scholarships/merit",
        },
        {
            "name": "Need-Based Scholarship",
            "criteria": "Family income criteria + academic performance",
            "benefit": "Up to 40% tuition fee waiver",
            "deadline": "2026-07-15",
            "link": "https://example.edu/scholarships/need-based",
        },
    ]

    loan_assistance = [
        {
            "title": "Education Loan Support",
            "description": "Apply through partner banks with admission proof and fee structure.",
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
    ]

    hostel_info = [
        {
            "hostel_name": "Central Boys Hostel",
            "type": "Boys",
            "capacity": 600,
            "fee_per_year": 90000,
            "facilities": ["Wi-Fi", "Mess", "Laundry", "Reading Room"],
        },
        {
            "hostel_name": "Central Girls Hostel",
            "type": "Girls",
            "capacity": 500,
            "fee_per_year": 95000,
            "facilities": ["Wi-Fi", "Mess", "Gym", "Security 24x7"],
        },
    ]

    transport_schedules = [
        {
            "route_name": "City Center to Campus",
            "pickup_points": ["Main Bus Stand", "Railway Station", "Market Circle"],
            "departure_time": "07:15",
            "arrival_time": "08:05",
            "bus_no": "VU-12",
        },
        {
            "route_name": "North Zone to Campus",
            "pickup_points": ["North Junction", "River Bridge", "Old Town Stop"],
            "departure_time": "07:00",
            "arrival_time": "08:00",
            "bus_no": "VU-08",
        },
    ]

    campus_navigation = [
        {
            "from": "Main Gate",
            "to": "CSE Block",
            "route_steps": ["Walk straight 250m", "Turn left at Admin Block", "Second building on right"],
            "approx_minutes": 6,
        },
        {
            "from": "Library",
            "to": "Examination Cell",
            "route_steps": ["Exit library", "Take central pathway", "Opposite seminar hall"],
            "approx_minutes": 4,
        },
    ]

    stress_resources = [
        {
            "title": "Breathing and Grounding Guide",
            "description": "Quick 5-minute stress reset exercises.",
            "type": "self_help",
            "link": "https://example.edu/wellness/breathing-guide",
            "contact": "counseling.center@university.edu",
        },
        {
            "title": "Counseling Helpline",
            "description": "Immediate student emotional support during campus hours.",
            "type": "helpline",
            "link": "https://example.edu/wellness/helpline",
            "contact": "+91-9000000010",
        },
    ]

    counseling_slots = [
        {
            "date": "2026-03-20",
            "start_time": "10:00",
            "end_time": "10:30",
            "mode": "offline",
            "counselor": "Dr. Meera Rao",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
        {
            "date": "2026-03-20",
            "start_time": "11:00",
            "end_time": "11:30",
            "mode": "online",
            "counselor": "Dr. Arjun Nair",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
    ]

    counseling_requests = [
        {
            "student": "rahul@example.com",
            "message": "Need support for exam anxiety.",
            "preferred_date": "2026-03-20",
            "status": "pending",
            "scheduled_slot_id": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    ]

    applications.extend(
        [
            {
                "registration_number": "22MECH0123",
                "email": "sneha@example.com",
                "application_id": "APP2026-0156",
                "program": "B.Tech Mechanical",
                "status": "Payment Pending",
                "last_updated": "2026-03-19",
            },
            {
                "registration_number": "22CIVIL0456",
                "email": "karan@example.com",
                "application_id": "APP2026-0188",
                "program": "B.Tech Civil",
                "status": "Submitted",
                "last_updated": "2026-03-16",
            },
        ]
    )
    programs.extend(
        [
            {
                "name": "B.Tech Mechanical Engineering",
                "degree": "B.Tech",
                "department": "Mechanical",
                "duration_years": 4,
                "intake": 120,
                "eligibility_summary": "10+2 with MPC and qualifying entrance score.",
            },
            {
                "name": "B.Tech Civil Engineering",
                "degree": "B.Tech",
                "department": "Civil",
                "duration_years": 4,
                "intake": 120,
                "eligibility_summary": "10+2 with MPC and qualifying entrance score.",
            },
        ]
    )
    course_registration_guidance.extend(
        [
            {
                "title": "Add/Drop Window Guidance",
                "steps": ["Open add/drop page", "Select subject change", "Submit before deadline"],
                "required_documents": ["Advisor note (if required)"],
                "contacts": ["advisor.office@university.edu"],
            },
            {
                "title": "Backlog Registration Guidance",
                "steps": ["Check failed subjects", "Pay backlog fee", "Confirm exam slot"],
                "required_documents": ["Fee receipt", "Hall ticket"],
                "contacts": ["exam.cell@university.edu"],
            },
            {
                "title": "Summer Term Registration",
                "steps": ["Check offered summer courses", "Submit request", "Pay summer fee"],
                "required_documents": ["No-dues certificate"],
                "contacts": ["summer.term@university.edu"],
            },
            {
                "title": "Elective Selection Guidance",
                "steps": ["Review elective basket", "Check seats", "Submit top preferences"],
                "required_documents": ["Advisor approval"],
                "contacts": ["electives@university.edu"],
            },
        ]
    )
    academic_calendar.extend(
        [
            {"event": "Course Registration Deadline", "date": "2026-07-10"},
            {"event": "Result Declaration", "date": "2026-12-15"},
        ]
    )
    credit_requirements.extend(
        [
            {"program": "B.Tech IT", "semester": "2", "required_credits": 22, "notes": "Core + Skill"},
            {"program": "B.Tech ECE", "semester": "1", "required_credits": 21, "notes": "Core + Labs"},
        ]
    )
    student_credits.extend(
        [
            {"registration_number": "22ECE0009", "program": "B.Tech ECE", "semester": "1", "earned_credits": 20},
            {"registration_number": "22MECH0123", "program": "B.Tech Mechanical", "semester": "2", "earned_credits": 17},
            {"registration_number": "22CIVIL0456", "program": "B.Tech Civil", "semester": "1", "earned_credits": 18},
        ]
    )
    fee_structure.extend(
        [
            {"program": "B.Tech ECE", "tuition_fee": 205000, "hostel_fee": 92000, "other_charges": 14500, "currency": "INR"},
            {"program": "B.Tech Mechanical", "tuition_fee": 195000, "hostel_fee": 88000, "other_charges": 13000, "currency": "INR"},
            {"program": "B.Tech Civil", "tuition_fee": 190000, "hostel_fee": 87000, "other_charges": 12500, "currency": "INR"},
        ]
    )
    scholarships.extend(
        [
            {
                "name": "Sports Excellence Scholarship",
                "criteria": "State/National representation certificate",
                "benefit": "Up to 20% tuition fee waiver",
                "deadline": "2026-07-20",
                "link": "https://example.edu/scholarships/sports",
            },
            {
                "name": "Girls in STEM Scholarship",
                "criteria": "Female students in STEM programs with merit criteria",
                "benefit": "Up to 30% tuition fee waiver",
                "deadline": "2026-07-10",
                "link": "https://example.edu/scholarships/stem",
            },
            {
                "name": "First Graduate Scholarship",
                "criteria": "First graduate in family + minimum academic threshold",
                "benefit": "Fixed grant support",
                "deadline": "2026-08-01",
                "link": "https://example.edu/scholarships/first-graduate",
            },
        ]
    )
    loan_assistance.extend(
        [
            {
                "title": "Public Bank Education Loan Desk",
                "description": "On-campus desk for public sector bank education loans.",
                "required_documents": ["Admission letter", "KYC", "Co-applicant income proof"],
                "contact": "loan.helpdesk@university.edu",
                "link": "https://example.edu/loan-assistance/public-bank",
            },
            {
                "title": "Private Bank Fast-Track Loan",
                "description": "Fast processing for approved partner banks.",
                "required_documents": ["Admission letter", "Fee structure", "Academic records"],
                "contact": "finance.fastloan@university.edu",
                "link": "https://example.edu/loan-assistance/private-bank",
            },
            {
                "title": "Subsidy and Moratorium Guidance",
                "description": "Support for subsidy schemes and repayment moratorium details.",
                "required_documents": ["Scheme form", "Income certificate", "Loan sanction letter"],
                "contact": "loan.schemes@university.edu",
                "link": "https://example.edu/loan-assistance/subsidy",
            },
            {
                "title": "International Student Loan Support",
                "description": "Special guidance for international students.",
                "required_documents": ["Passport", "Admission letter", "Financial statement"],
                "contact": "intl.finance@university.edu",
                "link": "https://example.edu/loan-assistance/international",
            },
        ]
    )
    hostel_info.extend(
        [
            {
                "hostel_name": "North Residence",
                "type": "Co-ed",
                "capacity": 300,
                "fee_per_year": 85000,
                "facilities": ["Wi-Fi", "Mess", "Indoor Games"],
            },
            {
                "hostel_name": "Scholars Block",
                "type": "Girls",
                "capacity": 280,
                "fee_per_year": 98000,
                "facilities": ["Wi-Fi", "Study Hall", "24x7 Security"],
            },
            {
                "hostel_name": "Tech Park Hostel",
                "type": "Boys",
                "capacity": 320,
                "fee_per_year": 92000,
                "facilities": ["Wi-Fi", "Gym", "Laundry"],
            },
        ]
    )
    transport_schedules.extend(
        [
            {
                "route_name": "East Zone to Campus",
                "pickup_points": ["East Circle", "Lake View", "Tech Park"],
                "departure_time": "07:05",
                "arrival_time": "08:00",
                "bus_no": "VU-15",
            },
            {
                "route_name": "West Zone to Campus",
                "pickup_points": ["West End", "City Mall", "College Road"],
                "departure_time": "07:20",
                "arrival_time": "08:10",
                "bus_no": "VU-18",
            },
            {
                "route_name": "South Zone to Campus",
                "pickup_points": ["South Terminal", "Airport Junction", "Ring Road"],
                "departure_time": "06:50",
                "arrival_time": "07:55",
                "bus_no": "VU-21",
            },
        ]
    )
    campus_navigation.extend(
        [
            {
                "from": "Main Gate",
                "to": "Hostel Block A",
                "route_steps": ["Walk 150m", "Take right near canteen", "Continue to hostel lane"],
                "approx_minutes": 5,
            },
            {
                "from": "Admin Block",
                "to": "Library",
                "route_steps": ["Exit admin block", "Take central avenue", "Library on left"],
                "approx_minutes": 3,
            },
            {
                "from": "Sports Complex",
                "to": "Medical Room",
                "route_steps": ["Move to main pathway", "Cross cafeteria", "Medical room beside pharmacy"],
                "approx_minutes": 7,
            },
        ]
    )
    stress_resources.extend(
        [
            {
                "title": "Sleep Hygiene Checklist",
                "description": "Simple checklist to improve sleep before exams.",
                "type": "self_help",
                "link": "https://example.edu/wellness/sleep",
                "contact": "wellness@university.edu",
            },
            {
                "title": "Peer Support Circle",
                "description": "Weekly peer listening sessions moderated by counselor.",
                "type": "group_support",
                "link": "https://example.edu/wellness/peer-support",
                "contact": "peer.support@university.edu",
            },
            {
                "title": "Crisis Response Contact",
                "description": "Immediate support for urgent mental health concerns.",
                "type": "emergency",
                "link": "https://example.edu/wellness/crisis",
                "contact": "+91-9000000099",
            },
        ]
    )
    counseling_slots.extend(
        [
            {
                "date": "2026-03-20",
                "start_time": "12:00",
                "end_time": "12:30",
                "mode": "offline",
                "counselor": "Dr. Neha Kapoor",
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "date": "2026-03-21",
                "start_time": "10:00",
                "end_time": "10:30",
                "mode": "online",
                "counselor": "Dr. Meera Rao",
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "date": "2026-03-21",
                "start_time": "11:00",
                "end_time": "11:30",
                "mode": "offline",
                "counselor": "Dr. Arjun Nair",
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        ]
    )
    counseling_requests.extend(
        [
            {
                "student": "anita@example.com",
                "message": "Feeling overwhelmed with assignments.",
                "preferred_date": "2026-03-20",
                "status": "pending",
                "scheduled_slot_id": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "student": "vijay@example.com",
                "message": "Need guidance for stress management routine.",
                "preferred_date": "2026-03-21",
                "status": "pending",
                "scheduled_slot_id": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "student": "sneha@example.com",
                "message": "Unable to focus before exams.",
                "preferred_date": "2026-03-21",
                "status": "pending",
                "scheduled_slot_id": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "student": "karan@example.com",
                "message": "Need a counseling slot for anxiety support.",
                "preferred_date": "2026-03-22",
                "status": "pending",
                "scheduled_slot_id": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        ]
    )

    upsert_many(applications_collection, applications, ["application_id"])
    upsert_many(programs_collection, programs, ["name"])
    upsert_many(course_registration_collection, course_registration_guidance, ["title"])
    upsert_many(academic_calendar_collection, academic_calendar, ["event", "date"])
    upsert_many(credit_requirements_collection, credit_requirements, ["program", "semester"])
    upsert_many(student_credits_collection, student_credits, ["registration_number"])
    upsert_many(fee_structure_collection, fee_structure, ["program"])
    upsert_many(scholarships_collection, scholarships, ["name"])
    upsert_many(loan_assistance_collection, loan_assistance, ["title"])
    upsert_many(hostel_info_collection, hostel_info, ["hostel_name"])
    upsert_many(transport_schedules_collection, transport_schedules, ["route_name", "bus_no"])
    upsert_many(campus_navigation_collection, campus_navigation, ["from", "to"])
    upsert_many(stress_resources_collection, stress_resources, ["title"])
    upsert_many(counseling_slots_collection, counseling_slots, ["date", "start_time", "end_time", "counselor"])
    upsert_many(counseling_collection, counseling_requests, ["student", "message", "preferred_date"])

    print("Dummy data seeded successfully.")
    print(f"Timestamp: {now}")


if __name__ == "__main__":
    main()
