from __future__ import annotations

"""CalDAV server views (RFC 4791).

Implements a CalDAV server compatible with Apple Calendar, DAVx5, and
Thunderbird:

- OPTIONS     — DAV capability discovery (``DAV: 1, 2, calendar-access``)
- PROPFIND    — property discovery on principal/calendar/event resources
- REPORT      — CALENDAR-QUERY and CALENDAR-MULTIGET
- MKCALENDAR  — create a new calendar collection (RFC 4791 sec 5.3.1)
- GET         — fetch a single VEVENT as .ics
- PUT         — create or update a VEVENT (If-Match / If-None-Match support)
- DELETE      — remove a VEVENT

All views require HTTP Basic authentication via the ``caldav_auth_required``
decorator.  The principal URL hierarchy is::

    /caldav/                              — root
    /caldav/<username>/                   — user principal
    /caldav/<username>/<calendar_id>/     — calendar collection
    /caldav/<username>/<calendar_id>/<uid>.ics  — event resource

Autodiscovery (RFC 6764)::

    /.well-known/caldav  → 301 → /caldav/

Limitations / TODO:
- FREEBUSY not yet implemented
- ACL / sharing not yet implemented
"""

import hashlib
import logging
from datetime import timezone
from xml.etree import ElementTree as ET

from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ..models import Calendar, Event
from ..caldav.auth import caldav_auth_required
from ..caldav.ical import event_to_ics, events_from_ics

logger = logging.getLogger(__name__)

# XML namespaces used in CalDAV
NS_DAV = "DAV:"
NS_CAL = "urn:ietf:params:xml:ns:caldav"
NS_CS = "http://calendarserver.org/ns/"

_CONTENT_TYPE_XML = "application/xml; charset=utf-8"
_CONTENT_TYPE_ICS = "text/calendar; charset=utf-8"


def _el(tag: str, ns: str = NS_DAV, text: str | None = None) -> ET.Element:
    el = ET.Element(f"{{{ns}}}{tag}")
    if text is not None:
        el.text = text
    return el


def _multistatus(*responses: ET.Element) -> bytes:
    ms = ET.Element(f"{{{NS_DAV}}}multistatus")
    ms.extend(responses)
    return ET.tostring(ms, xml_declaration=True, encoding="utf-8")


def _prop_response(href: str, props_ok: dict, props_nf: list | None = None) -> ET.Element:
    """Build a <response> element with <propstat> children."""
    resp = _el("response")
    _el_href = _el("href", text=href)
    resp.append(_el_href)

    # 200 propstat
    propstat_ok = _el("propstat")
    prop = _el("prop")
    for tag, value in props_ok.items():
        if isinstance(value, ET.Element):
            prop.append(value)
        else:
            el = ET.SubElement(prop, tag)
            if value is not None:
                el.text = str(value)
    propstat_ok.append(prop)
    status_ok = _el("status", text="HTTP/1.1 200 OK")
    propstat_ok.append(status_ok)
    resp.append(propstat_ok)

    # 404 propstat (not found)
    if props_nf:
        propstat_nf = _el("propstat")
        prop_nf = _el("prop")
        for tag in props_nf:
            ET.SubElement(prop_nf, tag)
        propstat_nf.append(prop_nf)
        status_nf = _el("status", text="HTTP/1.1 404 Not Found")
        propstat_nf.append(status_nf)
        resp.append(propstat_nf)

    return resp


@method_decorator([csrf_exempt, caldav_auth_required], name="dispatch")
class CalDavRootView(View):
    """Handles PROPFIND and MKCALENDAR on the CalDAV root / user principal."""

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.method == "PROPFIND":
            return self.propfind(request, *args, **kwargs)
        if request.method == "MKCALENDAR":
            return self.mkcalendar(request, *args, **kwargs)
        if request.method == "OPTIONS":
            return self.options(request, *args, **kwargs)
        return HttpResponse(status=405, headers={"Allow": "OPTIONS, PROPFIND, MKCALENDAR"})

    def options(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        response = HttpResponse(status=200)
        response["Allow"] = "OPTIONS, PROPFIND, MKCALENDAR"
        response["DAV"] = "1, 2, calendar-access"
        return response

    def propfind(self, request: HttpRequest, username: str) -> HttpResponse:
        href = f"/caldav/{username}/"

        # calendar-home-set tells clients where calendars live (RFC 4791 sec 6.2.1)
        home_set = ET.Element(f"{{{NS_CAL}}}calendar-home-set")
        home_href = ET.SubElement(home_set, f"{{{NS_DAV}}}href")
        home_href.text = f"/caldav/{username}/"

        props_ok = {
            f"{{{NS_DAV}}}displayname": username,
            f"{{{NS_DAV}}}resourcetype": _build_collection_type(principal=True),
            f"{{{NS_DAV}}}current-user-principal": _current_principal(username),
            f"{{{NS_CAL}}}calendar-home-set": home_set,
        }
        responses = [_prop_response(href, props_ok)]

        # Depth:1 — list all user's calendars (Apple Calendar, DAVx5 discovery)
        depth = request.META.get("HTTP_DEPTH", "0")
        if depth in ("1", "infinity"):
            calendars = Calendar.objects.filter(
                owner__user=request.caldav_user, caldav_enabled=True
            )
            for cal in calendars:
                cal_href = f"/caldav/{username}/{cal.pk}/"
                cal_props = {
                    f"{{{NS_DAV}}}displayname": cal.name,
                    f"{{{NS_DAV}}}resourcetype": _build_collection_type(calendar=True),
                    f"{{{NS_CS}}}getctag": _calendar_ctag(cal),
                }
                responses.append(_prop_response(cal_href, cal_props))

        body = _multistatus(*responses)
        return HttpResponse(body, content_type=_CONTENT_TYPE_XML, status=207)

    def mkcalendar(self, request: HttpRequest, username: str) -> HttpResponse:
        """Handle MKCALENDAR to create a new calendar collection (RFC 4791 sec 5.3.1)."""
        if request.caldav_user.username != username:
            return HttpResponse(status=403)

        # Parse optional displayname from the request body
        cal_name = "New Calendar"
        if request.body:
            try:
                root = ET.fromstring(request.body)
                displayname_el = root.find(f".//{{{NS_DAV}}}displayname")
                if displayname_el is not None and displayname_el.text:
                    cal_name = displayname_el.text
            except ET.ParseError:
                return HttpResponse(status=400)

        # Find the CircleMember for this user
        from circles.models import CircleMember

        member = CircleMember.objects.filter(user=request.caldav_user).first()
        if member is None:
            return HttpResponse(status=403)

        calendar = Calendar.objects.create(
            owner=member,
            name=cal_name,
            caldav_enabled=True,
        )
        response = HttpResponse(status=201)
        response["Location"] = f"/caldav/{username}/{calendar.pk}/"
        return response


@method_decorator([csrf_exempt, caldav_auth_required], name="dispatch")
class CalDavCalendarView(View):
    """Handles PROPFIND and REPORT on a calendar collection."""

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.method == "PROPFIND":
            return self.propfind(request, *args, **kwargs)
        if request.method == "REPORT":
            return self.report(request, *args, **kwargs)
        if request.method == "OPTIONS":
            return self.options(request, *args, **kwargs)
        return HttpResponse(status=405, headers={"Allow": "OPTIONS, PROPFIND, REPORT"})

    def options(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        response = HttpResponse(status=200)
        response["Allow"] = "OPTIONS, PROPFIND, REPORT"
        response["DAV"] = "1, 2, calendar-access"
        return response

    def propfind(self, request: HttpRequest, username: str, calendar_id: int) -> HttpResponse:
        try:
            calendar = Calendar.objects.get(
                pk=calendar_id,
                owner__user=request.caldav_user,
                caldav_enabled=True,
            )
        except Calendar.DoesNotExist:
            return HttpResponse(status=404)

        href = f"/caldav/{username}/{calendar_id}/"
        ctag = _calendar_ctag(calendar)
        rt = _build_collection_type(calendar=True)

        props_ok = {
            f"{{{NS_DAV}}}displayname": calendar.name,
            f"{{{NS_DAV}}}resourcetype": rt,
            f"{{{NS_CS}}}getctag": ctag,
        }
        responses = [_prop_response(href, props_ok)]

        # List child event resources
        depth = request.META.get("HTTP_DEPTH", "0")
        if depth in ("1", "infinity"):
            for event in calendar.events.all():
                event_href = f"/caldav/{username}/{calendar_id}/{event.uid}.ics"
                event_props = {
                    f"{{{NS_DAV}}}getetag": f'"{event.etag}"',
                    f"{{{NS_DAV}}}getcontenttype": _CONTENT_TYPE_ICS,
                    f"{{{NS_DAV}}}resourcetype": _el("resourcetype"),
                }
                responses.append(_prop_response(event_href, event_props))

        body = _multistatus(*responses)
        return HttpResponse(body, content_type=_CONTENT_TYPE_XML, status=207)

    def report(self, request: HttpRequest, username: str, calendar_id: int) -> HttpResponse:
        try:
            calendar = Calendar.objects.get(
                pk=calendar_id,
                owner__user=request.caldav_user,
                caldav_enabled=True,
            )
        except Calendar.DoesNotExist:
            return HttpResponse(status=404)

        try:
            root = ET.fromstring(request.body)
        except ET.ParseError:
            return HttpResponse(status=400)

        tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag

        if tag == "calendar-multiget":
            return self._multiget(request, calendar, username, calendar_id, root)
        if tag == "calendar-query":
            return self._calendar_query(request, calendar, username, calendar_id, root)

        return HttpResponse(status=422)

    def _multiget(
        self,
        request: HttpRequest,
        calendar: Calendar,
        username: str,
        calendar_id: int,
        root: ET.Element,
    ) -> HttpResponse:
        hrefs = [el.text for el in root.findall(f"{{{NS_DAV}}}href") if el.text]
        uid_list = [
            h.rstrip("/").split("/")[-1].removesuffix(".ics") for h in hrefs
        ]
        events = calendar.events.filter(uid__in=uid_list)
        responses = [
            _event_response(event, username, calendar_id) for event in events
        ]
        return HttpResponse(_multistatus(*responses), content_type=_CONTENT_TYPE_XML, status=207)

    def _calendar_query(
        self,
        request: HttpRequest,
        calendar: Calendar,
        username: str,
        calendar_id: int,
        root: ET.Element,
    ) -> HttpResponse:
        # Minimal filter support: time-range only
        events = calendar.events.all()
        time_range = root.find(
            f".//{{{NS_CAL}}}time-range"
        )
        if time_range is not None:
            start = time_range.get("start")
            end = time_range.get("end")
            if start:
                events = events.filter(end_at__gte=_parse_ical_dt(start))
            if end:
                events = events.filter(start_at__lte=_parse_ical_dt(end))

        responses = [
            _event_response(event, username, calendar_id) for event in events
        ]
        return HttpResponse(_multistatus(*responses), content_type=_CONTENT_TYPE_XML, status=207)


@method_decorator([csrf_exempt, caldav_auth_required], name="dispatch")
class CalDavEventView(View):
    """Handles GET, PUT, DELETE on a single event resource."""

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        method = request.method
        if method == "GET":
            return self.get(request, *args, **kwargs)
        if method == "PUT":
            return self.put(request, *args, **kwargs)
        if method == "DELETE":
            return self.delete(request, *args, **kwargs)
        if method == "OPTIONS":
            return self.options(request, *args, **kwargs)
        return HttpResponse(status=405, headers={"Allow": "OPTIONS, GET, PUT, DELETE"})

    def options(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        response = HttpResponse(status=200)
        response["Allow"] = "OPTIONS, GET, PUT, DELETE"
        response["DAV"] = "1, 2, calendar-access"
        return response

    def get(self, request: HttpRequest, username: str, calendar_id: int, uid: str) -> HttpResponse:
        try:
            event = Event.objects.get(
                uid=uid,
                calendar__pk=calendar_id,
                calendar__owner__user=request.caldav_user,
            )
        except Event.DoesNotExist:
            return HttpResponse(status=404)

        ics = _wrap_vcalendar(event_to_ics(event))
        response = HttpResponse(ics, content_type=_CONTENT_TYPE_ICS)
        response["ETag"] = f'"{event.etag}"'
        return response

    def put(self, request: HttpRequest, username: str, calendar_id: int, uid: str) -> HttpResponse:
        try:
            calendar = Calendar.objects.get(
                pk=calendar_id,
                owner__user=request.caldav_user,
                caldav_enabled=True,
            )
        except Calendar.DoesNotExist:
            return HttpResponse(status=404)

        raw = request.body.decode("utf-8", errors="replace")
        try:
            parsed_list = events_from_ics(raw)
        except Exception as exc:
            logger.warning("CalDAV PUT parse error: %s", exc)
            return HttpResponse(str(exc), status=400)

        if not parsed_list:
            return HttpResponse("No VEVENT found in request body.", status=400)

        ev_data = parsed_list[0]
        event_uid = ev_data.get("uid") or uid

        # ETag conditional headers (RFC 4791 / RFC 2616)
        if_match = request.META.get("HTTP_IF_MATCH", "").strip('"')
        if_none_match = request.META.get("HTTP_IF_NONE_MATCH", "").strip('"')

        try:
            event = Event.objects.get(uid=event_uid, calendar=calendar)

            # If-Match: update only if ETag matches (prevents lost updates)
            if if_match and event.etag != if_match:
                return HttpResponse(status=412)  # Precondition Failed

            # If-None-Match: * means "only create, don't overwrite"
            if if_none_match == "*":
                return HttpResponse(status=412)  # Precondition Failed — resource exists

            # Update in place — immutable uid preserved
            event.title = ev_data.get("title", event.title)
            event.description = ev_data.get("description", event.description)
            event.location = ev_data.get("location", event.location)
            event.start_at = ev_data["start_at"]
            event.end_at = ev_data["end_at"]
            event.all_day = ev_data.get("all_day", event.all_day)
            event.recurrence_rule = ev_data.get("recurrence_rule", event.recurrence_rule)
            event.caldav_raw = raw
            event.etag = _compute_etag(event)
            event.save()
            created = False
        except Event.DoesNotExist:
            # If-Match present but resource doesn't exist — fail
            if if_match:
                return HttpResponse(status=412)  # Precondition Failed

            event = Event.objects.create(
                uid=event_uid,
                calendar=calendar,
                title=ev_data.get("title", ""),
                description=ev_data.get("description", ""),
                location=ev_data.get("location", ""),
                start_at=ev_data["start_at"],
                end_at=ev_data["end_at"],
                all_day=ev_data.get("all_day", False),
                recurrence_rule=ev_data.get("recurrence_rule"),
                caldav_raw=raw,
            )
            event.etag = _compute_etag(event)
            event.save(update_fields=["etag"])
            created = True

        response = HttpResponse(status=201 if created else 204)
        response["ETag"] = f'"{event.etag}"'
        return response

    def delete(self, request: HttpRequest, username: str, calendar_id: int, uid: str) -> HttpResponse:
        try:
            event = Event.objects.get(
                uid=uid,
                calendar__pk=calendar_id,
                calendar__owner__user=request.caldav_user,
            )
        except Event.DoesNotExist:
            return HttpResponse(status=404)

        event.delete()
        return HttpResponse(status=204)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_etag(event: Event) -> str:
    source = f"{event.uid}{event.updated_at.isoformat()}"
    return hashlib.md5(source.encode()).hexdigest()  # noqa: S324


def _calendar_ctag(calendar: Calendar) -> str:
    latest = calendar.events.order_by("-updated_at").values_list("updated_at", flat=True).first()
    tag_source = f"{calendar.pk}{latest}"
    return hashlib.md5(tag_source.encode()).hexdigest()  # noqa: S324


def _build_collection_type(principal: bool = False, calendar: bool = False) -> ET.Element:
    rt = _el("resourcetype")
    rt.append(_el("collection"))
    if principal:
        rt.append(_el("principal"))
    if calendar:
        rt.append(ET.Element(f"{{{NS_CAL}}}calendar"))
    return rt


def _current_principal(username: str) -> ET.Element:
    el = _el("current-user-principal")
    href = ET.SubElement(el, f"{{{NS_DAV}}}href")
    href.text = f"/caldav/{username}/"
    return el


def _event_response(event: Event, username: str, calendar_id: int) -> ET.Element:
    href = f"/caldav/{username}/{calendar_id}/{event.uid}.ics"
    ics_block = _wrap_vcalendar(event_to_ics(event))
    cal_data_el = ET.Element(f"{{{NS_CAL}}}calendar-data")
    cal_data_el.text = ics_block
    props_ok = {
        f"{{{NS_DAV}}}getetag": f'"{event.etag}"',
        f"{{{NS_DAV}}}getcontenttype": _CONTENT_TYPE_ICS,
        f"{{{NS_CAL}}}calendar-data": cal_data_el,
    }
    return _prop_response(href, props_ok)


def _wrap_vcalendar(vevent_block: str) -> str:
    return "\r\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Ase//CalDAV//EN",
        vevent_block,
        "END:VCALENDAR",
    ])


def _parse_ical_dt(value: str):
    """Parse an iCalendar datetime string (basic format) to a UTC datetime."""
    from datetime import datetime
    try:
        dt = datetime.strptime(value.rstrip("Z"), "%Y%m%dT%H%M%S")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None
