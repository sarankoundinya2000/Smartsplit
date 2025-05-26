import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import os
import json
from datetime import datetime
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
from dotenv import load_dotenv



# Page configuration must be the first Streamlit command
st.set_page_config(
    page_title="SmartSplit",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables
load_dotenv('api.env')

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    st.error("GEMINI_API_KEY not found in environment variables. Please create a .env file with your API key.")

# Google OAuth configuration
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/contacts.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

# Paths for credentials and token
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

def init_session_state():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None
    if 'calendar_service' not in st.session_state:
        st.session_state.calendar_service = None
    if 'contacts_service' not in st.session_state:
        st.session_state.contacts_service = None
    if 'users' not in st.session_state:
        st.session_state.users = {}
    if 'groups' not in st.session_state:
        st.session_state.groups = {}
    if 'expenses' not in st.session_state:
        st.session_state.expenses = {}
    if 'credentials' not in st.session_state:
        st.session_state.credentials = None

def authenticate_google():
    try:
        # Always start fresh by removing existing token
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
            
        if not os.path.exists(CREDENTIALS_FILE):
            st.error("credentials.json file not found! Please make sure you have downloaded it from Google Cloud Console.")
            return None
            
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE,
            SCOPES,
            redirect_uri='http://localhost:8080'
        )
        
        # Force new login by not using cached credentials
        creds = flow.run_local_server(
            port=8080,
            prompt='consent',
            authorization_prompt_message='Please login with your Google account'
        )
        
        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        
        return creds
    except Exception as e:
        st.error(f"Authentication error: {str(e)}")
        return None

# Initialize session state
init_session_state()

# Data persistence functions
def load_data():
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    try:
        with open(data_dir / "users.json", "r") as f:
            st.session_state.users = json.load(f)
    except FileNotFoundError:
        st.session_state.users = {}
    
    try:
        with open(data_dir / "groups.json", "r") as f:
            st.session_state.groups = json.load(f)
    except FileNotFoundError:
        st.session_state.groups = {}
    
    try:
        with open(data_dir / "expenses.json", "r") as f:
            st.session_state.expenses = json.load(f)
    except FileNotFoundError:
        st.session_state.expenses = {}

def save_data():
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    with open(data_dir / "users.json", "w") as f:
        json.dump(st.session_state.users, f)
    
    with open(data_dir / "groups.json", "w") as f:
        json.dump(st.session_state.groups, f)
    
    with open(data_dir / "expenses.json", "w") as f:
        json.dump(st.session_state.expenses, f)

# Load data at startup
load_data()

# Define the email sending function
def send_expenses_summary_email(expenses, group_name, member_email, is_payer=False):
    try:
        if not st.session_state.credentials:
            st.error("No credentials available. Please log in again.")
            return False
            
        # Create message
        message = MIMEMultipart()
        message['to'] = member_email
        message['from'] = st.session_state.user_email
        message['subject'] = f'Expense Summary for {group_name}'

        # Calculate totals and what this person owes/paid
        total_amount = sum(expense['amount'] for expense in expenses)
        person_paid = sum(expense['amount'] for expense in expenses if expense['payer_email'] == member_email)
        person_owes = sum(expense['share'] for expense in expenses if member_email in expense['assignee_emails'] and expense['payer_email'] != member_email)
        
        # Create email body
        body = f"""
        <html>
            <body>
                <h2>Expense Summary for {group_name}</h2>
                <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        """
        
        if is_payer:
            body += f"""
                <h3>You paid a total of: ${person_paid:.2f}</h3>
                <p>Here's what others owe you:</p>
                <ul>
            """
            # Calculate what others owe this person
            owing_summary = {}
            for expense in expenses:
                if expense['payer_email'] == member_email:
                    for i, assignee_email in enumerate(expense['assignee_emails']):
                        if assignee_email != member_email:
                            assignee_name = expense['assignee_names'][i]
                            if assignee_name not in owing_summary:
                                owing_summary[assignee_name] = 0
                            owing_summary[assignee_name] += expense['share']
            
            for person, amount in owing_summary.items():
                body += f"<li><strong>{person}</strong> owes you: ${amount:.2f}</li>"
            
            body += "</ul>"
        else:
            body += f"""
                <h3>Your Share: ${person_owes:.2f}</h3>
                <p>Here's what you owe to others:</p>
                <ul>
            """
            # Calculate what this person owes to others
            owing_summary = {}
            for expense in expenses:
                if member_email in expense['assignee_emails'] and expense['payer_email'] != member_email:
                    payer_name = expense['payer_name']
                    if payer_name not in owing_summary:
                        owing_summary[payer_name] = 0
                    owing_summary[payer_name] += expense['share']
            
            for person, amount in owing_summary.items():
                body += f"<li>You owe <strong>{person}</strong>: ${amount:.2f}</li>"
            
            body += "</ul>"
        
        body += """
                <h3>Expense Details:</h3>
                <table border="1" cellpadding="5" style="border-collapse: collapse;">
                    <tr style="background-color: #f2f2f2;">
                        <th>Item</th>
                        <th>Amount</th>
                        <th>Paid By</th>
                        <th>Your Share</th>
                    </tr>
        """
        
        # Add relevant expenses to the table
        for expense in expenses:
            if member_email in expense['assignee_emails'] or expense['payer_email'] == member_email:
                body += f"""
                    <tr>
                        <td>{expense['item']}</td>
                        <td>${expense['amount']:.2f}</td>
                        <td>{expense['payer_name']}</td>
                        <td>${expense['share'] if member_email in expense['assignee_emails'] else expense['amount']:.2f}</td>
                    </tr>
                """
        
        body += """
                </table>
                <br>
                <p>Please settle your share of the expenses.</p>
            </body>
        </html>
        """
        
        message.attach(MIMEText(body, 'html'))
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send email using Gmail API
        gmail_service = build('gmail', 'v1', credentials=st.session_state.credentials)
        gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return True
    except Exception as e:
        st.error(f"Failed to send email: {str(e)}")
        return False

# CSS for better text visibility and sidebar
st.markdown("""
    <style>
    /* Main container styling */
    .main {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    
    /* Button styling */
    .stButton>button {
        background-color: #ff652f;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        border: none;
        transition: all 0.3s ease;
        width: 100%;
    }
    
    .stButton>button:hover {
        background-color: #ff4f1f;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    
    /* Text input styling */
    .stTextInput>div>input {
        background-color: #f8f9fa;
        color: #2c3e50;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 0.5rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput>div>input:focus {
        border-color: #ff652f;
        box-shadow: 0 0 0 2px rgba(255,101,47,0.2);
    }
    
    /* Select box styling */
    .stSelectbox>div>select {
        background-color: #f8f9fa;
        color: #2c3e50;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 0.5rem;
    }
    
    /* Multiselect styling */
    .stMultiSelect>div {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
    }
    
    /* Headers styling */
    h1, h2, h3 {
        color: #2c3e50;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    
    /* Card styling for expenses */
    .expense-card {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
    }
    
    /* Summary box styling */
    .summary-box {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
    }
    
    /* Success message styling */
    .stSuccess {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    
    /* Warning message styling */
    .stWarning {
        background-color: #fff3cd;
        color: #856404;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    
    /* Error message styling */
    .stError {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 0.5rem;
        font-weight: 600;
    }
    
    /* File uploader styling */
    .stFileUploader>div {
        background-color: #f8f9fa;
        border: 2px dashed #e9ecef;
        border-radius: 8px;
        padding: 1rem;
    }
    
    /* Progress bar styling */
    .stProgress>div>div>div {
        background-color: #ff652f;
    }
    </style>
""", unsafe_allow_html=True)

# Main application
st.title("SmartSplit 💸")
st.markdown("### Split expenses with friends and family")

# Authentication flow
if not st.session_state.authenticated:
    st.markdown("### 🔐 Login")
    st.markdown("Please log in with your Google account to continue.")
    
    if st.button("Login with Google"):
        try:
            creds = authenticate_google()
            if creds:
                # Get user email
                service = build('oauth2', 'v2', credentials=creds)
                user_info = service.userinfo().get().execute()
                user_email = user_info['email']
                
                # Update session state
                st.session_state.authenticated = True
                st.session_state.user_email = user_email
                st.session_state.credentials = creds
                
                # Initialize user if not exists
                if user_email not in st.session_state.users:
                    st.session_state.users[user_email] = {
                        "full_name": user_info.get('name', user_email),
                        "groups": [],
                        "expenses": []
                    }
                    save_data()
                
                st.success(f"Welcome, {st.session_state.users[user_email]['full_name']}!")
                st.rerun()
            else:
                st.error("Failed to authenticate. Please make sure you have the correct credentials.json file.")
        except Exception as e:
            st.error(f"Authentication failed: {str(e)}")
    st.stop()

# Sidebar for group management
with st.sidebar:
    st.header("👥 Groups")
    
    # Show user info in sidebar
    st.markdown(f"**Logged in as:** {st.session_state.users[st.session_state.user_email]['full_name']}")
    st.markdown(f"*{st.session_state.user_email}*")
    
    # Logout button
    if st.button("Logout"):
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        # Remove token file to force new login
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        # Reinitialize session state
        init_session_state()
        st.rerun()
    
    st.markdown("---")
    
    # Create new group
    with st.expander("Create New Group", expanded=True):
        group_name = st.text_input("Group Name", placeholder="e.g., Friends Trip", key="new_group_name")
        if st.button("Create Group", key="add_group_button"):
            if group_name and group_name not in st.session_state.groups:
                st.session_state.groups[group_name] = {
                    "members": [st.session_state.user_email],
                    "expenses": []
                }
                st.session_state.users[st.session_state.user_email]["groups"].append(group_name)
                save_data()
                st.success(f"Group '{group_name}' created!")
            elif group_name in st.session_state.groups:
                st.error("Group name already exists!")
    
    # Display and manage groups
    if st.session_state.groups:
        st.markdown("### Your Groups")
        selected_group = st.selectbox("Select Group", list(st.session_state.groups.keys()), key="group_select")
        
        # Group management options
        with st.expander("Manage Group", expanded=True):
            # Delete group option
            if st.button("Delete Group", key="delete_group"):
                if selected_group:
                    # Remove group from all members
                    for member_email in st.session_state.groups[selected_group]["members"]:
                        if member_email in st.session_state.users:
                            st.session_state.users[member_email]["groups"].remove(selected_group)
                    # Delete the group
                    del st.session_state.groups[selected_group]
                    save_data()
                    st.success(f"Group '{selected_group}' deleted!")
                    st.rerun()
            
            # Show existing members
            if st.session_state.groups[selected_group]["members"]:
                st.markdown("#### Members")
                for member_email in st.session_state.groups[selected_group]["members"]:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        member_name = st.session_state.users[member_email]["full_name"]
                        st.markdown(f"• {member_name} ({member_email})")
                    with col2:
                        if member_email != st.session_state.user_email:  # Can't remove yourself
                            if st.button("Remove", key=f"remove_{member_email}"):
                                # Remove member from group
                                st.session_state.groups[selected_group]["members"].remove(member_email)
                                # Remove group from member's groups
                                st.session_state.users[member_email]["groups"].remove(selected_group)
                                save_data()
                                st.success(f"Removed {member_name} from the group!")
                                st.rerun()
        
        # Add a section to update member names
        with st.expander("Update Member Names"):
            for member_email in st.session_state.groups[selected_group]["members"]:
                current_name = st.session_state.users[member_email]["full_name"]
                col1, col2 = st.columns([2, 1])
                with col1:
                    new_name = st.text_input(f"Name for {member_email}", 
                                            value=current_name, 
                                            key=f"update_name_{member_email}")
                with col2:
                    if st.button("Update", key=f"update_btn_{member_email}"):
                        if new_name != current_name:
                            st.session_state.users[member_email]["full_name"] = new_name
                            save_data()
                            st.success(f"Updated name for {member_email} to {new_name}")
                            st.rerun()
        
        # Then show the add member form
        st.write("**Add New Member:**")
        col1, col2 = st.columns(2)
        with col1:
            member_email = st.text_input("Email", placeholder="e.g., friend@example.com", key="add_member_email")
        with col2:
            member_name = st.text_input("Name", placeholder="e.g., John Smith", key="add_member_name")
        
        if st.button("Add Member", key="add_member_button"):
            if member_email and member_name:
                if member_email not in st.session_state.groups[selected_group]["members"]:
                    # If user doesn't exist in our system yet, create a new entry
                    if member_email not in st.session_state.users:
                        st.session_state.users[member_email] = {
                            "full_name": member_name,
                            "groups": [selected_group],
                            "expenses": []
                        }
                    else:
                        if selected_group not in st.session_state.users[member_email]["groups"]:
                            st.session_state.users[member_email]["groups"].append(selected_group)
                    
                    # Add to group
                    st.session_state.groups[selected_group]["members"].append(member_email)
                    save_data()
                    st.success(f"Added '{member_name}' to '{selected_group}'")
                else:
                    st.error("Member already in group")
            else:
                st.error("Please enter both email and name")

# Main content area
if 'selected_group' in locals() and selected_group:
    st.header(f"Group: {selected_group}")
    
    # Show expense summary
    with st.expander("Expense Summary", expanded=True):
        if st.session_state.groups[selected_group]["expenses"]:
            st.markdown("### Who Owes Whom")
            
            # Calculate who owes whom
            debts = {}
            for expense in st.session_state.groups[selected_group]["expenses"]:
                payer_email = expense['payer']
                payer_name = st.session_state.users[payer_email]["full_name"]
                
                for assignee_email in expense['assignees']:
                    if assignee_email != payer_email:  # Don't count if someone owes themselves
                        assignee_name = st.session_state.users[assignee_email]["full_name"]
                        
                        if assignee_email not in debts:
                            debts[assignee_email] = {}
                        
                        if payer_email not in debts[assignee_email]:
                            debts[assignee_email][payer_email] = 0
                        
                        debts[assignee_email][payer_email] += expense['share']
            
            # Display the summary
            if debts:
                for debtor_email, owes_to in debts.items():
                    debtor_name = st.session_state.users[debtor_email]["full_name"]
                    total_owed = sum(owes_to.values())
                    
                    st.markdown(f"""
                    <div style='background-color: #f8f9fa; padding: 0.5rem; border-radius: 8px; margin-bottom: 0.5rem; font-size: 0.9rem;'>
                        <p style='margin: 0;'><strong>{debtor_name}</strong> owes a total of <strong>${total_owed:.2f}</strong>:</p>
                    """, unsafe_allow_html=True)
                    
                    for creditor_email, amount in owes_to.items():
                        creditor_name = st.session_state.users[creditor_email]["full_name"]
                        st.markdown(f"""
                        <div style='padding-left: 1rem; font-size: 0.85rem;'>
                            • ${amount:.2f} to {creditor_name}
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No debts to show.")
        else:
            st.info("No expenses recorded yet.")
    
    # Upload and process receipt
    with st.expander("Add New Expense", expanded=True):
        uploaded_file = st.file_uploader("Upload Receipt", type=['png', 'jpg', 'jpeg'])
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            # Resize image to a reasonable width while maintaining aspect ratio
            max_width = 400
            ratio = max_width / image.width
            new_height = int(image.height * ratio)
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
            st.image(image, caption="Uploaded Receipt", width=max_width)
        
            if st.button("Extract Items"):
                with st.spinner("Processing receipt..."):
                    try:
                        # Initialize Gemini model
                        model = genai.GenerativeModel('gemini-1.5-flash-latest')
                        response = model.generate_content([
                            """Extract items, prices, and tax information from this receipt. 
                            Look for:
                            1. Individual items and their prices
                            2. Subtotal amount
                            3. Tax amounts (C-taxable, A-taxable, etc.)
                            4. Total amount
                            
                            Format the response as:
                            ITEMS:
                            Item1: $Price1
                            Item2: $Price2
                            ...
                            
                            TAXES:
                            C-taxable: $Amount
                            A-taxable: $Amount
                            ...
                            
                            TOTALS:
                            Subtotal: $Amount
                            Total: $Amount""",
                            image
                        ])
                        
                        # Parse the response
                        items = []
                        taxes = {}
                        subtotal = 0
                        total = 0
                        
                        current_section = None
                        for line in response.text.split('\n'):
                            line = line.strip()
                            if not line:
                                continue
                                
                            if line == "ITEMS:":
                                current_section = "items"
                                continue
                            elif line == "TAXES:":
                                current_section = "taxes"
                                continue
                            elif line == "TOTALS:":
                                current_section = "totals"
                                continue
                            
                            if current_section == "items" and ':' in line and '$' in line:
                                name, price = line.split(':')
                                price = float(price.strip().replace('$', ''))
                                items.append({"name": name.strip(), "price": price})
                            elif current_section == "taxes" and ':' in line and '$' in line:
                                tax_type, amount = line.split(':')
                                amount = float(amount.strip().replace('$', ''))
                                taxes[tax_type.strip()] = amount
                            elif current_section == "totals" and ':' in line and '$' in line:
                                total_type, amount = line.split(':')
                                amount = float(amount.strip().replace('$', ''))
                                if "subtotal" in total_type.lower():
                                    subtotal = amount
                                elif "total" in total_type.lower():
                                    total = amount
                        
                        # Use total amount if available, otherwise use subtotal
                        final_amount = total if total > 0 else subtotal
                        
                        if items:
                            # Adjust item prices proportionally to match the final amount
                            items_total = sum(item['price'] for item in items)
                            if items_total > 0:
                                ratio = final_amount / items_total
                                for item in items:
                                    item['price'] = round(item['price'] * ratio, 2)
                            
                            st.session_state.current_items = items
                            st.session_state.total_amount = final_amount
                            
                            # Show amounts in a clear order
                            st.markdown("### Receipt Summary")
                            
                            # Show subtotal
                            st.markdown(f"#### Subtotal: ${subtotal:.2f}")
                            
                            # Show tax breakdown
                            if taxes:
                                st.markdown("#### Tax Breakdown:")
                                total_tax = 0
                                for tax_type, amount in taxes.items():
                                    st.markdown(f"- {tax_type}: ${amount:.2f}")
                                    total_tax += amount
                                st.markdown(f"**Total Tax:** ${total_tax:.2f}")
                            
                            # Show final total
                            st.markdown(f"#### Total Amount: ${final_amount:.2f}")
                            
                            # Show items
                            st.markdown("### Items")
                            for item in items:
                                st.markdown(f"- {item['name']}: ${item['price']:.2f}")
                        else:
                            st.error("No items found in the receipt")
                    except Exception as e:
                        st.error(f"Error processing receipt: {str(e)}")

    # Expense management
    if 'current_items' in st.session_state:
        st.subheader("Split Expenses")
        
        # Create a mapping of emails to names and names to emails for selection
        email_to_name = {email: st.session_state.users[email]["full_name"] for email in st.session_state.groups[selected_group]["members"]}
        name_to_email = {st.session_state.users[email]["full_name"]: email for email in st.session_state.groups[selected_group]["members"]}
        member_names = list(name_to_email.keys())
        
        # Ask who paid before processing items
        payer_name = st.selectbox("Who paid the bill?", member_names)
        payer_email = name_to_email[payer_name]
        
        # To store pending expenses before saving
        if 'pending_expenses' not in st.session_state:
            st.session_state.pending_expenses = []
        
        for i, item in enumerate(st.session_state.current_items):
            with st.expander(f"{item['name']} - ${item['price']}", expanded=True):
                st.markdown("#### Split between:")
                assignee_names = st.multiselect(
                    "Select people to split with",
                    member_names,
                    default=[],
                    key=f"multiselect_{i}_{item['name'].replace(' ', '_')}"
                )
                
                # Convert selected names back to emails for storage
                assignee_emails = [name_to_email[name] for name in assignee_names]
                
                if assignee_names:
                    share = item['price'] / len(assignee_emails)
                    st.markdown(f"**Each person owes:** ${share:.2f}")
                    
                    # Automatically add to pending expenses when assignees are selected
                    expense = {
                        "id": str(datetime.now().timestamp()),
                        "item": item['name'],
                        "amount": item['price'],
                        "payer_email": payer_email,
                        "payer_name": payer_name,
                        "assignee_emails": assignee_emails,
                        "assignee_names": assignee_names,
                        "share": share,
                        "date": datetime.now().isoformat()
                    }
                    
                    # Check if this item is already in pending expenses
                    item_exists = False
                    for pending_exp in st.session_state.pending_expenses:
                        if pending_exp["item"] == item['name']:
                            item_exists = True
                            # Update the existing expense
                            pending_exp.update(expense)
                            break
                    
                    if not item_exists:
                        st.session_state.pending_expenses.append(expense)
                        st.success(f"{item['name']} added to pending expenses")
                        st.rerun()

        # Show pending expenses summary
        if st.session_state.pending_expenses:
            st.markdown("### Pending Expenses Summary")
            with st.container():
                st.markdown("#### Total Amount")
                total_amount = sum(item["amount"] for item in st.session_state.pending_expenses)
                st.markdown(f"**${total_amount:.2f}**")
                
                st.markdown("#### Amount paid by each person")
                payer_summary = {}
                for exp in st.session_state.pending_expenses:
                    payer_name = exp['payer_name']
                    if payer_name not in payer_summary:
                        payer_summary[payer_name] = 0
                    payer_summary[payer_name] += exp['amount']
                
                for payer, amount in payer_summary.items():
                    percentage = (amount / total_amount) * 100 if total_amount > 0 else 0
                    st.markdown(f"• {payer}: ${amount:.2f} ({percentage:.1f}% of total)")
                
                st.markdown("#### What each person owes")
                owing_summary = {}
                for expense in st.session_state.pending_expenses:
                    for i, assignee_email in enumerate(expense['assignee_emails']):
                        assignee_name = expense['assignee_names'][i]
                        if assignee_email != expense['payer_email']:
                            if assignee_name not in owing_summary:
                                owing_summary[assignee_name] = {}
                            
                            if expense['payer_name'] not in owing_summary[assignee_name]:
                                owing_summary[assignee_name][expense['payer_name']] = 0
                            
                            owing_summary[assignee_name][expense['payer_name']] += expense['share']
                
                for person, owes_to in owing_summary.items():
                    for creditor, amount in owes_to.items():
                        st.markdown(f"• {person} owes {creditor}: ${amount:.2f}")
                
                # Save All and Clear buttons
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("Save All Expenses", key="save_all"):
                        if not st.session_state.pending_expenses:
                            st.warning("No expenses to save!")
                        else:
                            with st.spinner("Processing all expenses..."):
                                # Create a copy of pending expenses to work with
                                pending_expenses_copy = st.session_state.pending_expenses.copy()
                                
                                # Save all expenses at once
                                all_storage_expenses = []
                                for expense in pending_expenses_copy:
                                    storage_expense = {
                                        "id": expense["id"],
                                        "item": expense["item"],
                                        "amount": expense["amount"],
                                        "payer": expense["payer_email"],
                                        "assignees": expense["assignee_emails"],
                                        "share": expense["share"],
                                        "date": expense["date"]
                                    }
                                    all_storage_expenses.append(storage_expense)
                                
                                # Add all expenses to the group at once
                                st.session_state.groups[selected_group]["expenses"].extend(all_storage_expenses)
                                save_data()
                                
                                # Prepare and send all emails at once
                                member_expenses_map = {}
                                for member_email in st.session_state.groups[selected_group]["members"]:
                                    member_expenses = [
                                        expense for expense in pending_expenses_copy
                                        if member_email in expense['assignee_emails'] or member_email == expense['payer_email']
                                    ]
                                    if member_expenses:
                                        member_expenses_map[member_email] = member_expenses
                                
                                # Send all emails
                                for member_email, member_expenses in member_expenses_map.items():
                                    is_payer = any(expense['payer_email'] == member_email for expense in member_expenses)
                                    send_expenses_summary_email(
                                        member_expenses,
                                        selected_group,
                                        member_email,
                                        is_payer
                                    )
                                
                                # Clear all pending expenses at once
                                st.session_state.pending_expenses = []
                                
                                st.success("All expenses saved and notifications sent!")
                
                with col2:
                    if st.button("Clear Pending", key="clear_pending"):
                        st.session_state.pending_expenses = []

# Footer
st.markdown("---")
st.markdown('<p style="text-align: center; color: #2c3e50;">Made with ❤️ using Gemini Vision | <a href="https://github.com/patchy631/ai-engineering-hub/issues">Report an Issue</a></p>', unsafe_allow_html=True)