import csv
import re
from datetime import datetime, date
from difflib import SequenceMatcher


TODAY = date(2026, 5, 29)
QUIET_DAYS = 21
FUZZY_MATCH_THRESHOLD = 0.84

SESSIONS_FILE = "sessions.csv"
TUTORS_FILE = "tutors.csv"

QUIET_OUTPUT_FILE = "quiet_tutors.csv"
NO_SESSION_OUTPUT_FILE = "no_session_tutors.csv"
UNMATCHED_OUTPUT_FILE = "unmatched_sessions.csv"


DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%d %b %Y",
    "%d %B %Y",
]


def clean(value):
    return (value or "").strip()


def normalize_header(header):
    header = clean(header).lower()
    header = re.sub(r"[^a-z0-9]+", "_", header)
    return header.strip("_")


def normalize_name(name):
    name = clean(name).lower()
    name = re.sub(r"[^a-z\s]", " ", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def parse_date(value):
    value = clean(value)

    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue

    return None


def similarity(left, right):
    return SequenceMatcher(None, left, right).ratio()


def load_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def get_field(row, possible_names):
    normalized_row = {
        normalize_header(key): value
        for key, value in row.items()
    }

    for name in possible_names:
        normalized_name = normalize_header(name)

        if normalized_name in normalized_row:
            return normalized_row[normalized_name]

    return ""


def build_tutor_records(tutors):
    tutor_records = {}
    tutor_lookup_by_name = {}

    for tutor in tutors:
        tutor_id = clean(get_field(tutor, ["tutor_id", "id"]))
        name = clean(get_field(tutor, ["name", "tutor_name"]))
        phone = clean(get_field(tutor, ["phone", "phone_number"]))
        email = clean(get_field(tutor, ["email"]))
        subject = clean(get_field(tutor, ["subject"]))

        if not tutor_id:
            continue

        tutor_records[tutor_id] = {
            "tutor_id": tutor_id,
            "name": name,
            "phone": phone,
            "email": email,
            "subject": subject,
            "last_session": None,
            "matched_session_names": set(),
            "match_confidence": "none",
        }

        normalized_name = normalize_name(name)

        if normalized_name:
            tutor_lookup_by_name[normalized_name] = tutor_id

    return tutor_records, tutor_lookup_by_name


def match_tutor_id(session_name, tutor_lookup_by_name):
    normalized_session_name = normalize_name(session_name)

    if not normalized_session_name:
        return None, "none"

    if normalized_session_name in tutor_lookup_by_name:
        return tutor_lookup_by_name[normalized_session_name], "exact"

    best_score = 0
    best_tutor_id = None

    for roster_name, tutor_id in tutor_lookup_by_name.items():
        score = similarity(normalized_session_name, roster_name)

        if score > best_score:
            best_score = score
            best_tutor_id = tutor_id

    if best_score >= FUZZY_MATCH_THRESHOLD:
        return best_tutor_id, f"fuzzy_{best_score:.2f}"

    return None, "none"


def update_latest_session(record, session_date, session_name, confidence):
    if record["last_session"] is None or session_date > record["last_session"]:
        record["last_session"] = session_date

    record["matched_session_names"].add(session_name)

    if record["match_confidence"] == "none" or confidence == "exact":
        record["match_confidence"] = confidence


def analyse_sessions(sessions, tutor_records, tutor_lookup_by_name):
    unmatched_sessions = []

    for session in sessions:
        session_name = clean(get_field(session, ["tutor_name", "name", "tutor"]))
        session_date_raw = get_field(session, ["date", "session_date"])
        session_date = parse_date(session_date_raw)

        if not session_name or session_date is None:
            unmatched_sessions.append({
                "session_tutor_name": session_name,
                "session_date": session_date_raw,
                "reason": "Missing or invalid tutor name/date",
            })
            continue

        matched_tutor_id, confidence = match_tutor_id(
            session_name,
            tutor_lookup_by_name
        )

        if matched_tutor_id and matched_tutor_id in tutor_records:
            update_latest_session(
                tutor_records[matched_tutor_id],
                session_date,
                session_name,
                confidence,
            )
        else:
            unmatched_sessions.append({
                "session_tutor_name": session_name,
                "session_date": session_date.isoformat(),
                "reason": "No confident roster match",
            })

    return unmatched_sessions


def build_output_rows(tutor_records):
    quiet_tutors = []
    no_session_tutors = []

    for record in tutor_records.values():
        last_session = record["last_session"]

        base_row = {
            "tutor_id": record["tutor_id"],
            "name": record["name"],
            "phone": record["phone"],
            "email": record["email"],
            "subject": record["subject"],
            "match_confidence": record["match_confidence"],
            "matched_session_names": "; ".join(
                sorted(record["matched_session_names"])
            ),
        }

        if last_session is None:
            no_session_tutors.append({
                **base_row,
                "last_session": "",
                "days_since_last_session": "",
                "status": "no matched sessions found",
            })
            continue

        days_since_last_session = (TODAY - last_session).days

        if days_since_last_session >= QUIET_DAYS:
            quiet_tutors.append({
                **base_row,
                "last_session": last_session.isoformat(),
                "days_since_last_session": days_since_last_session,
                "status": "quiet",
            })

    quiet_tutors.sort(
        key=lambda row: row["days_since_last_session"],
        reverse=True,
    )

    no_session_tutors.sort(key=lambda row: row["name"])

    return quiet_tutors, no_session_tutors


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    tutors = load_csv(TUTORS_FILE)
    sessions = load_csv(SESSIONS_FILE)

    tutor_records, tutor_lookup_by_name = build_tutor_records(tutors)
    unmatched_sessions = analyse_sessions(
        sessions,
        tutor_records,
        tutor_lookup_by_name,
    )

    quiet_tutors, no_session_tutors = build_output_rows(tutor_records)

    tutor_output_fields = [
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

    write_csv(QUIET_OUTPUT_FILE, quiet_tutors, tutor_output_fields)
    write_csv(NO_SESSION_OUTPUT_FILE, no_session_tutors, tutor_output_fields)
    write_csv(
        UNMATCHED_OUTPUT_FILE,
        unmatched_sessions,
        ["session_tutor_name", "session_date", "reason"],
    )

    print(f"Quiet tutors found: {len(quiet_tutors)}")
    print(f"Tutors with no matched sessions: {len(no_session_tutors)}")
    print(f"Unmatched session rows: {len(unmatched_sessions)}")
    print(
        "Created: "
        f"{QUIET_OUTPUT_FILE}, "
        f"{NO_SESSION_OUTPUT_FILE}, "
        f"{UNMATCHED_OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
