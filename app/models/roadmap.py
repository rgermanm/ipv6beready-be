from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RoadmapPosition(BaseModel):
    x: float
    y: float


class RoadmapNode(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    kind: Literal["skill", "lab", "module"] = "skill"
    title: str
    description: str = ""
    lab_slug: str | None = None
    module_id: str | None = None
    icon: str | None = None
    difficulty: Literal["easy", "medium", "hard"] | None = None
    position: RoadmapPosition
    # Filled when hydrating against the labs collection
    available: bool = False
    exercise_count: int = 0
    duration_minutes: int = 0


class RoadmapEdge(BaseModel):
    id: str
    source: str
    target: str


class RoadmapModule(BaseModel):
    id: str
    title: str
    summary: str = ""
    node_ids: list[str] = Field(default_factory=list)


class RoadmapSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    slug: str
    title: str
    description: str = ""
    difficulty: Literal["easy", "medium", "hard"] = "easy"
    estimated_hours: int = 8
    tags: list[str] = Field(default_factory=list)
    stage: str = ""
    stage_order: int = 0
    stage_summary: str = ""
    highlights: list[str] = Field(default_factory=list)
    module_count: int = 0
    lab_count: int = 0
    available_lab_count: int = 0
    lab_slugs: list[str] = Field(default_factory=list)
    enabled: bool = True

    @field_validator("difficulty", mode="before")
    @classmethod
    def _coerce_difficulty(cls, value):
        if value in ("easy", "medium", "hard"):
            return value
        return "easy"


class RoadmapDefinition(RoadmapSummary):
    modules: list[RoadmapModule] = Field(default_factory=list)
    nodes: list[RoadmapNode] = Field(default_factory=list)
    edges: list[RoadmapEdge] = Field(default_factory=list)
