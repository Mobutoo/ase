"""JSON parsing for settings inherited from PomoTracker."""

from djangorestframework_camel_case.parser import CamelCaseJSONParser


class UserSettingsJSONParser(CamelCaseJSONParser):
    # These serializer/model fields predate the snake_case API fields. Keep
    # their spelling while converting newer fields such as deepWorkDuration.
    json_underscoreize = {
        **CamelCaseJSONParser.json_underscoreize,
        "ignore_keys": (
            "startSound", "stopSound", "focusTime", "shortBreak",
            "longBreak", "focusColor", "breakColor",
        ),
        # Keys inside these dictionaries are domain identifiers (FlowMode),
        # not serializer field names. Convert only their outer field name.
        "ignore_fields": ("mode_label_map", "youtube_default_playlists"),
    }
