# 📈 FLEKS Control Panel (Client Accounting System)

## Project Overview

The FLEKS Control Panel is a simple web application designed to manage client finances and register services rendered. It started as a small project to learn Django but quickly evolved into a fully functional, deployed accounting system focusing on core transaction features.

The application is deployed on Render and uses Neon (PostgreSQL) as its database backend.

---

## Key Features Implemented

I focused on building a robust and practical accounting workflow suitable for a small service business.

### 1. Robust Deployment and Stability

* **Render Deployment:** The application is fully configured to run in the cloud, utilizing **Gunicorn** and **WhiteNoise** for serving static files efficiently.
* **Database:** Leveraging Neon PostgreSQL for reliable, scalable data storage.

### 2. Client Balance Management

The system features a complete client balance workflow:

* **Client Model:** Stores the client's name and their current financial balance.
* **Search Functionality:** Implemented **instant client search** by name on both the top-up and payment pages for quick service.
* **Top-Up Interface:** A dedicated view for crediting money to a client’s account. Critically, this view **displays the client's current balance** right before the transaction.
* **Service Payment (Spending):**
    * Allows quick debiting of funds equal to the service cost.
    * **Built-in Balance Check:** The system prevents negative balances by blocking any transaction that exceeds the client’s current funds.
    * **Staff Tracking:** The name of the worker who provided the service is recorded with the transaction.

### 3. Transaction Detail and Integrity

* **Transaction Model:** Every operation (credit or debit) is meticulously logged, including the amount, the client, the transaction type (IN/OUT), and the performing staff member.
* **Atomicity:** Both the balance update and the transaction creation are handled atomically (as a single unit), guaranteeing financial data integrity even under concurrent operations.

---

## Technical Stack

* **Backend:** Python 3.12+
* **Framework:** Django 5.2.7
* **Database:** PostgreSQL (Neon)
* **Deployment:** Render
* **Static Files:** WhiteNoise
* **Web Server:** Gunicorn

---

## Configuration

All sensitive configuration is read from environment variables; none of it is stored in this repository.

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | yes | PostgreSQL connection string (Neon) |
| `SECRET_KEY` | yes | Django secret key |
| `DEBUG` | no | `True`/`False`. Defaults to `True` to keep the current behaviour; set `False` in production |
| `ALLOWED_HOSTS` | no | Comma-separated host names. Defaults to `fleks-control-panel.onrender.com,127.0.0.1,localhost` |

* **Production (Render):** set the variables in the Render dashboard under *Service → Environment*.
* **Local development:** copy `.env.example` to `.env` (repository root or `DjangoProject1/.env`) and fill in your own values. `.env` files are gitignored.
* **Desktop build (PyInstaller):** build artifacts (`build/`, `dist/`) are not committed. Place a `.env` file next to `FleksControlPanel.exe`.
