from openai import OpenAI, OpenAIError
from typing import Literal
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()


class TradeAction(BaseModel):
    symbol: str
    action: Literal["BUY", "SELL", "HOLD"]
    quantity: int
    order_type: Literal["MKT", "LMT", "STP", "STP LMT", "MIT", "LIT", "MOC", "LOC", "MTL"]
    limit_price: float | None = None
    reasoning: str


class TradingDecision(BaseModel):
    actions: list[TradeAction]
    overall_reasoning: str
    confidence: Literal["low", "medium", "high"]
    halt_trading: bool


class AIServiceError(Exception):
    """Raised when ACORN's AI service encounters an error"""


def call_trading_model(content: str) -> TradingDecision:
    """Calls ChatGPT to make trading actions

        Args:
            content: text to send to model

        Returns:
            response: trading decision object
    """
    try:
        with open("./prompts/Trading.txt", "r", encoding="utf-8") as f:
            sysPrompt = f.read()

        response = client.responses.parse(
            model="gpt-5.4-mini",
            instructions=sysPrompt,
            input=content,
            text_format=TradingDecision
        )
        if response.output_parsed is None:
            raise AIServiceError("Model returned no parsabe output")
        return response.output_parsed
    except OpenAIError as e:
        raise AIServiceError(f"AI service encountered an error:\n{e}")
    except IOError as e:
        raise AIServiceError(f"AI service couldn't read context prompt:\n{e}")
        

def call_analysis_model(content: str) -> str:
    """Calls ChatGPT to give daily analysis

        Args:
            content: text to send to model

        Returns:
            response: trading decision object
    """
    try:
        with open("./prompts/Aftermath.txt", "r", encoding="utf-8") as f:
            sysPrompt = f.read()

        response = client.responses.create(
            model="gpt-5.4-mini",
            instructions=sysPrompt,
            input=content,
        )
        if response.output_text is None:
            raise AIServiceError("Model returned no text")
        return response.output_text
    except OpenAIError as e:
        raise AIServiceError(f"AI service encountered an error:\n{e}")
    except IOError as e:
        raise AIServiceError(f"AI service couldn't read context prompt:\n{e}")