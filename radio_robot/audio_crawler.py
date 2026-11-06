import json
import logging
from pathlib import Path
from xml.etree import ElementTree
from datetime import datetime
import requests
import urllib3

from radio_robot.enterprise import CrawlType
from radio_robot.utils import RobotRadioUtils


class AudioCrawler:
    def __init__(self, url: str):
        self.url = "https://www.rtp.pt/play/itunes/518"
        self.dest_dir = Path("Portugueses_no_Mundo")
        self._db_file = Path("downloaded.json")

        # --------------------------------------------------------------------
        # SSL
        # --------------------------------------------------------------------

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self._session = requests.Session()
        self._session.verify = False

    @staticmethod
    def register_parser(subparsers):
        parser = subparsers.add_parser(
            "crawl",
            help="Crawl audio content from a specified source",
        )

        parser.add_argument(
            "--type",
            type=CrawlType,
            choices=list(CrawlType),
            required=True,
            help="Type of crawl",
        )

        parser.set_defaults(command_class=AudioCrawler)

    def run(self, args):
        logging.info(f"Crawl type {args.type}")

        if args.type == CrawlType.RSS:
            logging.info(f"Crawling RSS feed from {self.url}")
            # Implement RSS crawling logic here
            self.rss_crawl()
        elif args.type == CrawlType.WEBSITE:
            logging.info(f"Crawling website from {self.url}")
            # Implement website crawling logic here
        elif args.type == CrawlType.SITEMAP:
            logging.info(f"Crawling sitemap from {self.url}")
            # Implement sitemap crawling logic here
        elif args.type == CrawlType.API:
            logging.info(f"Crawling API from {self.url}")
            # Implement API crawling logic here
        else:
            logging.error(f"Unknown crawl type: {args.type}")

        return 0

    def load_db(self):
        if self._db_file.exists():
            with open(self._db_file, "r", encoding="utf-8") as f:
                return json.load(f)

        return {}

    def save_db(self, db):
        with open(self._db_file, "w", encoding="utf-8") as f:
            json.dump(
                db,
                f,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
    def _save_file(self, mp3_url, filepath):
        with self._session.get( mp3_url, stream=True, timeout=120 ) as r:
            r.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

    def rss_crawl(self):
        logging.info(f"Starting RSS crawl from {self.url}")
        # Implement the actual RSS crawling logic here
        # For example, fetch the RSS feed, parse it, and download audio files
        self.dest_dir.mkdir(exist_ok=True)
        db = self.load_db()
        logging.info("Loading RSS...")

        rss = self._session.get(self.url, timeout=30)
        rss.raise_for_status()
        root = ElementTree.fromstring(rss.content)
        items = root.findall(".//item")
        logging.info(f"Found {len(items)} episodes")

        for item in items:
            title = item.findtext("title", "Untitled").strip()
            guid = item.findtext("guid")
            if not guid:
                logging.info(f"SKIP: missing GUID -> {title}")
                continue
            guid = guid.strip()
            # Last 8 chars only
            guid8 = guid[-8:]
            if guid8 in db:
                logging.info(f"SKIP: {title}")
                continue
            enclosure = item.find("enclosure")
            if enclosure is None:
                logging.info(f"SKIP: no enclosure -> {title}")
                continue
            mp3_url = enclosure.attrib.get("url")
            if not mp3_url:
                logging.info(f"SKIP: no MP3 URL -> {title}")
                continue
            safe_title = RobotRadioUtils.sanitize_filename(title)
            filename = f"{safe_title}_{guid8}.mp3"
            filepath = self.dest_dir / filename
            logging.info(f"DOWNLOAD: {filename}")
            self._save_file(mp3_url, filepath)

            db[guid8] = { "title": title, "file": filename,
                "guid": guid, "mp3_url": mp3_url,
                "downloaded_at": datetime.utcnow().isoformat()
            }

            self.save_db(db)
        logging.info("Done.")