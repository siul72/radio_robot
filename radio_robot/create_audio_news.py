
import io
import logging
import os
import re
from datetime import datetime
from typing import cast

import paramiko
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
from openai import OpenAI
import feedparser
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, \
    ChatCompletionUserMessageParam

from radio_robot.enterprise import NewsType
from radio_robot.sft_uploader import SftpUploader


class CreateAudioNews:
    def __init__(self):
        self._audio_news_file = "data/news.mp3"
        self._text_news_file = "data/news_script.txt"
        self.url = "https://www.rtp.pt/noticias/rss/pais"
        # Load environment variables
        load_dotenv("/home/radio/.env")
        self._chat_bot_api_key = os.getenv("DEEPSEEK_API_KEY")
        self._chat_bot_url = "https://api.deepseek.com"
        self._elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self._elevenlabs_voice_id = "kFbMPjq3Xu43WhJuf6Wz"
        self.in_file_path = "../in/events/events.json"  # Path to the events JSON file
        self._tts_client = None

    @property
    def tts_client(self):
        if not self._tts_client:
            self._tts_client = ElevenLabs(api_key=self._elevenlabs_api_key)
        return self._tts_client

    @classmethod
    def register_parser(cls, subparsers):
        parser = subparsers.add_parser(
            "create_news",
            help="Create audio news from a specified source",
        )

        parser.add_argument(
            "--type",
             choices=[e.name for e in NewsType],
            required=True,
            help="Type of crawl",
        )

        parser.set_defaults(command_class=CreateAudioNews)

    def run(self, args):
        logging.info(f"News type {args.type}")
        k = args.type
        news_type = NewsType.from_str(k)
        if news_type == NewsType.RSS:
            logging.info(f"Creating audio news from RSS feed: {self.url}")
            # Implement RSS news creation logic here
            self.create_news_from_rss()
            self.convert_text_to_audio()
            self.send_mp3_to_radio()
        elif news_type == NewsType.EVENTS_JSON:
            logging.info(f"Creating audio news from events JSON: {self.in_file_path}")
            # Implement events JSON news creation logic here:
            self.create_audio_from_events_json()
        elif news_type == NewsType.WEBSITE:
            logging.info(f"Creating audio news from website: {self.url}")
            # Implement website news creation logic here
        elif news_type == NewsType.API:
            logging.info(f"Creating audio news from API: {self.url}")
            # Implement API news creation logic here
        else:
            logging.error(f"Unknown news type: {args.type}")

        return 0

    def create_news_from_rss(self):
        # Implement the logic to create audio news from RSS feed
        logging.info(f"Fetching RSS feed from {self.url}")
        # Fetch and process the RSS feed, then create audio news
        # Load environment variables
        if not self._chat_bot_api_key:
            logging.error("ERROR: DEEPSEEK_API_KEY not defined")
            raise ValueError("DEEPSEEK_API_KEY not defined")

        client = OpenAI(api_key=self._chat_bot_api_key, base_url=self._chat_bot_url)
        feed = feedparser.parse(self.url)
        # Get latest 5 stories
        stories = []
        for entry in feed.entries[:5]:
            summary = entry.get("description", "")
            # Remove HTML tags
            summary = re.sub(r"<[^>]+>", "", summary)
            stories.append(
                f"""
                Headline: {entry.title}
                
                Summary:
                {summary.strip()}
                """
                    )

        news_input = "\n\n".join(stories)
        
        prompt = f"""
        You are the news editor of Radio Litoral.
        
        Create a radio news bulletin in European Portuguese.
        
        Rules:
        - Professional radio journalist tone.
        - Neutral and factual.
        - Summarise the stories naturally.
        - Maximum 120 words.
        - Suitable for a 45-60 second news bulletin.
        - Do not mention RTP.
        - Do not use bullet points.
        - Output only the final bulletin text.
        
        Stories:
        
        {news_input}
        """
        messages = [
            ChatCompletionSystemMessageParam(
                role="system",
                content="You are a professional Portuguese radio journalist."
            ),
            ChatCompletionUserMessageParam(
                role="user",
                content=prompt
            ),
        ]

        response = client.chat.completions.create(
            model="deepseek-flash",
            messages=messages,
            temperature=0.3
        )


        bulletin = response.choices[0].message.content.strip()
        
        # Add branded intro and outro
        final_script = f"""
        [pause]Rádio Litoral Notícias.
        
        {bulletin}
        
        [pause]Estas foram as notícias da Rádio Litoral.
        [pause][pause][pause]
        """

        with open(self._text_news_file, "w", encoding="utf-8") as f:
            f.write(final_script)
        
        logging.info(final_script)

    def _create_mp3_from_text(self, text: str, output_file: str):
        try:
            audio = self.tts_client.text_to_speech.convert( voice_id=self._elevenlabs_voice_id,
                                                            model_id="eleven_multilingual_v2", text=text )

            total_bytes = 0

            with open(output_file, "wb") as f:
                for chunk in audio:
                    if chunk:
                        f.write(chunk)
                        total_bytes += len(chunk)

            if total_bytes == 0:
                logging.error("ERROR: ElevenLabs returned no audio")
                raise ValueError("ElevenLabs returned no audio")

            logging.info(f"Received {total_bytes} bytes")

            size = os.path.getsize(output_file)
            if size < 1024:
                logging.error(f"ERROR: Output file too small ({size} bytes)")
                raise ValueError("Output file too small")
            logging.info(f"Created {output_file} ({size} bytes)")
        except Exception as e:
            logging.error(f"ERROR calling ElevenLabs: {e}")
            raise ValueError("Failed to create audio file")

    def convert_text_to_audio(self):
        if not self._elevenlabs_api_key:
            logging.error("ERROR: ELEVENLABS_API_KEY not defined")
            raise ValueError("ELEVENLABS_API_KEY not defined")


        with open(self._text_news_file, "r", encoding="utf-8") as f:
            news_text = f.read().strip()
        if not news_text:
            logging.error("ERROR: news_script.txt is empty")
            raise ValueError("news_script.txt is empty")

        self._create_mp3_from_text(text=news_text, output_file=self._audio_news_file)

        logging.info(f"Created {self._audio_news_file}")
        return True

    @staticmethod
    def load_private_key():
        key_text = os.environ["SFTP_PRIVATE_KEY"]

        for key_cls in (
                paramiko.Ed25519Key,
                paramiko.RSAKey,
                paramiko.ECDSAKey,
        ):
            try:
                return key_cls.from_private_key(
                    io.StringIO(key_text)
                )
            except Exception as e:
                logging.error(f"Error occurred while loading private key: {e}")
                pass

        raise RuntimeError("Unsupported private key format")

    def send_mp3_to_radio(self):

        uploader = SftpUploader(
            host="litoral-fm.lat",
            port=22,
            username="radio",
            private_key=self.load_private_key(),
        )

        uploader.upload_file( local_file=self._audio_news_file,
                              remote_file="/incoming/news/news.mp3",)


    @staticmethod
    def build_tts_text(event):
        parts = [event["tts"]]

        if event.get("tts_bilheteira"):
            parts.append(event["tts_bilheteira"])

        return " ".join(parts)

    def generate_event_audio(self, event):
        date_dir = datetime.fromisoformat(event["data_inicio"]).strftime("%Y-%m-%d")
        safe_name = "".join(c for c in event["titulo"]if c.isalnum() or c in (" ", "-", "_")).strip().replace(" ", "_")
        output_dir = os.path.join("..", "out", "events", date_dir)
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"{safe_name}.mp3")
        text = CreateAudioNews.build_tts_text(event)
        self._create_mp3_from_text(text=text, output_file=output_file)
        return  output_file

    def create_audio_from_events_json(self):
        import json
        generated_files = []
        with open(self.in_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        events = data.get("eventos", [])
        for event in events:
            mp3_file = self.generate_event_audio(event)
            generated_files.append(mp3_file)


