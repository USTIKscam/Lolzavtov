import os
import re
import time
import json
import random
import ctypes
import traceback

import requests
from loguru import logger


def set_title():
    if os.name == 'nt':
        ctypes.windll.kernel32.SetConsoleTitleW('[AutoLolz v4] by @its_niks - https://lolz.guru/members/3870999/')

with open('config.json') as file:
    config = json.load(file)
    if config['thread_url'] == '' or config['lolz_token'] == '':
        logger.error('Ошибка, заполните config.json')
        input()
        raise SystemExit()

with open('data.txt', 'r', encoding='utf-8') as file:
    keys = file.readlines()
    if len(keys) == 0:
        logger.error('Ошибка, заполните data.txt')
        input()
        raise SystemExit()

def save_replied_users(data):
    with open('replied_users.json', 'w', encoding="utf-8") as f:
        f.write(json.dumps(data, indent=4))

def save_keys(data):
    with open('data.txt', 'w', encoding="utf-8") as f:
        f.write(''.join(data))

if input('Вы хотите очистить replied_users.json ? (y/n): ').lower() == 'y':
    with open('replied_users.json', 'w', encoding="utf-8") as f:
        data = {}
        f.write(json.dumps(data, indent=4))
        logger.info('replied_users.json был успешно очищен.')

with open('replied_users.json', 'r', encoding="utf-8") as f:
    sent_messages = json.load(f)

delay = config['delay']
lolz_token = config['lolz_token']
data_count = config["data_count"]

class Lolz:
    def __init__(self, token):
        self.sess = requests.Session()
        self.sess.headers = {
            'Authorization': f'Bearer {token}',
            }

        self.thread_url = config["thread_url"]
        if config['proxy'] != '':
            proxy_dict = {
            "http":config['proxy'],
            "https":config['proxy'],
            }
            self.sess.proxies.update(proxy_dict)

    def check_user(self):
        response = self.sess.get('https://api.lolz.guru/market/me').json()
        if 'user' not in response.keys():
            return False
        return True

    def get_posts(self):
        match = re.search('https?://lolz\.guru/threads/(\d+)/?', self.thread_url)
        if not match:
            logger.error(f'Unexpected thread URL format: {self.thread_url}')
            input()
            raise SystemExit()
        thread_id = match.group(1)
        with open('replied_users.json', 'r', encoding="utf-8") as f:
            sent_messages = json.load(f)
        all_posts = []
        r = self.sess.get(f"https://api.lolz.guru/posts?thread_id={thread_id}")
        try:
            r = r.json()
        except:
            logger.error(f'Ошибка доступа к API.')
            logger.error(r.text)
            time.sleep(15)
            return
        try:
            all_pages = r["links"]['pages']
        except KeyError:
            all_pages = 1
        author_username = r["thread"]["creator_username"]
        time.sleep(6)
        for i in range(1 if len(sent_messages) == 0 else list(sent_messages.values())[-1], all_pages+1):
            r = self.sess.get(f"https://api.lolz.guru/posts?thread_id={thread_id}&page={i}")
            try:
                page = r.json()
            except:
                logger.error(f'Ошибка доступа к API.')
                logger.error(r.text)
                break
            posts = page["posts"]
            for post in posts:
                if str(post["post_id"]) not in sent_messages:
                    if post["poster_username"] != author_username:
                        all_posts.append({'post_id': post["post_id"], 'author' : post["poster_username"], 'page' : i, 'text' : post["post_body"]})
            time.sleep(6)
        return all_posts

    def post_comment(self, post_id, username,  text):
        data = {
            "comment_body" : f'[USERS={username}]@{username}, {text}[/USERS]',
            }
        r = self.sess.post(f'https://api.lolz.guru/posts/{post_id}/comments', data=data)
        try:
            response = r.json()
            if 'comment' in response.keys():
                return True
            else:
                return response
        except:
            logger.error(f'Ошибка доступа к API.')
            logger.error(r.text)

def distribution(lzt):
    if config['dynamic_data']:
        with open('data.txt', 'r', encoding='utf-8') as file:
            keys = file.readlines()
            if len(keys) == 0:
                logger.error('Ожидаю новые ключи...')
                time.sleep(10)
                return
    posts = lzt.get_posts()
    if len(posts) == 0:
        logger.info(f'Ожидаю новые сообщения')
        time.sleep(random.randrange(delay[0], delay[1]))
    else:
        logger.info(f'Найдено {len(posts)} сообщений.')
        for post in posts:
            if len(keys) == 0:
                if config['dynamic_data']:
                    logger.error('Ожидаю новые ключи...')
                    time.sleep(10)
                    return
                else:
                    logger.error('Закончились ключи. Нажмите на любую кнопку, чтобы завершить...')
                    input()
                    raise SystemExit()
            prize = '\n'
            for i in range(data_count):
                try:
                    prize += f'{keys[i].strip()}\n'
                    keys.remove(keys[i])
                except IndexError:
                    prize += ''
            comment_status = lzt.post_comment(post["post_id"], post["author"], prize)
            if comment_status == True:
                sent_messages[post["post_id"]] = post["page"]
                save_replied_users(sent_messages)
                save_keys(keys)
                if config["output_prize"] == 0:
                    logger.success(f'Сообщение {post["author"]} было прокомментировано.')
                elif config["output_prize"] == 1:
                    logger.success(f'Сообщение {post["author"]} было прокомментировано. ({prize})')
                else:
                    logger.error('Укажите верный параметр output_prize в config.json: 0 - отключить | 1 - включить')
                    input()
                    raise SystemExit()
            else:
                if config["output_prize"] == 0:
                    logger.info(comment_status)
                    logger.error(f'Ошибка при комментировании сообщения {post["author"]}')
                elif config["output_prize"] == 1:
                    logger.info(comment_status)
                    logger.error(f'Ошибка при комментировании сообщения {post["author"]} ({prize})')
                else:
                    logger.error('Укажите верный параметр output_prize в config.json: 0 - отключить | 1 - включить')
                    input()
                    raise SystemExit()
            time.sleep(random.randrange(delay[0], delay[1]))



def main():
    set_title()
    lzt = Lolz(lolz_token)
    if lzt.check_user():
        time.sleep(5)
        while True:
            try:
                distribution(lzt)
            except Exception as ex:
                logger.error(traceback.format_exc())
                time.sleep(random.randrange(delay[0], delay[1]))
    else:
        logger.error(f'Invalid Token')
        input()
        raise SystemExit()

main()
