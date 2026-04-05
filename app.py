import os
import datetime as dt
import streamlit as st

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_FILE = "token_calendar.json"
TIMEZONE = "Asia/Kolkata"


def get_calendar_service():
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    service = build("calendar", "v3", credentials=creds)
    return service


def create_event(title, start_dt, end_dt):
    service = get_calendar_service()

    event_body = {
        "summary": title,
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": TIMEZONE,
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": TIMEZONE,
        },
    }

    event = service.events().insert(calendarId="primary", body=event_body).execute()
    return event


st.title("My Calendar Assistant")

title = st.text_input("Event Title", "Test Meeting")
date = st.date_input("Date")
time = st.time_input("Time", dt.time(15, 0))
duration = st.number_input("Duration (minutes)", 30)

if st.button("Create Event"):
    start_dt = dt.datetime.combine(date, time)
    end_dt = start_dt + dt.timedelta(minutes=duration)

    event = create_event(title, start_dt, end_dt)

    st.success("Event created!")
    st.write(event.get("htmlLink"))
