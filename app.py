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
            client_config = {
                "installed": {
                    "client_id": st.secrets["google"]["client_id"],
                    "project_id": st.secrets["google"]["project_id"],
                    "auth_uri": st.secrets["google"]["auth_uri"],
                    "token_uri": st.secrets["google"]["token_uri"],
                    "auth_provider_x509_cert_url": st.secrets["google"]["auth_provider_x509_cert_url"],
                    "client_secret": st.secrets["google"]["client_secret"],
                    "redirect_uris": ["http://localhost"]
                }
            }

            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def create_event(title, start_dt, end_dt, description="", attendee_email="", add_meet=False):
    service = get_calendar_service()

    event_body = {
        "summary": title,
        "description": description,
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": TIMEZONE,
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": TIMEZONE,
        },
    }

    if attendee_email.strip():
        event_body["attendees"] = [{"email": attendee_email.strip()}]

    if add_meet:
        event_body["conferenceData"] = {
            "createRequest": {
                "requestId": f"meet-{int(dt.datetime.now().timestamp())}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }

    event = service.events().insert(
        calendarId="primary",
        body=event_body,
        sendUpdates="all",
        conferenceDataVersion=1 if add_meet else 0,
    ).execute()

    return event


st.title("My Calendar Assistant")

title = st.text_input("Event Title", "Test Meeting")
date = st.date_input("Date")
time = st.time_input("Time", dt.time(15, 0))
duration = st.number_input("Duration (minutes)", min_value=5, value=30, step=5)
attendee_email = st.text_input("Attendee Email (optional)", "")
description = st.text_area("Meeting Details / Description", "")
add_meet = st.checkbox("Add Google Meet link")

if st.button("Create Event"):
    start_dt = dt.datetime.combine(date, time)
    end_dt = start_dt + dt.timedelta(minutes=int(duration))

    try:
        event = create_event(
            title=title,
            start_dt=start_dt,
            end_dt=end_dt,
            description=description,
            attendee_email=attendee_email,
            add_meet=add_meet,
        )

        st.success("Event created successfully.")

        st.subheader("Meeting Details")
        st.write(f"**Title:** {event.get('summary', '')}")
        st.write(f"**Start:** {event['start'].get('dateTime', '')}")
        st.write(f"**End:** {event['end'].get('dateTime', '')}")

        if attendee_email.strip():
            st.write(f"**Invite sent to:** {attendee_email}")

        st.write(f"**Description:** {event.get('description', '')}")

        meet_link = event.get("hangoutLink")
        if meet_link:
            st.write(f"**Google Meet:** {meet_link}")

        st.write(f"**Calendar Link:** {event.get('htmlLink')}")

    except Exception as e:
        st.error(f"Error: {e}")
