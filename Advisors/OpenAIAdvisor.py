import logging
from typing import Optional, List

import openai

from Advisors.AdvisorInterface import AdvisorInterface

# 类openai接口的建议提供者
class OpenAIAdvisor(AdvisorInterface):
    api_key = ''
    model = ''
    temperature = ''
    endpoint = ''
    prompt = ''

    def __init__(self, api_key, model, temperature, endpoint, prompt):
        self.api_key = api_key
        self.model = model
        self.temperature = float(temperature)  # 确保 temperature 为浮点数类型
        self.endpoint = endpoint
        self.prompt = prompt
        if not self.endpoint:
            self.endpoint = None

    def get_text_suggestions(self, text) -> Optional[List[str]]:
        """调用OpenAI API获取建议"""
        try:

            client = openai.OpenAI(api_key=self.api_key, base_url=self.endpoint)

            prompt = (
                self.prompt
            )

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的写作助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=500
            )

            content = response.choices[0].message.content
            suggestions = [s.strip() for s in content.split("\n") if s.strip()]

            logging.debug(f"从OpenAI获取的原始响应: {content}")
            return suggestions[:3]  # 只返回前三个建议

        except Exception as e:
            logging.error(f"OpenAI API调用失败: {str(e)}", exc_info=True)
            raise