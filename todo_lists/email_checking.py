import imaplib
import email, email.policy
import datetime
from settings.models import Setting
import time
import base64
import binascii
import logging
import sys
import asyncio
import threading
import queue
from sqlalchemy import orm, create_engine

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("[{asctime} | {levelname}]: {message}", style="{", datefmt="%m-%d-%Y %I:%M:%S %p")

# file_handler = logging.FileHandler("ClassroomToTrello.log", "a")
# file_handler.setFormatter(formatter)
# logger.addHandler(file_handler)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


class EmailChecker:
    class ExitError(Exception):
        """indicates self.run_forever() should exit. Not used in base class"""
        pass

    def __init__(self):
        self.EMAIL_ADDRESS = Setting.get_or_create("Email Address").value
        self.PWD = Setting.get_or_create("Email Password").value

        self.ASSIGNMENTS_LIST = Setting.get_or_create("Email Address").value
        self.MATERIALS_LIST = Setting.get_or_create("Email Address").value

        self.IMAP_URL = Setting.get_or_create("Email IMAP URL").value
        self.IMAP_PORT = 993

        self.thread = None
        self.is_stopped = threading.Event()
        self.queue = queue.Queue()
        self.main_task = None

        self.latest_checked_email_num = None
        self.imap_conn = imaplib.IMAP4_SSL(self.IMAP_URL, 993)
        self.imap_conn.login(self.EMAIL_ADDRESS, self.PWD)

    def on_new_assignment(self, title, subject, date, description, **kwargs):
        raise NotImplementedError

    def on_new_material(self, title, subject, description, **kwargs):
        raise NotImplementedError

    def parse_email(self, email_message: email.message.Message):
        assert "New assignment" in email_message["subject"] or "New material" in email_message["subject"]
        assert email_message["from"].endswith("classroom.google.com>")
        assert email_message.is_multipart()  # payload 1 is raw text, 2 is html

        logger.info(f'Generating card for: Subject: {email_message["subject"]}')
        logger.debug(f"!!DEBUG{'=' * 100}")

        text = [msg.get_payload() for msg in email_message.get_payload() if msg.get_content_disposition() is None][0]
        try:  # Occasionally the the plaintext is b64 encoded for some reason?? idk
            text = base64.b64decode(text).decode()
        except (UnicodeDecodeError, binascii.Error):
            pass
        text = text.replace("\r", "")
        logger.debug(f"original text: \n {text}")

        classroom_type = email_message["subject"].split(" ")[1].lower().replace(":", "")

        logger.debug(f"classroom_type: {classroom_type}")
        og_title = email_message["subject"].split('"', 1)[1][:-1].replace("\r", "").replace("\n ", "\n")
        title = " ".join(og_title.split(' ')).replace("\n", "")
        while "  " in title:
            title = title.replace("  ", " ")
        title = title[:-1] if title.endswith(" ") else title
        title = title[1:] if title.startswith(" ") else title
        logger.debug(f"title: {[title]}, {title.split(' ')}, {title.endswith(' ')}\nog_title: {[og_title]}")


        subject_label = text.split("<https://classroom.google.com/c/")[0].split(f" posted a new {classroom_type} in ")[1]
        logger.debug([f"subject_label: {subject_label}"])


        try:
            url = "https://classroom.google.com/c/{}".format(
                text.split("\nOPEN  \n<https://classroom.google.com/c/")[1].split("/details>\n")[0])
        except IndexError:
            url = "https://classroom.google.com/c/{}".format(
                text.split("\nOpen  \n<https://classroom.google.com/c/")[1].split("/details>\n")[0])
        logger.debug(f"url: {url}")
        logger.debug(f"text.split(title) debug: {text.split(title), len(text.split(title)), title in text, type(text)}")
        try:
            description = text.split(og_title)[1].split("\nOPEN  \n<https://classroom.google.com/c/")[0].split(
                "\nOpen  \n<https://classroom.google.com/c/")[0]
        except IndexError:
            description = text.split(title)[1].split("\nOPEN  \n<https://classroom.google.com/c/")[0].split(
                "\nOpen  \n<https://classroom.google.com/c/")[0]

        description = f"{url}\n\n{description}".replace("\n", "<br>")
        logger.debug(f"description: {description}")

        date = None
        if classroom_type == "assignment":
            try:
                date = text.split(">.\n\n")[1].split(f"\n{title}")[0].replace("Due: ", "").replace(
                    "New assignment Due ", "")
                date = datetime.datetime.strptime(date, "%b %d")
                # If the date is in or past Jan, but before Sep, year is increased by 1
                date = date.replace(
                    year=datetime.datetime.now().year + 1 if 9 > date.month >= 1 else datetime.datetime.now().year)
            except ValueError:
                date = None

        logger.debug(f"date: {date}")
        logger.debug(f"!!END_DEBUG{'=' * 100}\n\n")
        return {"type": classroom_type, "title": title, "subject": subject_label, "date": date, "description": description}

    def wait_for_emails(self):
        print(threading.active_count())
        logger.info(f"{'=' * 100}\nStarting!")
        latest_message_num = int(self.imap_conn.select('INBOX')[1][0]) + 1
        logger.info(f"Latest message in inbox: {latest_message_num}\n")

        engine = create_engine('sqlite:///db.sqlite3', echo=False)
        session = orm.sessionmaker(bind=engine)()
        session.expire_on_commit = False

        # SqlAlchemy objects can only be used in the thread they were created in, so gotta do this
        self.latest_checked_email_num = session.query(Setting).filter(Setting.name == "email_latest_message_num").one_or_none()
        print(self.latest_checked_email_num)
        if self.latest_checked_email_num is None:
            self.latest_checked_email_num = Setting(name="email_latest_message_num", value=1)
            session.add(self.latest_checked_email_num)
            session.commit()

        for i in range(int(self.latest_checked_email_num.value), latest_message_num):
            if self.is_stopped.is_set():
                break

            self.latest_checked_email_num.value = i
            session.add(self.latest_checked_email_num)
            session.commit()

            msg = email.message_from_bytes(
                self.imap_conn.fetch(str(i), "(RFC822 BODY.PEEK[])")[1][0][1])
            try:
                args = self.parse_email(msg)
                self.queue.put(args)
            except AssertionError:
                logger.info(f'''IGNORED: Subject: {[msg['subject']]} | Received {msg["Date"]}''')
            time.sleep(0.3)

        while not self.is_stopped.is_set():
            msg = self.imap_conn.fetch(str(latest_message_num + 1), "(RFC822 BODY.PEEK[])")[1][0]
            if msg is not None:
                msg = msg[1]  # noqa

                latest_message_num += 1
                self.latest_checked_email_num.value = latest_message_num
                session.add(self.latest_checked_email_num)
                session.commit()

                try:
                    args = self.parse_email(msg)
                    self.queue.put(args)
                except AssertionError:
                    logger.info(f'''IGNORED: Subject: {[msg['subject']]} | Received: {msg["Date"]}''')
            time.sleep(1)

    def wait_for_emails_run_forever(self):
        while not self.is_stopped.is_set():
            try:
                self.wait_for_emails()
            except Exception as e:  # run at all costs
                if type(e) in (self.ExitError, asyncio.CancelledError):
                    break
                else:
                    logger.error("\n\nERROR in run_forever():", exc_info=sys.exc_info())
            time.sleep(1)

    async def main(self):
        self.is_stopped.clear()
        self.thread = threading.Thread(target=self.wait_for_emails_run_forever, daemon=True)
        self.thread.start()
        while not self.is_stopped.is_set():
            try:
                new = self.queue.get_nowait()

                if new["type"] == "assignment":
                    self.on_new_assignment(**new)
                else:
                    self.on_new_material(**new)
            except queue.Empty:
                pass
            await asyncio.sleep(0.3)

    def start(self):
        self.is_stopped.clear()
        self.main_task = asyncio.get_event_loop().create_task(self.main())

    def stop(self):
        self.is_stopped.set()
        self.main_task.cancel()
