
---

# 💸 SmartSplit – AI-Powered Group Expense Splitter

**SmartSplit** is an intelligent expense-splitting app built with **Streamlit** and **Google Gemini Vision API**. It simplifies group expense tracking by allowing users to scan receipts, split costs fairly, and send personalized email summaries—all in a beautiful, intuitive interface.

---

## 🎬 Demo Video

📺 **Watch the demo**: [SmartSplit on YouTube](https://youtu.be/ANoXysbAT2M)

---

## 🚀 Features

* 🔐 **Google Login** – Secure OAuth2 authentication with your Google account
* 👥 **Group Management** – Create groups, add/remove members, and edit member info
* 🧾 **Receipt Scanning** – Upload images of receipts and extract items/prices using Gemini Vision
* 💰 **Tax & Total Calculation** – Smart splitting with tax and total price handling
* 🔄 **Flexible Splitting** – Choose who paid and who shares each expense
* 📊 **Expense History** – View a detailed summary of who owes whom
* 📧 **Email Notifications** – Send automatic Gmail summaries to all participants
* 💻 **Modern UI** – Responsive, clean design built with Streamlit

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd <your-repo-directory>
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Google Cloud Credentials

* Visit [Google Cloud Console](https://console.cloud.google.com/)
* Create a project and enable the following APIs:

  * Gmail API
  * Google Calendar API
  * Google People API
* Create OAuth 2.0 credentials (Desktop App)
* Download `credentials.json` and place it in your project root

### 4. Configure Gemini API Key

* Get your Gemini API key from [Google AI Studio](https://makersuite.google.com/)
* Create a `.env` file in your root directory and add:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 5. Run the Application

```bash
streamlit run smart_split_recent.py
```

---

## 🧑‍💻 Usage Guide

1. **Login** – Authenticate via Google
2. **Create or Select Group** – Add group members (name + email)
3. **Upload Receipt** – Upload receipt photo
4. **Extract Items** – Auto-extract items and prices with Gemini Vision
5. **Split Expenses** – Choose who paid and who shares each item
6. **Save & Notify** – Save session and send summary emails to members

---

## 📁 File Structure

```
smart_split_app.py      # Main Streamlit app
requirements.txt           # Python dependencies
credentials.json           # Google OAuth credentials (excluded from repo)
.env                       # Gemini API key (excluded from repo)
```

---

## 🔒 Notes

* 🔧 **OAuth & APIs** – Ensure correct API setup and valid credentials.json
* 🧾 **Image Quality** – Use high-resolution and well-lit images for best extraction results

---

## 🛠 Troubleshooting

* ❗ **OAuth Issues** – Ensure `credentials.json` is correctly configured with required scopes
* 📷 **Extraction Errors** – Check Gemini API key and image quality
* ⚠️ **Streamlit UI Glitches** – Refresh tab or clear browser cache

---

Enjoy smarter expense sharing with **SmartSplit**! 🎉
*Built with ❤️ using Streamlit and Google AI.*


