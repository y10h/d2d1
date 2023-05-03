import re

import scrapy

PATTERN_CAR = re.compile(r"/r/[a-z0-9_]+/[a-z0-9_]+/[\d]+/")
PATTERN_CAR_LOGBOOK = re.compile(r"/r/[a-z0-9_]+/[a-z0-9_]+/[\d]+/logbook")
PATTERN_PHOTO_ALBUM = re.compile("/s/a/[a-zA-Z0-9]+")
PATTERN_PHOTO_POST = re.compile("/s/[a-zA-Z0-9]+")
PATTERN_PHOTO_IMAGE = re.compile("https://a.d-cd.net/[a-zA-Z0-9_-]+.jpg")

KIND_USER_PROFILE = "UserProfile"
KIND_CAR = "Car"
KIND_CAR_LOGBOOK = "CarLogbook"
KIND_PHOTO_ALBUM = "PhotoAlbum"
KIND_PHOTO = "Photo"
KIND_BLOG_POST = "BlogPost"
KIND_PHOTO_POST = "PhotoPost"

# If a page is a element in a container,
# then origin is an URL of the container.
META_KEY_ORIGIN = "scrapmetal_origin"
# Type of the entry.
# Parent is a root for a few collections.
# Generally, it's a car page.
META_KEY_PARENT = "scrapmetal_parent"

KEY_KIND = "kind"
KEY_URL = "url"
KEY_TITLE = "title"
KEY_DESCRIPTION = "description"
KEY_PUBLISHED = "published"
KEY_ORIGIN = "origin"
KEY_PARENT = "parent"
KEY_PHOTO_URL = "photo_url"

USER_PROFILE_TEMPLATE = "https://www.drive2.ru/users/{username}/"


class D2ExperimentalSpider(scrapy.Spider):
    name = "d2rnd"

    PARSER_MAP = {
        PATTERN_CAR: "parse_car",
        PATTERN_PHOTO_ALBUM: "parse_photo_album",
        PATTERN_CAR_LOGBOOK: "parse_logbook",
        PATTERN_PHOTO_POST: "parse_photo_post",
    }

    def start_requests(self):
        username = getattr(self, "username", None)
        if not username:
            raise ValueError(
                "username is missing, please pass it with "
                " `scrapy -a username=<drive2username>`"
            )
        url = USER_PROFILE_TEMPLATE.format(username=username)
        yield scrapy.Request(url=url, callback=self.parse_user_profile)

    def follow_known_links(self, links, patterns, response, meta={}, page_name="N/A"):
        for next_link in links:
            if next_link:
                link_parsed = False
                for pattern in patterns:
                    if pattern.match(next_link):
                        link_parsed = True
                        parser_name = self.PARSER_MAP[pattern]
                        callback = getattr(self, parser_name)
                        self.log(
                            f"Found next link {next_link} -- parser is {parser_name}."
                        )
                        next_url = response.urljoin(next_link)
                        yield scrapy.Request(next_url, callback=callback, meta=meta)
                if not link_parsed:
                    self.log(
                        f"Found a link {next_link} from the {page_name} "
                        f" ({response.url}) but don't know what to do with it"
                    )

    def parse_user_profile(self, response):
        yield from self.follow_known_links(
            links=response.css("a.u-link-area::attr(href)").getall(),
            patterns=(PATTERN_CAR, PATTERN_PHOTO_ALBUM),
            page_name="user profile",
            response=response,
        )

    def parse_car(self, response):
        meta = {
            META_KEY_PARENT: response.url,
        }
        car_title = response.css("h1.x-title::text").get().strip()
        car_description = response.css("div.c-car-desc__text").get()
        publish_date = (
            response.css("div.c-car-desc")
            .xpath("./meta[@itemprop='datePublished']/@content")
            .get()
        )
        yield {
            KEY_KIND: KIND_CAR,
            KEY_URL: response.url,
            KEY_TITLE: car_title,
            KEY_DESCRIPTION: car_description,
            KEY_PUBLISHED: publish_date,
        }
        car_photos = response.css("a.c-lightbox-anchor::attr(href)").getall()

        for car_photo_url in car_photos:
            # We don't download photos yet.
            yield {
                KEY_KIND: KIND_PHOTO,
                KEY_URL: car_photo_url,
                KEY_PARENT: meta[META_KEY_PARENT],
                KEY_ORIGIN: response.url,
            }
        yield from self.follow_known_links(
            links=response.css("h3 a.c-link::attr(href)").getall(),
            patterns=(PATTERN_CAR_LOGBOOK, PATTERN_PHOTO_ALBUM),
            page_name="car page",
            response=response,
            meta=meta,
        )

    def parse_photo_album(self, response):
        meta = {
            META_KEY_ORIGIN: response.meta.get(META_KEY_ORIGIN) or response.url,
            META_KEY_PARENT: response.meta.get(META_KEY_PARENT),
        }
        title = response.css("h1.x-title::text").get()
        # If the page origin is the same as current page, then it's the photo
        # main photo album and not one of its pages, thus we should return the payload.
        if meta[META_KEY_ORIGIN] == response.url:
            yield {
                KEY_KIND: KIND_PHOTO_ALBUM,
                KEY_TITLE: title,
                KEY_URL: response.url,
                KEY_PARENT: meta.get(META_KEY_PARENT),
            }
        next_page = response.xpath(
            "//a[has-class('c-pager__link')][@rel='next']/@href"
        ).get()
        if next_page:
            next_url = response.urljoin(next_page)
            yield scrapy.Request(next_url, callback=self.parse_photo_album, meta=meta)
        yield from self.follow_known_links(
            links=response.css("div.c-snaps-preview a::attr('href')").getall(),
            patterns=(PATTERN_PHOTO_POST,),
            page_name="photo album",
            response=response,
            meta=meta,
        )

    def parse_photo_post(self, response):
        username = (
            response.css("a.c-username").xpath("./span[@itemprop='name']/text()").get()
        )
        photo_description = response.xpath("//div[@itemprop='description']/*").get()
        photo_url = response.css("a.c-lightbox-anchor::attr('href')").get() or ""
        publish_date = response.xpath(
            "//meta[@property='article:published_time']/@content"
        ).get()
        match = PATTERN_PHOTO_IMAGE.match(photo_url)
        if not photo_url:
            self.log(f"Photo page {response.url} doesn't have a link to the photo.")
        elif photo_url and not match:
            self.log(
                f"Photo url {photo_url} from {response.url} is not recognized "
                "as an url to a photo"
            )
        elif username != getattr(self, "username"):
            self.log(
                "It looks like spider accidentally crawls a photo which "
                f"isn't owned by a user: photo post {response.url} its user {username}."
            )
        else:
            yield {
                KEY_KIND: KIND_PHOTO_POST,
                KEY_DESCRIPTION: photo_description,
                KEY_PUBLISHED: publish_date,
                KEY_PARENT: response.meta.get(META_KEY_PARENT),
                KEY_ORIGIN: response.meta.get(META_KEY_ORIGIN),
            }
            # We don't download photos yet.
            yield {
                KEY_KIND: KIND_PHOTO,
                KEY_URL: photo_url,
                KEY_PARENT: response.meta.get(META_KEY_PARENT),
                KEY_ORIGIN: response.url,
            }

    def parse_logbook(self, response):
        # Does not support parsing yet.

        yield {
            KEY_KIND: KIND_CAR_LOGBOOK,
            KEY_PARENT: response.meta.get(META_KEY_PARENT),
            KEY_URL: response.url,
        }
