import base64
import time
from typing import Literal

from google import genai
from google.genai import types
from nonebot import get_plugin_config
from nonebot.log import logger
from nonebot_plugin_alconna import UniMessage
from pydantic import BaseModel, Field

from .config import Config

config = get_plugin_config(Config)

client: genai.Client | None = None


def get_client():
    global client
    if not client:
        client = genai.Client(api_key=config.gemini_api_key)
    return client


class ConversationHistory(BaseModel):
    """会话历史记录模型"""

    history: types.ContentListUnionDict = Field(default=[])
    timestamp: float = Field(default_factory=time.time)

    class Config:
        arbitrary_types_allowed = True

    def add_message(self, role: Literal["user", "model"], message: types.ContentListUnionDict):
        """添加消息到会话历史"""
        self.history.append({"role": role, "parts": message})
        self.timestamp = time.time()


class GeminiResponse(BaseModel):
    """Gemini响应模型"""

    success: bool = Field(default=True)
    message: UniMessage = Field(default=None)
    error: str | None = Field(default=None)

    class Config:
        arbitrary_types_allowed = True


conversations: dict[str, ConversationHistory] = {}


def get_conversation(user_id: str) -> ConversationHistory:
    """获取或创建会话历史记录"""
    if user_id not in conversations or (conversations[user_id].timestamp + 600 < time.time()):
        conversations[user_id] = ConversationHistory()
    return conversations[user_id]


def clear_conversation_history(user_id: str) -> bool:
    """
    清除特定用户的对话历史

    Args:
        user_id: 用户ID

    Returns:
        bool: 是否成功清除
    """
    if user_id in conversations:
        del conversations[user_id]
        return True
    return False


def build_contents(
    conversation: ConversationHistory,
    user_id: str,
    prompt: str,
    image_list: list[bytes] | None = None,
) -> types.ContentListUnionDict:
    """
    构建发送给Gemini的内容

    Args:
        conversation: 会话历史记录对象
        user_id: 用户ID
        prompt: 用户提问
        image_list: 可选的多张图片数据列表

    Returns:
        types.ContentListUnionDict: 构建好的内容列表
    """
    contents = []
    if getattr(config, "gemini_preset", ""):
        contents.append({"role": "system", "parts": [{"text": config.gemini_preset}]})
    contents.extend(conversation.history)
    parts = [{"text": prompt}]
    if image_list:
        for img_data in image_list:
            parts.append(
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": base64.b64encode(img_data).decode("utf-8"),
                    }
                }
            )
    contents.append({"role": "user", "parts": parts})
    return contents


async def chat_with_gemini(
    prompt: str,
    user_id: str,
    image_list: list[bytes] | None = None,
) -> GeminiResponse:
    """
    与Gemini进行对话

    Args:
        prompt: 用户提问
        user_id: 用户ID，用于追踪会话历史
        image_list: 可选的多张图片数据列表

    Returns:
        GeminiResponse: 包含成功状态、文本、图片和错误信息的响应对象
    """
    if not config.gemini_api_key:
        return GeminiResponse(success=False, error="未配置Gemini API密钥")
    try:
        conversation = get_conversation(user_id)
        generate_content_config = types.GenerateContentConfig(response_modalities=(["Text", "Image"]), top_p=0.95)
        client = get_client()
        response = await client.aio.models.generate_content(
            model=config.gemini_model,
            contents=build_contents(conversation, user_id, prompt, image_list),
            config=generate_content_config,
        )
        message = UniMessage()
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                message += UniMessage(part.text)
            if part.inline_data is not None:
                message += UniMessage.image(
                    raw=part.inline_data.data,
                    mimetype=part.inline_data.mime_type,
                )
        # Extract parts from the last user message in built contents
        user_parts = build_contents(conversation, user_id, prompt, image_list)[-1]["parts"]
        conversation.add_message(
            role="user",
            message=user_parts,
        )
        conversation.add_message(
            role="model",
            message=response.candidates[0].content.parts,
        )
        conversation.timestamp = time.time()
        return GeminiResponse(success=True, message=message)

    except Exception as e:
        logger.error(f"Gemini对话出错: {e!s}")
        return GeminiResponse(success=False, error=f"对话出错: {e!s}")
