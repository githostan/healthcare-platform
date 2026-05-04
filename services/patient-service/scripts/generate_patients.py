import json
import random
from datetime import date, timedelta

from app.utils.nhs import generate_valid_nhs_number

FIRST_NAMES = [
    "Ugom",
    "Grace",
    "Nola",
    "Linus",
    "Marie",
    "Alan",
    "Nia",
    "Tariq",
    "Abdullah",
    "Kwame",
]
LAST_NAMES = [
    "Nnaji",
    "Turing",
    "Hopper",
    "Johnson",
    "Okafor",
    "Smith",
    "Patel",
    "Ghazi",
    "Brown",
    "Osei",
]

GENDERS = ["MALE", "FEMALE", "OTHER", "UNKNOWN"]
CONTACT_METHODS = ["SMS", "EMAIL", "PHONE", "NONE"]
STATUSES = ["ACTIVE", "INACTIVE"]


def random_date_of_birth(min_age: int = 18, max_age: int = 90) -> date:
    today = date.today()
    age = random.randint(min_age, max_age)
    days_offset = random.randint(0, 365)
    return today - timedelta(days=age * 365 + days_offset)


def random_phone() -> str:
    return f"07{random.randint(100000000, 999999999)}"


def random_email(first: str, last: str, index: int) -> str:
    return f"{first.lower()}.{last.lower()}.{index}@example.com"


def generate_patient(index: int, used_nhs_numbers: set[str]) -> dict:
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)

    nhs_number = generate_valid_nhs_number()
    while nhs_number in used_nhs_numbers:
        nhs_number = generate_valid_nhs_number()
    used_nhs_numbers.add(nhs_number)

    return {
        "nhs_number": nhs_number,
        "first_name": first,
        "last_name": last,
        "date_of_birth": random_date_of_birth().isoformat(),
        "gender": random.choice(GENDERS),
        "phone": random_phone(),
        "email": random_email(first, last, index),
        "preferred_contact_method": random.choice(CONTACT_METHODS),
        "registered_practice_code": "L83120",
        "status": random.choice(STATUSES),
    }


def generate_patients(count: int = 10) -> list[dict]:
    used_nhs_numbers: set[str] = set()
    return [generate_patient(i, used_nhs_numbers) for i in range(count)]


if __name__ == "__main__":
    patients = generate_patients(10)
    print(json.dumps(patients, indent=2))
