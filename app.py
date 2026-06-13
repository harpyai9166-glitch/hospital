import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- BACKEND: DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lab_data.db')
    c = conn.cursor()
    # अप्वाइंटमेंट और मास्टर डेटा टेबल
    c.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT,
            age INTEGER,
            gender TEXT,
            test_name TEXT,
            billing_amount INTEGER,
            status TEXT DEFAULT 'Pending',
            test_result TEXT DEFAULT 'Not Generated',
            ref_doctor TEXT DEFAULT 'Self',
            sample_status TEXT DEFAULT 'Sample Not Collected',
            followup_date TEXT DEFAULT 'No Followup',
            department TEXT DEFAULT 'Pathology',
            is_outsourced TEXT DEFAULT 'No'
        )
    ''')
    # स्टाफ मैनेजमेंट टेबल
    c.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            role TEXT,
            phone TEXT
        )
    ''')
    
    # पुरानी फाइलों के बैकवर्ड सपोर्ट के लिए सुरक्षा चक्र
    try:
        c.execute("ALTER TABLE appointments ADD COLUMN department TEXT DEFAULT 'Pathology'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE appointments ADD COLUMN is_outsourced TEXT DEFAULT 'No'")
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()

init_db()

# --- FRONTEND: UI & SECURITY ---
st.set_page_config(page_title="Pro Lab Suite", layout="wide")

# डेटा सिक्योरिटी (Login Session)
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.title("🔒 Hospital Lab Core Security")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Secure Login"):
            if username == "admin" and password == "lab123":
                st.session_state["logged_in"] = True
                st.rerun()
            else:
                st.error("गलत पासवर्ड! (Hint: admin / lab123)")
    st.stop()

if st.sidebar.button("🔒 Logout"):
    st.session_state["logged_in"] = False
    st.rerun()

# 14 के 14 फीचर्स को कवर करता हुआ फाइनल नेविगेशन पैनल
menu = ["Dashboard", "Appointment", "Sample Tracking", "Lab Reporting", "SMART Report", "Patient Management Portal", "Staff Management", "Patient Followup"]
choice = st.sidebar.selectbox("Menu Navigation", menu)

# --- APP MASTER LOGIC ---

# 1. DASHBOARD AREA
if choice == "Dashboard":
    st.title("🏥 Hospital Lab Management System")
    st.subheader("Live Operational Analytics")
    
    conn = sqlite3.connect('lab_data.db')
    df = pd.read_sql_query("SELECT * FROM appointments", conn)
    conn.close()
    
    col1, col2, col3 = st.columns(3)
    if not df.empty:
        col1.metric("Total Patients Served", len(df))
        col2.metric("Gross Revenue", f"₹{df['billing_amount'].sum()}")
        col3.metric("Pending Lab Cases", len(df[df['status'] == 'Pending']))
        
        st.write("### Active Operational Master Board")
        available_cols = [c for c in ['id', 'patient_name', 'test_name', 'department', 'is_outsourced', 'sample_status', 'status'] if c in df.columns]
        st.dataframe(df[available_cols], use_container_width=True)
    else:
        st.info("डेटाबेस अभी पूरी तरह खाली है। कृपया नया अपॉइंटमेंट दर्ज करें।")

# 2. APPOINTMENT AREA (Updated with Department & Outsourcing)
elif choice == "Appointment":
    st.title("📅 Patient Registration & Booking")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Add New Patient Entry")
        with st.form("appointment_form", clear_on_submit=True):
            name = st.text_input("Patient Full Name")
            age = st.number_input("Age", min_value=1, max_value=100, value=25)
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
            doctor = st.text_input("Reference Doctor Name", value="Self")
            
            # Feature 10 & 11: Departmentwise & Outsourcing Selection
            dept = st.selectbox("Assign Department", ["Pathology (Blood/Urine)", "Radiology (X-Ray/Scan)", "Biochemistry", "Microbiology"])
            outsourced = st.selectbox("Is this test outsourced to a third-party lab?", ["No", "Yes"])
            
            test_prices = {
                "Blood Test (CBC)": 300,
                "Diabetes Profile (HbA1c)": 400,
                "X-Ray Chest": 500,
                "Full Body Checkup": 1500
            }
            test = st.selectbox("Select Test Profile", list(test_prices.keys()))
            submit = st.form_submit_button("Register & Generate Token")
            
            if submit and name:
                price = test_prices[test]
                conn = sqlite3.connect('lab_data.db')
                c = conn.cursor()
                c.execute('''
                    INSERT INTO appointments (patient_name, age, gender, test_name, billing_amount, ref_doctor, department, is_outsourced) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, age, gender, test, price, doctor, dept, outsourced))
                conn.commit()
                conn.close()
                st.success(f"🎟️ Token generated successfully for {name}!")
                st.rerun()

    with col2:
        st.subheader("Today's Token Ledger")
        conn = sqlite3.connect('lab_data.db')
        df = pd.read_sql_query("SELECT id, patient_name, test_name, department, is_outsourced, status FROM appointments", conn)
        conn.close()
        if not df.empty:
            st.dataframe(df, use_container_width=True)

# 3. SAMPLE TRACKING AREA
elif choice == "Sample Tracking":
    st.title("🧪 Sample Lifecycle Tracking")
    conn = sqlite3.connect('lab_data.db')
    df = pd.read_sql_query("SELECT id, patient_name, test_name, sample_status FROM appointments WHERE status='Pending'", conn)
    conn.close()
    
    if df.empty:
        st.success("सभी सैंपल्स प्रोसेस हो चुके हैं!")
    else:
        patient_list = [f"{row['id']} - {row['patient_name']} ({row['test_name']})" for index, row in df.iterrows()]
        selected_patient = st.selectbox("Select Active Patient", patient_list)
        patient_id = selected_patient.split(" - ")[0]
        
        current_status = df[df['id'] == int(patient_id)]['sample_status'].values[0]
        st.info(f"Current Status: **{current_status}**")
        
        new_status = st.selectbox("Update Stage To", ["Sample Collected", "Sent to Main Lab", "Processing", "Done"])
        if st.button("Change Stage"):
            conn = sqlite3.connect('lab_data.db')
            c = conn.cursor()
            c.execute("UPDATE appointments SET sample_status=? WHERE id=?", (new_status, patient_id))
            conn.commit()
            conn.close()
            st.success("सैंपल स्टेटस अपडेट हो गया है।")
            st.rerun()

# 4. LAB REPORTING AREA
elif choice == "Lab Reporting":
    st.title("🔬 Clinical Test Reporting Panel")
    conn = sqlite3.connect('lab_data.db')
    df = pd.read_sql_query("SELECT id, patient_name, test_name, status, sample_status FROM appointments WHERE status='Pending'", conn)
    conn.close()
    
    if df.empty:
        st.success("🎉 कोई भी रिपोर्ट पेंडिंग नहीं है!")
    else:
        patient_list = [f"{row['id']} - {row['patient_name']} ({row['test_name']})" for index, row in df.iterrows()]
        selected_patient = st.selectbox("Select Patient to Enter Results", patient_list)
        patient_id = selected_patient.split(" - ")[0]
        
        st.write("---")
        result_input = st.text_area("Enter Diagnostic Observations/Findings")
        
        st.write("### Followup Configuration")
        need_followup = st.checkbox("क्या इस मरीज के लिए फॉलोअप विजिट जरूरी है?")
        f_date = "No Followup"
        if need_followup:
            chosen_date = st.date_input("Select Next Appointment Date")
            f_date = chosen_date.strftime("%Y-%m-%d")

        if st.button("Authorize & Lock Report"):
            if result_input:
                conn = sqlite3.connect('lab_data.db')
                c = conn.cursor()
                c.execute('''
                    UPDATE appointments 
                    SET status='Completed', test_result=?, sample_status='Report Generated', followup_date=? 
                    WHERE id=?
                ''', (result_input, f_date, patient_id))
                conn.commit()
                conn.close()
                st.success("🔒 रिपोर्ट लॉक हो गई है और SMART Report में देखने के लिए उपलब्ध है।")
                st.rerun()

# 5. SMART REPORT AREA
elif choice == "SMART Report":
    st.title("📄 SMART Medical Reports (Letterhead Print)")
    conn = sqlite3.connect('lab_data.db')
    df = pd.read_sql_query("SELECT * FROM appointments WHERE status='Completed'", conn)
    conn.close()
    
    if df.empty:
        st.warning("कोई भी कम्प्लीटेड रिपोर्ट उपलब्ध नहीं है। पहले 'Lab Reporting' में रिजल्ट्स दर्ज करें।")
    else:
        completed_list = [f"{row['id']} - {row['patient_name']}" for index, row in df.iterrows()]
        selected_completed = st.selectbox("Choose Case File", completed_list)
        p_id = selected_completed.split(" - ")[0]
        patient_data = df[df['id'] == int(p_id)].iloc[0]
        
        st.write("---")
        st.markdown(f"""
        <div style="border: 3px solid #4CAF50; padding: 20px; border-radius: 10px; background-color: #f9f9f9; color: black;">
            <h2 style="text-align: center; color: #4CAF50; margin-bottom: 0;">PRO HEALTH LABS & DIAGNOSTICS</h2>
            <p style="text-align: center; margin-top: 2px; font-size: 14px;">Department: {patient_data['department']} | Outsourced: {patient_data['is_outsourced']}</p>
            <hr style="border: 1px solid #4CAF50;">
            <table style="width: 100%; font-size: 16px;">
                <tr>
                    <td><b>Patient Name:</b> {patient_data['patient_name']}</td>
                    <td><b>Age/Gender:</b> {patient_data['age']} / {patient_data['gender']}</td>
                </tr>
                <tr>
                    <td><b>Ref Doctor:</b> Dr. {patient_data['ref_doctor']}</td>
                    <td><b>Next Followup Visit:</b> <mark>{patient_data['followup_date']}</mark></td>
                </tr>
            </table>
            <hr style="border: 0.5px solid #ccc;">
            <h4 style="color: #333;">TEST: {patient_data['test_name']}</h4>
            <div style="background-color: white; padding: 15px; border-left: 5px solid #4CAF50;">
                <p style="white-space: pre-line; font-size: 16px;">{patient_data['test_result']}</p>
            </div>
            <br><br>
            <p style="text-align: right; font-weight: bold;">Authorized Signatory<br><span style="font-size: 12px; font-weight: normal; color: #666;">MD (Pathology)</span></p>
        </div>
        """, unsafe_allow_html=True)

# 6. PATIENT MANAGEMENT PORTAL (Features 9 & 13)
elif choice == "Patient Management Portal":
    st.title("📊 Patient Demographics & Analytics Portal")
    conn = sqlite3.connect('lab_data.db')
    df = pd.read_sql_query("SELECT age, gender, test_name, department FROM appointments", conn)
    conn.close()
    
    if df.empty:
        st.info("एनालिटिक्स देखने के लिए पहले मरीज रजिस्टर करें।")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Gender Distribution")
            st.bar_chart(df['gender'].value_counts())
        with col2:
            st.subheader("Departmentwise Test Loads")
            st.bar_chart(df['department'].value_counts())
            
        st.subheader("Patient Age Group Distribution")
        st.line_chart(df['age'])

# 7. STAFF MANAGEMENT
elif choice == "Staff Management":
    st.title("👥 Lab Staff Directories")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Onboard New Staff")
        with st.form("staff_form", clear_on_submit=True):
            s_name = st.text_input("Staff Name")
            s_role = st.selectbox("Designation", ["Pathologist", "Radiologist", "Lab Technician", "Receptionist"])
            s_phone = st.text_input("Mobile Number")
            if st.form_submit_button("Save Staff Member") and s_name:
                conn = sqlite3.connect('lab_data.db')
                c = conn.cursor()
                c.execute("INSERT INTO staff (name, role, phone) VALUES (?, ?, ?)", (s_name, s_role, s_phone))
                conn.commit()
                conn.close()
                st.success("स्टाफ को सफलतापूर्वक सिस्टम में शामिल कर लिया गया है!")
                st.rerun()
    with col2:
        st.subheader("Active Staff List")
        conn = sqlite3.connect('lab_data.db')
        df_staff = pd.read_sql_query("SELECT * FROM staff", conn)
        conn.close()
        if not df_staff.empty:
            st.dataframe(df_staff, use_container_width=True)

# 8. PATIENT FOLLOWUP
elif choice == "Patient Followup":
    st.title("📅 Active Followup Calendars")
    conn = sqlite3.connect('lab_data.db')
    df = pd.read_sql_query("SELECT id, patient_name, test_name, followup_date FROM appointments WHERE followup_date != 'No Followup'", conn)
    conn.close()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("आने वाले दिनों में किसी मरीज का कोई फॉलोअप शेड्यूल नहीं है।")