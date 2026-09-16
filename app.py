from flask import Flask, render_template, request, session, redirect, url_for
from datetime import datetime, date, timedelta
import calendar
import os
import secrets as secrets_mod

app = Flask(__name__)
# Reads from env var in production; falls back to a random key per-run in dev
# so a stale hardcoded secret can't be reused to forge sessions.
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets_mod.token_hex(32)

# ==========================================
# OOP: BOOKING CLASS
# ==========================================
class Booking:
    def __init__(self, name, check_in, check_out):
        self.name = name
        self.check_in = check_in
        self.check_out = check_out

    def to_str(self):
        return f"{self.name} | {self.check_in.date()} to {self.check_out.date()}"


# DATA STRUCTURE: List to store bookings
booking_list = []

# ADMIN CREDENTIALS
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


# ==========================================
# ALGORITHM 1: BINARY SEARCH — Check Availability
# ==========================================
def is_available(check_in, check_out):
    sorted_bookings = sorted(booking_list, key=lambda b: b.check_in)
    left, right = 0, len(sorted_bookings) - 1
    while left <= right:
        mid = (left + right) // 2
        b = sorted_bookings[mid]
        if not (check_out <= b.check_in or check_in >= b.check_out):
            return False
        if check_out <= b.check_in:
            right = mid - 1
        else:
            left = mid + 1
    return True


# ==========================================
# ALGORITHM 2: BUBBLE SORT — Sort by Check-in Date
# ==========================================
def sort_bookings_bubble():
    n = len(booking_list)
    for i in range(n):
        for j in range(0, n - i - 1):
            if booking_list[j].check_in > booking_list[j + 1].check_in:
                booking_list[j], booking_list[j + 1] = booking_list[j + 1], booking_list[j]


# ==========================================
# Get Booked Dates for Calendar Highlighting
# ==========================================
def get_booked_dates():
    booked = set()
    for b in booking_list:
        days = (b.check_out - b.check_in).days
        for d in range(days):
            day = (b.check_in + timedelta(days=d)).date()
            booked.add(day)
    return booked


# ==========================================
# Resolve which (year, month) is being viewed
# ==========================================
def get_year_month(source):
    now = datetime.now()
    try:
        y = int(source.get("y", now.year))
        m = int(source.get("m", now.month))
        if m < 1 or m > 12:
            y, m = now.year, now.month
    except (TypeError, ValueError):
        y, m = now.year, now.month
    return y, m


# ==========================================
# Generate Calendar HTML
# ==========================================
def generate_calendar(year, month):
    cal = calendar.monthcalendar(year, month)
    booked_dates = get_booked_dates()
    today = date.today()

    # PREV / NEXT MONTH CALCULATION — CORRECT!
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    html = f"""
    <div class='calendar-nav'>
        <a href='?y={prev_year}&m={prev_month}' class='nav-btn'>◀ Prev</a>
        <h3>{calendar.month_name[month]} {year}</h3>
        <a href='?y={next_year}&m={next_month}' class='nav-btn'>Next ▶</a>
    </div>
    """
    html += "<div class='calendar-header'><span>Sun</span><span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span></div>"
    html += "<div class='calendar-days'>"

    for week in cal:
        for day in week:
            if day == 0:
                html += "<span class='day empty'></span>"
            else:
                day_date = date(year, month, day)
                date_str = day_date.strftime("%Y-%m-%d")
                if day_date < today:
                    html += f"<span class='day past' data-date='{date_str}'>{day}<div class='day-label'>⏳ PAST</div></span>"
                elif day_date in booked_dates:
                    html += f"<span class='day booked' data-date='{date_str}'>{day}<div class='day-label'>❌ BOOKED</div></span>"
                else:
                    html += f"<span class='day available' data-date='{date_str}'>{day}<div class='day-label'>✅ AVAILABLE</div></span>"
    html += "</div></div>"
    return html


# ==========================================
# HOME / GUEST PAGE
# ==========================================
@app.route("/")
def home():
    sort_bookings_bubble()
    y, m = get_year_month(request.args)

    cal = generate_calendar(y, m)
    return render_template("index.html", calendar=cal, year=y, month=m,
                            message=request.args.get("msg"))


# ==========================================
# MAKE BOOKING — ✅ WORKS ACROSS MONTHS!
# ==========================================
@app.route("/book", methods=["GET", "POST"])
def make_booking():
    now = datetime.now()

    if request.method == "POST":
        # Read the month/year the guest was actually looking at (hidden
        # form fields), not just the query string, so a booking made while
        # browsing a future month doesn't bounce back to the current month.
        y, m = get_year_month(request.form)

        name = request.form.get("guest_name", "").strip()
        start = request.form.get("check_in", "").strip()
        end = request.form.get("check_out", "").strip()

        if not name or not start or not end:
            message = "❌ Please fill ALL fields: Name, Check-in, Check-out!"
        else:
            try:
                check_in = datetime.strptime(start, "%Y-%m-%d")
                check_out = datetime.strptime(end, "%Y-%m-%d")

                if check_in >= check_out:
                    message = "❌ Check-out must be AFTER Check-in!"
                elif check_in.date() < now.date():
                    message = "❌ Cannot book past dates!"
                elif is_available(check_in, check_out):
                    new_booking = Booking(name, check_in, check_out)
                    booking_list.append(new_booking)
                    sort_bookings_bubble()
                    message = f"✅ BOOKED SUCCESSFULLY! {check_in.date()} → {check_out.date()}"
                else:
                    message = "❌ Dates overlap with another booking!"

            except ValueError:
                message = "❌ Invalid date! Use YYYY-MM-DD format"

        # Redirect (PRG pattern) instead of re-rendering directly, so
        # refreshing the result page never re-submits the booking.
        return redirect(url_for("home", y=y, m=m, msg=message))

    # GET /book with no form submitted — just show the booking page.
    y, m = get_year_month(request.args)
    cal = generate_calendar(y, m)
    return render_template("index.html", calendar=cal, year=y, month=m, message=None)


# ==========================================
# CHECK AVAILABILITY
# ==========================================
@app.route("/check", methods=["POST"])
def check_availability():
    start = request.form.get("check_in", "").strip()
    end = request.form.get("check_out", "").strip()
    y, m = get_year_month(request.form)
    cal = generate_calendar(y, m)

    try:
        check_in = datetime.strptime(start, "%Y-%m-%d")
        check_out = datetime.strptime(end, "%Y-%m-%d")
    except ValueError:
        return render_template("index.html", calendar=cal, year=y, month=m, message="❌ Invalid date!")

    if check_in >= check_out:
        return render_template("index.html", calendar=cal, year=y, month=m,
                                message="❌ Check-out must be AFTER Check-in!")

    msg = "✅ AVAILABLE — You can book!" if is_available(check_in, check_out) else "❌ NOT AVAILABLE — dates overlap!"
    return render_template("index.html", calendar=cal, year=y, month=m, message=msg)


# ==========================================
# ADMIN LOGIN / LOGOUT
# ==========================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if (secrets_mod.compare_digest(username, ADMIN_USERNAME)
                and secrets_mod.compare_digest(password, ADMIN_PASSWORD)):
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        return render_template("login.html", error="❌ Wrong username or password!")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ==========================================
# ADMIN DASHBOARD
# ==========================================
@app.route("/admin")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))
    sort_bookings_bubble()
    y, m = get_year_month(request.args)

    cal = generate_calendar(y, m)
    return render_template("admin.html", bookings=booking_list, calendar=cal)


# ==========================================
# DELETE BOOKING
# ==========================================
@app.route("/delete/<int:index>")
def delete_booking(index):
    if session.get("admin_logged_in") and 0 <= index < len(booking_list):
        booking_list.pop(index)
    return redirect(url_for("admin_dashboard"))


# ==========================================
# RUN THE APP
# ==========================================
if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)