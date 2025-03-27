import base64
import asyncio
import os
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from nonebot import get_plugin_config
from nonebot.log import logger
from google.genai import types
from google import genai
from .config import Config
import time

config = get_plugin_config(Config)
os.environ["http_proxy"] = config.http_proxy
os.environ["https_proxy"] = config.https_proxy
os.environ["ALL_PROXY"] = config.http_proxy
os.environ["GRPC_PROXY"] = config.http_proxy

client: Optional[genai.Client] = None


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


class GeminiResponse(BaseModel):
    """Gemini响应模型"""

    success: bool = Field(default=True)
    text: str = Field(default="")
    image: Optional[Any] = Field(default=None)
    error: Optional[str] = Field(default=None)


conversations: Dict[str, ConversationHistory] = {}


def get_conversation(user_id: str) -> ConversationHistory:
    """获取或创建会话历史记录"""
    if user_id not in conversations or (
        conversations[user_id].timestamp + 600 < time.time()
    ):
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


async def chat_with_gemini(
    prompt: str,
    user_id: str,
    image_list: Optional[List[bytes]] = None,
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
        parts = []
        parts.append({"text": prompt})
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
        generate_content_config = types.GenerateContentConfig(
            response_modalities=(["Text", "Image"]),
        )
        client = get_client()
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=config.gemini_model,
            contents=conversation.history + [{"parts": parts, "role": "user"}],
            config=generate_content_config,
        )

        response_text = ""
        response_image = None

        for part in response.candidates[0].content.parts:
            if part.text is not None:
                response_text = part.text
            elif part.inline_data is not None:
                response_image = part.inline_data.data
        conversation.history.append(
            {
                "parts": parts,
                "role": "user",
            }
        )
        conversation.history.append(
            {
                "parts": response.candidates[0].content.parts,
                "role": "model",
            }
        )
        conversation.timestamp = time.time()
        return GeminiResponse(success=True, text=response_text, image=response_image)

    except Exception as e:
        logger.error(f"Gemini对话出错: {str(e)}")
        return GeminiResponse(success=False, error=f"对话出错: {str(e)}")
