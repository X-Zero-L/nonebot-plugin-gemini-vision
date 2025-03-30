import asyncio

import aiohttp
from nonebot import get_plugin_config, require
from nonebot.exception import FinishedException
from nonebot.log import logger
from nonebot.params import Depends
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

require("nonebot_plugin_alconna")
require("nonebot_plugin_session")
require("nonebot_plugin_uninfo")
from arclet.alconna import AllParam
from nonebot.adapters import Bot, Event
from nonebot_plugin_alconna import (
    Alconna,
    Args,
    Match,
    MsgId,
    UniMessage,
    on_alconna,
)
from nonebot_plugin_alconna import (
    Image as AlconnaImage,
)
from nonebot_plugin_alconna.builtins.extensions import ReplyRecordExtension
from nonebot_plugin_session import Session, extract_session

from .config import Config
from .core import GeminiResponse, chat_with_gemini, clear_conversation_history

config = get_plugin_config(Config)
_help_str = """
Gemini Vision 帮助
/gemini <问题> [图片列表] - 提交问题和图片，支持编辑/生成/理解图片，同时支持回复某消息，获取消息内的图片进行对话
例如：
/gemini 把皮卡丘的耳朵和腮红去掉 [某黄色生物图片]
回复某消息+/gemini 把头发染成绿的
支持上下文对话，当你上文已经提交了图片后，可以像这样: /gemini 改成紫色
也支持清空当前上下文：/gemini exit
/gemini_help - 查看帮助信息
""".strip()
__plugin_meta__ = PluginMetadata(
    name="Gemini Vision",
    description="基于Google Gemini多模态模型的聊天与图像生成功能",
    usage=_help_str,
    type="application",  # library
    homepage="https://github.com/X-Zero-L/nonebot-plugin-gemini-vision",
    config=Config,
    supported_adapters=inherit_supported_adapters(
        "nonebot_plugin_alconna", "nonebot_plugin_uninfo", "nonebot_plugin_session"
    ),
    # supported_adapters={"~onebot.v11"},
    extra={"author": "X-Zero-L <zeroeeau@gmail.com>"},
)

gemini_command = on_alconna(
    Alconna(
        "/gemini",
        Args["prompt?", str],
        Args["image?", AllParam],
    ),
    skip_for_unmatch=False,
    use_cmd_start=True,
    priority=5,
    block=True,
    extensions=[ReplyRecordExtension()],
    aliases={"@gemini", "/g", "gemini"},
)

help_command = on_alconna(
    Alconna("/gemini_help"),
    use_cmd_start=True,
    priority=5,
    block=True,
    aliases={"@gemini_help", "/ghelp", "gemini帮助"},
)

user_lock: dict[str, asyncio.Lock] = {}


def get_lock(user_id: str) -> asyncio.Lock:
    """获取用户锁"""
    if user_id not in user_lock:
        user_lock[user_id] = asyncio.Lock()
    return user_lock[user_id]


async def get_image_data_from_url(url: str) -> bytes | None:
    """从URL获取图片数据"""
    try:
        logger.info(f"获取图像数据: {url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    logger.error(f"无法获取图片数据: {resp.status}")
                    return None
                return await resp.read()
    except Exception as e:
        logger.error(f"获取图像数据失败: {e}")
        return None


async def to_image_data(segment) -> bytes | None:
    """从消息段中提取图片数据"""
    if segment.type == "image" and hasattr(segment, "data"):
        try:
            if "url" in segment.data:
                img_url = segment.data["url"]
                return await get_image_data_from_url(img_url)

            elif hasattr(segment, "raw") and segment.raw is not None:
                return segment.raw
        except Exception as e:
            logger.error(f"获取图像数据失败: {e}")

    elif isinstance(segment, AlconnaImage):
        try:
            if segment.raw is not None:
                return segment.raw

            if segment.url is not None:
                return await get_image_data_from_url(segment.url)

        except Exception as e:
            logger.error(f"获取AlconnaImage图像数据失败: {e}")

    return None


async def extract_images_from_message(message) -> list[bytes]:
    """从消息中提取所有图片"""
    image_list: list[bytes] = []

    if not message:
        return image_list

    for segment in message:
        img_bytes = await to_image_data(segment)
        if img_bytes:
            image_list.append(img_bytes)

    return image_list


async def send_gemini_response(response: GeminiResponse, msg_id: MsgId):
    """处理并发送Gemini的响应"""
    if not response.success:
        await gemini_command.finish(UniMessage(response.error))

    await gemini_command.finish(response.message.reply(id=msg_id))


@gemini_command.handle()
async def handle_gemini(
    bot: Bot,
    event: Event,
    prompt: Match[str],
    ext: ReplyRecordExtension,
    msg_id: MsgId,
    session: Session = Depends(extract_session),
):
    user_id = str(session.id1)
    lock = get_lock(user_id)
    if lock.locked():
        await gemini_command.send(UniMessage("正在处理您的上一个请求，请稍等...").reply(id=msg_id))
    async with lock:
        if not prompt.available or not prompt.result:
            await gemini_command.finish(UniMessage(_help_str).reply(id=msg_id))

        prompt_text = prompt.result

        if prompt_text in ["清除历史", "清除对话历史", "clear", "exit"]:
            await handle_clear_history(user_id, msg_id)

        image_list = await collect_images(event, ext, msg_id, bot)
        await send_processing_message(image_list, msg_id)
        await process_gemini_request(prompt_text, user_id, image_list, msg_id)


async def handle_clear_history(user_id: str, msg_id: MsgId):
    """处理清除历史记录的请求"""
    success = clear_conversation_history(user_id)
    if success:
        await gemini_command.finish(UniMessage("对话历史已清除").reply(id=msg_id))
    else:
        await gemini_command.finish(UniMessage("没有找到对话历史").reply(id=msg_id))


async def collect_images(event: Event, ext: ReplyRecordExtension, msg_id: MsgId, bot: Bot) -> list[bytes]:
    """收集所有图片数据"""
    image_list: list[bytes] = []

    reply = ext.get_reply(msg_id)
    if reply:
        try:
            uni_reply = await UniMessage.generate(message=reply.msg, event=event, bot=bot)
            for segment in uni_reply:
                if isinstance(segment, AlconnaImage):
                    img_bytes = await to_image_data(segment)
                    if img_bytes:
                        image_list.append(img_bytes)
        except Exception as e:
            logger.error(f"处理回复消息中的图片出错: {e}")

    try:
        message_images = await extract_images_from_message(event.get_message())
        image_list.extend(message_images)
    except Exception as e:
        logger.error(f"处理消息中图片出错: {e}")

    return image_list


async def send_processing_message(image_list: list[bytes], msg_id: MsgId):
    """发送处理中的提示消息"""
    if image_list and len(image_list) > 0:
        await gemini_command.send(
            UniMessage(f"正在处理您的请求（包含 {len(image_list)} 张图片），请稍等...").reply(id=msg_id)
        )
    else:
        await gemini_command.send(UniMessage("正在处理您的请求，请稍等...").reply(id=msg_id))


async def process_gemini_request(
    prompt_text: str,
    user_id: str,
    image_list: list[bytes],
    msg_id: MsgId,
):
    try:
        response = await chat_with_gemini(
            prompt=prompt_text,
            user_id=user_id,
            image_list=image_list,
        )

        await send_gemini_response(response, msg_id)

    except FinishedException:
        pass

    except Exception as e:
        logger.error(f"处理请求出错: {e}")
        await gemini_command.finish(UniMessage(f"处理请求时出错: {e!s}").reply(id=msg_id))


@help_command.handle()
async def handle_help():
    await help_command.finish(UniMessage(_help_str))
