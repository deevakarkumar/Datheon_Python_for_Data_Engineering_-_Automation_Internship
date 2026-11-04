"""
Sample Messy Dataset Generator
------------------------------
Generates a realistic synthetic customer dataset (125 records) containing
intentional real-world data quality anomalies for testing the Automated
Data Cleaning & Schema Transformation pipeline.

Anomalies included:
- Inconsistent and whitespace-padded column headers
- Leading/trailing whitespaces in string fields
- Missing values (critical fields like customer name, and non-critical fields)
- Outliers and invalid values (negative age, age > 120, negative salaries)
- Diverse currency representations (₹, INR, Rs., $, commas, decimals)
- Mixed date formats (DD-MM-YYYY, YYYY/MM/DD, DD Mon YYYY, YYYY-MM-DD, corrupt dates)
- Exact duplicates and primary key duplicates
- Boolean inconsistencies ('yes', 'no', 'TRUE', 'False', '1', '0')
- Sparsely populated columns (>90% missing)
"""

import csv
import random
from pathlib import Path


def generate_dataset(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    headers = [
        "Cust_ID ",
        " Customer Name",
        " Age",
        "Email_Address ",
        "Phone Number",
        "Annual Income ",
        "Join_Date",
        "City ",
        "Active Status",
        "Notes"
    ]

    first_names = [
        "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan",
        "Krishna", "Ishaan", "Diya", "Saanvi", "Ananya", "Aadhya", "Pari", "Chiara",
        "Rohan", "Pooja", "Vikram", "Sneha", "Rahul", "Priya", "Amit", "Neha"
    ]
    last_names = [
        "Sharma", "Verma", "Patel", "Mehta", "Reddy", "Nair", "Iyer", "Gupta",
        "Singh", "Kumar", "Rao", "Joshi", "Bose", "Chatterjee", "Chopra", "Das"
    ]
    cities = ["Mumbai", "Bengaluru", "Delhi", "Hyderabad", "Pune", "Chennai", "Kolkata", "Ahmedabad"]

    raw_currencies = [
        "₹{:,}", "INR {:,}", "{:,} INR", "Rs. {:,}", "{:,}.00", "₹ {:,}.50", "Rs {:,}"
    ]

    dates_pool = [
        "2023-01-15", "15-01-2023", "2023/01/15", "15 Jan 2023",
        "2022-11-20", "20-11-2022", "2022/11/20", "20 Nov 2022",
        "2024-05-10", "10-05-2024", "2024/05/10", "10 May 2024",
        "2021-08-01", "01-08-2021", "2021/08/01", "01 Aug 2021",
        "2020-12-25", "25-12-2020", "2020/12/25", "25 Dec 2020"
    ]

    rows = []
    current_id = 1001

    random.seed(42)  # For deterministic generation

    for i in range(1, 116):
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        name = f"{fn} {ln}"
        age = random.randint(22, 65)
        email = f"{fn.lower()}.{ln.lower()}{random.randint(10, 99)}@example.com"
        phone = f"+91-{random.randint(7000000000, 9999999999)}"
        base_salary = random.randint(35000, 220000)
        curr_fmt = random.choice(raw_currencies)
        salary = curr_fmt.format(base_salary)
        join_date = random.choice(dates_pool)
        city = random.choice(cities)
        status = random.choice(["TRUE", "true", "yes", "Y", "1", "FALSE", "false", "no", "N", "0"])
        notes = ""  # Sparse

        # Inoculate specific data quality anomalies on specific records
        if i in (5, 32):
            name = "   "  # Missing name (critical field)
        elif i in (12, 45):
            name = f"  {name}  "  # Whitespace padding
        
        if i in (8, 62):
            age = ""  # Missing age
        elif i == 19:
            age = -4  # Invalid negative age
        elif i == 77:
            age = 165  # Outlier impossible age
        elif i == 93:
            age = 14  # Minor below min limit 18

        if i in (14, 55):
            salary = ""  # Missing salary
        elif i == 23:
            salary = "-₹45,000"  # Negative salary
        elif i == 88:
            salary = "Rs. -20,000"  # Negative salary with Rs.
        elif i == 102:
            salary = "UNKNOWN_VAL"  # Invalid non-numeric salary

        if i in (10, 50):
            join_date = "99/99/9999"  # Completely invalid date
        elif i == 35:
            join_date = "not_a_date"  # Text date
        elif i == 70:
            join_date = ""  # Missing date

        if i in (17, 80):
            city = ""  # Missing categorical value
        elif i == 28:
            city = "  Bengaluru  "  # Whitespace in categorical

        if i in (4, 40):
            email = "invalid-email-format"  # Invalid email format
        elif i in (15, 60):
            notes = "Special VIP customer account"  # Sparse column content

        row = [
            str(current_id),
            name,
            str(age),
            email,
            phone,
            salary,
            join_date,
            city,
            status,
            notes
        ]
        rows.append(row)
        current_id += 1

    # Inject Exact Duplicates (e.g. repeat row 3 and row 25)
    rows.append(list(rows[3]))
    rows.append(list(rows[25]))
    rows.append(list(rows[50]))

    # Inject Duplicate Primary Key with slightly altered details
    dup_pk_row = list(rows[10])
    dup_pk_row[1] = "Altered Name Duplicate"
    rows.append(dup_pk_row)

    dup_pk_row_2 = list(rows[20])
    dup_pk_row_2[5] = "₹999,999"
    rows.append(dup_pk_row_2)

    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"Generated {len(rows)} rows into {output_path}")


if __name__ == "__main__":
    target = Path(__file__).resolve().parent.parent / "data" / "raw" / "sample_messy_data.csv"
    generate_dataset(target)
