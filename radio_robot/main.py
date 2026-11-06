import argparse
import logging
import sys

from radio_robot.audio_crawler import AudioCrawler
from radio_robot.create_audio_news import CreateAudioNews


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="radio_robot",
        description="An Application to manage audio content from radio sources.",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    AudioCrawler.register_parser(subparsers)
    CreateAudioNews.register_parser(subparsers)


    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    return args.command_class().run(args)

if __name__ == "__main__":
    sys.exit(main())