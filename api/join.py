from http.server import BaseHTTPRequestHandler
import json
import yaml
import base64
import binascii
import random
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
from urllib import parse

# --- TLS Fingerprint Setup ---
ORIGIN_CIPHERS = ('ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:'
                  'DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES')

class DESAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        CIPHERS = ORIGIN_CIPHERS.split(':')
        random.shuffle(CIPHERS)
        self.CIPHERS = ':'.join(CIPHERS) + ':!aNULL:!eNULL:!MD5'
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context(ciphers=self.CIPHERS)
        kwargs['ssl_context'] = context
        return super(DESAdapter, self).init_poolmanager(*args, **kwargs)

def CreateClient():
    client = requests.session()
    client.mount('https://', DESAdapter())
    return client

# --- Discord Headers Spoofer ---
class Headers:
    @staticmethod
    def get_fingerprint(client):
        try:
            return client.get("https://discord.com/api/v9/experiments", timeout=5).json().get("fingerprint")
        except Exception:
            return None

    @staticmethod
    def get_super_properties():
        properties = '{"os":"Windows","browser":"Chrome","device":"","system_locale":"en-GB","browser_user_agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36","browser_version":"95.0.4638.54","os_version":"10","referrer":"","referring_domain":"","referrer_current":"","referring_domain_current":"","release_channel":"stable","client_build_number":102113,"client_event_source":null}'
        return base64.b64encode(properties.encode()).decode()
    
    @staticmethod
    def get_cookies(client):
        try:
            r = client.get("https://discord.com/", timeout=5)
            dcf = r.cookies.get("__dcfduid")
            sdc = r.cookies.get("__sdcfduid")
            return f'__dcfduid={dcf}; __sdcfduid={sdc}'
        except Exception:
            return ""
    
    @staticmethod
    def get_headers(client, token) -> dict:
        return {
            'authority': 'discord.com',
            'method': 'POST',
            'scheme': 'https',
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate',
            'accept-language': 'en-US',
            'authorization': token,
            'cookie': Headers.get_cookies(client),
            'origin': 'https://discord.com',
            'sec-ch-ua': '"Google Chrome";v="95", "Chromium";v="95", ";Not A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36',
            'x-debug-options': 'bugReporterEnabled',
            'x-fingerprint': Headers.get_fingerprint(client),
            'x-super-properties': Headers.get_super_properties(),
        }

# --- Core Business Logic ---
class AuthUtils:
    def __init__(self, config: dict, request_client: requests.Session) -> None:
        self.RequestClient = request_client
        self.ClientToken = config['BotConfig'].get('BotToken')
        self.ClientId = config['BotConfig'].get("ClientId")
        self.ClientSecret = config['BotConfig'].get("ClientSecret")
        self.ClientRedirectUri = config['BotConfig'].get("RedirectUri")

        api_end = "https://discord.com/api/v9/"
        encoded_redirect = parse.quote_plus(self.ClientRedirectUri)
        encoded_perms = "%20".join(config['BotConfig']['Perms'])
        
        self.FetchLocUri = f"{api_end}oauth2/authorize?client_id={self.ClientId}&response_type=code&redirect_uri={encoded_redirect}&scope={encoded_perms}"
        self.FetchAuthUri = f"{api_end}oauth2/token"
        self.JoinUri = "https://discord.com/api/guilds/{}/members/{}"

    def token_id(self, token: str) -> int:
        token_id = token.split(".")[0]
        for _ in range(3):
            try:
                return int(base64.b64decode(token_id).decode(encoding="utf-8"))
            except binascii.Error:
                token_id += "="
        raise ValueError("Invalid Token Format")

    def fetch_location(self, token: str):
        req = self.RequestClient.post(
            url=self.FetchLocUri,
            headers=Headers.get_headers(self.RequestClient, token),
            json={"permissions": 0, "authorize": True}
        )
        req_json = req.json()
        if req.status_code == 200 and 'location' in req_json:
            return {'success': True, 'code': req_json['location'].split("=")[1]}
        if req.status_code == 429 and 'retry_after' in req_json:
            time.sleep(int(req_json['retry_after']))
            return self.fetch_location(token=token)
        return {'success': False, 'message': req_json.get("message", "Failed to retrieve authorize location.")}

    def fetch_auth(self, code: str):
        rex = self.RequestClient.post(
            url=self.FetchAuthUri,
            data={
                'client_id': self.ClientId,
                'client_secret': self.ClientSecret,
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': self.ClientRedirectUri
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        rex_json = rex.json()
        if rex.status_code == 200 and 'access_token' in rex_json:
            return {
                'success': True,
                'Auth': {
                    'AccessToken': rex_json['access_token'],
                    'RefreshToken': rex_json['refresh_token']
                }
            }
        if rex.status_code == 429 and 'retry_after' in rex_json:
            time.sleep(int(rex_json['retry_after']))
            return self.fetch_auth(code=code)
        return {'success': False, 'message': rex_json.get("message", "Token authorization error")}

    def auth_join(self, access_token: str, user_id: int, guild_id: int):
        req = self.RequestClient.put(
            url=self.JoinUri.format(guild_id, user_id),
            headers={
                "Authorization": f"Bot {self.ClientToken}",
                "Content-Type": "application/json"
            },
            json={"access_token": access_token}
        )
        req_json = req.json() if req.text else {}
        if req.status_code in [204, 201]:
            return {
                'success': True,
                'message': 'Already in server' if req.status_code == 204 else 'Successfully joined'
            }
        if req.status_code == 429 and 'retry_after' in req_json:
            time.sleep(int(req_json['retry_after'] / 1000))
            return self.auth_join(access_token, user_id, guild_id)
        return {'success': False, 'message': req_json.get("message", "Join guild error")}

# --- Vercel Serverless Entry Point ---
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/join':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            # Configuration payload parsed directly from UI
            config = {
                "BotConfig": {
                    "BotToken": data.get("botToken"),
                    "ClientId": data.get("clientId"),
                    "ClientSecret": data.get("clientSecret"),
                    "RedirectUri": data.get("redirectUri"),
                    "Perms": ['guilds.join', 'identify']
                },
                "GuildId": data.get("guildId")
            }

            token = data.get("token")
            access_token = data.get("accessToken", None)

            client = CreateClient()
            auth_utils = AuthUtils(config, client)
            response_data = {"success": False, "message": "Unknown runtime state", "token": token}

            try:
                if not access_token:
                    # Execute Step 1: Request Code Authorization
                    loc_res = auth_utils.fetch_location(token)
                    if loc_res['success']:
                        # Execute Step 2: Swap Authorization Code for Access Token
                        auth_res = auth_utils.fetch_auth(loc_res['code'])
                        if auth_res['success']:
                            access_token = auth_res['Auth']['AccessToken']
                            response_data["accessToken"] = access_token
                        else:
                            response_data = {"success": False, "message": f"Auth Exchange Failed: {auth_res['message']}", "token": token}
                    else:
                        response_data = {"success": False, "message": f"Oauth Init Failed: {loc_res['message']}", "token": token}

                # Execute Step 3: Use Token Credentials to force Add user to Guild
                if access_token:
                    user_id = auth_utils.token_id(token)
                    join_res = auth_utils.auth_join(
                        access_token=access_token,
                        user_id=user_id,
                        guild_id=int(config['GuildId'])
                    )
                    response_data = {
                        "success": join_res['success'],
                        "message": join_res['message'],
                        "token": token,
                        "accessToken": access_token
                    }

            except Exception as e:
                response_data = {"success": False, "message": f"System Exception: {str(e)}", "token": token}

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
