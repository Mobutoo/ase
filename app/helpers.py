"""Helper functions for the view's app."""

import os
from pathlib import Path


def saveSettings(form, user):
    """Save user settings to the database."""
    settings = user.settings
    if form['image']:
        save_image_local(form['image'])
        settings.image = form['image'].name
    if form['shortBreak']:
        settings.shortBreak = int(form['shortBreak'])
    if form['longBreak']:
        settings.longBreak = int(form['longBreak'])
    if form['theme']:
        settings.theme = form['theme']
        theme_color_map = {
            'forest': '#EAE7B1',
            'aquamarine': '#6BAAAA',
            'default': '#f1c232',
            'white': '#f1c232',
            'garnet': '#9a1b18',
            'coral': '#FAD6A5',
            'afrofuturist': '#f59e0b',
        }
        settings.focusColor = theme_color_map.get(form['theme'], '#f1c232')
    if form['startSound']:
        settings.startSound = form['startSound']
    if form['stopSound']:
        settings.stopSound = form['stopSound']
    if form['timezone']:
        settings.timezone = form['timezone']
    settings.save()


def save_image_local(image):
    """Save profile image to local media directory."""
    media_dir = Path(os.environ.get('MEDIA_ROOT', 'media/profile_pics'))
    media_dir.mkdir(parents=True, exist_ok=True)
    dest = media_dir / image.name
    with open(dest, 'wb') as f:
        for chunk in image.chunks():
            f.write(chunk)
