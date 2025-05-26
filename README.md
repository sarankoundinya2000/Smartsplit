

💸 SmartSplit – AI-Powered Group Expense Splitter

SmartSplit is an intelligent expense-splitting app built with Streamlit and Google Gemini Vision API. It makes group expense tracking effortless by allowing users to scan receipts, split costs fairly, and send personalized email summaries—all in a beautiful, intuitive interface.

⸻
🎬 Demo Video

Want to see SmartSplit in action?
Check out the demo on YouTube: https://youtu.be/ANoXysbAT2M

⸻

🚀 Features
	•	🔐 Google Login – Secure OAuth2 authentication using your Google account
	•	👥 Group Management – Create groups, add/remove members, and update member info
	•	🧾 Receipt Scanning – Upload receipt images and auto-extract items & prices using Gemini Vision
	•	💰 Tax & Total Calculation – Smart splitting that includes tax and total price breakdown
	•	🔄 Flexible Splitting – Choose who paid and who shares each expense
	•	📊 Expense History – See a clear summary of who owes whom
	•	📧 Email Notifications – Automatically sends detailed summaries via Gmail API
	•	💻 Modern UI – Streamlit-based clean and responsive interface

⸻

⚙️ Setup Instructions

1. Clone the Repository

git clone <your-repo-url>
cd <your-repo-directory>

2. Install Dependencies

pip install -r requirements.txt

3. Set Up Google Cloud Credentials
	•	Go to Google Cloud Console
	•	Create a new project and enable:
	•	Gmail API
	•	Google Calendar API
	•	Google People API
	•	Create OAuth 2.0 credentials (as a Desktop App)
	•	Download the credentials.json file and place it in your project root directory

4. Configure Gemini API Key
	•	Get your Gemini API key from Google AI Studio
	•	Create a .env file in your root directory:

GEMINI_API_KEY=your_gemini_api_key_here

5. Run the Application

streamlit run smart_split_recent.py


⸻

🧑‍💻 Usage Guide
	1.	Login – Use Google authentication to log in securely
	2.	Create or Select a Group – Add group members with names and email addresses
	3.	Upload Receipt – Upload a photo of the group expense receipt
	4.	Extract Items – Use Gemini Vision to extract items and prices automatically
	5.	Split Expenses – Assign payer and shared members for each item
	6.	Save & Notify – Save the session and email a detailed summary to all participants

⸻

📁 File Structure

smart_split_recent.py      # Main Streamlit application
requirements.txt           # Required Python libraries
credentials.json           # Google OAuth credentials (excluded)
.env                       # Gemini API key (excluded)
data/
  ├── users.json           # User details (auto-generated)
  ├── groups.json          # Group information (auto-generated)
  └── expenses.json        # Expense records (auto-generated)


⸻

🔒 Notes
	•	Data Privacy: All user and group data is stored locally in the data/ folder.
	•	OAuth & APIs: Ensure correct configuration of credentials.json and that required Google APIs are enabled.
	•	Image Quality: For best receipt extraction results, upload high-resolution and well-lit images.

⸻

🛠 Troubleshooting
	•	❗ Authentication Errors: Check if credentials.json is correct and OAuth scopes are enabled
	•	🧾 Receipt Extraction Issues: Verify your Gemini API key and image quality
	•	⚠️ Widget/Streamlit Errors: Refresh the browser tab or clear the cache
⸻

Enjoy smarter expense sharing with SmartSplit! 🎉
Built with ❤️ using Streamlit and Google AI.

⸻
