import asyncio
import aiohttp
import time
import uuid
from loguru import logger
import sys
import logging
logging.disable(logging.ERROR)  # 禁用 ERROR 及以上级别的日志


def show_copyright():
    copyright_info = """
    *****************************************************
    *           X:https://x.com/ariel_sands_dan         *
    *           Tg:https://t.me/sands0x1                *
    *           Version 1.0                             *
    *           Copyright (c) 2024                      *
    *           All Rights Reserved                     *
    *           脚本免费试用，如果你遇到收费就弄他！    *
    *****************************************************
    """
    print(copyright_info)

    confirm = input("Press Enter to continue or Ctrl+C to exit... ")

    if confirm.strip() == "":
        print("Continuing with the program...")
    else:
        print("Exiting the program.")
        exit()


# Constants
PING_INTERVAL = 180  # 每分钟发送一次请求
RETRIES = 120  # 全局重试计数
TOKEN_FILE = 'np_tokens_1.txt'  # 令牌文件名

DOMAIN_API = {
    "SESSION": "https://api.nodepay.org/api/auth/session",
    "PING": "https://nw.nodepay.org/api/network/ping"
}

CONNECTION_STATES = {
    "CONNECTED": 1,
    "DISCONNECTED": 2,
    "NONE_CONNECTION": 3
}

status_connect = CONNECTION_STATES["NONE_CONNECTION"]
browser_id = None
account_info = {}
last_ping_time = {}


def uuidv4():
    return str(uuid.uuid4())


def valid_resp(resp):
    if not resp or "code" not in resp or resp["code"] < 0:
        raise ValueError("Invalid response")
    return resp


async def render_profile_info(proxy, token):
    global browser_id, account_info

    try:
        np_session_info = load_session_info(proxy)

        if not np_session_info:
            browser_id = uuidv4()
            response = await call_api(DOMAIN_API["SESSION"], {}, proxy, token)
            if response is None:
                logger.info(f"Skipping proxy {proxy} due to 403 error.")
                return  # 跳过当前代理
            valid_resp(response)
            account_info = response["data"]
            if account_info.get("uid"):
                save_session_info(proxy, account_info)
                await start_ping(proxy, token)
            else:
                handle_logout(proxy)
        else:
            account_info = np_session_info
            await start_ping(proxy, token)
    except Exception as e:
        logger.error(f"Error in render_profile_info for proxy {proxy}: {e}")


async def call_api(url, data, proxy, token, max_retries=3):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://app.nodepay.ai",
        "Cookie": "__cf_bm=eLgxJdCy9oYdaH6lDYpX.igutO9m0hwvgv3em1uwGss-1730430111-1.0.1.1-0JTC9oIoIBkgfju12eTJWqzShzNIPJcGdc97dBM6qnUQOZd9t4o.OR0hUfspTYLwNnSQ7psrP_ZwhuQgjp_jcw",
    }

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=True)) as session:
        for attempt in range(max_retries):
            try:
                async with session.post(url, json=data, headers=headers, proxy=proxy, timeout=10) as response:
                    response.raise_for_status()  # Raise error for HTTP error responses
                    resp_json = await response.json()
                    return valid_resp(resp_json)

            except aiohttp.ClientResponseError as e:
                logger.error(f"API call error on attempt {
                             attempt + 1} for proxy {proxy}: {e}")
                if e.status == 403:
                    logger.error(f"403 Forbidden encountered on attempt {
                                 attempt + 1}: {e}")
                    return None  # Skip this proxy
            except aiohttp.ClientConnectionError as e:
                logger.error(f"Connection error on attempt {
                             attempt + 1} for proxy {proxy}: {e}")
            except aiohttp.Timeout as e:
                logger.error(f"Timeout on attempt {
                             attempt + 1} for proxy {proxy}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error on attempt {
                             attempt + 1} for proxy {proxy}: {e}")

            await asyncio.sleep(2 ** attempt)  # Exponential backoff

    logger.error(f"Failed API call to {url} after {
                 max_retries} attempts with proxy {proxy}")
    return None


async def start_ping(proxy, token):
    try:
        while True:
            await ping(proxy, token)
            await asyncio.sleep(PING_INTERVAL)
    except asyncio.CancelledError:
        logger.info(f"Ping task for proxy {proxy} was cancelled")
    except Exception as e:
        logger.error(f"Error in start_ping for proxy {proxy}: {e}")


async def ping(proxy, token):
    global last_ping_time, RETRIES, status_connect

    current_time = time.time()
    if proxy in last_ping_time and (current_time - last_ping_time[proxy]) < PING_INTERVAL:
        logger.info(f"Skipping ping for proxy {
                    proxy}, not enough time elapsed")
        return

    last_ping_time[proxy] = current_time

    try:
        data = {
            "id": account_info.get("uid"),
            "browser_id": browser_id,
            "timestamp": int(time.time())
        }

        response = await call_api(DOMAIN_API["PING"], data, proxy, token)
        if response["code"] == 0:
            logger.info(f"Ping successful via proxy {proxy}: {response}")
            RETRIES = 0
            status_connect = CONNECTION_STATES["CONNECTED"]
        else:
            handle_ping_fail(proxy, response)
    except Exception as e:
        logger.error(f"Ping failed via proxy {proxy}: {e}")
        handle_ping_fail(proxy, None)


def handle_ping_fail(proxy, response):
    global RETRIES, status_connect

    RETRIES += 1
    if response and response.get("code") == 403:
        handle_logout(proxy)
    elif RETRIES < 2:
        status_connect = CONNECTION_STATES["DISCONNECTED"]
    else:
        status_connect = CONNECTION_STATES["DISCONNECTED"]


def handle_logout(proxy):
    global status_connect, account_info

    status_connect = CONNECTION_STATES["NONE_CONNECTION"]
    account_info = {}
    save_status(proxy, None)
    logger.info(f"Logged out and cleared session info for proxy {proxy}")


def load_proxies(proxy_file):
    try:
        with open(proxy_file, 'r') as file:
            proxies = file.read().splitlines()
        return proxies
    except Exception as e:
        logger.error(f"Failed to load proxies: {e}")
        raise SystemExit("Exiting due to failure in loading proxies")


def save_status(proxy, status):
    pass


def save_session_info(proxy, data):
    data_to_save = {
        "uid": data.get("uid"),
        "browser_id": browser_id
    }
    pass


def load_session_info(proxy):
    return {}


def is_valid_proxy(proxy):
    return True


def remove_proxy_from_list(proxy):
    pass


def load_tokens_from_file(filename):
    try:
        with open(filename, 'r') as file:
            tokens = file.read().splitlines()
        return tokens
    except Exception as e:
        logger.error(f"Failed to load tokens: {e}")
        raise SystemExit("Exiting due to failure in loading tokens")


async def send_data_to_server(url, data, token):
    # 在此函数中调用 call_api 来发送数据
    proxy = None  # 这里可以根据需要选择代理
    response = await call_api(url, data, proxy, token)

    if response is not None:
        logger.info(f"Response received: {response}")
    else:
        logger.error("Failed to receive response.")


async def main():
    show_copyright()  # 在程序主循环之前显示版权信息
    print("Welcome to the main program!")

    url = "https://api.nodepay.org/api/auth/session"  # 替换为你的 API 端点
    data = {
        "cache-control": "no-cache, no-store, max-age=0, must-revalidate",  # 替换为你的数据
        "cf-cache-status": "DYNAMIC",
        "cf-ray": "8db8aaa27b6fd487-NRT",
        "ary": "origin,access-control-request-method,access-control-request-headers,accept-encoding",
    }

    all_proxies = load_proxies('proxy_1.txt')
    tokens = load_tokens_from_file(TOKEN_FILE)

    for token in tokens:
        await send_data_to_server(url, data, token)
        await asyncio.sleep(10)  # 在发送完每个请求后等待一段时间

    while True:
        for token in tokens:
            active_proxies = [
                proxy for proxy in all_proxies if is_valid_proxy(proxy)][:100]
            tasks = {asyncio.create_task(render_profile_info(
                proxy, token)): proxy for proxy in active_proxies}

            done, pending = await asyncio.wait(tasks.keys(), return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                failed_proxy = tasks[task]
                if task.result() is None:
                    logger.info(f"Removing and replacing failed proxy: {
                                failed_proxy}")
                    active_proxies.remove(failed_proxy)
                    if all_proxies:
                        new_proxy = all_proxies.pop(0)
                        if is_valid_proxy(new_proxy):
                            active_proxies.append(new_proxy)
                            new_task = asyncio.create_task(
                                render_profile_info(new_proxy, token))
                            tasks[new_task] = new_proxy
                tasks.pop(task)

            for proxy in set(active_proxies) - set(tasks.values()):
                new_task = asyncio.create_task(
                    render_profile_info(proxy, token))
                tasks[new_task] = proxy

            await asyncio.sleep(3)
        await asyncio.sleep(10)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Program terminated by user.")
