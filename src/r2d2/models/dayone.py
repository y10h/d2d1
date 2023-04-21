"""Data model for Day One journal."""

import dataclasses
import datetime

from typing import List


@dataclasses.dataclass
class Photo:
    path: str


@dataclasses.dataclass
class Entry:
    created_at: datetime.datetime
    tags: List[str]
    title: str
    text: str
    attached_photos: List[Photo]


@dataclasses.dataclass
class Journal:
    entries: List[Entry]
