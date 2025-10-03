<div align="center">
    <a href="https://v2.nonebot.dev/store">
    <img src="https://raw.githubusercontent.com/fllesser/nonebot-plugin-template/refs/heads/resource/.docs/NoneBotPlugin.svg" width="300" alt="logo"></a>
</div>

<div align="center">

## ✨ nonebot-plugin-gemini-vision ✨

<a href="./LICENSE">
    <img src="https://img.shields.io/github/license/X-Zero-L/nonebot-plugin-gemini-vision.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-gemini-vision">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-gemini-vision.svg" alt="pypi">
</a>
<img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="python">
<a href="https://github.com/astral-sh/ruff">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json" alt="ruff">
</a>
<a href="https://github.com/astral-sh/uv">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json" alt="uv">
</a>
</div>

> [!IMPORTANT] > **收藏项目** ～ ⭐️

<img width="100%" src="https://starify.komoridevs.icu/api/starify?owner=X-Zero-L&repo=nonebot-plugin-gemini-vision" alt="starify" />

## 📖 介绍

支持图像分析、生成、编辑的 Gemini 对话插件，并且带有连续上下文，消息回复功能。

## 💿 安装

<details open>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-gemini-vision --upgrade

使用 **pypi** 源安装

    nb plugin install nonebot-plugin-gemini-vision --upgrade -i "https://pypi.org/simple"

使用**清华源**安装

    nb plugin install nonebot-plugin-gemini-vision --upgrade -i "https://pypi.tuna.tsinghua.edu.cn/simple"

</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details open>
<summary>uv</summary>

    uv add nonebot-plugin-gemini-vision

安装仓库 master 分支

    uv add git+https://github.com/X-Zero-L/nonebot-plugin-gemini-vision@master

</details>

<details>
<summary>pdm</summary>

    pdm add nonebot-plugin-gemini-vision

安装仓库 master 分支

    pdm add git+https://github.com/X-Zero-L/nonebot-plugin-gemini-vision@master

</details>
<details>
<summary>poetry</summary>

    poetry add nonebot-plugin-gemini-vision

安装仓库 master 分支

    poetry add git+https://github.com/X-Zero-L/nonebot-plugin-gemini-vision@master

</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot_plugin_gemini_vision"]

</details>

## ⚙️ 配置

在 nonebot2 项目的`.env`文件中添加下表中的必填配置

|     配置项     | 必填 |              默认值              |                    说明                     |
| :------------: | :--: | :------------------------------: | :-----------------------------------------: |
| gemini_api_key |  是  |                无                |          Gemini API 密钥，必须提供          |
|  gemini_model  |  否  | "gemini-2.5-flash-image-preview" | Gemini 模型名称，默认使用支持图像生成的模型 |
| gemini_preset  |  否  |                ""                |      系统预设提示词，用于设置 AI 角色       |

如需要代理访问，在环境变量中设置`HTTP_PROXY`和`HTTPS_PROXY`或`ALL_PROXY`，如：

```bash
export HTTP_PROXY=localhost:7890
export HTTPS_PROXY=localhost:7890
export ALL_PROXY=localhost:7890
```

如使用 **Windows** 系统，设置环境变量的命令为：

```bash
set HTTP_PROXY=localhost:7890
set HTTPS_PROXY=localhost:7890
set ALL_PROXY=localhost:7890
```

## 🎉 使用

### 指令表

|       指令       |  权限  | 需要@ |   范围    |                    说明                    |
| :--------------: | :----: | :---: | :-------: | :----------------------------------------: |
|  /gemini <问题>  | 所有人 |  否   | 私聊/群聊 | 与 Gemini 对话，可包含图片分析、编辑等功能 |
|  @gemini <问题>  | 所有人 |  是   | 私聊/群聊 |               同上，别名形式               |
|    /g <问题>     | 所有人 |  否   | 私聊/群聊 |                简短命令形式                |
|  gemini <问题>   | 所有人 |  否   | 私聊/群聊 |              无斜杠的简便形式              |
| /gemini 清除历史 | 所有人 |  否   | 私聊/群聊 |           清除当前用户的对话历史           |
|   /gemini_help   | 所有人 |  否   | 私聊/群聊 |                查看帮助信息                |
|      /ghelp      | 所有人 |  否   | 私聊/群聊 |           查看帮助信息的简短形式           |

### 特殊功能

- **图片分析**：回复一张或多张图片发送问题，Gemini 将分析图片内容
- **图片生成**：模型支持生成图片，直接提问即可生成相关图片，也支持上传图片进行编辑
- **连续对话**：支持上下文连续对话，保持 10 分钟的会话状态
- **清除历史**：使用"清除历史"、"clear"或"exit"命令可清除会话记录

### 使用示例

1. 文本对话: `/gemini 介绍一下自己的功能`
2. 图片分析: 回复一张图片 + `/gemini 这张图片里有什么？`
3. 图片生成: `/gemini 画一幅夕阳下的海滩风景画`
4. 清除对话历史: `/gemini 清除历史`
5. 查看帮助: `/gemini_help`

注意：图像生成功能需要使用支持该功能的 Gemini 模型，默认配置已选择支持图像生成的模型。

### 🎨 效果图

![效果图1](docs/images/1.png)
![效果图2](docs/images/2.png)
![效果图3](docs/images/3.png)
![效果图4](docs/images/4.png)
