"""
Verea Within — Backend API & static site server.

Serves the static frontend (site/) and provides a small JSON API backed by
SQLite for:
  - Package inquiries (from packages.html)
  - Consultation bookings (from consultation.html)

Run locally:
    pip install -r requirements.txt
    python app.py

Configuration is read from environment variables (see .env.example).
Email sending is optional — if SMTP settings are not provided, the API
still stores the data and responds successfully, it just skips the email.
"""
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SITE_DIR = os.path.join(BASE_DIR, "site")

app = Flask(__name__, static_folder=None)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'verea.db')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")

SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "verea.within@gmail.com")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "verea.within@gmail.com")


# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------

class Inquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    edd = db.Column(db.String(32))
    hospital = db.Column(db.String(160))
    package = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "edd": self.edd,
            "hospital": self.hospital,
            "package": self.package,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
        }


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    partner_name = db.Column(db.String(120))
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(64), nullable=False)
    edd = db.Column(db.String(32))
    language = db.Column(db.String(32))
    region = db.Column(db.String(160))
    care_interests = db.Column(db.String(255))
    note = db.Column(db.Text)
    meeting_type = db.Column(db.String(32))
    booking_date = db.Column(db.String(16), nullable=False)
    time_slot = db.Column(db.String(16), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("booking_date", "time_slot", name="uq_date_slot"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "partner_name": self.partner_name,
            "email": self.email,
            "phone": self.phone,
            "edd": self.edd,
            "language": self.language,
            "region": self.region,
            "care_interests": self.care_interests,
            "note": self.note,
            "meeting_type": self.meeting_type,
            "date": self.booking_date,
            "slot": self.time_slot,
            "created_at": self.created_at.isoformat(),
        }


with app.app_context():
    db.create_all()


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def email_configured():
    """True only if SMTP is set up with a real (non-placeholder) password."""
    return bool(
        SMTP_HOST
        and SMTP_USER
        and SMTP_PASS
        and "replace" not in (SMTP_PASS or "").lower()
    )


def send_email(to_addr, subject, body):
    """Best-effort email send. Returns True/False, never raises."""
    if not to_addr or not email_configured():
        app.logger.warning(
            "EMAIL SKIPPED (SMTP not configured — set a real Gmail App Password "
            "as SMTP_PASS in .env). Would have sent '%s' to %s",
            subject, to_addr,
        )
        return False
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = FROM_EMAIL
        msg["To"] = to_addr
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(FROM_EMAIL, [to_addr], msg.as_string())
        return True
    except Exception as exc:  # noqa: BLE001 - we never want email failures to break the API
        app.logger.warning("Failed to send email to %s: %s", to_addr, exc)
        return False


def require_admin():
    key = request.headers.get("X-Admin-Key", "")
    if not ADMIN_API_KEY or key != ADMIN_API_KEY:
        abort(401, description="Invalid or missing admin key.")


# --------------------------------------------------------------------------
# Static site serving
# --------------------------------------------------------------------------

@app.route("/")
def serve_index():
    return send_from_directory(SITE_DIR, "index.html")


@app.route("/<path:filename>")
def serve_site_file(filename):
    full_path = os.path.join(SITE_DIR, filename)
    if os.path.isfile(full_path):
        return send_from_directory(SITE_DIR, filename)
    abort(404)


# --------------------------------------------------------------------------
# Public API — Package Inquiries
# --------------------------------------------------------------------------

@app.route("/api/inquiry", methods=["POST"])
def create_inquiry():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    package = (data.get("package") or "").strip()

    if not name or not email or not package:
        return jsonify({"status": "error", "message": "Name, email and package are required."}), 400

    inquiry = Inquiry(
        name=name,
        email=email,
        edd=(data.get("edd") or "").strip() or None,
        hospital=(data.get("hospital") or "").strip() or None,
        package=package,
        message=(data.get("message") or "").strip() or None,
    )
    db.session.add(inquiry)
    db.session.commit()

    notify_body = (
        "New doula inquiry received:\n\n"
        f"Name: {inquiry.name}\n"
        f"Email: {inquiry.email}\n"
        f"EDD: {inquiry.edd}\n"
        f"Hospital: {inquiry.hospital}\n"
        f"Package: {inquiry.package}\n"
        f"Message: {inquiry.message}\n"
    )
    send_email(NOTIFY_EMAIL, f"Verea Within Inquiry — {inquiry.name}", notify_body)
    send_email(
        inquiry.email,
        "We received your inquiry — Verea Within",
        f"Dear {inquiry.name},\n\n"
        "Thank you for reaching out to Verea Within. We have received your inquiry "
        f"about the \"{inquiry.package}\" package and will reply personally within 24 hours.\n\n"
        "Warmly,\nVerea Within",
    )

    return jsonify({"status": "ok", "inquiry": inquiry.to_dict()}), 201


# --------------------------------------------------------------------------
# Public API — Consultation Bookings
# --------------------------------------------------------------------------

@app.route("/api/booking", methods=["POST"])
def create_booking():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    booking_date = (data.get("date") or "").strip()
    time_slot = (data.get("slot") or "").strip()

    if not all([name, email, phone, booking_date, time_slot]):
        return jsonify({
            "status": "error",
            "message": "Name, email, phone, date and time slot are required.",
        }), 400

    existing = Booking.query.filter_by(booking_date=booking_date, time_slot=time_slot).first()
    if existing:
        return jsonify({
            "status": "error",
            "message": "That slot was just booked by someone else. Please pick another time.",
        }), 409

    care_interests = data.get("care_interests")
    if isinstance(care_interests, list):
        care_interests = ", ".join(care_interests)

    booking = Booking(
        name=name,
        partner_name=(data.get("partner_name") or "").strip() or None,
        email=email,
        phone=phone,
        edd=(data.get("edd") or "").strip() or None,
        language=(data.get("language") or "").strip() or None,
        region=(data.get("region") or "").strip() or None,
        care_interests=care_interests,
        note=(data.get("note") or "").strip() or None,
        meeting_type=(data.get("meeting_type") or "").strip() or None,
        booking_date=booking_date,
        time_slot=time_slot,
    )
    db.session.add(booking)

    try:
        db.session.commit()
    except Exception:  # noqa: BLE001 - likely a race on the unique constraint
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": "That slot was just booked by someone else. Please pick another time.",
        }), 409

    notify_body = (
        "New consultation booking:\n\n"
        f"Name: {booking.name}\n"
        f"Partner: {booking.partner_name}\n"
        f"Email: {booking.email}\n"
        f"Phone: {booking.phone}\n"
        f"EDD: {booking.edd}\n"
        f"Language: {booking.language}\n"
        f"Region: {booking.region}\n"
        f"Care interests: {booking.care_interests}\n"
        f"Meeting type: {booking.meeting_type}\n"
        f"Date/Time: {booking.booking_date} {booking.time_slot} CET\n"
        f"Note: {booking.note}\n"
    )
    send_email(NOTIFY_EMAIL, f"Verea Within Booking — {booking.name}", notify_body)
    send_email(
        booking.email,
        "Your Verea Within consultation is confirmed",
        f"Dear {booking.name},\n\n"
        "Your complimentary 30-minute consultation is confirmed for "
        f"{booking.booking_date} at {booking.time_slot} CET ({booking.meeting_type}).\n\n"
        "We look forward to connecting.\n\nWarmly,\nVerea Within",
    )

    return jsonify({"status": "ok", "booking": booking.to_dict()}), 201


@app.route("/api/availability", methods=["GET"])
def availability():
    """Returns already-booked date/slot pairs so the frontend calendar can
    disable them. Optional ?month=YYYY-MM filter."""
    month = request.args.get("month")
    query = Booking.query
    if month:
        query = query.filter(Booking.booking_date.like(f"{month}%"))
    taken = [{"date": b.booking_date, "slot": b.time_slot} for b in query.all()]
    return jsonify({"status": "ok", "taken": taken})


# --------------------------------------------------------------------------
# Simple admin API (header-key protected) to review submissions
# --------------------------------------------------------------------------

@app.route("/api/admin/inquiries", methods=["GET"])
def list_inquiries():
    require_admin()
    inquiries = Inquiry.query.order_by(Inquiry.created_at.desc()).all()
    return jsonify([i.to_dict() for i in inquiries])


@app.route("/api/admin/bookings", methods=["GET"])
def list_bookings():
    require_admin()
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    return jsonify([b.to_dict() for b in bookings])


@app.errorhandler(404)
def not_found(_e):
    return jsonify({"status": "error", "message": "Not found."}), 404


@app.errorhandler(401)
def unauthorized(_e):
    return jsonify({"status": "error", "message": "Unauthorized."}), 401


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    if email_configured():
        print(f"[email] ENABLED — notifications will be sent to {NOTIFY_EMAIL} via {SMTP_HOST}")
    else:
        print(
            "[email] DISABLED — set a real Gmail App Password as SMTP_PASS in .env to "
            f"forward bookings/inquiries to {NOTIFY_EMAIL}. Data is still saved regardless."
        )
    app.run(host="0.0.0.0", port=port, debug=debug)

