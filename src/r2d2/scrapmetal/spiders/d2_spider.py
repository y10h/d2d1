import re

import scrapy

PATTERN_CAR = re.compile(r"/r/[a-z0-9_]+/[a-z0-9_]+/[\d]+/")
PATTERN_CAR_LOGBOOK = re.compile(r"/r/[a-z0-9_]+/[a-z0-9_]+/[\d]+/logbook")
PATTERN_PHOTO_ALBUM = re.compile("/s/a/[a-zA-Z0-9]+")

KIND_USER_PROFILE = "UserProfile"
KIND_CAR = "Car"
KIND_CAR_LOGBOOK = "CarLogbook"
KIND_PHOTO_ALBUM = "PhotoAlbum"
KIND_PHOTO = "Photo"
KIND_BLOG_POST = "BlogPost"
KIND_PHOTO_POST = "PhotoPost"

META_KEY_ORIGIN = "scrapmetal_origin"
META_KEY_KIND = "scrapmetal_kind"
META_KEY_PARENT = "scrapmetal_parent"

KEY_URL = "url"
KEY_TITLE = "title"
KEY_DESCRIPTION = "description"
KEY_PUBLISHED = "published"

USER_PROFILE_TEMPLATE = "https://www.drive2.ru/users/{username}/"


class D2ExperimentalSpider(scrapy.Spider):
    name = "d2rnd"

    def start_requests(self):
        username = getattr(self, "username", None)
        if not username:
            raise ValueError(
                "username is missing, please pass it with "
                " `scrapy -a username=<drive2username>`"
            )
        url = USER_PROFILE_TEMPLATE.format(username=username)
        yield scrapy.Request(url=url, callback=self.parse_user_profile)

    def parse_user_profile(self, response):
        meta = {
            META_KEY_ORIGIN: response.url,
            META_KEY_KIND: KIND_USER_PROFILE,
        }
        next_links = response.css("a.u-link-area::attr(href)").getall()
        for next_link in next_links:
            if next_link:
                if PATTERN_CAR.match(next_link):
                    callback = self.parse_car
                elif PATTERN_PHOTO_ALBUM.match(next_link):
                    callback = self.parse_photo_album
                else:
                    self.log(
                        f"Found a link {next_link} from user profile "
                        "but don't know what to do with it"
                    )
                    continue
                next_url = response.urljoin(next_link)
                self.log(f"Found next link {next_link} -- callback is {callback}.")
                yield scrapy.Request(next_url, callback=callback, meta=meta)

    def parse_car(self, response):
        meta = {
            META_KEY_ORIGIN: response.url,
            META_KEY_KIND: KIND_CAR,
            META_KEY_PARENT: response.url,
        }
        car_title = response.css("h1.x-title::text").get().strip()
        car_description = response.css("div.c-car-desc__text").get()
        publish_date = (
            response.css("div.c-car-desc")
            .xpath("./meta[@itemprop='datePublished']")
            .css("::attr('content')")
            .get()
        )
        yield {
            META_KEY_KIND: KIND_CAR,
            KEY_URL: response.url,
            KEY_TITLE: car_title,
            KEY_DESCRIPTION: car_description,
            KEY_PUBLISHED: publish_date,
        }
        car_photos = response.css("a.c-lightbox-anchor::attr(href)").getall()
        next_links = response.css("h3 a.c-link::attr(href)").getall()
        for car_photo_url in car_photos:
            # Do not schedule parsing photo since we don't download photos yet.
            yield {
                META_KEY_KIND: KIND_PHOTO,
                KEY_URL: car_photo_url,
                META_KEY_PARENT: meta[META_KEY_PARENT],
            }
        for next_link in next_links:
            if next_link:
                if PATTERN_CAR_LOGBOOK.match(next_link):
                    callback = self.parse_logbook
                elif PATTERN_PHOTO_ALBUM.match(next_link):
                    callback = self.parse_photo_album
                else:
                    self.log(
                        f"Found a link {next_link} from car page "
                        f"{response.url} but don't know what to do with it"
                    )
                    continue
                next_url = response.urljoin(next_link)
                self.log(f"Found next link {next_link} -- callback is {callback}.")
                yield scrapy.Request(next_url, callback=callback, meta=meta)

    def parse_photo_album(self, response):
        {
            META_KEY_ORIGIN: response.url,
            META_KEY_KIND: KIND_PHOTO_ALBUM,
            META_KEY_PARENT: response.meta.get(META_KEY_PARENT),
        }
        # Does not support parsing yet.
        yield {
            META_KEY_KIND: KIND_PHOTO_ALBUM,
            META_KEY_PARENT: response.meta.get(META_KEY_PARENT),
            KEY_URL: response.url,
        }

    def parse_logbook(self, response):
        # Does not support parsing yet.
        {
            META_KEY_ORIGIN: response.url,
            META_KEY_KIND: KIND_CAR_LOGBOOK,
            META_KEY_PARENT: response.meta.get(META_KEY_PARENT),
        }
        yield {
            META_KEY_KIND: KIND_CAR_LOGBOOK,
            META_KEY_PARENT: response.meta.get(META_KEY_PARENT),
            KEY_URL: response.url,
        }
