# Autonomiqa Contact Form — Setup & Testing Guide

## File Structure

```
project/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── .env               ← created from .env.example
├── frontend/
│   └── src/
│       └── ContactForm.jsx
└── .env.example
```

---

## Step 1 — Google Cloud: Create a Service Account

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and select or create a project.
2. Navigate to **APIs & Services → Library**.
3. Search for and **Enable** both:
   - `Google Sheets API`
   - `Google Drive API`
4. Go to **APIs & Services → Credentials → Create Credentials → Service Account**.
5. Give it a name (e.g. `autonomiqa-sheets-writer`), click **Done**.
6. Click the service account → **Keys tab → Add Key → Create new key → JSON**.
7. Download the JSON file (e.g. `key.json`). **Keep this file secret.**

---

## Step 2 — Share Your Google Sheet with the Service Account

1. Open the Google Sheet you want to write to (or create a new one).
2. Copy the **Sheet ID** from the URL:
   ```
   https://docs.google.com/spreadsheets/d/THIS_IS_YOUR_SHEET_ID/edit
   ```
3. Click **Share** in the top-right corner.
4. Paste the `client_email` from your `key.json` (looks like `name@project.iam.gserviceaccount.com`).
5. Set role to **Editor** and click **Send**.

---

## Step 3 — Configure .env

In the `backend/` folder, create a `.env` file:

```bash
cd backend
cp ../.env.example .env
```

Fill in the two values:

**SHEET_ID** — paste from the URL above.

**SERVICE_ACCOUNT_JSON** — convert your key.json to a single-line string:

```bash
python3 -c "import json,sys; print(json.dumps(json.load(open('key.json'))))"
```

Copy the output and paste it as the value of `SERVICE_ACCOUNT_JSON` in `.env`.

---

## Step 4 — Run the Backend

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload --port 8000
```

You should see:
```
✅  Google Sheets connected — Sheet ID: <your_id>
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Interactive API docs are available at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Step 5 — Run the React Frontend

```bash
cd frontend

# If using Vite (recommended)
npm create vite@latest . -- --template react
npm install
# Copy ContactForm.jsx into src/ or your website's component folder
# and point it at the deployed backend or local API.

# Start dev server
npm run dev
```

Import and render the form in your `App.jsx` or directly in the website:

```jsx
import ContactForm from "./ContactForm";

function App() {
  return (
    <main>
      {/* ... other sections ... */}
      <ContactForm apiUrl={import.meta.env.VITE_CONTACT_FORM_API_URL || "http://localhost:8000/submit-form"} />
    </main>
  );
}
```

If the website and backend are deployed separately, set `VITE_CONTACT_FORM_API_URL` in the website app's `.env` file to the backend endpoint. If they share the same domain, you can leave the default `/submit-form` path and proxy it at the web server layer.

---

## Step 6 — Verify with Postman

Open Postman (or any HTTP client) and send:

```
POST http://localhost:8000/submit-form
Content-Type: application/json

{
  "name": "Kanika Test",
  "email": "kanika@autonomiqa.co",
  "message": "This is a test submission from Postman."
}
```

**Expected response (201 Created):**
```json
{
  "success": true,
  "message": "Thank you! Your message has been received."
}
```

Then open your Google Sheet — you should see a new row:

| Timestamp (UTC)       | Name         | Email                 | Message                                    |
|-----------------------|--------------|-----------------------|--------------------------------------------|
| 2025-01-15 09:32:11 UTC | Kanika Test | kanika@autonomiqa.co | This is a test submission from Postman. |

---

## Step 7 — Test Client-Side Validation (React UI)

| Test Case                        | Expected Behaviour                              |
|----------------------------------|-------------------------------------------------|
| Submit with all fields empty     | Three error messages appear below each field    |
| Enter invalid email (`abc@`)     | "Enter a valid email address." shown on blur    |
| Message under 10 characters      | Error shown on blur and on submit               |
| Valid form submission             | Button shows spinner → success screen appears   |
| Backend offline during submit     | Orange API error banner shown above the button  |

---

## Common Errors

| Error | Fix |
|---|---|
| `SHEET_ID is not set in .env` | Make sure `.env` is in the same folder as `main.py` |
| `403 Forbidden` from Google API | Sheet not shared with the service account email |
| `CORS` error in browser | Add your frontend origin to `allow_origins` in `main.py` |
| `json.decoder.JSONDecodeError` | `SERVICE_ACCOUNT_JSON` is not valid single-line JSON — re-run the python3 command |
| `gspread.exceptions.SpreadsheetNotFound` | Wrong `SHEET_ID` or sheet not shared with service account |

---

## Production Notes

- Store `SERVICE_ACCOUNT_JSON` in your hosting platform's **Secrets/Environment Variables** (Render, Railway, Fly.io, etc.) — never in a committed file.
- Add your production domain to `allow_origins` in `main.py`.
- Consider adding rate limiting (e.g. `slowapi`) to prevent form spam.
- For email notifications on new submissions, add `fastapi-mail` and send from the `/submit-form` endpoint after the sheet append.
