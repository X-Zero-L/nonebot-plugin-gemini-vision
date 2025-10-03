from pydantic import BaseModel


class Config(BaseModel):
    """Gemini Vision Plugin Config"""

    gemini_api_key: str = ""  # 必填项，Gemini API密钥
    gemini_model: str = "gemini-2.5-flash-image-preview"  # 注意：需要使用支持图像生成的模型
    gemini_preset: str = ""  # 可选项，系统预设提示词
