"""
Marketing Planning App - GUI Version
=====================================
Roles:
  ADMIN  - Can view all client profiles and all appointments, update the
           status of any appointment, check clients in before room entry, and enforce no-show bans, and
           create additional admin accounts. Admins cannot delete client
           profiles or appointments, and cannot edit a client's profile
           details directly.
  CLIENT - Can view/update their OWN profile (including changing or
           resetting their own password), and add/update their OWN
           appointments only.

On first run, you'll be asked to set up the first Admin account (ID, Name, Password).
Additional admins can be created afterwards from the Admin Dashboard.
Clients register their own profile (Name, Email, Phone, Password, Company, Industry)
and then log in using their registered Email + Password to manage their own
details/appointments. A "Forgot password?" link on the login screen lets a
client reset their password via a one-time OTP.

Data is stored in local JSON files:
  admins.json        - admin accounts (id, name, password_hash)
  profiles.json       - client profiles (id, name, email, phone, password_hash,
                         company, industry, notes)
  appointments.json   - appointments (id, client_id, date, time, purpose, status)
"""

import json
import os
import re
import hashlib
import random
import calendar
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog

ADMIN_FILE = "admins.json"
PROFILES_FILE = "profiles.json"
APPOINTMENTS_FILE = "appointments.json"
AUDIT_FILE = "admin_audit.json"

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^\d{9,10}$")

MIN_PASSWORD_LENGTH = 8
MAX_NAME_LENGTH = 50
MAX_COMPANY_LENGTH = 50
MAX_INDUSTRY_LENGTH = 50
MAX_NOTES_LENGTH = 300
MAX_PURPOSE_LENGTH = 150
MAX_UNBAR_REASON_LENGTH = 300

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 60

OTP_LENGTH = 6
OTP_VALID_SECONDS = 300  # 5 minutes
MAX_OTP_ATTEMPTS = 5

NO_SHOW_GRACE_MINUTES = 15
BAR_DAYS = 3


# ----------------------------------------------------------------------
# Shared helpers
# ----------------------------------------------------------------------
def load_data(filename):
    """Load JSON data from disk. Returns [] (instead of crashing) if the
    file is missing, corrupted, or unreadable."""
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: could not read {filename} ({e}). Starting with empty data.")
            return []
    return []


def save_data(filename, data):
    """Save JSON data to disk. Returns True on success, False on failure
    (e.g. disk full, permissions issue) instead of raising and crashing
    the whole app."""
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
        return True
    except OSError as e:
        print(f"Warning: could not save {filename} ({e}).")
        return False


def next_id(records):
    return (max((r["id"] for r in records), default=0)) + 1


def hash_password(password):
    """Simple SHA-256 hash. Note: this is unsalted, so it is fine for a
    learning project but not for production use - a real system should
    use a salted hash (e.g. bcrypt/scrypt/argon2) to protect against
    rainbow-table attacks and to give identical passwords different
    stored hashes."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def is_valid_email(value):
    return bool(EMAIL_PATTERN.match(value))


def is_valid_phone(value):
    return bool(PHONE_PATTERN.match(value))


def is_valid_password(value):
    if len(value) < MIN_PASSWORD_LENGTH:
        return False
    has_letter = any(c.isalpha() for c in value)
    has_digit = any(c.isdigit() for c in value)
    return has_letter and has_digit


PASSWORD_REQUIREMENTS_MSG = (
    f"Password must be at least {MIN_PASSWORD_LENGTH} characters long "
    "and contain at least one letter and one number."
)


def generate_otp():
    """Generates a random numeric OTP (zero-padded), e.g. '048213'."""
    return str(random.randint(0, 10 ** OTP_LENGTH - 1)).zfill(OTP_LENGTH)


class LoginThrottle:
    """Tracks failed login attempts per key (e.g. admin ID or email) and
    temporarily locks a key out after too many failures in a row.
    This is in-memory only (resets when the app restarts) - good enough
    to slow down casual brute-forcing in a learning project."""

    def __init__(self, max_attempts=MAX_LOGIN_ATTEMPTS, lockout_seconds=LOCKOUT_SECONDS):
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self.failures = {}   # key -> number of consecutive failed attempts
        self.locked_until = {}  # key -> timestamp when lockout ends

    def is_locked_out(self, key):
        unlock_time = self.locked_until.get(key)
        if unlock_time is None:
            return False, 0
        remaining = unlock_time - datetime.now().timestamp()
        if remaining <= 0:
            # Lockout period has passed - clear it
            del self.locked_until[key]
            self.failures[key] = 0
            return False, 0
        return True, int(remaining)

    def register_failure(self, key):
        self.failures[key] = self.failures.get(key, 0) + 1
        if self.failures[key] >= self.max_attempts:
            self.locked_until[key] = datetime.now().timestamp() + self.lockout_seconds

    def register_success(self, key):
        self.failures[key] = 0
        self.locked_until.pop(key, None)


# ----------------------------------------------------------------------
# Admin Accounts
# ----------------------------------------------------------------------
class AdminManager:
    def __init__(self):
        self.records = load_data(ADMIN_FILE)
        self.throttle = LoginThrottle()

    def save(self):
        return save_data(ADMIN_FILE, self.records)

    def ensure_admin_exists(self):
        """On first run (no admin accounts yet), walk the user through
        creating the first Admin account."""
        if self.records:
            return

        # This will be handled by GUI now
        return None

    def find_by_name(self, name):
        name = name.strip().lower()
        return next((a for a in self.records if a["name"].lower() == name), None)

    def add_admin(self, name, password):
        """Register an additional admin account (beyond the first)."""
        admin = {
            "id": next_id(self.records),
            "name": name,
            "password_hash": hash_password(password),
        }
        self.records.append(admin)
        if not self.save():
            self.records.remove(admin)
            return None, "Could not save the new admin account. Please try again."
        return admin, None

    def login(self, admin_id, password):
        locked, remaining = self.throttle.is_locked_out(admin_id)
        if locked:
            return None, f"Too many failed attempts. Try again in {remaining} second(s)."

        record = next((a for a in self.records if a["id"] == admin_id), None)
        if not record or record["password_hash"] != hash_password(password):
            self.throttle.register_failure(admin_id)
            return None, "Invalid Admin ID or password."

        self.throttle.register_success(admin_id)
        return record, None

    def get_admin(self, admin_id):
        return next((a for a in self.records if a["id"] == admin_id), None)


# ----------------------------------------------------------------------
# B. Client Profile Management
# ----------------------------------------------------------------------
class ProfileManager:
    def __init__(self):
        self.records = load_data(PROFILES_FILE)
        self.throttle = LoginThrottle()
        self.pending_otps = {}  # email (lowercase) -> {"otp": str, "expires": ts, "attempts": int}

    def save(self):
        return save_data(PROFILES_FILE, self.records)

    def get_profile(self, client_id):
        return next((r for r in self.records if r["id"] == client_id), None)

    def find_by_email(self, email):
        email = email.strip().lower()
        return next((r for r in self.records if r["email"].lower() == email), None)

    def find_by_phone(self, phone):
        return next((r for r in self.records if r["phone"] == phone), None)

    def add_profile(self, name, email, phone, password, company="", industry=""):
        if self.find_by_email(email):
            return None, "An account with this email already exists."
        if self.find_by_phone(phone):
            return None, "An account with this phone number already exists."
        if not is_valid_password(password):
            return None, PASSWORD_REQUIREMENTS_MSG

        profile = {
            "id": next_id(self.records),
            "name": name,
            "email": email,
            "phone": phone,
            "password_hash": hash_password(password),
            "company": company,
            "industry": industry,
            "notes": "",
        }
        self.records.append(profile)
        if not self.save():
            self.records.remove(profile)
            return None, "Could not save your profile. Please try again."
        return profile, None

    def login(self, email, password):
        key = email.strip().lower()
        locked, remaining = self.throttle.is_locked_out(key)
        if locked:
            return None, f"Too many failed attempts. Try again in {remaining} second(s)."

        profile = self.find_by_email(email)
        if not profile:
            self.throttle.register_failure(key)
            return None, "No profile found with that email. Please register first."
        if profile.get("password_hash") != hash_password(password):
            self.throttle.register_failure(key)
            return None, "Incorrect password."

        self.throttle.register_success(key)
        return profile, None

    def change_password(self, client_id, new_password):
        profile = self.get_profile(client_id)
        if not profile:
            return False, "Profile not found."
        if not is_valid_password(new_password):
            return False, PASSWORD_REQUIREMENTS_MSG
        old_hash = profile["password_hash"]
        profile["password_hash"] = hash_password(new_password)
        if not self.save():
            profile["password_hash"] = old_hash
            return False, "Could not save the new password. Please try again."
        return True, "Password updated successfully."

    def request_password_reset(self, email):
        """Generates a one-time OTP for the given email and stores it
        in-memory with an expiry. Returns (otp, None) on success or
        (None, error) if no account matches the email."""
        profile = self.find_by_email(email)
        if not profile:
            return None, "No profile found with that email."

        key = email.strip().lower()
        otp = generate_otp()
        self.pending_otps[key] = {
            "otp": otp,
            "expires": datetime.now().timestamp() + OTP_VALID_SECONDS,
            "attempts": 0,
        }
        return otp, None

    def verify_otp_and_reset(self, email, otp_entered, new_password):
        """Verifies the OTP for the given email and, if correct and not
        expired, resets the password. Limits OTP guesses separately from
        the login lockout so someone can't brute-force the OTP either."""
        key = email.strip().lower()
        entry = self.pending_otps.get(key)
        if not entry:
            return False, "No password reset was requested for this email. Please request a new OTP."

        if datetime.now().timestamp() > entry["expires"]:
            del self.pending_otps[key]
            return False, "This OTP has expired. Please request a new one."

        if entry["attempts"] >= MAX_OTP_ATTEMPTS:
            del self.pending_otps[key]
            return False, "Too many incorrect OTP attempts. Please request a new one."

        if otp_entered.strip() != entry["otp"]:
            entry["attempts"] += 1
            remaining = MAX_OTP_ATTEMPTS - entry["attempts"]
            return False, f"Incorrect OTP. {remaining} attempt(s) remaining."

        if not is_valid_password(new_password):
            return False, PASSWORD_REQUIREMENTS_MSG

        profile = self.find_by_email(email)
        if not profile:
            del self.pending_otps[key]
            return False, "Profile no longer exists."

        old_hash = profile["password_hash"]
        profile["password_hash"] = hash_password(new_password)
        if not self.save():
            profile["password_hash"] = old_hash
            return False, "Could not save the new password. Please try again."

        del self.pending_otps[key]
        self.throttle.register_success(key)  # clear any login lockout too
        return True, "Password reset successfully. You can now log in with your new password."

    def update_profile(self, client_id, updates):
        """Applies multiple field updates atomically - either everything in
        `updates` is saved together, or nothing is. This avoids ending up
        with a half-updated profile if a duplicate check fails or the save
        itself fails partway through a multi-field edit."""
        profile = self.get_profile(client_id)
        if not profile:
            return False, "Profile not found."

        if "email" in updates:
            new_email = updates["email"]
            if new_email.lower() != profile["email"].lower():
                existing = self.find_by_email(new_email)
                if existing and existing["id"] != client_id:
                    return False, "That email is already used by another profile."

        if "phone" in updates:
            new_phone = updates["phone"]
            if new_phone != profile["phone"]:
                existing = self.find_by_phone(new_phone)
                if existing and existing["id"] != client_id:
                    return False, "That phone number is already used by another profile."

        previous_values = {field: profile.get(field) for field in updates}
        profile.update(updates)

        if not self.save():
            profile.update(previous_values)
            return False, "Could not save your changes. Please try again."

        return True, "Profile updated successfully."

    def get_all_profiles(self):
        return self.records

    def search_profiles(self, keyword):
        keyword = keyword.strip().lower()
        if not keyword:
            return self.records
        return [
            r for r in self.records
            if keyword in r["name"].lower()
            or keyword in r["email"].lower()
            or keyword in r["company"].lower()
        ]


# ----------------------------------------------------------------------
# A. Client Appointment Management
# ----------------------------------------------------------------------
class AppointmentManager:
    def __init__(self):
        self.records = load_data(APPOINTMENTS_FILE)
        self.audit_records = load_data(AUDIT_FILE)
        self._refresh_appointment_statuses()

    def save(self):
        return save_data(APPOINTMENTS_FILE, self.records)

    def save_audit(self):
        return save_data(AUDIT_FILE, self.audit_records)

    def _log_admin_action(self, admin_id, action, appointment=None, client_id=None, reason=""):
        """Store an admin action in a separate audit file."""
        entry = {
            "id": next_id(self.audit_records),
            "timestamp": datetime.now().isoformat(timespec="minutes"),
            "admin_id": admin_id,
            "action": action,
            "appointment_id": appointment.get("id") if appointment else None,
            "client_id": client_id if client_id is not None else (appointment.get("client_id") if appointment else None),
            "reason": reason.strip() if reason else "",
        }
        self.audit_records.append(entry)
        if not self.save_audit():
            self.audit_records.remove(entry)
            return False
        return True

    def get_audit_history(self):
        return sorted(self.audit_records, key=lambda x: x.get("timestamp", ""), reverse=True)

    def get_statistics(self):
        self._refresh_appointment_statuses()
        statuses = {"Scheduled": 0, "Checked In": 0, "Completed": 0, "Missed": 0, "Cancelled": 0}
        for record in self.records:
            status = record.get("status")
            if status in statuses:
                statuses[status] += 1
        barred_clients = sum(1 for client_id in {r.get("client_id") for r in self.records if r.get("client_id") is not None}
                             if self.get_barred_until(client_id))
        statuses["Barred Clients"] = barred_clients
        return statuses

    def _client_display_name(self, client_id, profile_manager):
        profile = profile_manager.get_profile(client_id)
        return profile["name"] if profile else "Unknown / Deleted Client"

    def _appointment_datetime(self, record):
        try:
            return datetime.strptime(f"{record['date']} {record['time']}", "%Y-%m-%d %H:%M")
        except (ValueError, KeyError):
            return None

    def _refresh_appointment_statuses(self):
        """Automatically mark unattended appointments as Missed.

        Scheduled appointments receive a short grace period. If no admin has
        checked the client in by then, the appointment becomes Missed. Checked-in
        appointments remain Checked In until an admin manually marks them Completed.
        """
        now = datetime.now()
        changed = False
        for record in self.records:
            appointment_dt = self._appointment_datetime(record)
            if appointment_dt is None:
                continue

            if record.get("status") == "Scheduled":
                no_show_time = appointment_dt + timedelta(minutes=NO_SHOW_GRACE_MINUTES)
                if now >= no_show_time:
                    record["status"] = "Missed"
                    record["missed_at"] = no_show_time.isoformat(timespec="minutes")
                    changed = True
            # Checked In appointments are not completed automatically.
            # The admin must manually change them to Completed after service ends.

        if changed:
            self.save()

    def get_barred_until(self, client_id):
        """Return the end of the client's latest active no-show ban."""
        self._refresh_appointment_statuses()
        barred_until = None
        for record in self.records:
            if record.get("client_id") != client_id or record.get("status") != "Missed":
                continue
            # An admin may waive the penalty for a reasonable, recorded reason.
            # The appointment remains Missed for history, but no longer creates a ban.
            if record.get("bar_waived") is True:
                continue

            missed_at_text = record.get("missed_at")
            try:
                missed_at = datetime.fromisoformat(missed_at_text) if missed_at_text else None
            except ValueError:
                missed_at = None
            if missed_at is None:
                appointment_dt = self._appointment_datetime(record)
                if appointment_dt is None:
                    continue
                missed_at = appointment_dt + timedelta(minutes=NO_SHOW_GRACE_MINUTES)

            candidate = missed_at + timedelta(days=BAR_DAYS)
            if barred_until is None or candidate > barred_until:
                barred_until = candidate

        return barred_until if barred_until and barred_until > datetime.now() else None

    def unbar_client(self, client_id, reason, admin_id):
        """Waive every currently active no-show penalty for a client.

        The missed appointment records are kept for audit/history. Each waived
        record stores the admin ID, reason, and waiver time.
        """
        self._refresh_appointment_statuses()
        reason = reason.strip()
        if not reason:
            return False, "A reason is required before unbarring a client."
        if len(reason) > MAX_UNBAR_REASON_LENGTH:
            return False, f"Reason must be {MAX_UNBAR_REASON_LENGTH} characters or fewer."

        if self.get_barred_until(client_id) is None:
            return False, "This client is not currently barred."

        now = datetime.now()
        changed_records = []
        for record in self.records:
            if record.get("client_id") != client_id or record.get("status") != "Missed":
                continue
            if record.get("bar_waived") is True:
                continue

            missed_at_text = record.get("missed_at")
            try:
                missed_at = datetime.fromisoformat(missed_at_text) if missed_at_text else None
            except ValueError:
                missed_at = None
            if missed_at is None:
                appointment_dt = self._appointment_datetime(record)
                if appointment_dt is None:
                    continue
                missed_at = appointment_dt + timedelta(minutes=NO_SHOW_GRACE_MINUTES)

            if missed_at + timedelta(days=BAR_DAYS) > now:
                old = dict(record)
                record["bar_waived"] = True
                record["unbar_reason"] = reason
                record["unbarred_at"] = now.isoformat(timespec="minutes")
                record["unbarred_by_admin_id"] = admin_id
                changed_records.append((record, old))

        if not changed_records:
            return False, "No active missed-appointment penalty was found for this client."

        if not self.save():
            for record, old in changed_records:
                record.clear()
                record.update(old)
            return False, "Could not save the unbar action. Please try again."

        self._log_admin_action(
            admin_id, "Unbarred Client", client_id=client_id, reason=reason
        )

        return True, (
            f"Client ID {client_id} has been unbarred successfully. "
            f"Reason recorded: {reason}"
        )

    def get_client_appointments(self, client_id):
        self._refresh_appointment_statuses()
        return [r for r in self.records if r["client_id"] == client_id]

    def has_conflict(self, date_str, time_str, exclude_app_id=None):
        self._refresh_appointment_statuses()
        for record in self.records:
            if record["id"] == exclude_app_id:
                continue
            if record.get("status") not in ("Scheduled", "Checked In"):
                continue
            if record["date"] == date_str and record["time"] == time_str:
                return True
        return False

    def add_appointment(self, client_id, date_str, time_str, purpose):
        self._refresh_appointment_statuses()
        barred_until = self.get_barred_until(client_id)
        if barred_until:
            return None, (
                "You are temporarily barred because of a missed appointment. "
                f"You cannot make an appointment until {barred_until.strftime('%Y-%m-%d %H:%M')}."
            )

        try:
            appointment_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            return None, "Invalid date or time format."

        if appointment_dt < datetime.now():
            return None, "Appointment date/time cannot be in the past."
        if self.has_conflict(date_str, time_str):
            return None, (
                f"There is already an appointment scheduled for {date_str} at {time_str}. "
                "Please choose a different date or time."
            )

        appointment = {
            "id": next_id(self.records), "client_id": client_id,
            "date": date_str, "time": time_str, "purpose": purpose,
            "status": "Scheduled"
        }
        self.records.append(appointment)
        if not self.save():
            self.records.remove(appointment)
            return None, "Could not save the appointment. Please try again."
        return appointment, None

    def update_appointment(self, app_id, client_id, date_str=None, time_str=None, purpose=None, status=None):
        self._refresh_appointment_statuses()
        record = next((r for r in self.records if r["id"] == app_id and r["client_id"] == client_id), None)
        if not record:
            return False, "Appointment not found, or it does not belong to you."
        if record.get("status") != "Scheduled":
            return False, "Only Scheduled appointments can be edited."

        barred_until = self.get_barred_until(client_id)
        if barred_until:
            return False, f"Your account is barred until {barred_until.strftime('%Y-%m-%d %H:%M')}."

        previous = dict(record)
        if date_str:
            record["date"] = date_str
        if time_str:
            record["time"] = time_str
        if purpose:
            record["purpose"] = purpose

        new_dt = self._appointment_datetime(record)
        if new_dt is None:
            record.clear(); record.update(previous)
            return False, "Invalid date or time format."
        if new_dt < datetime.now():
            record.clear(); record.update(previous)
            return False, "Appointment date/time cannot be in the past."
        if (date_str or time_str) and self.has_conflict(record["date"], record["time"], app_id):
            record.clear(); record.update(previous)
            return False, "That date and time slot is already occupied."

        if not self.save():
            record.clear(); record.update(previous)
            return False, "Could not save your changes. Please try again."
        return True, "Appointment updated successfully."

    def check_in_client(self, app_id, admin_id=None):
        """Admin confirms that the client is physically present before entry."""
        self._refresh_appointment_statuses()
        record = next((r for r in self.records if r["id"] == app_id), None)
        if not record:
            return False, "Appointment not found."
        if record.get("status") != "Scheduled":
            return False, f"This appointment is already '{record.get('status')}'."

        barred_until = self.get_barred_until(record["client_id"])
        if barred_until:
            return False, (
                "Entry denied. This client is barred due to a missed appointment until "
                f"{barred_until.strftime('%Y-%m-%d %H:%M')}."
            )

        appointment_dt = self._appointment_datetime(record)
        if appointment_dt is None:
            return False, "Invalid appointment date/time."
        now = datetime.now()
        if now < appointment_dt:
            return False, (
                f"Check-in is not available yet. This appointment starts at "
                f"{appointment_dt.strftime('%Y-%m-%d %H:%M')}."
            )
        if now >= appointment_dt + timedelta(minutes=NO_SHOW_GRACE_MINUTES):
            self._refresh_appointment_statuses()
            return False, "The check-in grace period has passed. This appointment is Missed."

        record["status"] = "Checked In"
        record["checked_in_at"] = now.isoformat(timespec="minutes")
        if not self.save():
            record["status"] = "Scheduled"
            record.pop("checked_in_at", None)
            return False, "Could not save the check-in. Please try again."
        if admin_id is not None:
            record["checked_in_by_admin_id"] = admin_id
            self.save()
            self._log_admin_action(
                admin_id, "Checked In", appointment=record, reason="Client arrived and was admitted."
            )
        return True, f"Appointment #{app_id} checked in. Client may enter the room."

    def get_allowed_admin_statuses(self, record):
        """Return valid manual status changes for the appointment.

        Scheduled appointments may only be cancelled manually. Check-in must use
        the Check In Client action. Checked-in appointments may only be completed.
        Completed, Cancelled, and Missed appointments are final records.
        """
        current_status = record.get("status")
        if current_status == "Scheduled":
            return ("Cancelled",)
        if current_status == "Checked In":
            return ("Completed",)
        return ()

    def update_appointment_status_admin(self, app_id, new_status, admin_id=None, reason=""):
        self._refresh_appointment_statuses()
        record = next((r for r in self.records if r["id"] == app_id), None)
        if not record:
            return False, "Appointment not found."

        current_status = record.get("status")
        if new_status == "Checked In":
            return False, "Use the 'Check In Client' button to check in a scheduled client."

        allowed_statuses = self.get_allowed_admin_statuses(record)
        if new_status not in allowed_statuses:
            if current_status in ("Completed", "Cancelled", "Missed"):
                return False, f"'{current_status}' is a final status and cannot be changed."
            if current_status == "Scheduled":
                return False, "A Scheduled appointment can only be Cancelled manually. Use Check In Client for check-in."
            if current_status == "Checked In":
                return False, "A Checked In appointment can only be changed to Completed."
            return False, "This status change is not allowed."

        if new_status == "Cancelled" and not reason.strip():
            return False, "A cancellation reason is required."

        old = dict(record)
        record["status"] = new_status
        if new_status == "Completed":
            record["completed_at"] = datetime.now().isoformat(timespec="minutes")
            if admin_id is not None:
                record["completed_by_admin_id"] = admin_id
        elif new_status == "Cancelled":
            record["cancelled_at"] = datetime.now().isoformat(timespec="minutes")
            record["cancellation_reason"] = reason.strip()
            if admin_id is not None:
                record["cancelled_by_admin_id"] = admin_id

        if not self.save():
            record.clear()
            record.update(old)
            return False, "Could not save the status change. Please try again."
        if admin_id is not None:
            audit_reason = reason.strip() if new_status == "Cancelled" else "Appointment service finished."
            self._log_admin_action(admin_id, new_status, appointment=record, reason=audit_reason)
        return True, f"Appointment #{app_id} status updated to '{new_status}' successfully."

    def get_all_appointments(self, profile_manager=None):
        self._refresh_appointment_statuses()
        return sorted(self.records, key=lambda x: (x["date"], x["time"]))

    def search_appointments_by_client(self, keyword, profile_manager):
        self._refresh_appointment_statuses()
        keyword = keyword.strip().lower()
        matching_ids = {p["id"] for p in profile_manager.records if keyword in p["name"].lower()}
        matches = self.records if not keyword else [r for r in self.records if r["client_id"] in matching_ids]
        return sorted(matches, key=lambda x: (x["date"], x["time"]))

    def get_appointment_display(self, appointment, profile_manager):
        client_name = self._client_display_name(appointment["client_id"], profile_manager)
        barred_until = self.get_barred_until(appointment["client_id"])
        return {
            "id": appointment["id"],
            "client": f"{client_name} (ID {appointment['client_id']})",
            "client_id": appointment["client_id"],
            "date": appointment["date"], "time": appointment["time"],
            "purpose": appointment["purpose"], "status": appointment["status"],
            "barred_until": barred_until.strftime("%Y-%m-%d %H:%M") if barred_until else "-"
        }


# ----------------------------------------------------------------------
# GUI Application
# ----------------------------------------------------------------------

from admin_page import AdminPageMixin
from client_page import ClientPageMixin


class MarketingAppGUI(AdminPageMixin, ClientPageMixin):
    def __init__(self, root):
        self.root = root
        self.root.title("Marketing Planning App - Status Rules v4")
        self.root.geometry("800x600")
        
        # Initialize managers
        self.admin_manager = AdminManager()
        self.profile_manager = ProfileManager()
        self.appointment_manager = AppointmentManager()
        
        # Check if admin exists, if not create one
        self.ensure_first_admin()
        
        # Current session state
        self.current_user = None  # 'admin' or 'client'
        self.current_admin_id = None
        self.current_client_id = None
        
        # Setup GUI
        self.setup_styles()
        self.show_main_menu()


    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Title.TLabel', font=('Helvetica', 16, 'bold'))
        style.configure('Heading.TLabel', font=('Helvetica', 12, 'bold'))


    def clear_frame(self):
        for widget in self.root.winfo_children():
            widget.destroy()


    def _limit_entry_length(self, entry, max_length):
        """Stop an Entry widget from accepting more than max_length
        characters, so long input can't overflow the Treeview columns
        or bloat the JSON files."""
        vcmd = (self.root.register(lambda text: len(text) <= max_length), '%P')
        entry.configure(validate='key', validatecommand=vcmd)


    def _add_show_password_toggle(self, parent, entry, row, column):
        """Places a small 'Show' checkbox right after a password Entry
        widget that toggles it between masked (*) and plain text."""
        show_var = tk.BooleanVar(value=False)

        def toggle():
            entry.configure(show='' if show_var.get() else '*')

        check = ttk.Checkbutton(parent, text="Show", variable=show_var, command=toggle)
        check.grid(row=row, column=column, sticky='w', padx=(5, 0))
        return check


    def _add_show_password_toggle_pack(self, parent, entry, **pack_opts):
        """Same as _add_show_password_toggle but for containers using pack()
        instead of grid() (mixing managers on the same parent isn't allowed)."""
        show_var = tk.BooleanVar(value=False)

        def toggle():
            entry.configure(show='' if show_var.get() else '*')

        opts = {'pady': (0, 5)}
        opts.update(pack_opts)
        check = ttk.Checkbutton(parent, text="Show password", variable=show_var, command=toggle)
        check.pack(**opts)
        return check


    def _build_date_picker(self, parent, initial=None, years_ahead=2):
        """Builds a Year/Month/Day set of dropdowns (no free-typing, no
        invalid dates possible - the Day list is rebuilt to match the
        chosen month/year, including leap years). Returns (frame, get_date_str).
        get_date_str() returns the picked date as 'YYYY-MM-DD'."""
        frame = ttk.Frame(parent)
        
        today = datetime.now()
        initial_dt = today
        if initial:
            try:
                initial_dt = datetime.strptime(initial, "%Y-%m-%d")
            except ValueError:
                initial_dt = today
        
        years = [str(y) for y in range(today.year, today.year + years_ahead + 1)]
        year_var = tk.StringVar(value=str(initial_dt.year) if str(initial_dt.year) in years else years[0])
        year_combo = ttk.Combobox(frame, textvariable=year_var, values=years, width=6, state='readonly')
        year_combo.grid(row=0, column=0, padx=2)
        
        months = [f"{m:02d}" for m in range(1, 13)]
        month_var = tk.StringVar(value=f"{initial_dt.month:02d}")
        month_combo = ttk.Combobox(frame, textvariable=month_var, values=months, width=4, state='readonly')
        month_combo.grid(row=0, column=1, padx=2)
        
        day_var = tk.StringVar(value=f"{initial_dt.day:02d}")
        day_combo = ttk.Combobox(frame, textvariable=day_var, width=4, state='readonly')
        day_combo.grid(row=0, column=2, padx=2)
        
        def refresh_days(*_args):
            year_val = int(year_var.get())
            month_val = int(month_var.get())
            days_in_month = calendar.monthrange(year_val, month_val)[1]
            day_values = [f"{d:02d}" for d in range(1, days_in_month + 1)]
            day_combo['values'] = day_values
            if day_var.get() not in day_values:
                day_var.set(day_values[-1])
        
        year_combo.bind('<<ComboboxSelected>>', refresh_days)
        month_combo.bind('<<ComboboxSelected>>', refresh_days)
        refresh_days()
        
        def get_date_str():
            return f"{year_var.get()}-{month_var.get()}-{day_var.get()}"
        
        return frame, get_date_str


    def _build_time_picker(self, parent, initial=None, minute_step=5):
        """Builds an Hour/Minute set of dropdowns (24-hour format, minutes in
        minute_step increments). Returns (frame, get_time_str) where
        get_time_str() returns the picked time as 'HH:MM'."""
        frame = ttk.Frame(parent)
        
        initial_dt = datetime.now()
        if initial:
            try:
                initial_dt = datetime.strptime(initial, "%H:%M")
            except ValueError:
                pass
        
        hours = [f"{h:02d}" for h in range(0, 24)]
        hour_var = tk.StringVar(value=f"{initial_dt.hour:02d}")
        hour_combo = ttk.Combobox(frame, textvariable=hour_var, values=hours, width=4, state='readonly')
        hour_combo.grid(row=0, column=0, padx=2)
        
        ttk.Label(frame, text=":").grid(row=0, column=1)
        
        minutes = [f"{m:02d}" for m in range(0, 60, minute_step)]
        rounded_minute = (initial_dt.minute // minute_step) * minute_step
        minute_var = tk.StringVar(value=f"{rounded_minute:02d}")
        minute_combo = ttk.Combobox(frame, textvariable=minute_var, values=minutes, width=4, state='readonly')
        minute_combo.grid(row=0, column=2, padx=2)
        
        def get_time_str():
            return f"{hour_var.get()}:{minute_var.get()}"
        
        return frame, get_time_str


    def show_main_menu(self):
        self.clear_frame()
        
        # Header
        header = ttk.Label(self.root, text="MARKETING PLANNING APP", style='Title.TLabel')
        header.pack(pady=30)
        
        # Main options
        frame = ttk.Frame(self.root)
        frame.pack(pady=50)
        
        ttk.Button(frame, text="Admin Login", command=self.show_admin_login, width=30).pack(pady=10)
        ttk.Button(frame, text="Client Login / Register", command=self.show_client_login, width=30).pack(pady=10)
        ttk.Button(frame, text="Exit", command=self.root.quit, width=30).pack(pady=10)



if __name__ == "__main__":
    root = tk.Tk()
    app = MarketingAppGUI(root)
    root.mainloop()
