"""Settings JSON output preserves flow identifiers inside configuration maps."""

from djangorestframework_camel_case.render import CamelCaseJSONRenderer


class UserSettingsJSONRenderer(CamelCaseJSONRenderer):
    json_underscoreize = {
        **CamelCaseJSONRenderer.json_underscoreize,
        # Outer field names remain camelCase; deep_work/free_flow map keys
        # must match the mode identifiers used by the timer and settings UI.
        "ignore_fields": ("mode_label_map", "youtube_default_playlists"),
    }
