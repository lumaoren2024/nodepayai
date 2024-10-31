import asyncio
import aiohttp
import time
import uuid
import cloudscraper  # 引入 cloudscraper
from loguru import logger


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
PING_INTERVAL = 60  # 每分钟发送一次请求
RETRIES = 60  # 全局重试计数
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
last_ping_time = {}  # 使用字典来记录每个代理的最后 ping 时间


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
            # 生成新的 browser_id
            browser_id = uuidv4()
            response = await call_api(DOMAIN_API["SESSION"], {}, proxy, token)
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
        error_message = str(e)
        if any(phrase in error_message for phrase in [
            "sent 1011 (internal error) keepalive ping timeout; no close frame received",
            "500 Internal Server Error"
        ]):
            logger.info(f"Removing error proxy from the list: {proxy}")
            remove_proxy_from_list(proxy)
            return None
        else:
            logger.error(f"Connection error: {e}")
            return proxy


async def call_api(url, data, proxy, token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://app.nodepay.ai",
    }

    try:
        # 使用 cloudscraper 创建会话
        scraper = cloudscraper.create_scraper()

        # 使用 cloudscraper 发起请求
        response = scraper.post(url, json=data, headers=headers, proxies={
                                "http": proxy, "https": proxy}, timeout=10)

        # 检查响应状态码
        response.raise_for_status()
        return valid_resp(response.json())
    except Exception as e:
        logger.error(f"Error during API call: {e}")
        raise ValueError(f"Failed API call to {url}")


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

    # 检查是否距离上次ping已经过去了指定的间隔
    if proxy in last_ping_time and (current_time - last_ping_time[proxy]) < PING_INTERVAL:
        logger.info(f"Skipping ping for proxy {
                    proxy}, not enough time elapsed")
        return

    # 更新上次ping的时间
    last_ping_time[proxy] = current_time

    try:
        data = {
            "id": account_info.get("uid"),
            "browser_id": browser_id,  # 使用当前的 browser_id
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
    pass  # 这里可以添加保存状态的逻辑


def save_session_info(proxy, data):
    # 将 browser_id 也保存到会话信息中
    data_to_save = {
        "uid": data.get("uid"),
        "browser_id": browser_id  # 保存 browser_id
    }
    # 这里可以添加保存逻辑，例如写入文件或数据库
    pass


def load_session_info(proxy):
    return {}  # 这里可以加载会话信息


def is_valid_proxy(proxy):
    return True  # 这里可以验证代理的有效性


def remove_proxy_from_list(proxy):
    pass  # 这里可以移除代理的逻辑


def load_tokens_from_file(filename):
    try:
        with open(filename, 'r') as file:
            tokens = file.read().splitlines()
        return tokens
    except Exception as e:
        logger.error(f"Failed to load tokens: {e}")
        raise SystemExit("Exiting due to failure in loading tokens")


async def main():
    all_proxies = load_proxies('proxy_1.txt')  # 从文件加载代理
    tokens = load_tokens_from_file(TOKEN_FILE)  # 从文件加载令牌

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

            # 防止快速失败导致的紧密循环
            await asyncio.sleep(3)
        await asyncio.sleep(10)  # 在处理下一个令牌之前等待

# 主程序入口
if __name__ == '__main__':
    show_copyright()
    print("Welcome to the main program!")
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Program terminated by user.")
