# =============================================================================
# NHS number utilities (modulus‑11 validation + unique valid number generation)
# =============================================================================
# NOTE (Purpose):
# - Implements the official NHS modulus‑11 check‑digit algorithm via
#   `calculate_nhs_check_digit`, providing a single, reusable source of truth
#   for validating NHS numbers across the entire service.
#
# - Designed so that schema-level validators, service-layer checks, and data
#   generators all call the same function, eliminating duplication and ensuring
#   the validation logic cannot drift over time.
#
# - `generate_valid_nhs_number()` produces synthetically valid NHS numbers by
#   generating a 9‑digit prefix and computing the correct check digit. Invalid
#   combinations (where the check digit would be 10) are automatically skipped.
#
# - `generate_unique_valid_nhs_numbers(count)` generates large batches of
#   collision‑free, valid NHS numbers suitable for seed data, synthetic patient
#   datasets, and load‑testing scenarios.
#
# - The check‑digit function is intentionally small, deterministic, and easily
#   unit‑testable, making it suitable for both validation and generation paths.
#
# - Intended for development and testing environments only; production systems
#   should rely on externally issued NHS numbers rather than generating them.

import random


def calculate_nhs_check_digit(first_nine_digits: str) -> int | None:
    """Return the NHS check digit for a 9-digit prefix.

    Returns None when the prefix produces an invalid check digit result
    (i.e. calculated check digit would be 10).
    """
    if len(first_nine_digits) != 9 or not first_nine_digits.isdigit():
        return None

    weights = [10, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(
        int(digit) * weight for digit, weight in zip(first_nine_digits, weights)
    )
    remainder = total % 11
    check_digit = 11 - remainder

    if check_digit == 11:
        return 0
    if check_digit == 10:
        return None

    return check_digit


def generate_valid_nhs_number() -> str:
    while True:
        first_nine = "".join(str(random.randint(0, 9)) for _ in range(9))
        check_digit = calculate_nhs_check_digit(first_nine)
        if check_digit is not None:
            return f"{first_nine}{check_digit}"


def generate_unique_valid_nhs_numbers(count: int) -> list[str]:
    numbers: set[str] = set()

    while len(numbers) < count:
        numbers.add(generate_valid_nhs_number())

    return list(numbers)
