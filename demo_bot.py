from speakeasypy import Chatroom, EventType, Speakeasy, get_logger

HOST = "https://speakeasy.ifi.uzh.ch"

# Replace with your group credentials
BOT_USERNAME = "YOUR_GROUP_NAME"
BOT_PASSWORD = "YOUR_PASSWORD"

logger = get_logger("speakeasy_bot")


class Agent:
    def __init__(self, username, password):
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

    def on_new_message(self, message: str, room: Chatroom):
        try:
            # Implement your chatbot logic here
            answer = f"Received your message: '{message}'"
            room.post_messages(answer)

        except Exception:
            logger.exception(
                f"Room: [{room.room_id}], Reply Failed"
            )

    def listen(self):
        self.speakeasy.start_listening()


if __name__ == "__main__":
    bot = Agent(BOT_USERNAME, BOT_PASSWORD)
    bot.listen()