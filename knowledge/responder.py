# 小禾/knowledge/responder.py

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from infrastructure.llm import llm
from domain.messages import UserMessage, BotMessage
from domain.state import Turn
from prompts.history_builder import HistoryBuilder
from prompts.loader import load_prompt
from knowledge.providers import KnowledgeChunk

# 当你要走 知识 这个轨道的时候  调用
class KnowledgeResponder:

    async def respond(
            self,
            user_message: UserMessage,
            recent_turns: list[Turn],
            chunks: list[KnowledgeChunk]
    ) -> list[BotMessage]:
        # 准备提示词上下文
        user_message = HistoryBuilder._render_user_message(user_message) # 渲染用户消息
        history = HistoryBuilder.build(recent_turns) # 构建历史对话
        knowledge_content = "\n\n".join([chunk.content for chunk in chunks]) # 合并知识内容

        # 构造chain
        prompt_text = load_prompt("knowledge_respond") # 加载知识回复提示词
        prompt = PromptTemplate.from_template(
            prompt_text,
            template_format="jinja2"
        ) # 构造提示词模板
        chain = prompt | llm | StrOutputParser()# 构造chain

        # 运行chain
        response = await chain.ainvoke({
            "user_message": user_message,
            "history": history,
            "knowledge_content": knowledge_content,
        }) # 运行chain

        return [BotMessage(text=response)] # 返回机器人回复消息
