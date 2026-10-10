# itwwy/knowledge/providers.py

import json, asyncio
from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel
from conf.config import settings
from domain.state import DialogueState
from infrastructure import http_client

# 供应商  就是 具体 如何进行 知识检索（搜索）供应知识

class KnowledgeChunk(BaseModel):
    content: str


class KnowledgeProvider(ABC):
    # 知识提者的ID
    provider_id = ""

    @abstractmethod
    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        """
        提供检索方法
        :param state:
        :return:
        """
        pass

# 商品API
class ProductAPIProvider(KnowledgeProvider):
    provider_id = 'api.product'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        product_id = state.focused_object.id
        data: dict[str, Any] = await self._get_product_info_by_id(product_id)
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return [KnowledgeChunk(content=f"商品信息:\n{text}")]

    async def _get_product_info_by_id(self, product_id: str) -> dict[str, Any]:
        url = f"{settings.commerce_api_base_url}/products/{product_id}"
        # http://127.0.0.1:18081/products/123456
        # 注意此处：
        # 文件头部 from itwwy.infrastructure import http_client
        # 此处使用 http_client.http_client.get(url) 调用

        # 不要这样做：
        # 文件头部 from itwwy.infrastructure.http_client import http_client
        # 此处使用 http_client.get(url) 调用
        # 会使拿到的 http_client 是 None
        response = await http_client.http_client.get(url)
        return response.json()["data"]


# 订单API
class OrderAPIProvider(KnowledgeProvider):
    provider_id = 'api.order'# 订单API 供应商的ID

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        order_number = state.focused_object.id # 订单号

        order_payload, logistics_payload = await asyncio.gather(
            self._fetch_order(order_number),# 查订单信息
            self._fetch_logistics(order_number),# 查物流信息
        )

        return [
            KnowledgeChunk(
                content="订单与物流信息：\n"
                        + json.dumps(
                    {
                        "order_number": order_number,
                        "order": order_payload,
                        "logistics": logistics_payload,
                    },
                    ensure_ascii=False,# 不使用_ascii编码
                    indent=2,# 缩进2个空格
                )
            )
        ]

    async def _fetch_order(self, order_number) -> dict[str, Any]:
        url = f"{settings.commerce_api_base_url}/orders/{order_number}"
        # http://127.0.0.1:18081/orders/123456
        response = await http_client.http_client.get(url)
        return response.json()["data"]

    async def _fetch_logistics(self, order_number) -> dict[str, Any]:
        url = f"{settings.commerce_api_base_url}/orders/{order_number}/logistics"
        # http://127.0.0.1:18081/orders/123456/logistics
        response = await http_client.http_client.get(url)
        return response.json().get("data", {})

# 常见问题API
class FAQProvider(KnowledgeProvider):
    provider_id = 'faq.default'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        # TODO
        return [KnowledgeChunk(content="FAQ：未检索到相关问题")]

# RAGAPI
class RAGProvider(KnowledgeProvider):
    provider_id = 'rag.default'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        # TODO 接口
        return [KnowledgeChunk(content="RAG：未检索到相关信息")]
