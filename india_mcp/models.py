from datetime import date
from typing import Literal
from pydantic import BaseModel, HttpUrl, Field

Status = Literal["in_force", "repealed", "needs_manual_review"]


class SectionFrontmatter(BaseModel):
    act: str
    section: str
    chapter: int | None = None
    heading: str
    status: Status
    amended_by: list[str] = Field(default_factory=list)
    source_url: HttpUrl
    source_hash: str
    synced: date
    parse_error: str | None = None


class ActMeta(BaseModel):
    slug: str
    title: str
    year: int
    ministry: str
    source_url: HttpUrl
    last_synced: date
    section_count: int
