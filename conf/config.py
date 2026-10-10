# itwwy/conf/config.py
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"




# 配置文件的 模型类 校验
class Settings(BaseSettings):

    # LLM
    llm_api_key: str
    llm_model: str
    llm_base_url: str

    # 数据库
    database_url: str

    # 商城 API
    commerce_api_base_url: str

    # 服务器
    app_host: str
    app_port: int

    # ===== 魔珐星云（Xmov Xingyun）具身智能数字人 =====
    # 设计取舍：以下全部给默认值，未配置时不启用数字人能力，
    # 保证原有 /api/chat 链路不受任何影响（最小侵入）。
    xmov_enabled: bool = False
    xmov_app_id: str | None = None
    xmov_app_secret: str | None = None
    # 官方 JS SDK 示例中出现的会话网关地址
    xmov_gateway_server: str = "https://nebula-agent.xingyun3d.com/user/v1/ttsa/session"
    # 后端调用基地址（若官方开放 REST，可在此覆盖）
    xmov_api_base: str = "https://nebula-agent.xingyun3d.com"
    # 官方 JS SDK 地址（来自官方文档 developers/52-183 的 script 标签）
    xmov_js_sdk_url: str = (
        "https://media.xingyun3d.com/xingyun3d/general/litesdk/xmovAvatar@latest.js"
    )
    # 默认形象标识：在星云控制台「应用管理 → 驱动应用」创建后获取
    xmov_default_avatar_id: str = "default"
    xmov_timeout_seconds: float = 15.0
    xmov_max_retries: int = 2
    # 是否允许把 AppSecret 下发给浏览器（仅本地演示可开，生产必须为 False）
    xmov_allow_secret_to_client: bool = False


    # 从.env文件中读取配置信息
    # 如果读取真实环境变量，则不写这句话
    # extra="ignore" 表示忽略.env那个文件中有，setting类没有写的配置项，不会报错
    # env_file_encoding：如果遇到乱码问题则添加这个属性解决
    # 注意这里对象名必须叫model_config ，而且必须定义，否则配置会被回收
    # 继承 BaseSettings   里面也提供一系列 默认 的属性
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore", env_file_encoding="utf-8")

settings = Settings()


if __name__ == '__main__':

    a = int(os.getenv("APP_PORT")) # int
    print(type(a)) # int   NoneType
    # from itwwy.conf.config import settings
    # 自动为我们做了 类型转换
    print(type(settings.database_url))

