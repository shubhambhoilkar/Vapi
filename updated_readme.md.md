# Excel to VAPI Outbound Call

This project demonstrates a **minimal, working pipeline** to:

1. Read user data from an **Excel sheet**
2. Print and validate the data in Python
3. Place a **real outbound phone call using VAPI**

This README is intentionally simple and practical. The goal is to **prove end‑to‑end calling works** before adding batching, retries, or schedulers.

---

## 📌 What This Project Is

- A **debug‑friendly bridge** between Excel and VAPI
- Designed to validate:
  - Excel parsing
  - Phone number formatting
  - VAPI credentials
  - Real outbound calls

If this script works, you can safely build scheduling, retries, and concurrency on top of it.

---

## 🧩 Files

```
.
├── working_vapi_putbound_calling.py   # Main script
├── call_data.xlsx         # Input Excel file
└── README.md
```

### File name
```
call_data.xlsx
```

### Sheet name
```
call_queue
```

### Required Columns

| Column Name   | Description |
|--------------|-------------|
| Sr_no        | Serial number (any value) |
| user_name    | User name passed to assistant |
| phone_number | Destination phone number |
| email        | User email |
| status       | Must be `queued` to place call |

### Example Row

| Sr_no | user_name | phone_number   | email          | status |
|------|-----------|---------------|----------------|--------|
| 1    | Sam       | +910959470450 | sam99@test.com   | queued |

### ⚠️ Important Excel Rules

- **phone_number column MUST be formatted as TEXT**
- Phone number must be in **E.164 format**
  - Correct: `+910959470450`
  - Incorrect: `+91 0959470450`, `910959470450`, `9.17045E+11`
- Do **not** add spaces or dashes

---

## 🔐 Environment Variables (Required)

You must export valid VAPI credentials before running the script.

```bash
export VAPI_API_KEY="sk_live_xxxxx"
export ASSISTANT_ID="asst_xxxxx"
export PHONE_NUMBER_ID="pn_xxxxx"
```

Verify they are set:

```bash
echo $VAPI_API_KEY
echo $ASSISTANT_ID
echo $PHONE_NUMBER_ID
```

---

## 📦 Python Requirements

- Python **3.12**
- Required packages:

```bash
pip install pandas openpyxl httpx
```

---

## ▶️ How to Run

```bash
python excel_to_vapi_call.py
```

---

## 🖥️ What the Script Does

1. Reads `call_data.xlsx → call_queue`
2. Prints all rows so you can verify parsing
3. Filters rows with `status = queued`
4. Normalizes phone number
5. Sends outbound call request to VAPI
6. Prints full API response
7. Stops after **first call** (safe testing)

---

## ✅ Expected Output

Terminal output example:

```
📄 Excel Data Read Successfully
  Sr_no user_name   phone_number           email status
0     1      Sam  +910959470450  sam@test.com queued
--------------------------------------------------

🚀 Preparing outbound call
Name : Sam
Email: sam@test.com
Phone: +910959470450
Time : 2025-01-01T10:12:45Z

✅ HTTP Status: 200
📨 Response JSON: {'id': 'call_xxx', 'status': 'queued'}
```

Your phone should ring shortly after this output.

---

## 🔍 Troubleshooting

### Phone does not ring
Check the following in **VAPI Dashboard**:

- Phone number is verified
- Outbound calling enabled
- Country (+91) allowed
- Assistant is published
- Account has sufficient credits

### HTTP 401 / 403
- Invalid or inactive API key

### HTTP 400
- Incorrect assistant ID or phone number ID
- Invalid phone number format

---

## 🚀 Next Steps (Recommended)

Once this script works reliably:

- Add Excel status updates (`queued → in-progress → success`)
- Add retry logic for `no-response`
- Add batching & concurrency
- Add webhook listener for real call outcomes

This file is the **foundation** for all future orchestration.

---

## ✅ Key Takeaway

If this script places a call, your **VAPI + phone setup is correct**.
Everything else is just controlled automation on top of this.

