from pydantic import BaseModel, ConfigDict


class CsvAnalysis(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    filename: str
    rows: int
    columns: int
    headers: list[str]
    preview: list[list[str]]
