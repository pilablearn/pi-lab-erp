import streamlit as st
import pandas as pd
import gspread
import builtins
import io
from datetime import datetime
from google.oauth2 import service_account
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# PAGE CONFIG

st.set_page_config(
    page_title="Pi Lab Learning ERP",
    page_icon="⚡",
    layout="wide"
)

# SESSION STATE

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None

# GOOGLE SHEET CONNECTION

@st.cache_resource

def get_spreadsheet():
    try:
        if hasattr(builtins, "spreadsheet"):
            return builtins.spreadsheet

        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )

        gc = gspread.authorize(creds)
        builtins.spreadsheet = gc.open_by_key(
            "15azhC-cUcVpQbiPiMmlab8RxwM3zfUVdaq4NqNXM9ok"
        )
        return builtins.spreadsheet

    except Exception as e:
        st.session_state["_sheet_conn_error"] = str(e)
        return None

# AUTO CREATE RECEIPTS SHEET

def ensure_receipts_sheet():
    spreadsheet = get_spreadsheet()

    if spreadsheet is None:
        st.error("Spreadsheet connection failed")
        return None

    try:
        ws = spreadsheet.worksheet("Receipts")
        return ws

    except Exception:
        ws = spreadsheet.add_worksheet("Receipts", rows=1000, cols=20)

        ws.append_row([
            "Receipt No",
            "Date",
            "Student ID",
            "Student Name",
            "Fee Month",
            "Amount Paid",
            "Payment Mode"
        ])

        return ws
ensure_receipts_sheet()

# LOAD DATA

@st.cache_data(ttl=10)
def load_data():
    spreadsheet = get_spreadsheet()

if spreadsheet is None:
    st.error("Spreadsheet connection failed")
    st.stop()
    
student_ws = spreadsheet.worksheet("Student Master")
fee_ws = spreadsheet.worksheet("Fee Tracker")
marks_ws = spreadsheet.worksheet("Marks")

student_rows = student_ws.get_all_values()
fee_rows = fee_ws.get_all_values()
marks_rows = marks_ws.get_all_values()

student_df = pd.DataFrame(student_rows[1:], columns=student_rows[0]) if len(student_rows) > 1 else pd.DataFrame(columns=student_rows[0] if student_rows else [])
fee_df = pd.DataFrame(fee_rows[1:], columns=fee_rows[0]) if len(fee_rows) > 1 else pd.DataFrame(columns=fee_rows[0] if fee_rows else [])
marks_df = pd.DataFrame(marks_rows[1:], columns=marks_rows[0]) if len(marks_rows) > 1 else pd.DataFrame(columns=marks_rows[0] if marks_rows else [])

    if "Monthly Fee" in fee_df.columns:
        fee_df["Monthly Fee"] = pd.to_numeric(
            fee_df["Monthly Fee"], errors="coerce"
        ).fillna(0)

    if "Outstanding Amount" in fee_df.columns:
        fee_df["Outstanding Amount"] = pd.to_numeric(
            fee_df["Outstanding Amount"], errors="coerce"
        ).fillna(0)

    return student_df, fee_df, marks_df

student_df, fee_df, marks_df = load_data()

# LOGIN

def verify_login(username, password):
    cred_ws = spreadsheet.worksheet("Credentials")
    rows = cred_ws.get_all_values()

    headers = rows[0]
    df = pd.DataFrame(rows[1:], columns=headers)

    match = df[
        (df["Username"] == username) &
        (df["Password"] == password)
    ]

    if not match.empty:
        return True, match.iloc[0]["Role"]

    return False, None

if not st.session_state.logged_in:
    st.title("⚡ PI LAB LEARNING ERP")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        ok, role = verify_login(username, password)
        if ok:
            st.session_state.logged_in = True
            st.session_state.user_role = role
            st.rerun()
        else:
            st.error("Invalid login")

    st.stop()

# SIDEBAR

st.sidebar.title("⚡ PI LAB ERP")

menu = st.sidebar.radio(
    "Menu",
    [
        "Dashboard",
        "Students",
        "Fees",
        "Attendance",
        "Academics"
    ]
)

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# DASHBOARD

if menu == "Dashboard":
    st.title("Dashboard")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Total Students", len(student_df))

    with c2:
        active_count = len(
            student_df[
                student_df["Status"].str.strip() == "Active"
            ]
        ) if "Status" in student_df.columns and not student_df.empty else 0
        st.metric("Active Students", active_count)

    with c3:
        if "Outstanding Amount" in fee_df.columns:
            st.metric(
                "Outstanding",
                f"₹ {fee_df['Outstanding Amount'].sum():,.0f}"
            )

# STUDENTS

elif menu == "Students":
    action = st.selectbox(
        "Action",
        [
            "View Students",
            "New Admission"
        ]
    )

    if action == "View Students":
        st.dataframe(student_df, use_container_width=True)

    else:
        st.subheader("New Admission")

        admission_date = st.date_input("Admission Date")
        student_name = st.text_input("Student Name")
        parent_name = st.text_input("Parent Name")
        whatsapp1 = st.text_input("WhatsApp 1")
        whatsapp2 = st.text_input("WhatsApp 2")
        grade = st.selectbox(
            "Grade",
            ["G5","G6","G7","G8","G9","G10","G11","G12"]
        )
        board = st.selectbox(
            "Board",
            ["ICSE","CBSE","State Board"]
        )
        school = st.text_input("School Name")
        course = st.text_input("Course Enrolled")
        monthly_fee = st.number_input("Monthly Fee", min_value=0)

        if st.button("Submit Admission"):
            # FIX #9 (partial): block duplicate names to reduce ambiguous lookups downstream
            existing_names = student_df["Student Name"].str.strip().str.lower().tolist() if "Student Name" in student_df.columns else []
            if student_name.strip().lower() in existing_names:
                st.error(f"A student named '{student_name}' already exists. Please use a different name or add a distinguishing suffix (e.g. initial/grade) since records are looked up by name.")
            elif not student_name.strip():
                st.error("Student Name cannot be empty.")
            else:
                student_ws = spreadsheet.worksheet("Student Master")
                rows = student_ws.get_all_values()

                # FIX #1: robust ID generation, won't crash on blank/malformed last row
                nums = []
                for r in rows[1:]:
                    if r and r[0].strip().startswith("PL"):
                        try:
                            nums.append(int(r[0].strip().replace("PL", "")))
                        except ValueError:
                            continue
                new_num = (max(nums) + 1) if nums else 1
                new_id = f"PL{new_num:05d}"

                student_ws.append_row([
                    new_id,
                    str(admission_date),
                    student_name,
                    parent_name,
                    whatsapp1,
                    whatsapp2,
                    grade,
                    board,
                    school,
                    course,
                    monthly_fee,
                    "Active",
                    ""
                ])

                fee_ws = spreadsheet.worksheet("Fee Tracker")
                fee_ws.append_row([
                    new_id,
                    student_name,
                    monthly_fee,
                    "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", 0
                ])

                st.success(f"Admission Added — {new_id}")
                st.cache_data.clear()

# FEES

elif menu == "Fees":
    action = st.selectbox(
        "Action",
        [
            "View Ledger",
            "Collect Fee"
        ]
    )

    if action == "View Ledger":
        st.dataframe(fee_df)

    else:
        active_students = student_df[
            student_df["Status"] == "Active"
        ]["Student Name"].tolist() if "Status" in student_df.columns else []

        student_name = st.selectbox(
            "Student",
            sorted(active_students)
        )

        payment_month = st.selectbox(
            "Fee Month",
            ["Jun","Jul","Aug","Sep","Oct","Nov","Dec","Jan","Feb","Mar"]
        )

        amount_paid = st.number_input(
            "Amount Paid",
            min_value=0
        )

        payment_mode = st.selectbox(
            "Payment Mode",
            ["Cash","UPI","Bank Transfer"]
        )

        payment_date = st.date_input("Payment Date")

        if st.button("Submit Payment"):
            fee_ws = spreadsheet.worksheet("Fee Tracker")
            rows = fee_ws.get_all_values()
            headers = rows[0]

            # FIX #3 (related): guard against missing columns
            if payment_month not in headers or f"{payment_month} Date" not in headers:
                st.error(f"Column '{payment_month}' or '{payment_month} Date' not found in Fee Tracker sheet. Check sheet headers.")
            else:
                month_col = headers.index(payment_month) + 1
                date_col = headers.index(f"{payment_month} Date") + 1

                target_row = None
                student_id = ""

                for i, row in enumerate(rows[1:], start=2):
                    if len(row) > 1 and row[1].strip() == student_name.strip():
                        target_row = i
                        student_id = row[0]
                        break

                # FIX #3: explicit feedback if student row isn't found instead of silent no-op
                if target_row is None:
                    st.error(
                        f"Could not find a Fee Tracker row for '{student_name}'. "
                        "No payment was recorded. Check for a name mismatch between "
                        "Student Master and Fee Tracker."
                    )
                else:
                    fee_ws.update_cell(target_row, month_col, "Paid")
                    fee_ws.update_cell(
                        target_row,
                        date_col,
                        str(payment_date)
                    )

                    receipt_ws = spreadsheet.worksheet("Receipts")
                    receipt_rows = receipt_ws.get_all_values()

                    receipt_no = f"RCP-{datetime.now().year}-{len(receipt_rows):05d}"

                    receipt_ws.append_row([
                        receipt_no,
                        str(payment_date),
                        student_id,
                        student_name,
                        payment_month,
                        amount_paid,
                        payment_mode
                    ])

                    st.success(f"Payment Recorded | Receipt: {receipt_no}")
                    st.cache_data.clear()

# ATTENDANCE

elif menu == "Attendance":
    st.title("Attendance")

    attendance_ws = spreadsheet.worksheet("Attendance")
    rows = attendance_ws.get_all_values()

    today_str = datetime.now().strftime("%Y-%m-%d")

    active_students = student_df[
        student_df["Status"].str.strip() == "Active"
    ]["Student Name"].tolist() if "Status" in student_df.columns else []

    if not rows:
        attendance_df = pd.DataFrame({"Student Name": active_students})
        attendance_df[today_str] = "Absent"
    else:
        attendance_df = pd.DataFrame(rows[1:], columns=rows[0])

        if today_str not in attendance_df.columns:
            attendance_df[today_str] = "Absent"

    selected_student = st.selectbox(
        "Student",
        sorted(active_students)
    )

    status = st.selectbox(
        "Status",
        ["Present", "Absent"]
    )

    if st.button("Mark Attendance"):
        if selected_student in attendance_df["Student Name"].values:
            attendance_df.loc[
                attendance_df["Student Name"] == selected_student,
                today_str
            ] = status
        else:
            new_row = {col: "Absent" for col in attendance_df.columns}
            new_row["Student Name"] = selected_student
            new_row[today_str] = status
            attendance_df = pd.concat(
                [attendance_df, pd.DataFrame([new_row])],
                ignore_index=True
            )

        attendance_ws.clear()
        attendance_ws.update(
            [attendance_df.columns.tolist()] +
            attendance_df.values.tolist()
        )

        st.success("Attendance Updated")
        st.cache_data.clear()

    st.dataframe(attendance_df, use_container_width=True)

# ACADEMICS

elif menu == "Academics":
    action = st.selectbox(
        "Action",
        [
            "Leaderboard",
            "Enter Marks",
            "Progress Report"
        ]
    )

    if not marks_df.empty:
        marks_df["Marks Obtained"] = pd.to_numeric(
            marks_df["Marks Obtained"],
            errors="coerce"
        ).fillna(0)

        marks_df["Total Marks"] = pd.to_numeric(
            marks_df["Total Marks"],
            errors="coerce"
        ).fillna(100)

        # FIX #8 (partial): prevent zero/negative totals from sheet edits
        marks_df.loc[marks_df["Total Marks"] <= 0, "Total Marks"] = 100

        marks_df["Percentage"] = (
            marks_df["Marks Obtained"] /
            marks_df["Total Marks"]
        ) * 100

    # LEADERBOARD

    if action == "Leaderboard":
        if marks_df.empty:
            st.warning("No marks data")
        else:
            leaderboard = marks_df.groupby(
                "Student Name"
            )["Percentage"].mean().reset_index()

            leaderboard = leaderboard.sort_values(
                by="Percentage",
                ascending=False
            )

            st.dataframe(
                leaderboard,
                use_container_width=True
            )

    # ENTER MARKS

    elif action == "Enter Marks":
        active_students = student_df[
            student_df["Status"].str.strip() == "Active"
        ]["Student Name"].tolist() if "Status" in student_df.columns else []

        selected_student = st.selectbox(
            "Student",
            sorted(active_students)
        )

        subject = st.selectbox(
            "Subject",
            ["Maths", "Science", "English", "Social", "Coding"]
        )

        test_name = st.text_input("Test Name")
        marks_obtained = st.number_input(
            "Marks Obtained",
            min_value=0
        )
        total_marks = st.number_input(
            "Total Marks",
            min_value=1,
            value=100
        )

        if st.button("Submit Marks"):
            if marks_obtained > total_marks:
                st.error("Marks Obtained cannot exceed Total Marks.")
            else:
                marks_ws = spreadsheet.worksheet("Marks")

                student_row = student_df[
                    student_df["Student Name"] == selected_student
                ].iloc[0]

                student_id = student_row["Student ID"]

                marks_ws.append_row([
                    str(datetime.now().date()),
                    student_id,
                    selected_student,
                    subject,
                    test_name,
                    marks_obtained,
                    total_marks
                ])

                st.success("Marks Added")
                st.cache_data.clear()

    # PROGRESS REPORT

    elif action == "Progress Report":
        active_students = student_df[
            student_df["Status"].str.strip() == "Active"
        ]["Student Name"].tolist() if "Status" in student_df.columns else []

        selected_student = st.selectbox(
            "Student",
            sorted(active_students)
        )

        if st.button("Generate PDF"):
            student_marks = marks_df[
                marks_df["Student Name"] == selected_student
            ]

            if student_marks.empty:
                st.warning(f"No marks recorded yet for {selected_student}.")
            else:
                buffer = io.BytesIO()
                doc = SimpleDocTemplate(
                    buffer,
                    pagesize=letter
                )

                styles = getSampleStyleSheet()
                story = []

                story.append(
                    Paragraph(
                        "PI LAB LEARNING",
                        styles["Title"]
                    )
                )

                story.append(Spacer(1, 20))

                story.append(
                    Paragraph(
                        f"Progress Report: {selected_student}",
                        styles["Heading2"]
                    )
                )

                story.append(Spacer(1, 20))

                table_data = [
                    ["Subject", "Test", "Score", "Percent"]
                ]

                for _, row in student_marks.iterrows():
                    # FIX #8: guard against zero/invalid Total Marks to avoid crashing PDF generation
                    total = row["Total Marks"] if row["Total Marks"] else 100
                    percent = (row["Marks Obtained"] / total) * 100

                    table_data.append([
                        row["Subject"],
                        row["Test Name"],
                        f"{int(row['Marks Obtained'])}/{int(total)}",
                        f"{percent:.1f}%"
                    ])

                report_table = Table(table_data)

                report_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black)
                ]))

                story.append(report_table)
                doc.build(story)

                pdf_data = buffer.getvalue()

                st.download_button(
                    "Download PDF Report",
                    pdf_data,
                    file_name=f"{selected_student}_report.pdf",
                    mime="application/pdf"
                )
