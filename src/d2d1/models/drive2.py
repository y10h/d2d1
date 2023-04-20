"""Data model for Drive2 blogs."""

import dataclasses
import datetime

from typing import Optional, List


@dataclasses.dataclass
class Photo:
    url: str
    path: Optional[str]


@dataclasses.dataclass
class PhotoPost:
    url: str
    photo: Photo
    description: str
    published: datetime.datetime


@dataclasses.dataclass
class PhotoAlbum:
    url: str
    photo_posts: PhotoPost


@dataclasses.dataclass
class BlogPost:
    url: str
    title: str
    published: datetime.datetime
    html_text: str
    markdown_text: str
    attached_photos: List[Photo]
    tag: str
    cost: Optional[str]
    mileage: Optional[str]


@dataclasses.dataclass
class Blog:
    url: str
    List[BlogPost]


@dataclasses.dataclass
class Car:
    url: str
    title: str
    description: str
    published: datetime.datetime
    attached_photos: List[Photo]
    photo_album: PhotoAlbum
    blog: Blog


@dataclasses.dataclass
class UserProfile:
    url: str
    photo_albums: List[PhotoAlbum]
    cars: List[Car]
    blog: Blog
