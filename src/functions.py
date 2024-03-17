from .console import C, log, Render, prompt
from tls_client import exceptions
from websocket import WebSocket
from json import dumps, loads
from time import sleep, time
from .scrape import scrape
from .session import Data
from uuid import uuid4
from os import path
import src.menu
import random
import string


def get_random_str(length: int) -> str:
    return "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(length)
    )


class Raider:
    def __init__(self) -> None:
        self.session = Data().build_session()

    def headers(self, token: str) -> dict:
        headers = Data().headers
        headers.update({"Authorization": token})
        return headers

    def joiner(self, token: str, invite: str, fingerprint: str):
        headers = self.headers(token)
        headers.update({"X-Fingerprint": fingerprint})
        while True:
            try:
                payload = {"session_id": uuid4().hex}
                response = self.session.post(
                    f"https://discord.com/api/v9/invites/{invite}",
                    headers=self.headers(token),
                    json=payload,
                )
                if response.status_code != 429:
                    match response.status_code:
                        case 200:
                            log("JOINED", C["green"], token[:25], f".gg/{invite}")
                        case 400:
                            log("CAPTCHA", C["yellow"], token[:25], f".gg/{invite}")
                        case _:
                            log(
                                "FAILED",
                                C["red"],
                                token[:25],
                                response.json().get("message"),
                            )
                    break
                else:
                    retry_after = response.json().get("retry_after", {})
                    log("RATELIMIT", C["magenta"], token[:25], str(retry_after) + "s")
                    sleep(retry_after)
            except Exception as e:
                log("FAILED", C["red"], token[:25], e)
                break

    def leaver(self, token: str, guild: str):
        try:
            payload = {
                "lurking": False,
            }

            response = self.session.delete(
                f"https://discord.com/api/v9/users/@me/guilds/{guild}",
                json=payload,
                headers=self.headers(token),
            )
            match response.status_code:
                case 204:
                    log("LEFT", C["green"], token[:25], guild)
                case _:
                    log(
                        "FAILED",
                        C["red"],
                        token[:25],
                        response.json().get("message"),
                    )

        except Exception as e:
            log("FAILED", C["red"], token[:25], e)

    def member_scrape(self, guild_id: str, channel_id: str, tokens: list):
        try:
            in_guild = []

            if not path.exists(f"scraped/{guild_id}.txt"):
                for token in tokens:
                    response = self.session.get(
                        f"https://discord.com/api/v9/guilds/{guild_id}",
                        headers=self.headers(token),
                    )
                    match response.status_code:
                        case 200:
                            in_guild.append(token)
                            break

                if not in_guild:
                    log("FAILED", C["red"], "Missing Access")

                token = random.choice(in_guild)

                members = scrape(token, guild_id, channel_id)
                with open(f"scraped/{guild_id}.txt", "a") as f:
                    f.write("\n".join(members))
        except Exception as e:
            log("FAILED", C["red"], token[:25], e)

    def get_random_members(self, guild_id: str, count: int):
        try:
            with open(f"scraped/{guild_id}.txt") as f:
                members = f.read().splitlines()

            message = ""
            for _ in range(count):
                message += f"<@!{random.choice(members)}>"
            return message
        except Exception as e:
            log("FAILED", C["red"], "Failed to get Random Members", e)

    def spammer(
        self,
        token: str,
        channel: str,
        message: str,
        guild=None,
        massping=None,
        pings=None,
    ):
        while True:
            if massping:
                msg = self.get_random_members(guild, int(pings))
                payload = {"content": f"{message} {msg}"}
            else:
                payload = {"content": message}

            response = self.session.post(
                f"https://discord.com/api/v9/channels/{channel}/messages",
                headers=self.headers(token),
                json=payload,
            )
            match response.status_code:
                case 200:
                    log("SENT", C["green"], token[:25])
                case 429:
                    retry_after = response.json().get("retry_after")
                    sleep(retry_after)
                case _:
                    log(
                        "FAILED",
                        C["red"],
                        token[:25],
                        response.json().get("message"),
                    )
                    return

    def token_checker(self, tokens: list):
        valid = []

        def main(token):
            while True:
                try:
                    response = self.session.get(
                        "https://discord.com/api/v9/users/@me/library?country_code=PL",
                        headers=self.headers(token),
                    )
                    if response.status_code != 429:
                        match response.status_code:
                            case 200:
                                log("UNLOCKED", C["green"], token[:25])
                                valid.append(token)
                            case 403:
                                log("LOCKED", C["yellow"], token[:25])
                            case _:
                                log(
                                    "INVALID",
                                    C["red"],
                                    token[:25],
                                    response.json().get("message"),
                                )
                        break
                    else:
                        retry_after = response.json().get("retry_after", {})
                        log(
                            "RATELIMIT",
                            C["magenta"],
                            token[:25],
                            str(retry_after) + "s",
                        )
                        sleep(retry_after)

                except exceptions.TLSClientExeption:
                    log("PROXY", C["magenta"], token[:25])
                    sleep(5)
                except Exception as e:
                    log("FAILED", C["red"], token[:25], e)
                    break

            with open("data/tokens.txt", "w") as f:
                f.write("\n".join(valid))

        args = [(token,) for token in tokens]
        src.menu.Menu().run(main, args)

    def add_emoji(
        self,
        token: str,
        channel_id: str,
        message_id: str,
        emoji: str,
    ):
        params = {
            "location": "Message",
            "type": "0",
        }
        response = self.session.put(
            f"https://canary.discord.com/api/v9/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/%40me",
            headers=self.headers(token),
            params=params,
        )
        if response.status_code == 429:
            return float(response.json().get("retry_after", {}))
        return response.text

    def reactor_main(self, message: str, tokens: list):
        try:
            channel_id = message.split("/")[5]
            message_id = message.split("/")[6]
            access_token = []
            emojis = []

            params = {"around": message_id, "limit": 50}
            Render().render_ascii()

            for token in tokens:
                response = self.session.get(
                    f"https://discord.com/api/v9/channels/{channel_id}/messages",
                    headers=self.headers(token),
                    params=params,
                )
                match response.status_code:
                    case 200:
                        access_token.append(token)
                        break

            if not access_token:
                log("FAILED", C["red"], "Missing Permissions")
                src.menu.Menu().main_menu(True)

            data = response.json()
            for __ in data:
                if __["id"] == message_id:
                    reactions = __["reactions"]
                    for cwel in reactions:
                        if cwel:
                            emoji_id = cwel["emoji"]["id"]
                            emoji_name = cwel["emoji"]["name"]

                            if emoji_id is None:
                                emojis.append(emoji_name)
                            else:
                                emojis.append(f"{emoji_name}:{emoji_id}")
                        else:
                            log(
                                "FAILED",
                                C["red"],
                                "No reactions Found in this message",
                            )
                            src.menu.Menu().main_menu(True)

            for i, emoji in enumerate(emojis, start=1):
                print(f"{C['light_blue']}0{i}:{C['white']} {emoji}")

            choice = input(f"\n{prompt('Choice')}")
            selected = emojis[int(choice) - 1]

            def add_react(token):
                while True:
                    try:
                        response = self.add_emoji(
                            token, channel_id, message_id, selected
                        )
                        if type(response) == str:
                            if not response:
                                log("REACTED", C["green"], token[:20], emoji)
                            else:
                                data = loads(response)
                                log(
                                    "FAILED",
                                    C["red"],
                                    token[:20],
                                    data.get("message", {}),
                                )
                            break
                        else:
                            log(
                                "RATELIMIT",
                                C["magenta"],
                                token[:25],
                                str(response) + "s",
                            )
                            sleep(float(response))
                    except Exception as e:
                        log("FAILED", C["red"], token[:25], e)
                        break

            args = [(token,) for token in tokens]
            src.menu.Menu().run(add_react, args)

        except Exception as e:
            log("FAILED", C["red"], "Failed to get Emojis", e)
            src.menu.Menu().main_menu(True)

    def spam_reactions(self, token: str, message_link: str):
        emojis = list("😊🌟🎉🌈🌸🚀🐱🍕🎶🏖️🎤🏆📱💻🎨🏰🌉🎡🍔🍟🍣🍍🥑🍓🍇🍉🍒🍌🍐🍏🍊🍋🍈🍅")
        channel_id = message_link.split("/")[5]
        message_id = message_link.split("/")[6]

        for emoji in emojis:
            try:
                response = self.add_emoji(token, channel_id, message_id, emoji)
                if type(response) == str:
                    if not response:
                        log("REACTED", C["green"], token[:20], emoji)
                    elif "Unknown Emoji" in response:
                        continue
                    else:
                        data = loads(response)
                        log("FAILED", C["red"], token[:20], data.get("message", {}))
                        break
                else:
                    log(
                        "RATELIMIT",
                        C["magenta"],
                        token[:25],
                        str(response) + "s",
                    )
                    sleep(float(response))
            except Exception as e:
                log("FAILED", C["red"], token[:25], e)
                break

    def format_tokens(self, tokens: list):
        try:
            formatted = []

            for token in tokens:
                token = token.strip()

                if token:
                    tokens_split = token.split(":")
                    if len(tokens_split) >= 3:
                        formatted_token = tokens_split[2]
                        formatted.append(formatted_token)
                    else:
                        formatted.append(token)

            log("SUCCESS", C["green"], f"Formatted {len(formatted)} tokens")

            with open("data/tokens.txt", "w") as f:
                for token in formatted:
                    f.write(f"{token}\n")
        except Exception as e:
            log("FAILED", C["red"], token[:25], e)

    def button_bypass(self, message: str, tokens: list, bot_id: str):
        try:
            access = []

            guild_id, channel_id, message_id = (
                message.split("/")[4],
                message.split("/")[5],
                message.split("/")[6],
            )

            for token in tokens:
                params = {"around": message_id, "limit": 50}
                response = self.session.get(
                    f"https://discord.com/api/v9/channels/{channel_id}/messages",
                    headers=self.headers(token),
                    params=params,
                )
                match response.status_code:
                    case 200:
                        access.append(token)
                        break

            if not access:
                log("FAILED", C["red"], "Missing Permissions")
                src.menu.Menu().main_menu(True)

            dictionary = []
            chosen = {}
            for msg in response.json():
                if msg.get("components", []):
                    for component in msg["components"]:
                        for button in component["components"]:
                            if button.get("custom_id", {}):
                                custom_id = button["custom_id"]
                                dictionary.append(custom_id)

            for i, button in enumerate(dictionary, start=1):
                print(f"0{i}: {button}")
            option = input("option: ")
            chosen[option] = button

            custom_id = chosen[option]

            def run_button(token):
                try:
                    json_data = {
                        "type": 3,
                        "guild_id": guild_id,
                        "channel_id": channel_id,
                        "message_flags": 0,
                        "message_id": message_id,
                        "application_id": bot_id,
                        "session_id": uuid4().hex,
                        "data": {
                            "component_type": 2,
                            "custom_id": custom_id,
                        },
                    }
                    response = self.session.post(
                        "https://discord.com/api/v9/interactions",
                        headers=self.headers(token),
                        json=json_data,
                    )
                    match response.status_code:
                        case 204:
                            log("PRESSED", C["green"], token[:25])
                        case _:
                            log(
                                "FAILED",
                                C["red"],
                                token[:25],
                                response.json().get("message"),
                            )
                except Exception as e:
                    log("FAILED", C["red"], token[:25], e)

            args = [(token,) for token in tokens]
            src.menu.Menu().run(run_button, args)

        except Exception as e:
            log("FAILED", C["red"], "Failed to Create a Button", e)

    def accept_rules(self, guild_id: str, tokens: list):
        try:
            valid = []
            for token in tokens:
                value = self.session.get(
                    f"https://discord.com/api/v9/guilds/{guild_id}/member-verification",
                    headers=self.headers(token),
                )
                match value.status_code:
                    case 200:
                        valid.append(token)
                        payload = value.json()
                        break

            if not valid:
                log("FAILED", C["red"], "All tokens are Invalid")
                src.menu.Menu().main_menu(True)

        except Exception as e:
            log("FAILED", C["red"], "Failed to Accept Rules", e)

        def run_main(token):
            try:
                response = self.session.put(
                    f"https://discord.com/api/v9/guilds/{guild_id}/requests/@me",
                    headers=self.headers(token),
                    json=payload,
                )
                match response.status_code:
                    case 201:
                        log("ACCEPTED", C["green"], token[:25], guild_id)
                    case _:
                        log(
                            "FAILED",
                            C["red"],
                            token[:25],
                            response.json().get("message"),
                        )

            except Exception as e:
                log("FAILED", C["red"], token[:25], e)

        args = [(token,) for token in tokens]
        src.menu.Menu().run(run_main, args)

    def guild_checker(self, guild_id: str, tokens: list):
        in_guild = []

        def main_checker(token):
            try:
                response = self.session.get(
                    f"https://discord.com/api/v9/guilds/{guild_id}",
                    headers=self.headers(token),
                )
                match response.status_code:
                    case 200:
                        log("FOUND", C["green"], token[:25], guild_id)
                        in_guild.append(token)
                    case _:
                        log("NOT FOUND", C["red"], token[:25], guild_id)
                with open("data/tokens.txt", "w") as f:
                    f.write("\n".join(in_guild))
            except Exception as e:
                log("FAILED", C["red"], token[:25], e)

        args = [(token,) for token in tokens]
        src.menu.Menu().run(main_checker, args)

    def bio_changer(self, token: str, bio: str):
        try:
            payload = {"bio": bio}
            response = self.session.patch(
                "https://discord.com/api/v9/users/@me/profile",
                headers=self.headers(token),
                json=payload,
            )
            match response.status_code:
                case 200:
                    log("CHANGED", C["green"], token[:25], bio)
                case _:
                    log(
                        "FAILED",
                        C["red"],
                        token[:25],
                        response.json().get("message"),
                    )

        except Exception as e:
            log("FAILED", C["red"], token[:25], e)

    def token_onliner(self, token: str, ws: WebSocket):
        ws.connect("wss://gateway.discord.gg/?v=9&encoding=json")

        ws.send(
            dumps(
                {
                    "op": 2,
                    "d": {
                        "token": token,
                        "properties": {
                            "$os": "Windows",
                        },
                    },
                }
            )
        )

    def join_voice_channel(self, guild_id: str, channel_id: str, tokens: list):
        ws = WebSocket()

        def check_for_guild(token: str) -> bool:
            response = self.session.get(
                f"https://discord.com/api/v9/guilds/{guild_id}",
                headers=self.headers(token),
            )
            match response.status_code:
                case 200:
                    return True
                case _:
                    log("FAILED", C["red"], "Missing Access")

        def check_for_channel(token: str) -> bool:
            if check_for_guild(token):
                response = self.session.get(
                    f"https://discord.com/api/v9/channels/{channel_id}",
                    headers=self.headers(token),
                )
                match response.status_code:
                    case 200:
                        return True
                    case _:
                        return False

        def run(token):
            if check_for_channel(token):
                log("JOINED", C["green"], token[:25], channel_id)
                self.voice_spammer(token, ws, guild_id, channel_id, True)
            else:
                log("FAILED", C["red"], token[:25], channel_id)

        args = [(token,) for token in tokens]
        src.menu.Menu().run(run, args)

    def thread_spammer(self, token: str, channel_id: str, name: str):
        try:
            payload = {
                "name": name,
                "type": 11,
                "auto_archive_duration": 4320,
                "location": "Thread Browser Toolbar",
            }
            while True:
                response = self.session.post(
                    f"https://discord.com/api/v9/channels/{channel_id}/threads",
                    headers=self.headers(token),
                    json=payload,
                )
                match response.status_code:
                    case 201:
                        log("CREATED", C["green"], token[:25], name)
                    case 429:
                        retry_after = response.json().get("retry_after")
                        if int(retry_after) > 10:
                            log(
                                "STOPPED",
                                C["magenta"],
                                token[:25],
                                f"Ratelimit Exceeded - {int(round(retry_after))}s",
                            )
                            break
                        else:
                            log(
                                "RATELIMIT",
                                C["yellow"],
                                token[:25],
                                f"{int(round(retry_after))}s",
                            )
                            sleep(float(retry_after))
                    case _:
                        log(
                            "FAILED",
                            C["red"],
                            token[:25],
                            response.json().get("message"),
                        )
                        break
        except Exception as e:
            log("FAILED", C["red"], token[:25], e)

    def open_dm(self, token: str, user_id: str) -> str:
        try:
            payload = {"recipients": [user_id]}
            response = self.session.post(
                "https://discord.com/api/v9/users/@me/channels",
                headers=self.headers(token),
                json=payload,
            )
            match response.status_code:
                case 200:
                    return response.json()["id"]
                case 429:
                    retry_after = response.json().get("retry_after", {})
                    log("RATELIMITED", C["magenta"], token[:25], user_id)
                    sleep(retry_after)
                case _:
                    log("FAILED", C["red"], token[:25], response.json().get("message"))
                    return
        except Exception as e:
            log("FAILED", C["red"], token[:25], e)

    def voice_spammer(
        self,
        token: str,
        ws: WebSocket,
        guild_id: str,
        channel_id: str,
        close: bool = None,
    ):
        try:
            self.token_onliner(token, ws)
            ws.send(
                dumps(
                    {
                        "op": 4,
                        "d": {
                            "guild_id": guild_id,
                            "channel_id": channel_id,
                            "self_mute": False,
                            "self_deaf": False,
                            "self_stream": False,
                            "self_video": True,
                        },
                    }
                )
            )
            ws.send(
                dumps(
                    {
                        "op": 18,
                        "d": {
                            "type": "guild",
                            "guild_id": guild_id,
                            "channel_id": channel_id,
                            "preferred_region": "singapore",
                        },
                    }
                )
            )
            ws.send(dumps({"op": 1, "d": None}))
            if close:
                ws.close()

        except Exception as e:
            log("FAILED", C["red"], token[:25], e)

    def call_spammer(self, token: str, user_id: str):
        while True:
            try:
                channel_id = self.open_dm(token, user_id)
                if type(channel_id) == str:
                    response = self.session.get(
                        f"https://discord.com/api/v9/channels/{channel_id}/call",
                        headers=self.headers(token),
                    )
                    print(response.status_code)
                    match response.status_code:
                        case 200:
                            log("CALLED", C["green"], token[:25], user_id)
                            ws = WebSocket()
                            self.voice_spammer(token, ws, None, channel_id, True)
                            break

                        case _:
                            log(
                                "FAILED",
                                C["red"],
                                token[:25],
                                response.json().get("message"),
                            )
                            break
            except Exception as e:
                log("FAILED", C["red"], token[:25], e)
                break

    def onboard_bypass(self, guild_id: str, tokens: list):
        try:
            onboarding_responses_seen = {}
            onboarding_prompts_seen = {}
            onboarding_responses = []
            in_guild = []

            for _token in tokens:
                response = self.session.get(
                    f"https://discord.com/api/v9/guilds/{guild_id}/onboarding",
                    headers=self.headers(_token),
                )
                match response.status_code:
                    case 200:
                        in_guild.append(_token)
                        break

            if not in_guild:
                log("FAILED", C["red"], "Missing Access")
                src.menu.Menu().main_menu(True)
            else:
                data = response.json()
                now = int(time() * 1000)

                for __ in data["prompts"]:
                    onboarding_responses.append(__["options"][-1]["id"])

                    onboarding_prompts_seen[__["id"]] = now

                    for prompt in __["options"]:
                        if prompt:
                            onboarding_responses_seen[prompt["id"]] = now
                        else:
                            log(
                                "FAILED",
                                C["red"],
                                "No onboarding in This Server",
                            )
                            src.menu.Menu().main_menu(True)

        except Exception as e:
            log("FAILED", C["red"], "Failed to Pass Onboard", e)
            src.menu.Menu().main_menu(True)

        def run_task(token):
            try:
                json_data = {
                    "onboarding_responses": onboarding_responses,
                    "onboarding_prompts_seen": onboarding_prompts_seen,
                    "onboarding_responses_seen": onboarding_responses_seen,
                }
                response = self.session.post(
                    f"https://discord.com/api/v9/guilds/{guild_id}/onboarding-responses",
                    headers=self.headers(token),
                    json=json_data,
                )
                match response.status_code:
                    case 200:
                        log("ACCEPTED", C["green"], token[:25])
                    case _:
                        log(
                            "FAILED",
                            C["red"],
                            token[:25],
                            response.json().get("message"),
                        )
            except Exception as e:
                log("FAILED", C["red"], token[:25], e)

        args = [(token,) for token in tokens]
        src.menu.Menu().run(run_task, args)
