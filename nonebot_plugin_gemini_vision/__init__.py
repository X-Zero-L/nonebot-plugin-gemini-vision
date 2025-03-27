import aiohttp
from typing import Optional, List
from pathlib import Path

from nonebot import get_plugin_config, require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot.log import logger
from nonebot.params import Depends
from nonebot.exception import FinishedException

require("nonebot_plugin_alconna")
require("nonebot_plugin_session")
from nonebot_plugin_alconna import (
    Alconna,
    Args,
    on_alconna,
    Match,
    UniMessage,
    MsgId,
    Image as AlconnaImage,
)
from arclet.alconna import AllParam
from nonebot_plugin_alconna.builtins.extensions import ReplyRecordExtension
from nonebot_plugin_session import Session, extract_session
from nonebot.adapters import Bot, Event

from .config import Config
from .core import chat_with_gemini, clear_conversation_history, GeminiResponse

config = get_plugin_config(Config)
_help_str = """
Gemini Vision 帮助
/gemini <问题> - 与Gemini聊天，可包含以下特殊指令：
- 回复图片 + 问题：分析图片内容（支持多图）、编辑图片
- "清除历史"：清除对话历史记录
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
        "nonebot_plugin_alconna", "nonebot_plugin_uninfo"
    ),
    # supported_adapters={"~onebot.v11"},
    extra={"author": "X-Zero-L <your@mail.com>"},
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


async def to_image_data(segment) -> Optional[bytes]:
    """从消息段中提取图片数据"""
    if segment.type == "image" and hasattr(segment, "data"):
        try:
            # 尝试从URL获取图片数据
            if "url" in segment.data:
                img_url = segment.data["url"]
                logger.info(f"从URL提取图片数据: {img_url}")
                async with aiohttp.ClientSession() as session:
                    async with session.get(img_url) as resp:
                        if resp.status != 200:
                            logger.error(f"无法获取图片数据: {resp.status}")
                            return None
                        return await resp.read()

            # 尝试从文件路径获取图片数据
            elif "file" in segment.data:
                file_path = segment.data["file"]
                logger.info(f"从文件提取图片数据: {file_path}")
                return Path(file_path).read_bytes()

            # 如果有raw字段直接使用
            elif hasattr(segment, "raw") and segment.raw is not None:
                return segment.raw
        except Exception as e:
            logger.error(f"获取图像数据失败: {e}")

    elif isinstance(segment, AlconnaImage):
        try:
            if segment.raw is not None:
                return segment.raw

            if segment.url is not None:
                logger.info(f"从URL提取图片数据: {segment.url}")
                async with aiohttp.ClientSession() as session:
                    async with session.get(segment.url) as resp:
                        if resp.status != 200:
                            logger.error(f"无法获取图片数据: {resp.status}")
                            return None
                        return await resp.read()
        except Exception as e:
            logger.error(f"获取AlconnaImage图像数据失败: {e}")

    return None


async def extract_images_from_message(message) -> List[bytes]:
    """从消息中提取所有图片"""
    image_list: List[bytes] = []

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
        return

    msg = UniMessage()
    if response.text:
        msg += UniMessage(response.text)
    if response.image:
        msg += UniMessage.image(raw=response.image)

    await gemini_command.finish(msg.reply(id=msg_id))


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
    if not prompt.available or not prompt.result:
        await gemini_command.finish(UniMessage(_help_str))

    prompt_text = prompt.result

    if prompt_text in ["清除历史", "清除对话历史", "clear", "exit"]:
        await handle_clear_history(user_id)
        await gemini_command.finish(UniMessage("对话历史已清除"))

    image_list = await collect_images(event, ext, msg_id, bot)
    await send_processing_message(image_list, msg_id)
    await process_gemini_request(prompt_text, user_id, image_list, msg_id)


async def handle_clear_history(user_id: str):
    """处理清除历史记录的请求"""
    success = clear_conversation_history(user_id)
    if success:
        await gemini_command.finish(UniMessage("对话历史已清除"))
    else:
        await gemini_command.finish(UniMessage("没有找到对话历史"))


async def collect_images(
    event: Event, ext: ReplyRecordExtension, msg_id: MsgId, bot: Bot
) -> List[bytes]:
    """收集所有图片数据"""
    image_list: List[bytes] = []

    reply = ext.get_reply(msg_id)
    if reply:
        try:
            uni_reply = await UniMessage.generate(
                message=reply.msg, event=event, bot=bot
            )
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


async def send_processing_message(image_list: List[bytes], msg_id: MsgId):
    """发送处理中的提示消息"""
    if image_list and len(image_list) > 0:
        await gemini_command.send(
            UniMessage(
                f"正在处理您的请求（包含 {len(image_list)} 张图片），请稍等..."
            ).reply(id=msg_id)
        )
    else:
        await gemini_command.send(
            UniMessage(f"正在处理您的请求，请稍等...").reply(id=msg_id)
        )


async def process_gemini_request(
    prompt_text: str,
    user_id: str,
    image_list: List[bytes],
    msg_id: MsgId,
):
    try:
        response = await chat_with_gemini(
            prompt=prompt_text,
            user_id=user_id,
            image_list=image_list,
        )

        await send_gemini_response(response, msg_id)

    except FinishedException as e:
        pass

    except Exception as e:
        logger.error(f"处理请求出错: {e}")
        await gemini_command.finish(UniMessage(f"处理请求时出错: {str(e)}"))


@help_command.handle()
async def handle_help():
    await help_command.finish(UniMessage(_help_str))
