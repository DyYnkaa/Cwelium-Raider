from .console import prompt, Render
from .functions import Raider
from .session import Data
import threading


class Menu:
    def __init__(self):
        self.raider = Raider()
        self.options = {
            "1": self.joiner,
            "2": self.leaver,
            "3": self.spammer,
            "4": self.checker,
            "5": self.reactor,
            "6": self.formatter,
            "7": self.button,
            "8": self.accept,
            "9": self.guild,
            "10": self.bio,
            "14": self.thread,
            "16": self.caller,
            "19": self.onboard,
        }
        with open("data/tokens.txt", "r", encoding="utf-8") as f:
            self.tokens = f.read().splitlines()

    def main_menu(self, _input=None):
        if _input:
            input()
        Render().run()
        choice = input(prompt("Choice"))
        if choice in self.options:
            Render().render_ascii()
            self.options[choice]()
        else:
            self.main_menu()

    def run(self, func, args):
        threads = []
        Render().render_ascii()
        for arg in args:
            thread = threading.Thread(target=func, args=arg)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        input("\n ~/> press enter to continue ")
        self.main_menu()

    def joiner(self):
        invite = input(prompt("Invite"))
        fingerprint = Data.fingerprint()
        args = [(token, invite, fingerprint) for token in self.tokens]
        self.run(self.raider.joiner, args)

    def leaver(self):
        guild = input(prompt("Guild ID"))
        args = [(token, guild) for token in self.tokens]
        self.run(self.raider.leaver, args)

    def spammer(self):
        channel_id = input(prompt("Channel ID"))
        message = input(prompt("Message"))
        massping = input(prompt("Massping", True))

        if "y" in massping:
            guild_id = input(prompt("Guild ID"))
            count = input(prompt("Pings Amount"))
            self.raider.member_scrape(guild_id, channel_id, self.tokens)

            args = [
                (token, channel_id, message, guild_id, True, count)
                for token in self.tokens
            ]
            self.run(self.raider.spammer, args)
        else:
            args = [(token, channel_id, message) for token in self.tokens]
            self.run(self.raider.spammer, args)

    def checker(self):
        self.raider.token_checker(self.tokens)

    def reactor(self):
        message = input(prompt("Message Link"))
        flood = input(prompt("Flood Mode", True))
        if "y" in flood.lower():
            args = [(token, message) for token in self.tokens]
            self.run(self.raider.spam_reactions, args)
        else:
            self.raider.reactor_main(message, self.tokens)

    def formatter(self):
        self.raider.format_tokens(self.tokens)

    def button(self):
        message = input(prompt("Message Link"))
        bot_id = input(prompt("Bot ID"))
        Render().render_ascii()
        self.raider.button_bypass(message, self.tokens, bot_id)

    def accept(self):
        guild_id = input(prompt("Guild ID"))
        self.raider.accept_rules(guild_id, self.tokens)

    def guild(self):
        guild_id = input(prompt("Guild ID"))
        self.raider.guild_checker(guild_id, self.tokens)

    def bio(self):
        bio = input(prompt("Bio"))
        args = [(token, bio) for token in self.tokens]
        self.run(self.raider.bio_changer, args)

    def thread(self):
        channel_id = input(prompt("Channel ID"))
        message = input(prompt("Message"))
        args = [(token, channel_id, message) for token in self.tokens]
        self.run(self.raider.thread_spammer, args)

    def caller(self):
        user_id = input(prompt("User ID"))
        for token in self.tokens:
            threading.Thread(
                target=self.raider.call_spammer, args=(token, user_id)
            ).start()

    def onboard(self):
        guild_id = input(prompt("Guild ID"))
        self.raider.onboard_bypass(guild_id, self.tokens)


def main():
    return Menu().main_menu()
