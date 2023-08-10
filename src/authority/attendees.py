"""
Module containing the XKE source class
"""
import logging
import re
import typing
from datetime import datetime, date

import gcloud_config_helper
import google
import pytz
from google.cloud import firestore




def main():
    if gcloud_config_helper.on_path():
        credentials, _ = gcloud_config_helper.default()
    else:
        logging.info("using application default credentials")
        credentials, _ = google.auth.default()
    xke_db = firestore.Client(credentials=credentials, project="xke-nxt")



    now = datetime.now().astimezone(pytz.utc)
    events = (
        xke_db.collection("events")
        .where(
            "startTime",
            ">=",
            now,
        )
        .order_by("startTime")
    )
    attendees = {}

    for event in events.stream():
        event_date = event.to_dict().get('startTime')
        if event_date.date() > date(2023, 1, 1):
            break
        for session in (
                xke_db.collection("events")
                        .document(event.id)
                        .collection("sessions-private")
                        .stream()
        ):
            session_data = session.reference.get().to_dict()
            session_data.update(xke_db.document(session.reference.path.replace("/sessions-private/", "/sessions-public/")).get().to_dict())
            if session_data.get('title').startswith('Crossing'):
                pass
            if session_data.get('unit', {}).get('id') != 'CLOUD':
                continue
            print(session_data.get('title'))
            start_time = session_data.get("startTime")
            if start_time not in attendees:
                attendees[start_time] = set()
            for ref in session.reference.collection("attendees").stream():
                attendee = ref.reference.get().to_dict()
                if attendee.get("name").startswith("Tibor"):
                    print(session_data['title'])
                attendees[start_time].add(attendee.get("name"))

    for s in sorted(attendees.keys()):
        print(s.isoformat())
        for a in sorted(attendees[s]):
            print (f" - {a}")


if __name__ == "__main__":
    main()
