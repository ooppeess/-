from pydantic import BaseModel, Field

class CaseInfo(BaseModel):
    case_name: str = Field(...)
    case_id: str = Field(...)
    person_type: str = Field(...)

class UploadResponse(BaseModel):
    status: str
    message: str
    case_id: str | None = None
    imported: int | None = None

class TrendResponse(BaseModel):
    months: list[str]
    incomes: list[float]
    expenses: list[float]

class InteractionLink(BaseModel):
    source: str
    target: str
    value: float
    detail: dict

class InteractionResponse(BaseModel):
    nodes: list[dict]
    links: list[InteractionLink]

