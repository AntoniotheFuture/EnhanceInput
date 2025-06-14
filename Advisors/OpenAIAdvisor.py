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
            if not text.strip():
                raise ValueError("输入文本不能为空")

            if not self.api_key:
                raise ValueError("OpenAI API密钥未配置")

            client = openai.OpenAI(api_key=self.api_key, base_url=self.endpoint)

            prompt = self.prompt.replace("<text>", text)

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

            if not suggestions:
                raise ValueError("API返回了空建议")

            logging.debug(f"从OpenAI获取的原始响应: {content}")
            return suggestions[:3]

        except openai.AuthenticationError:
            error_msg = "OpenAI认证失败，请检查API密钥"
            logging.error(error_msg)
            raise ValueError(error_msg)
        except openai.APIConnectionError:
            error_msg = "连接OpenAI API失败，请检查网络和端点配置"
            logging.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            logging.error(f"OpenAI API调用失败: {str(e)}", exc_info=True)
            raise