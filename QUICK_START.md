# Quick Start Guide - Testing the UI

## Step 1: Start the Backend Server

Open a terminal/PowerShell window and run:

```bash
cd backend
python app.py
```

The backend will start on `http://localhost:5000`

## Step 2: Start the Frontend Server

Open a **NEW** terminal/PowerShell window and run:

```bash
cd frontend
npm install    # Only needed the first time
npm start
```

The frontend will start on `http://localhost:3000` and should automatically open in your browser.

## Step 3: Test the Application

Once both servers are running, you can:

### Option 1: Upload a JSON File
1. Click the "📁 Upload JSON File" button
2. Select a JSON file from your computer
3. The converted TOON output will appear on the right side
4. Click "📥 Download TOON File" to save the result

### Option 2: Paste JSON Directly
1. Paste JSON into the text area on the left
2. Click "Convert to TOON" button
3. View the converted output on the right
4. Download if needed

### Example JSON to Test:
```json
{
  "name": "John Doe",
  "age": 30,
  "address": {
    "street": "123 Main St",
    "city": "New York",
    "zip": "10001"
  },
  "hobbies": ["reading", "coding", "gaming"],
  "active": true
}
```

## Troubleshooting

- **Backend not responding?** Make sure Flask is running on port 5000
- **Frontend can't connect?** Check that the backend is running first
- **CORS errors?** Ensure Flask-CORS is installed and the backend is running
- **Port already in use?** Change the port in `app.py` (line 49) or stop the conflicting service
