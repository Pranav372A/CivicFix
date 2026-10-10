import os
from flask import Flask, render_template, request, redirect
import mysql.connector


# =========================================================
# FLASK APPLICATION
# =========================================================

app = Flask(__name__)


# =========================================================
# MYSQL DATABASE CONFIGURATION
# =========================================================

db_config = {
    "host": "localhost",
    "user": "root",
    "password": os.getenv("CIVICFIX_DB_PASSWORD", ""),
    "database": "civicfix_db"
}


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    return mysql.connector.connect(**db_config)


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Average priority score for homepage
        cursor.execute(
            """
            SELECT
                ROUND(AVG(priority_score), 2) AS avg_priority
            FROM complaints
            """
        )

        result = cursor.fetchone()

        avg_priority = (
            result["avg_priority"]
            if result["avg_priority"] is not None
            else 0
        )

        return render_template(
            "index.html",
            avg_priority=avg_priority
        )

    except Exception as e:

        return f"""
        <h2>Home Page Error</h2>
        <p>{e}</p>
        """

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# TEST DATABASE CONNECTION
# =========================================================

@app.route("/test-db")
def test_db():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        if connection.is_connected():

            cursor = connection.cursor()

            cursor.execute("SELECT DATABASE()")

            database = cursor.fetchone()[0]

            return f"""
            <h2>Database Connection Successful!</h2>
            <p>Connected Database:
                <b>{database}</b>
            </p>
            """

    except Exception as e:

        return f"""
        <h2>Database Connection Failed</h2>
        <p>{e}</p>
        """

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# REPORT CIVIC ISSUE
# =========================================================

@app.route("/report", methods=["GET", "POST"])
def report():

    if request.method == "GET":
        return render_template("report.html")

    connection = None
    cursor = None

    try:

        # -------------------------------------------------
        # GET FORM VALUES
        # -------------------------------------------------

        raw_user_id = request.form.get("user_id")

        if raw_user_id and raw_user_id.isdigit():
            user_id = int(raw_user_id)
        else:
            user_id = 1

        print("REPORT DEBUG USER ID:", user_id)

        category_id = int(
            request.form.get("category_id")
        )

        location_id = int(
            request.form.get("location_id")
        )

        title = request.form.get("title")

        description = request.form.get("description")

        severity = int(
            request.form.get("severity")
        )

        affected_people = int(
            request.form.get("affected_people") or 1
        )

        # -------------------------------------------------
        # DATABASE CONNECTION
        # -------------------------------------------------

        connection = get_db_connection()

        cursor = connection.cursor(dictionary=True)

        # -------------------------------------------------
        # VERIFY USER EXISTS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT user_id
            FROM users
            WHERE user_id = %s
            """,
            (user_id,)
        )

        user_exists = cursor.fetchone()

        # If invalid user ID comes from the form,
        # use the existing demo user ID = 1.
        if not user_exists:

            print(
                "Invalid user ID received."
            )

            print(
                "Using demo user ID = 1"
            )

            user_id = 1

            cursor.execute(
                """
                SELECT user_id
                FROM users
                WHERE user_id = %s
                """,
                (user_id,)
            )

            user_exists = cursor.fetchone()

            if not user_exists:

                raise Exception(
                    "User ID 1 does not exist in users table."
                )

        print("FINAL USER ID USED:", user_id)

        # -------------------------------------------------
        # PRIORITY CALCULATION
        # -------------------------------------------------

        severity_score = severity * 10

        affected_score = min(
            affected_people / 4,
            50
        )

        priority_score = min(
            severity_score + affected_score,
            100
        )

        # -------------------------------------------------
        # INSERT COMPLAINT
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO complaints
            (
                user_id,
                category_id,
                location_id,
                title,
                description,
                severity,
                affected_people,
                priority_score,
                status
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                'SUBMITTED'
            )
            """,
            (
                user_id,
                category_id,
                location_id,
                title,
                description,
                severity,
                affected_people,
                priority_score
            )
        )

        complaint_id = cursor.lastrowid

        # -------------------------------------------------
        # INITIAL STATUS HISTORY
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO complaint_status_history
            (
                complaint_id,
                old_status,
                new_status,
                changed_by
            )
            VALUES
            (
                %s,
                NULL,
                %s,
                NULL
            )
            """,
            (
                complaint_id,
                "SUBMITTED"
            )
        )

        # -------------------------------------------------
        # COMMIT
        # -------------------------------------------------

        connection.commit()

        # -------------------------------------------------
        # SUCCESS PAGE
        # -------------------------------------------------

        return f"""
        <!DOCTYPE html>

        <html>

        <head>

            <title>Complaint Submitted</title>

            <style>

                body {{
                    font-family: Arial, sans-serif;
                    background: #f4f7fb;
                    text-align: center;
                    padding-top: 70px;
                }}

                .box {{
                    background: white;
                    width: 500px;
                    max-width: 90%;
                    margin: auto;
                    padding: 40px;
                    border-radius: 12px;
                    box-shadow:
                        0 5px 20px
                        rgba(0,0,0,0.1);
                }}

                h1 {{
                    color: #159447;
                }}

                .button {{
                    display: inline-block;
                    margin-top: 25px;
                    padding: 12px 25px;
                    background: #2447a8;
                    color: white;
                    text-decoration: none;
                    border-radius: 7px;
                }}

            </style>

        </head>

        <body>

            <div class="box">

                <h1>
                    Complaint Submitted Successfully!
                </h1>

                <p>
                    Your civic issue has been recorded
                    in the CivicFix database.
                </p>

                <p>
                    <b>Complaint ID:</b>
                    {complaint_id}
                </p>

                <p>
                    <b>Title:</b>
                    {title}
                </p>

                <p>
                    <b>Priority Score:</b>
                    {priority_score:.2f}
                </p>

                <p>
                    <b>Status:</b>
                    SUBMITTED
                </p>

                <a class="button" href="/">
                    Back to CivicFix
                </a>

            </div>

        </body>

        </html>
        """

    except Exception as e:

        if connection:
            connection.rollback()

        print("REPORT ERROR:", e)

        return f"""
        <h2>Complaint Submission Failed</h2>

        <p>{e}</p>

        <a href="/report">
            Go Back
        </a>
        """

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# VIEW ALL COMPLAINTS
# =========================================================

@app.route("/complaints")
def complaints():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                complaint_id,
                title,
                description,
                severity,
                affected_people,
                priority_score,
                status,
                reported_at
            FROM complaints
            ORDER BY
                priority_score DESC,
                complaint_id DESC
            """
        )

        complaints_data = cursor.fetchall()

        return render_template(
            "complaints.html",
            complaints=complaints_data
        )

    except Exception as e:

        return f"""
        <h2>Unable to Load Complaints</h2>
        <p>{e}</p>
        """

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
def admin():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(dictionary=True)

        # -------------------------------------------------
        # TOTAL COMPLAINTS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM complaints
            """
        )

        total = cursor.fetchone()["total"]

        # -------------------------------------------------
        # PENDING COMPLAINTS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*) AS pending
            FROM complaints
            WHERE status IN
            (
                'SUBMITTED',
                'VERIFIED',
                'ASSIGNED'
            )
            """
        )

        pending = cursor.fetchone()["pending"]

        # -------------------------------------------------
        # IN PROGRESS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*) AS in_progress
            FROM complaints
            WHERE status = 'IN_PROGRESS'
            """
        )

        in_progress = cursor.fetchone()["in_progress"]

        # -------------------------------------------------
        # RESOLVED
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*) AS resolved
            FROM complaints
            WHERE status IN
            (
                'RESOLVED',
                'CLOSED'
            )
            """
        )

        resolved = cursor.fetchone()["resolved"]

        # -------------------------------------------------
        # COMPLAINT LIST
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                complaint_id,
                title,
                severity,
                affected_people,
                priority_score,
                status,
                reported_at
            FROM complaints
            ORDER BY
                priority_score DESC,
                complaint_id DESC
            """
        )

        complaints_data = cursor.fetchall()

        return render_template(
            "admin.html",
            total=total,
            pending=pending,
            in_progress=in_progress,
            resolved=resolved,
            complaints=complaints_data
        )

    except Exception as e:

        return f"""
        <h2>Admin Dashboard Error</h2>
        <p>{e}</p>
        """

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# UPDATE COMPLAINT STATUS
# =========================================================

@app.route(
    "/admin/update-status",
    methods=["POST"]
)
def update_status():

    complaint_id = request.form.get(
        "complaint_id"
    )

    new_status = request.form.get(
        "status"
    )

    allowed_statuses = [
        "SUBMITTED",
        "VERIFIED",
        "ASSIGNED",
        "IN_PROGRESS",
        "RESOLVED",
        "CLOSED"
    ]

    if new_status not in allowed_statuses:

        return "Invalid status", 400

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        # -------------------------------------------------
        # GET CURRENT STATUS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT status
            FROM complaints
            WHERE complaint_id = %s
            """,
            (complaint_id,)
        )

        complaint = cursor.fetchone()

        if not complaint:

            return "Complaint not found", 404

        old_status = complaint["status"]

        # -------------------------------------------------
        # IF STATUS IS SAME
        # -------------------------------------------------

        if old_status == new_status:

            return redirect("/admin")

        # -------------------------------------------------
        # UPDATE STATUS
        # -------------------------------------------------

        cursor.execute(
            """
            UPDATE complaints
            SET status = %s
            WHERE complaint_id = %s
            """,
            (
                new_status,
                complaint_id
            )
        )

        # -------------------------------------------------
        # STATUS HISTORY
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO complaint_status_history
            (
                complaint_id,
                old_status,
                new_status,
                changed_by
            )
            VALUES
            (
                %s,
                %s,
                %s,
                NULL
            )
            """,
            (
                complaint_id,
                old_status,
                new_status
            )
        )

        connection.commit()

        return redirect("/admin")

    except Exception as e:

        if connection:
            connection.rollback()

        return f"""
        <h2>Update Failed</h2>

        <p>{e}</p>

        <a href="/admin">
            Back to Admin Dashboard
        </a>
        """

    finally:

        if cursor:

            try:
                cursor.close()
            except:
                pass

        if connection:

            try:
                connection.close()
            except:
                pass


# =========================================================
# ADD RESOLUTION
# =========================================================

@app.route(
    "/admin/add-resolution",
    methods=["POST"]
)
def add_resolution():

    connection = None
    cursor = None

    try:

        complaint_id = request.form.get(
            "complaint_id"
        )

        resolution_description = request.form.get(
            "resolution_description"
        )

        if (
            not complaint_id
            or not resolution_description
        ):

            return (
                "Complaint ID and resolution "
                "description are required.",
                400
            )

        connection = get_db_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO resolutions
            (
                complaint_id,
                resolution_description
            )
            VALUES
            (
                %s,
                %s
            )
            """,
            (
                complaint_id,
                resolution_description
            )
        )

        connection.commit()

        return redirect("/admin")

    except Exception as e:

        if connection:
            connection.rollback()

        return f"""
        <h2>Resolution Failed</h2>

        <p>{e}</p>

        <a href="/admin">
            Back to Admin Dashboard
        </a>
        """

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# SUBMIT FEEDBACK
# =========================================================

@app.route(
    "/submit-feedback",
    methods=["POST"]
)
def submit_feedback():

    connection = None
    cursor = None

    try:

        complaint_id = request.form.get(
            "complaint_id"
        )

        raw_user_id = request.form.get(
            "user_id"
        )

        if (
            raw_user_id
            and raw_user_id.isdigit()
        ):
            user_id = int(raw_user_id)
        else:
            user_id = 1

        rating = request.form.get(
            "rating"
        )

        comments = request.form.get(
            "comments"
        )

        print(
            "FEEDBACK USER ID:",
            user_id
        )

        if (
            not complaint_id
            or not rating
        ):

            return (
                "Complaint ID and rating "
                "are required.",
                400
            )

        rating = int(rating)

        if rating < 1 or rating > 5:

            return (
                "Rating must be between "
                "1 and 5.",
                400
            )

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        # -------------------------------------------------
        # VERIFY USER
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT user_id
            FROM users
            WHERE user_id = %s
            """,
            (user_id,)
        )

        user_exists = cursor.fetchone()

        if not user_exists:

            user_id = 1

            cursor.execute(
                """
                SELECT user_id
                FROM users
                WHERE user_id = %s
                """,
                (user_id,)
            )

            if not cursor.fetchone():

                return (
                    "No valid citizen user found.",
                    400
                )

        # -------------------------------------------------
        # INSERT FEEDBACK
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO feedback
            (
                complaint_id,
                user_id,
                rating,
                comments
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                complaint_id,
                user_id,
                rating,
                comments
            )
        )

        connection.commit()

        return redirect("/admin")

    except Exception as e:

        if connection:
            connection.rollback()

        return f"""
        <h2>Feedback Submission Failed</h2>

        <p>{e}</p>

        <a href="/admin">
            Back to Admin Dashboard
        </a>
        """

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# ANALYTICS DASHBOARD
# =========================================================

@app.route("/analytics")
def analytics():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        # -------------------------------------------------
        # TOTAL COMPLAINTS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM complaints
            """
        )

        total_complaints = (
            cursor.fetchone()["total"]
        )

        # -------------------------------------------------
        # PENDING
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM complaints
            WHERE status IN
            (
                'SUBMITTED',
                'VERIFIED',
                'ASSIGNED'
            )
            """
        )

        pending_complaints = (
            cursor.fetchone()["total"]
        )

        # -------------------------------------------------
        # IN PROGRESS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM complaints
            WHERE status = 'IN_PROGRESS'
            """
        )

        in_progress = (
            cursor.fetchone()["total"]
        )

        # -------------------------------------------------
        # RESOLVED
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM complaints
            WHERE status IN
            (
                'RESOLVED',
                'CLOSED'
            )
            """
        )

        resolved = (
            cursor.fetchone()["total"]
        )

        # -------------------------------------------------
        # COMPLAINTS BY CATEGORY
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                c.category_name,
                COUNT(co.complaint_id) AS total
            FROM categories c
            LEFT JOIN complaints co
                ON c.category_id =
                   co.category_id
            GROUP BY
                c.category_id,
                c.category_name
            ORDER BY total DESC
            """
        )

        category_data = cursor.fetchall()

        # -------------------------------------------------
        # COMPLAINTS BY STATUS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                status,
                COUNT(*) AS total
            FROM complaints
            GROUP BY status
            ORDER BY total DESC
            """
        )

        status_data = cursor.fetchall()

        # -------------------------------------------------
        # HIGH PRIORITY
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                complaint_id,
                title,
                priority_score,
                status
            FROM complaints
            ORDER BY priority_score DESC
            LIMIT 5
            """
        )

        high_priority = cursor.fetchall()

        # -------------------------------------------------
        # TOP CATEGORY
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                c.category_name,
                COUNT(co.complaint_id) AS total
            FROM categories c
            LEFT JOIN complaints co
                ON c.category_id =
                   co.category_id
            GROUP BY
                c.category_id,
                c.category_name
            ORDER BY total DESC
            LIMIT 1
            """
        )

        top_category = cursor.fetchone()

        # -------------------------------------------------
        # AVERAGE PRIORITY
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                ROUND(
                    AVG(priority_score),
                    2
                ) AS avg_priority
            FROM complaints
            """
        )

        avg_priority_result = (
            cursor.fetchone()
        )

        avg_priority = (
            avg_priority_result["avg_priority"]
            if avg_priority_result["avg_priority"]
            is not None
            else 0
        )

        # -------------------------------------------------
        # RETURN ANALYTICS
        # -------------------------------------------------

        return render_template(
            "analytics.html",
            total_complaints=total_complaints,
            pending_complaints=pending_complaints,
            in_progress=in_progress,
            resolved=resolved,
            category_data=category_data,
            status_data=status_data,
            high_priority=high_priority,
            top_category=top_category,
            avg_priority=avg_priority
        )

    except Exception as e:

        return f"""
        <h2>Analytics Error</h2>

        <p>{e}</p>
        """

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# HIGH PRIORITY COMPLAINTS
# =========================================================

@app.route("/high-priority")
def high_priority():

    connection = None
    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                c.complaint_id,
                c.title,
                cat.category_name,
                c.severity,
                c.affected_people,
                c.priority_score,
                c.status,
                c.reported_at
            FROM complaints c
            JOIN categories cat
                ON c.category_id =
                   cat.category_id
            WHERE c.priority_score >= 80
            ORDER BY c.priority_score DESC
            """
        )

        complaints_data = cursor.fetchall()

        return render_template(
            "complaints.html",
            complaints=complaints_data
        )

    except Exception as e:

        return f"""
        <h2>
            High Priority Complaints Error
        </h2>

        <p>{e}</p>
        """

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(debug=True)