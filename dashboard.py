import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
import builtins
import io
import urllib.parse

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    Image
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
st.markdown("""
<style>
.main {
    background-color: #f5f7fb;
}

.metric-card {
    background: white;
    padding: 20px;
    border-radius: 18px;
    box-shadow: 0px 4px 16px rgba(0,0,0,0.08);
    margin-bottom: 20px;
}

.big-number {
    font-size: 40px;
    font-weight: 700;
    color: #111827;
}

.label {
    color: #6b7280;
    font-size: 18px;
}

.sidebar .sidebar-content {
    background: linear-gradient(180deg,#ffffff,#f5f7fb);
}
</style>
""", unsafe_allow_html=True)
from datetime import datetime
from google.oauth2 import service_account
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="Pi Lab Learning ERP",
    page_icon="⚡",
    layout="wide"
)

# -----------------------------
# SESSION STATE
# -----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None

# -----------------------------
# GOOGLE SHEETS
# -----------------------------
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
        st.error(f"Sheet Connection Error: {str(e)}")
        st.stop()

def get_sheet(sheet_name):
    spreadsheet = get_spreadsheet()

    try:
        return spreadsheet.worksheet(sheet_name)
    except Exception as e:
        st.error(f"Sheet not found: {sheet_name}")
        st.stop()
    
# -----------------------------
# ENSURE RECEIPTS SHEET
# -----------------------------
def ensure_receipts_sheet():
    spreadsheet = get_spreadsheet()

    try:
        ws = spreadsheet.worksheet("Receipts")
        return ws
    except Exception:
        ws = spreadsheet.add_worksheet(
            title="Receipts",
            rows=1000,
            cols=20
        )
        
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
def create_whatsapp_link(
    parent_mobile,
    student_name,
    payment_month,
    amount_paid,
    receipt_no
):
    message = f"""
Dear Parent,

We have received the fee payment successfully.

Student: {student_name}
Fee Month: {payment_month}
Amount Paid: ₹{amount_paid}
Receipt No: {receipt_no}

Please find the receipt attached.

Regards,
Pi Lab Learning
8123417618
"""

    encoded = urllib.parse.quote(message)
    return f"https://wa.me/{parent_mobile}?text={encoded}"

def generate_receipt_pdf(
    receipt_no,
    payment_date,
    student_id,
    student_name,
    payment_month,
    amount_paid,
    payment_mode
):
    filename = f"{student_name}_{payment_month}_{receipt_no}.pdf"

    doc = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    logo_path = "logo.png"

    try:
        logo = Image(logo_path, width=80, height=80)
        story.append(logo)
        story.append(Spacer(1, 10))
    except:
        pass

     # Heading
    story.append(Paragraph("PI LAB LEARNING", styles["Title"]))
    story.append(Spacer(1, 15))
    story.append(Paragraph("PAYMENT RECEIPT", styles["Heading1"]))
    story.append(Spacer(1, 20))

    # Receipt data table
    data = [
        ["Receipt No", receipt_no],
        ["Payment Date", str(payment_date)],
        ["Student ID", student_id],
        ["Student Name", student_name],
        ["Fee Month", payment_month],
        ["Amount Paid", f"Rs. {amount_paid}"],
        ["Payment Mode", payment_mode]
    ]
    
    table = Table(data, colWidths=[150, 250])
    story.append(table)

    story.append(Spacer(1, 30))
    story.append(Paragraph("Thank you for your payment.", styles["Normal"]))
    story.append(Spacer(1, 20))
    story.append(Paragraph("Pi Lab Learning", styles["Normal"]))

    doc.build(story)

    return filename
# -----------------------------
# LOAD DATA
# -----------------------------
@st.cache_data(ttl=15)
def load_data():
    student_ws = get_sheet("Student Master")
    fee_ws = get_sheet("Fee Tracker")
    marks_ws = get_sheet("Marks")

    student_rows = student_ws.get_all_values()
    fee_rows = fee_ws.get_all_values()
    marks_rows = marks_ws.get_all_values()

    student_df = (
        pd.DataFrame(student_rows[1:], columns=student_rows[0])
        if len(student_rows) > 1 else pd.DataFrame()
    )

    fee_df = (
        pd.DataFrame(fee_rows[1:], columns=fee_rows[0])
        if len(fee_rows) > 1 else pd.DataFrame()
    )

    marks_df = (
        pd.DataFrame(marks_rows[1:], columns=marks_rows[0])
        if len(marks_rows) > 1 else pd.DataFrame()
    )

    if not fee_df.empty:
        if "Monthly Fee" in fee_df.columns:
            fee_df["Monthly Fee"] = pd.to_numeric(
                fee_df["Monthly Fee"],
                errors="coerce"
            ).fillna(0)

        if "Outstanding Amount" in fee_df.columns:
            fee_df["Outstanding Amount"] = pd.to_numeric(
                fee_df["Outstanding Amount"],
                errors="coerce"
            ).fillna(0)
            
    return student_df, fee_df, marks_df

def create_fee_reminder_link(
    parent_mobile,
    student_name,
    month,
    reminder_type
):
    if reminder_type == "polite":
        message = f"""
Dear Parent,

This is a gentle reminder that the tuition fee for {student_name} for {month} is due on 5th of this month.

Kindly make the payment on or before the due date.

Regards,
Pi Lab Learning
8123417618
"""
    elif reminder_type == "due":
        message = f"""
Dear Parent,

This is a reminder that the tuition fee for {student_name} for {month} is still pending.

We kindly request you to complete the payment at the earliest.

Regards,
Pi Lab Learning
8123417618
"""
    else:
        message = f"""
Dear Parent,

This is an urgent reminder regarding the pending tuition fee for {student_name} for {month}.

Kindly arrange to complete the pending payment at the earliest.

Please ignore this message if payment has already been made.

Regards,
Pi Lab Learning
8123417618
"""

    encoded = urllib.parse.quote(message)
    return f"https://wa.me/{parent_mobile}?text={encoded}"

# -----------------------------
# LOGIN
# -----------------------------
def verify_login(username, password):
    cred_ws = get_sheet("Credentials")
    rows = cred_ws.get_all_values()

    if len(rows) < 2:
        return False, None

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

# -----------------------------
# SIDEBAR
# -----------------------------
st.sidebar.title("PI LAB ERP")
st.sidebar.image("logo.png", width=140)

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
# -----------------------------
# DASHBOARD
# -----------------------------
if menu == "Dashboard":
    st.markdown("<h1 style='font-size:48px;'>Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    chart_df = pd.DataFrame({
        "Month": ["Jun", "Jul", "Aug", "Sep"],
        "Collection": [39000, 49000, 52000, 47000]
    })

    fig = px.bar(
        chart_df,
        x="Month",
        y="Collection",
        title="Monthly Fee Collection"
    )

    st.plotly_chart(fig, use_container_width=True)
    
    c1, c2, c3 = st.columns(3)

    with c1:
        def metric_card(title, value):
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">{title}</div>
                <div class="big-number">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    c1,c2,c3 = st.columns(3)

    with c1:
        metric_card("🎓 Total Students", 17)

    with c2:
        metric_card("👨‍🎓 Active Students", 17)

    with c3:
        metric_card("💰 Outstanding", "₹151,500")
        
    with c2:
        active_count = 0
        if not student_df.empty and "Status" in student_df.columns:
            active_count = len(
                student_df[
                    student_df["Status"].str.strip() == "Active"
                ]
            )
        st.metric("Active Students", active_count)

    with c3:
        outstanding = 0
        if not fee_df.empty and "Outstanding Amount" in fee_df.columns:
            outstanding = fee_df["Outstanding Amount"].sum()

        st.metric("Outstanding", f"₹ {outstanding:,.0f}")
# -----------------------------
# STUDENTS MODULE
# -----------------------------
elif menu == "Students":
    action = st.selectbox(
        "Action",
        ["View Students", "New Admission"]
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
            student_ws = get_sheet("Student Master")
            fee_ws = get_sheet("Fee Tracker")

            rows = student_ws.get_all_values()

            nums = []
            for r in rows[1:]:
                if r and r[0].startswith("PL"):
                    try:
                        nums.append(int(r[0].replace("PL", "")))
                    except:
                        pass

            new_num = max(nums) + 1 if nums else 1
            student_id = f"PL{new_num:05d}"

            student_ws.append_row([
                student_id,
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

            fee_ws.append_row([
                student_id,
                student_name,
                monthly_fee,
                "", "", "", "", "", "", "",
                "", "", "", "", "", "", "",
                "", "", "", "", "", 0
            ])

            st.success(f"Admission Added: {student_id}")
            st.cache_data.clear()
            st.rerun()

# -----------------------------
# FEES MODULE
# -----------------------------
elif menu == "Fees":
    action = st.selectbox(
        "",
        ["View Ledger", "Collect Fee"]
    )

     student_df, fee_df, marks_df = load_data()

    if action == "View Ledger":

        selected_month = st.selectbox(
            "Reminder Month",
            ["Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
        )

        reminder_type = st.selectbox(
            "Reminder Type",
            ["Polite", "Due", "Urgent"]
        )
  
        pending_df = fee_df[
            fee_df[selected_month].astype(str).str.strip() != "Paid"
        ]
            
        st.subheader(f"Pending Students - {selected_month}")
            
        for _, row in pending_df.iterrows():
            student_name = row["Student Name"]
                
            student_row = student_df[
                student_df["Student Name"] == student_name
            ]
                
            mobile = str(
                student_row.iloc[0]["Parent WhatsApp"]
            ).replace(".0", "").strip()
                
            if len(mobile) == 10:
                mobile = "91" + mobile
                
            wa_link = create_fee_reminder_link(
                mobile,
                student_name,
                selected_month,
                reminder_type.lower()
            )
                
            st.link_button(
                f"Send Reminder - {student_name}",
                wa_link
            )
                
        st.dataframe(fee_df, use_container_width=True)
        
    else:
        active_students = []

        if not student_df.empty:
            active_students = student_df[
                student_df["Status"] == "Active"
            ]["Student Name"].tolist()

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
            ["Cash", "UPI", "Bank Transfer"]
        )

        payment_date = st.date_input("Payment Date")

        if st.button("Submit Payment"):
            fee_ws = get_sheet("Fee Tracker")
            receipt_ws = get_sheet("Receipts")

            rows = fee_ws.get_all_values()
            headers = rows[0]

            month_col = headers.index(payment_month) + 1
            date_col = headers.index(f"{payment_month} Date") + 1

            target_row = None
            student_id = ""

            for i, row in enumerate(rows[1:], start=2):
                if len(row) > 1 and row[1] == student_name:
                    target_row = i
                    student_id = row[0]
                    break

            if target_row:
                fee_ws.update_cell(target_row, month_col, "Paid")
                fee_ws.update_cell(
                    target_row,
                    date_col,
                    str(payment_date)
                )

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

                st.success(f"Payment Recorded | Receipt {receipt_no}")

                pdf_file = generate_receipt_pdf(
                    receipt_no,
                    payment_date,
                    student_id,
                    student_name,
                    payment_month,
                    amount_paid,
                    payment_mode
                )
                    
                with open(pdf_file, "rb") as file:
                    st.download_button(
                        label="Download Receipt PDF",
                        data=file,
                        file_name=pdf_file,
                        mime="application/pdf"
                    )
                    
                student_row = student_df[
                    student_df["Student Name"] == student_name
                ]
                
                parent_mobile = str(
                    student_row.iloc[0]["Parent WhatsApp"]
                ).strip()
                
                parent_mobile = (
                    parent_mobile
                    .replace(".0", "")
                    .replace("+", "")
                    .replace(" ", "")
                )
                    
                if len(parent_mobile) == 10:
                     parent_mobile = "91" + parent_mobile
                                  
                wa_link = create_whatsapp_link(
                    parent_mobile,
                    student_name,
                    payment_month,
                    amount_paid,
                    receipt_no
                )
                       
                st.link_button(
                    "Send Receipt via WhatsApp",
                    wa_link
                )
                if st.button("Refresh Page"):
                    st.cache_data.clear()
                    st.rerun()
# -----------------------------
# ATTENDANCE MODULE
# -----------------------------
elif menu == "Attendance":
    st.title("Attendance")
    
    attendance_ws = get_sheet("Attendance")
    today_str = datetime.now().strftime("%Y-%m-%d")

# Active students from Student Master
    active_students_df = student_df[
        student_df["Status"].astype(str).str.strip() == "Active"
    ][["Student ID", "Student Name", "Grade"]].copy()

# Load attendance sheet
    rows = attendance_ws.get_all_values()

    if len(rows) <= 1:
        attendance_df = active_students_df.copy()
    else:
        attendance_df = pd.DataFrame(rows[1:], columns=rows[0])

# Remove duplicates
    if not attendance_df.empty:
        attendance_df = attendance_df.drop_duplicates(
            subset=["Student ID"],
            keep="last"
        )

# Sync new admissions
    existing_ids = []
    if not attendance_df.empty and "Student ID" in attendance_df.columns:
        existing_ids = attendance_df["Student ID"].tolist()

    for _, student in active_students_df.iterrows():
        if student["Student ID"] not in existing_ids:
            new_row = pd.DataFrame([{
                "Student ID": student["Student ID"],
                "Student Name": student["Student Name"],
                "Grade": student["Grade"]
            }])
            attendance_df = pd.concat(
                [attendance_df, new_row],
                ignore_index=True
             )

# Create today column if missing
    if today_str not in attendance_df.columns:
        attendance_df[today_str] = "Absent"

    selected_student = st.selectbox(
        "Student",
        sorted(attendance_df["Student Name"].tolist())
    )

    status = st.selectbox(
        "Status",
        ["Present", "Absent"]
    )

    if st.button("Mark Attendance"):
        idx = attendance_df.index[
            attendance_df["Student Name"] == selected_student
        ][0]
    
        attendance_df.loc[idx, today_str] = status

        attendance_ws.clear()
        attendance_ws.update(
            [attendance_df.columns.tolist()] +
            attendance_df.values.tolist()
        )

        st.success("Attendance Updated")
        st.rerun()

    st.dataframe(attendance_df, use_container_width=True)

# -----------------------------
# ACADEMICS MODULE
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
        active_students = []
        if not student_df.empty:
            active_students = student_df[
                student_df["Status"].str.strip() == "Active"
            ]["Student Name"].tolist()

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
            marks_ws = get_sheet("Marks")

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
            st.rerun()

    # PROGRESS REPORT
    elif action == "Progress Report":
        active_students = []
        if not student_df.empty:
            active_students = student_df[
                student_df["Status"].str.strip() == "Active"
            ]["Student Name"].tolist()

        selected_student = st.selectbox(
            "Student",
            sorted(active_students)
        )

        if st.button("Generate PDF"):
            student_marks = marks_df[
                marks_df["Student Name"] == selected_student
            ]

            if student_marks.empty:
                st.warning("No marks found")
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
                    percent = (
                        row["Marks Obtained"] /
                        row["Total Marks"]
                    ) * 100

                    table_data.append([
                        row["Subject"],
                        row["Test Name"],
                        f"{int(row['Marks Obtained'])}/{int(row['Total Marks'])}",
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
