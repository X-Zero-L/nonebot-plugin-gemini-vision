from pydantic import BaseModel


class Config(BaseModel):
    """Gemini Vision Plugin Config"""

    gemini_api_key: str = ""  # 必填项，Gemini API密钥
    gemini_model: str = (
        "gemini-2.0-flash-exp-image-generation"  # 注意：需要使用支持图像生成的模型
    )
    http_proxy: str = ""  # HTTP代理
    https_proxy: str = ""  # HTTPS代理
