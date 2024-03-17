from requests import get, exceptions
from tls_client import Session
from json import dump, load
from random import choice
from time import sleep
from os import path

if not path.exists("config.json"):
    json_data = {"proxies": False}
    with open("config.json", "w") as f:
        dump(json_data, f, indent=4)

with open("config.json", "r") as f:
    info = load(f)
support = info.get("proxies", {})


class Data:
    def __init__(self) -> None:
        with open("data/proxies.txt", "r", encoding="utf-8") as f:
            self.proxies = f.read().splitlines()
        self.headers = {
            "Accept-Encoding": "gzip",
            "Accept-Language": "en-US",
            "Connection": "Keep-Alive",
            "Content-Type": "application/json; charset=UTF-8",
            "Host": "discord.com",
            "User-Agent": "Discord-Android/126021",
            "X-Context-Properties": "eyJsb2NhdGlvbiI6Ikludml0ZSBCdXR0b24gRW1iZWQiLCJsb2NhdGlvbl9ndWlsZF9pZCI6MTE3MDMxNzE4MTU3MDAxMTIxNywibG9jYXRpb25fY2hhbm5lbF9pZCI6MTE3MDMxODI5MDYyNzg1NDM4NiwibG9jYXRpb25fY2hhbm5lbF90eXBlIjowfQ==",
            "X-Discord-Locale": "en-US",
            "X-Super-Properties": "eyJicm93c2VyIjoiRGlzY29yZCBBbmRyb2lkIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiRGlzY29yZC1BbmRyb2lkLzEyNjAyMSIsImNsaWVudF9idWlsZF9udW1iZXIiOjEyNjAyMSwiY2xpZW50X3ZlcnNpb24iOiIxMjYuMjEgLSBTdGFibGUiLCJkZXZpY2UiOiJPTkVQTFVTIEE1MDAwLCBPbmVQbHVzNSIsIm9zIjoiQW5kcm9pZCIsIm9zX3Nka192ZXJzaW9uIjoiMjUiLCJvc192ZXJzaW9uIjoiNy4xLjEiLCJzeXN0ZW1fbG9jYWxlIjoiZW4tVVMiLCJhY2Nlc3NpYmlsaXR5X3N1cHBvcnRfZW5hYmxlZCI6ZmFsc2UsImFjY2Vzc2liaWxpdHlfZmVhdHVyZXMiOjEyOCwiZGV2aWNlX2FkdmVydGlzZXJfaWQiOiI0MjI2OTZjYy1hYWJmLTQxZDktOTYyMy1lMTllZmEzZWY5ODMiLCJjbGllbnRfcGVyZm9ybWFuY2VfY3B1IjoxLCJjbGllbnRfcGVyZm9ybWFuY2VfbWVtb3J5IjoyNjEzMDgsImNwdV9jb3JlX2NvdW50Ijo0fQ==",
        }

    @classmethod
    def fingerprint(cls):
        while True:
            try:
                response = get("http://discord.com/api/v9/experiments").json().get("fingerprint", {})
                return response
            except exceptions.ConnectionError:
                sleep(5)
            except Exception as e:
                print(f"{e} (get_discord_cookies)")
                break

    def cookies(self):
        while True:
            try:
                response = get("https://discord.com", headers=self.headers).cookies
                return response.get_dict()
            except exceptions.ConnectionError:
                sleep(5)
            except Exception as e:
                print(f"{e} (get_discord_cookies)")
                break

    def build_session(self):
        cookies = self.cookies()
        session = Session("chrome120", random_tls_extension_order=True)
        session.cookies.update(cookies)
        if support:
            proxy = choice(self.proxies)
            session.proxies.update({"http": proxy, "https": proxy})
        return session
