from pydantic import BaseModel, Field


class ExecuteNowRequest(BaseModel):
    instruction: str | None = Field(default=None, max_length=10_000)
