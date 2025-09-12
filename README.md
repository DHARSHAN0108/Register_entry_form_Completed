# Register_entry_form
A modern Django-based Entry Register Web Application that allows visitors to register their details and book an appointment in a step-by-step form with file upload and validation. The system provides an easy-to-use UI with gradient backgrounds, modern pop-up modals for validation, and an integrated admin dashboard for viewing all entries.
🚀 Features
🌐 Frontend (User Side)

Multi-step form:

Step 1 → Collect personal details (Name, Email, Phone, Category).

Step 2 → Collect appointment details (Reason, Date, Time, Attendee, Document upload).

Modern UI/UX with gradient backgrounds, floating labels, and animations.

Smart Validation:

File upload restricted to PDFs only (max size: 2MB).

Appointment date restricted to today & future dates.

Appointment time restricted to 9:00 AM – 10:00 PM, with real-time past-time checks.

Custom Popup Modals for errors (File/Time validation) and success messages.

🔐 Backend (Django)

Django Models for storing visitor details & appointments.

Admin Panel Integration:

Search by Name, Email, Phone.

Filter by Date, Category, Attendee.

View uploaded documents directly.

Secure File Handling: Uploaded documents stored under media/documents/.

🛠️ Tech Stack

Frontend → HTML5, CSS3, Bootstrap 5, JavaScript

Backend → Django (Python)

Database → SQLite (default, can be switched to PostgreSQL/MySQL)

📸 Screenshots

(Add screenshots of Step1, Step2, Success modal, and Admin dashboard here)

⚡ How to Run Locally

Clone the repository:

git clone https://github.com/yourusername/entry-register.git
cd entry-register


Create a virtual environment & activate:

python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows


Install dependencies:

pip install -r requirements.txt


Apply migrations:

python manage.py makemigrations
python manage.py migrate


Create a superuser (for admin access):

python manage.py createsuperuser


Run the server:

python manage.py runserver


Open in browser:

User Form → http://127.0.0.1:8000/

Admin Panel → http://127.0.0.1:8000/admin/

📌 Future Enhancements

Export entries to Excel/PDF.

Email/SMS notifications for appointment confirmation.

Receptionist dashboard with advanced data analytics.
