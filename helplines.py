"""
Verified public support resources used by the hackathon demo.
Verified against official Government of India sources on 2026-09-29.
"""

PUBLIC_SUPPORT_RESOURCES = [
    {
        "name": "RBI Contact Centre",
        "phone": "14448",
        "category": "Banking / lender grievance guidance",
        "availability": "Contact-centre hours apply",
        "description": (
            "Provides information and guidance on RBI's grievance-redress mechanism "
            "for complaints involving RBI-regulated entities. It is not a debt-counselling service."
        ),
        "source_label": "Reserve Bank of India — Complaint Management System",
        "source_url": "https://cms.rbi.org.in",
    },
    {
        "name": "National Consumer Helpline",
        "phone": "1915",
        "alternate_phone": "1800-11-4000",
        "category": "Consumer grievance support",
        "availability": "8 AM–8 PM (official portal)",
        "description": (
            "Government of India consumer grievance support. Useful when the issue involves "
            "a consumer service, lender communication, billing or a related consumer grievance."
        ),
        "source_label": "Department of Consumer Affairs — National Consumer Helpline",
        "source_url": "https://consumerhelpline.gov.in/",
    },
]

WELLBEING_SUPPORT = {
    "name": "Tele-MANAS",
    "phone": "14416",
    "alternate_phone": "1800-89-14416",
    "category": "Mental-health support",
    "availability": "24×7",
    "description": (
        "Government of India tele-mental-health service for people who need emotional or "
        "mental-health support. This is separate from financial grievance support."
    ),
    "source_label": "Ministry of Health & Family Welfare — Tele-MANAS",
    "source_url": "https://dghs.mohfw.gov.in/national-mental-health-programme.php",
}


def get_financial_support_resources():
    return list(PUBLIC_SUPPORT_RESOURCES)


def get_wellbeing_support():
    return dict(WELLBEING_SUPPORT)
