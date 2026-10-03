# Verea Within — Doula Practice Website

A full-stack site for a holistic doula practice in Zurich: static frontend
(`site/`) + a Flask API backend (`app.py`) that stores package inquiries and
consultation bookings in SQLite, sends confirmation emails, and serves the
site itself.

## Project structure

```
VereaWithin/
  app.py              # Flask app: static site + JSON API
  requirements.txt     # Python dependencies
  .env.example         # Copy to .env and configure SMTP / admin key
  site/
    index.html          # Homepage
    packages.html        # Packages & pricing + inquiry form
    consultation.html    # Free consultation booking flow
  verea.db             # SQLite database (created automatically, gitignored)
```

## Running locally

1. Create/activate a virtual environment and install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. A `.env` file is already set up to forward all inquiries and bookings to
   **verea.within@gmail.com**. To actually enable email sending, you must
   generate a Gmail **App Password** (the normal Gmail password won't work
   for SMTP):

   1. Go to https://myaccount.google.com/security and turn on **2-Step Verification** for verea.within@gmail.com.
   2. Go to https://myaccount.google.com/apppasswords
   3. Create an app password (select "Mail" as the app), copy the 16-character code.
   4. Open `.env` and replace `SMTP_PASS=replace-with-gmail-app-password` with that code.

   Until you do this, the API still works perfectly (bookings/inquiries are
   saved to the database) — it just skips sending the email and logs a
   warning instead.

3. Start the server:

   ```powershell
   python app.py
   ```

4. Open http://127.0.0.1:5000/ in your browser.

## Where things get forwarded to verea.within@gmail.com

- Every new **package inquiry** (from `packages.html`) sends a notification
  email to `verea.within@gmail.com` with the client's details, plus an
  auto-reply to the client.
- Every new **consultation booking** (from `consultation.html`) sends a
  notification email to `verea.within@gmail.com` with the booking details,
  plus a confirmation email to the client.
- All `mailto:` links and JS fallbacks across the site (footer, contact
  cards, "fast-forward" box) also point to `verea.within@gmail.com`, so even
  if the backend is offline, visitors' email clients open addressed to the
  right inbox.
- You can review everything that's come in at any time via
  `GET /api/admin/inquiries` and `GET /api/admin/bookings` (send header
  `X-Admin-Key: <value from .env>`).

## API Endpoints

| Method | Path                     | Description                                           |
|--------|--------------------------|--------------------------------------------------------|
| GET    | `/`                      | Serves `site/index.html`                               |
| GET    | `/<file>.html`           | Serves any file from `site/`                            |
| POST   | `/api/inquiry`           | Create a package inquiry (name, email, package, ...)    |
| POST   | `/api/booking`           | Create a consultation booking (name, email, phone, date, slot, ...) — rejects double-booked slots with `409` |
| GET    | `/api/availability`      | Returns already-booked `{date, slot}` pairs (optional `?month=YYYY-MM`) |
| GET    | `/api/admin/inquiries`   | List all inquiries — requires header `X-Admin-Key`      |
| GET    | `/api/admin/bookings`    | List all bookings — requires header `X-Admin-Key`       |

## Frontend ↔ Backend wiring

- `packages.html`'s inquiry form POSTs JSON to `/api/inquiry`. If the backend
  is unreachable, it gracefully falls back to opening the visitor's email
  client via `mailto:`.
- `consultation.html`'s booking form POSTs JSON to `/api/booking`, fetches
  `/api/availability` on load to grey out already-booked time slots, and
  shows a friendly error if a slot was taken in the meantime.

## Deployment notes

- Swap `SQLALCHEMY_DATABASE_URI` (via `DATABASE_URL` env var) for a managed
  Postgres/MySQL instance in production.
- Put the app behind a real WSGI server (gunicorn/waitress) instead of
  Flask's dev server, and set `FLASK_DEBUG=0`.
- Set a strong, random `ADMIN_API_KEY` before exposing `/api/admin/*`.

