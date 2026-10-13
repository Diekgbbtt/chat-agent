import os

from speakeasypy import Chatroom, EventType, Speakeasy, get_logger
from kg import KnowledgeGraph
HOST = "https://speakeasy.ifi.uzh.ch"

# Replace with your group credentials
BOT_USERNAME = os.environ["BOT_USERNAME"]
BOT_PASSWORD = os.environ["BOT_PASSWORD"]

logger = get_logger("speakeasy_bot")


class Agent:
    def __init__(self, username, password, kg:KnowledgeGraph):
        self.kg = kg
        self.speakeasy = Speakeasy(
            host=HOST,
            username=username,
            password=password,
            logger=logger,
        )

        self.speakeasy.login()

        self.speakeasy.register_callback(
            self.on_new_message,
            EventType.MESSAGE,
        )

    def answer(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return "Your message was empty. Send me a SPARQL query about movies!"
        if self.kg.looks_like_sparql(text):
            return self.kg.run(text)
        return ("Hi! Right now I answer SPARQL queries over the movie knowledge graph. "
                "Send me a SELECT query and I'll run it.")
 

    def on_new_message(self, message: str, room: Chatroom):
        try:
            # Implement your chatbot logic here
            logger.info(f"Room [{room.room_id}] received: {message[:300]!r}")
            room.post_messages(self.answer(message))

        except Exception:
            logger.exception(f"Room: [{room.room_id}], Reply Failed")
            try:
                room.post_messages("Sorry, something went wrong on my side. Could you try again?")
            except Exception:
                pass

    def listen(self):
        self.speakeasy.start_listening()


if __name__ == "__main__":
    kg = KnowledgeGraph()

    while True:
        try:
            Agent(BOT_USERNAME,BOT_PASSWORD,kg).listen()
        except KeyboardInterrupt:
            logger.info("Stopped by user")
            break
        except Exception:
            logger.exception("Agent crashed, reconnecting in 10 s")
            time.sleep(10)