import asyncio
import html
import logging
import pydle
import re
import sys
import toml
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils.exceptions import MessageIsTooLong
from tenacity import retry, stop_after_attempt

if len(sys.argv) > 1:
    config = toml.load(sys.argv[1])
else:
    config = toml.load("telegramirc.toml")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

irc_q = asyncio.Queue()
tg_q = asyncio.Queue()
i2t_map = {channel: config["channel"][channel]["chatid"] for channel in config["channel"]}
t2i_map = {chatid: channel for channel, chatid in i2t_map.items()}


async def telegram_serve():
    bot = Bot(token=config["telegram"]["token"], parse_mode=types.ParseMode.HTML)
    dp = Dispatcher(bot)

    @dp.message_handler(commands='start')
    async def start(message):
        await message.reply("I'm a bot, please don't talk to me!")

    @dp.message_handler(commands='chatid')
    async def chatid(message):
        await message.reply(str(message.chat.id))

    @dp.message_handler(commands='msg')
    async def msg(message):
        _, target, msg = message.text.split(" ", 2)
        logging.info(f'TG DM {message.chat.id} {target}: {msg}')
        if message.from_user.username == config["telegram"]["allowed_username"]:
            await irc_q.put((target, msg))

    @dp.message_handler(commands='me')
    async def me(message):
        _, msg = message.text.split(" ", 1)
        logging.info(f'TG {message.chat.id} {message.from_user.username} ACTION {msg}')
        if message.from_user.username == config["telegram"]["allowed_username"]:
            await irc_q.put((t2i_map[message.chat.id], ("ACTION", msg)))

    @dp.message_handler()
    async def handler(message):
        logging.info(f'TG {message.chat.id} {message.from_user.username}: {message.text}')
        if message.from_user.username == config["telegram"]["allowed_username"]:
            await irc_q.put((t2i_map[message.chat.id], message.text))

    @retry(stop=stop_after_attempt(20), reraise=True)
    async def send_message_with_retry(*arg, **kwargs):
        await bot.send_message(*arg, **kwargs)

    async def queue_watch():
        while True:
            try:
                fwd_msgs = {}
                target, msg = await tg_q.get()
                fwd_msgs[target] = msg
                await asyncio.sleep(0.01)
                while not tg_q.empty():
                    target, msg = await tg_q.get()
                    if target in fwd_msgs:
                        fwd_msgs[target] += "\n" + msg
                    else:
                        fwd_msgs[target] = msg

            except:
                logging.warning(f"TG Failed to process messages: {str(fwd_msgs)}", exc_info=True)
                try:
                    await tg_q.put((config["telegram"]["fallback_chatid"], f"TG Failed to process messages: {html.escape(str(fwd_msgs))}"))
                except:
                    pass

            else:
                for target in fwd_msgs:
                    try:
                        await send_message_with_retry(target, fwd_msgs[target])
                    except MessageIsTooLong:
                        logging.warning(f"TG Failed to send message: {fwd_msgs[target]} to {target}, possible loop detected, disabled retrying.", exc_info=True)
                    except:
                        logging.warning(f"TG Failed to send message: {fwd_msgs[target]} to {target}", exc_info=True)
                        if target == config["telegram"]["fallback_chatid"] and "TG Failed to send message" in fwd_msgs[target]:
                            logging.warning(f"TG Failed to send fallback message.")
                        else:
                            try:
                                await tg_q.put((config["telegram"]["fallback_chatid"], f"TG Failed to send message: {html.escape(fwd_msgs[target])} to {target}"))
                            except:
                                pass

    asyncio.create_task(queue_watch())
    await dp.start_polling()


class IRCClient(pydle.Client):
    READ_TIMEOUT = 30

    async def on_connect(self):
        await super().on_connect()
        logging.info('IRC Connected')

        if "nickserv_password_first" in config["irc"]:
            if config["irc"]["nickserv_password_first"]:
                await self.message("NICKSERV", f"identify {config['irc']['password']} {config['irc']['username']}")
            else:
                await self.message("NICKSERV", f"identify {config['irc']['username']} {config['irc']['password']}")
            logging.info('IRC NickServ Identify Attempted')

        for channel in config["channel"]:
            await self.join(channel, config["channel"][channel].get("key", None))
            logging.info(f'IRC Joining channel {channel}')

        asyncio.create_task(self.queue_watch())

    async def on_join(self, target, user):
        await super().on_join(target, user)
        logging.info(f"IRC Joined channel: {target} - {user}")
        if config["irc"].get("enable_join_part", False):
            if target in i2t_map:
                await tg_q.put((i2t_map[target], f"<b>{user}</b> joined channel."))
            else:
                await tg_q.put((config["telegram"]["fallback_chatid"], f"IRC {user} joined {target}."))

    async def on_part(self, target, user, message):
        await super().on_join(target, user)
        logging.info(f"IRC Left channel: {target} - {user} ({message})")
        if config["irc"].get("enable_join_part", False):
            if target in i2t_map:
                await tg_q.put((i2t_map[target], f"<b>{user}</b> left channel ({message})."))
            else:
                await tg_q.put((config["telegram"]["fallback_chatid"], f"IRC {user} left {target} ({message})."))

    async def on_kick(self, target, user, by, reason):
        await super().on_join(target, user)
        logging.info(f"IRC Left channel: {target} - {user} (kicked by {by}: {reason})")
        if config["irc"].get("enable_join_part", False):
            if target in i2t_map:
                await tg_q.put((i2t_map[target], f"<b>{user}</b> left channel (kicked by {by}: {reason})."))
            else:
                await tg_q.put((config["telegram"]["fallback_chatid"], f"IRC {user} left {target} (kicked by {by}: {reason})."))

    async def on_message(self, target, by, message):
        await super().on_message(target, by, message)
        if by == self.nickname:
            return

        logging.info(f'IRC {target} {by}: {message}')

        message = re.sub(f'(?<![a-zA-Z0-9_/]){config["telegram"]["allowed_username"]}(?![a-zA-Z0-9_/])', f'@{config["telegram"]["allowed_username"]}', message)

        if target in i2t_map:
            await tg_q.put((i2t_map[target], f"&lt;<b>{by}</b>&gt; {html.escape(message)}"))
        elif target == self.nickname:
            await tg_q.put((config["telegram"]["fallback_chatid"], f"IRC DM &lt;<b>{by}</b>&gt; {html.escape(message)}"))
        else:
            await tg_q.put((config["telegram"]["fallback_chatid"], f"IRC {target} &lt;<b>{by}</b>&gt; {html.escape(message)}"))

        # Attempt to reclaim nickname
        if self.nickname != config["irc"]["username"]:
            await self.set_nickname(config["irc"]["username"])

    async def on_notice(self, target, by, message):
        await super().on_notice(target, by, message)
        if by == self.nickname:
            return

        logging.info(f'IRC NOTICE {target} {by}: {message}')
        if target == self.nickname:
            await tg_q.put((config["telegram"]["fallback_chatid"], f"IRC NOTICE &lt;<b>{by}</b>&gt; {html.escape(message)}"))
        else:
            await tg_q.put((config["telegram"]["fallback_chatid"], f"IRC NOTICE {target} &lt;<b>{by}</b>&gt; {html.escape(message)}"))

    async def on_ctcp(self, by, target, what, contents):
        await super().on_ctcp(by, target, what, contents)
        if by == self.nickname:
            return

        if target in i2t_map and what == "ACTION":
            await tg_q.put((i2t_map[target], f"<b>{by}</b> {html.escape(contents if contents else '')}"))
        else:
            await tg_q.put((config["telegram"]["fallback_chatid"], f"IRC CTCP {what} {target} &lt;<b>{by}</b>&gt; {html.escape(contents if contents else '')}"))

    async def queue_watch(self):
        while True:
            try:
                name, msg = await irc_q.get()
                if isinstance(msg, tuple):
                    await self.ctcp(name, *msg)
                else:
                    await self.message(name, msg)
            except:
                logging.warning(f"IRC Failed to send message: {msg} to {name}", exc_info=True)
                try:
                    await tg_q.put((config["telegram"]["fallback_chatid"], f"IRC Failed to send message: {html.escape(msg)} to {name}"))
                except:
                    pass


async def irc_serve():
    if config["irc"].get("password", None):
        client = IRCClient(
            config["irc"]["username"],
            sasl_username=config["irc"]["username"],
            sasl_password=config["irc"]["password"],
            sasl_identity=config["irc"]["username"]
        )
    else:
        client = IRCClient(config["irc"]["username"])

    await client.connect(config["irc"]["server"], tls=True, tls_verify=True)


async def main():
    await irc_serve()
    await telegram_serve()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
