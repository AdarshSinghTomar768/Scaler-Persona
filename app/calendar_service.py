from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .config import (
    CALCOM_API_KEY,
    CALCOM_API_VERSION,
    CALCOM_EVENT_TYPE_ID,
    CALCOM_TIMEZONE,
    GOOGLE_ACCESS_TOKEN,
    GOOGLE_CALENDAR_ID,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REFRESH_TOKEN,
    GOOGLE_TIMEZONE,
)


class CalendarService:
    def get_slots(self, days: int = 7) -> dict:
        if GOOGLE_REFRESH_TOKEN or GOOGLE_ACCESS_TOKEN:
            return self._get_google_slots(days=days)
        if CALCOM_API_KEY and CALCOM_EVENT_TYPE_ID:
            return self._get_calcom_slots(days=days)
        return {
            "provider": "unconfigured",
            "status": "missing_credentials",
            "message": "Calendar provider is not configured. Add Google Calendar or Cal.com credentials.",
            "slots": [],
        }

    def book(self, name: str, email: str, start_at: str, notes: str = "") -> dict:
        if GOOGLE_REFRESH_TOKEN or GOOGLE_ACCESS_TOKEN:
            return self._book_google(name=name, email=email, start_at=start_at, notes=notes)
        if CALCOM_API_KEY and CALCOM_EVENT_TYPE_ID:
            return self._book_calcom(name=name, email=email, start_at=start_at, notes=notes)
        return {
            "provider": "unconfigured",
            "status": "missing_credentials",
            "message": "Booking is unavailable until calendar credentials are configured.",
        }

    def get_event_types(self) -> dict:
        if not CALCOM_API_KEY:
            return {
                "provider": "cal.com",
                "status": "missing_credentials",
                "message": "CALCOM_API_KEY is not configured.",
                "event_types": [],
            }
        request = urllib.request.Request(
            "https://api.cal.com/v2/event-types",
            headers={
                "Authorization": f"Bearer {CALCOM_API_KEY}",
                "cal-api-version": CALCOM_API_VERSION,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            return {
                "provider": "cal.com",
                "status": "error",
                "message": f"Cal.com event types failed: {exc.code} {detail}",
                "event_types": [],
            }

        event_types = []
        for item in data.get("data", []):
            event_types.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "slug": item.get("slug"),
                    "lengthInMinutes": item.get("lengthInMinutes"),
                    "description": item.get("description"),
                }
            )
        return {"provider": "cal.com", "status": "ok", "event_types": event_types}

    def _google_token(self) -> str:
        if GOOGLE_REFRESH_TOKEN and GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
            payload = urllib.parse.urlencode(
                {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "refresh_token": GOOGLE_REFRESH_TOKEN,
                    "grant_type": "refresh_token",
                }
            ).encode("utf-8")
            request = urllib.request.Request(
                "https://oauth2.googleapis.com/token",
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    data = json.loads(response.read().decode("utf-8"))
                return data["access_token"]
            except urllib.error.HTTPError:
                pass
        if GOOGLE_ACCESS_TOKEN:
            return GOOGLE_ACCESS_TOKEN
        raise RuntimeError("Google Calendar credentials are not usable.")

    def _google_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._google_token()}",
            "Content-Type": "application/json",
        }

    def _get_google_slots(self, days: int) -> dict:
        tz = ZoneInfo(GOOGLE_TIMEZONE)
        now = datetime.now(tz)
        start = now.astimezone(UTC).replace(microsecond=0)
        end = (now + timedelta(days=days)).astimezone(UTC).replace(microsecond=0)
        payload = {
            "timeMin": start.isoformat().replace("+00:00", "Z"),
            "timeMax": end.isoformat().replace("+00:00", "Z"),
            "timeZone": GOOGLE_TIMEZONE,
            "items": [{"id": GOOGLE_CALENDAR_ID}],
        }
        request = urllib.request.Request(
            "https://www.googleapis.com/calendar/v3/freeBusy",
            data=json.dumps(payload).encode("utf-8"),
            headers=self._google_headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            return {
                "provider": "google-calendar",
                "status": "error",
                "message": f"Google Calendar availability failed: {exc.code} {detail}",
                "slots": [],
            }

        busy = data.get("calendars", {}).get(GOOGLE_CALENDAR_ID, {}).get("busy", [])
        busy_ranges = [
            (
                datetime.fromisoformat(item["start"].replace("Z", "+00:00")).astimezone(tz),
                datetime.fromisoformat(item["end"].replace("Z", "+00:00")).astimezone(tz),
            )
            for item in busy
        ]

        slots = []
        slot_length = timedelta(minutes=30)
        for offset in range(days):
            day = (now + timedelta(days=offset)).date()
            if day.weekday() >= 5:
                continue
            window_start = datetime.combine(day, time(hour=10), tz)
            window_end = datetime.combine(day, time(hour=18), tz)
            cursor = max(window_start, now.replace(second=0, microsecond=0) + timedelta(minutes=5))
            while cursor + slot_length <= window_end:
                overlap = any(cursor < busy_end and cursor + slot_length > busy_start for busy_start, busy_end in busy_ranges)
                if not overlap:
                    slots.append(
                        {
                            "start": cursor.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                            "end": (cursor + slot_length).astimezone(UTC).isoformat().replace("+00:00", "Z"),
                        }
                    )
                cursor += slot_length

        return {
            "provider": "google-calendar",
            "status": "ok",
            "timezone": GOOGLE_TIMEZONE,
            "slots": slots[:12],
        }

    def _book_google(self, name: str, email: str, start_at: str, notes: str) -> dict:
        start = datetime.fromisoformat(start_at.replace("Z", "+00:00"))
        end = start + timedelta(minutes=30)
        payload = {
            "summary": f"Interview with {name}",
            "description": notes or "Booked by AI persona.",
            "start": {"dateTime": start.isoformat()},
            "end": {"dateTime": end.isoformat()},
            "attendees": [{"email": email, "displayName": name}],
        }
        request = urllib.request.Request(
            f"https://www.googleapis.com/calendar/v3/calendars/{urllib.parse.quote(GOOGLE_CALENDAR_ID, safe='')}/events",
            data=json.dumps(payload).encode("utf-8"),
            headers=self._google_headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            return {
                "provider": "google-calendar",
                "status": "error",
                "message": f"Google Calendar booking failed: {exc.code} {detail}",
            }
        return {
            "provider": "google-calendar",
            "status": "confirmed",
            "booking_id": data.get("id"),
            "start": data.get("htmlLink"),
            "message": "Meeting booked successfully.",
            "raw": data,
        }

    def _get_calcom_slots(self, days: int) -> dict:
        if not str(CALCOM_EVENT_TYPE_ID).isdigit():
            return {
                "provider": "cal.com",
                "status": "invalid_config",
                "message": "CALCOM_EVENT_TYPE_ID must be the real numeric event type ID from Cal.com v2. Use /api/calendar/event-types to find it.",
                "slots": [],
            }
        start = datetime.now(UTC).replace(microsecond=0)
        end = start + timedelta(days=days)
        query = urllib.parse.urlencode(
            {
                "eventTypeId": int(CALCOM_EVENT_TYPE_ID),
                "start": start.isoformat().replace("+00:00", "Z"),
                "end": end.isoformat().replace("+00:00", "Z"),
                "timeZone": CALCOM_TIMEZONE,
                "format": "range",
            }
        )
        request = urllib.request.Request(
            f"https://api.cal.com/v2/slots?{query}",
            headers={
                "Authorization": f"Bearer {CALCOM_API_KEY}",
                "cal-api-version": CALCOM_API_VERSION,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            return {
                "provider": "cal.com",
                "status": "error",
                "message": f"Cal.com availability failed: {exc.code} {detail}",
                "slots": [],
            }

        slots = []
        for key, values in data.get("data", {}).get("slots", {}).items():
            for item in values:
                slots.append({"start": item.get("start") or key, "end": item.get("end")})

        return {"provider": "cal.com", "status": "ok", "timezone": CALCOM_TIMEZONE, "slots": slots[:12]}

    def _book_calcom(self, name: str, email: str, start_at: str, notes: str) -> dict:
        if not str(CALCOM_EVENT_TYPE_ID).isdigit():
            return {
                "provider": "cal.com",
                "status": "invalid_config",
                "message": "CALCOM_EVENT_TYPE_ID must be the real numeric event type ID from Cal.com v2.",
            }
        payload = {
            "start": start_at,
            "eventTypeId": int(CALCOM_EVENT_TYPE_ID),
            "attendee": {"name": name, "email": email, "timeZone": CALCOM_TIMEZONE},
            "responses": {"notes": notes},
        }
        request = urllib.request.Request(
            "https://api.cal.com/v2/bookings",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {CALCOM_API_KEY}",
                "cal-api-version": CALCOM_API_VERSION,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            return {"provider": "cal.com", "status": "error", "message": f"Cal.com booking failed: {exc.code} {detail}"}

        booking = data.get("data", {})
        return {
            "provider": "cal.com",
            "status": "confirmed",
            "booking_id": booking.get("id"),
            "start": booking.get("start"),
            "message": "Meeting booked successfully.",
            "raw": booking,
        }
