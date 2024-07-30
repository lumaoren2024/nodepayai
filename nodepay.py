import asyncio
import requests
import json
import time
import uuid
from loguru import logger

# Constants
NP_TOKEN = "你的token"
PING_INTERVAL = 30  # seconds
RETRIES = 60  # Global retry counter for ping failures

DOMAIN_API = {
    "SESSION": "https://api.nodepay.ai/api/auth/session",
    "PING": "https://nw2.nodepay.ai/api/network/ping"
}

CONNECTION_STATES = {
    "CONNECTED": 1,
    "DISCONNECTED": 2,
    "NONE_CONNECTION": 3
}

status_connect = CONNECTION_STATES["NONE_CONNECTION"]
token_info = NP_TOKEN
browser_id = None
account_info = {}


def uuidv4():
    return str(uuid.uuid4())


def valid_resp(resp):
    if not resp or "code" not in resp or resp["code"] < 0:
        raise ValueError("Invalid response")
    return resp


async def render_profile_info():
    global browser_id, token_info, account_info

    try:
        np_session_info = load_session_info()

        if not np_session_info:
            response = call_api(DOMAIN_API["SESSION"], {})
            valid_resp(response)
            account_info = response["data"]
            if account_info.get("uid"):
                save_session_info(account_info)
                await start_ping()
            else:
                handle_logout()
        else:
            account_info = np_session_info
            await start_ping()
    except Exception as e:
        logger.error(f"Error in render_profile_info: {e}")
        error_message = str(e)
        if any(phrase in error_message for phrase in [
            "sent 1011 (internal error) keepalive ping timeout; no close frame received",
            "500 Internal Server Error"
        ]):
            logger.info("Encountered a critical error.")
        else:
            logger.error(f"Connection error: {e}")


def call_api(url, data):
    headers = {
        "Authorization": f"Bearer {token_info}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Error during API call: {e}")
        raise ValueError(f"Failed API call to {url}")

    return valid_resp(response.json())


async def start_ping():
    try:
        await ping()
        while True:
            await asyncio.sleep(PING_INTERVAL)
            await ping()
    except asyncio.CancelledError:
        logger.info("Ping task was cancelled")
    except Exception as e:
        logger.error(f"Error in start_ping: {e}")


async def ping():
    global RETRIES, status_connect

    try:
        data = {
            "id": account_info.get("uid"),
            "browser_id": browser_id,
            "timestamp": int(time.time())
        }

        response = call_api(DOMAIN_API["PING"], data)
        if response["code"] == 0:
            logger.info(f"Ping successful: {response}")
            RETRIES = 0
            status_connect = CONNECTION_STATES["CONNECTED"]
        else:
            handle_ping_fail(response)
    except Exception as e:
        logger.error(f"Ping failed: {e}")
        handle_ping_fail(None)


def handle_ping_fail(response):
    global RETRIES, status_connect

    RETRIES += 1
    if response and response.get("code") == 403:
        handle_logout()
    elif RETRIES < 2:
        status_connect = CONNECTION_STATES["DISCONNECTED"]
    else:
        status_connect = CONNECTION_STATES["DISCONNECTED"]


def handle_logout():
    global token_info, status_connect, account_info

    token_info = None
    status_connect = CONNECTION_STATES["NONE_CONNECTION"]
    account_info = {}
    save_status(None)
    logger.info("Logged out and cleared session info")


def save_status(status):
    pass


def save_session_info(data):
    pass


def load_session_info():
    return {}


async def main():
    await render_profile_info()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Program terminated by user.")
