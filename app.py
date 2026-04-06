import datetime as dt
import urllib.parse

import requests
import streamlit as st
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TIMEZONE = "Asia/Kolkata"


def get_google_auth_url():
    params = {
        "client_id": st.secrets["google"]["client_id"],
        "redirect_uri": st.secrets["google"]["redirect_uri"],
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)


def exchange_code_for_token(code):
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": st.secrets["google"]["client_id"],
        "client_secret": st.secrets["google"]["client_secret"],
        "redirect_uri": st.secrets["google"]["redirect_uri"],
        "grant_type": "authorization_code",
    }
    response = requests.post(token_url, data=data, timeout=30)
    response.raise_for_status()
    return response.json()


def handle_oauth_callback():
    query_params = st.query_params

    if "code" in query_params and "google_token" not in st.session_state:
        code = query_params["code"]

        if isinstance(code, list):
            code = code[0]

        token_data = exchange_code_for_token(code)
        st.session_state["google_token"] = token_data

        st.query_params.clear()
        st.rerun()


def get_calendar_service():
    if "google_token" not in st.session_state:
        auth_url = get_google_auth_url()
        st.info("Please sign in with Google first.")
        st.markdown(f"[Sign in with Google]({auth_url})")
        st.stop()

    token_data = st.session_state["google_token"]

    creds = Credentials(
        token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=st.secrets["google"]["client_id"],
        client_secret=st.secrets["google"]["client_secret"],
        scopes=SCOPES,
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        st.session_state["google_token"]["access_token"] = creds.token

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

handle_oauth_callback()

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

        st.write(f"**Calendar Link:** {event.get('htmlLink', '')}")

    except Exception as e:
        st.error(f"Error: {e}")
