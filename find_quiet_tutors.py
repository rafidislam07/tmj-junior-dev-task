import csv
import re
from datetime import datetime, date
from difflib import SequenceMatcher

TODAY = date(2026, 5, 29)
QUIET_DAYS = 21
CUTOFF_DATE = TODAY.toordinal() - QUIET_DAYS


def clean(value):
    return (value or "").strip()


def normalize_name(name):
    name = clean(name).lower()
    name = re.sub(r"[^a-z\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def parse_date(value):
    value = clean(value)

    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%d %b %Y",
        "%d %B %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass

    return None


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def load_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def get_field(row, possible_names):
    lowered = {k.lower().strip(): v for k, v in row.items()}

    for name in possible_names:
        if name.lower() in lowered:
            return lowered[name.lower()]

    return ""


tutors = load_csv("tutors.csv")
sessions = load_csv("sessions.csv")

# Build tutor lookup
tutor_lookup = {}
tutor_records = {}

for tutor in tutors:
    tutor_id = clean(get_field(tutor, ["tutor_id", "id"]))
    name = clean(get_field(tutor, ["name", "tutor_name"]))
    subject = clean(get_field(tutor, ["subject"]))
    email = clean(get_field(tutor, ["email"]))
    phone = clean(get_field(tutor, ["phone", "phone_number"]))

    norm_name = normalize_name(name)

    if tutor_id:
        tutor_records[tutor_id] = {
            "tutor_id": tutor_id,
            "name": name,
            "subject": subject,
            "email": email,
            "phone": phone,
            "last_session": None,
            "matched_session_names": set(),
            "match_confidence": "none",
        }

    if norm_name and tutor_id:
        tutor_lookup[norm_name] = tutor_id


unmatched_sessions = []

for session in sessions:
    session_name = clean(get_field(session, ["tutor_name", "name", "tutor"]))
    session_date_raw = get_field(session, ["date", "session_date"])
    session_date = parse_date(session_date_raw)

    if not session_name or not session_date:
        continue

    norm_session_name = normalize_name(session_name)

    matched_tutor_id = None
    confidence = "none"

    # 1. Exact normalized name match
    if norm_session_name in tutor_lookup:
        matched_tutor_id = tutor_lookup[norm_session_name]
        confidence = "exact"
    else:
        # 2. Fuzzy match for messy real-world names
        best_score = 0
        best_tutor_id = None

        for roster_name, tutor_id in tutor_lookup.items():
            score = similarity(norm_session_name, roster_name)

            if score > best_score:
                best_score = score
                best_tutor_id = tutor_id

        if best_score >= 0.84:
            matched_tutor_id = best_tutor_id
            confidence = f"fuzzy_{best_score:.2f}"

    if matched_tutor_id and matched_tutor_id in tutor_records:
        record = tutor_records[matched_tutor_id]

        if record["last_session"] is None or session_date > record["last_session"]:
            record["last_session"] = session_date

        record["matched_session_names"].add(session_name)

        if record["match_confidence"] == "none" or confidence == "exact":
            record["match_confidence"] = confidence
    else:
        unmatched_sessions.append({
            "session_tutor_name": session_name,
            "session_date": session_date.isoformat(),
            "reason": "No confident roster match",
        })


quiet_tutors = []
no_session_tutors = []

for tutor_id, record in tutor_records.items():
    last_session = record["last_session"]

    if last_session is None:
        no_session_tutors.append({
            **record,
            "last_session": "",
            "days_since_last_session": "",
            "status": "no matched sessions found",
            "matched_session_names": "",
        })
        continue

    days_since = (TODAY - last_session).days

    if days_since >= QUIET_DAYS:
        quiet_tutors.append({
            **record,
            "last_session": last_session.isoformat(),
            "days_since_last_session": days_since,
            "status": "quiet",
            "matched_session_names": "; ".join(sorted(record["matched_session_names"])),
        })


quiet_tutors.sort(key=lambda x: x["days_since_last_session"], reverse=True)

with open("quiet_tutors.csv", "w", newline="", encoding="utf-8") as f:
    fieldnames = [
        "tutor_id",
        "name",
        "phone",
        "email",
        "subject",
        "last_session",
        "days_since_last_session",
        "status",
        "match_confidence",
        "matched_session_names",
    ]

    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for row in quiet_tutors:
        writer.writerow(row)

with open("no_session_tutors.csv", "w", newline="", encoding="utf-8") as f:
    fieldnames = [
        "tutor_id",
        "name",
        "phone",
        "email",
        "subject",
        "last_session",
        "days_since_last_session",
        "status",
        "match_confidence",
        "matched_session_names",
    ]

    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for row in no_session_tutors:
        writer.writerow(row)

with open("unmatched_sessions.csv", "w", newline="", encoding="utf-8") as f:
    fieldnames = ["session_tutor_name", "session_date", "reason"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for row in unmatched_sessions:
        writer.writerow(row)


print(f"Quiet tutors found: {len(quiet_tutors)}")
print(f"Tutors with no matched sessions: {len(no_session_tutors)}")
print(f"Unmatched session rows: {len(unmatched_sessions)}")
print("Created: quiet_tutors.csv, no_session_tutors.csv, unmatched_sessions.csv")
