from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LabCredentials(BaseModel):
    username: str
    password: str


class ExerciseCheck(BaseModel):
    """Declarative rule used by the frontend to mark an exercise complete.

    A check passes when a matching command was run on an allowed device and
    (optionally) the captured command output satisfies the include/exclude
    patterns.
    """

    type: Literal["command"] = "command"
    # Containerlab node names: r1, r2, r3, pc1, pc2, pc3
    # Empty / omitted = any device of the matching kind is allowed
    devices: list[str] = Field(default_factory=list)
    # Regex matched against the submitted command (case-insensitive)
    command: str
    # All of these substrings must appear in the command output
    output_includes: list[str] = Field(default_factory=list)
    # None of these substrings may appear in the command output
    output_excludes: list[str] = Field(default_factory=list)
    # Human-readable hint shown when debugging (optional)
    description: str | None = None


class Exercise(BaseModel):
    id: str
    number: int
    title: str
    description: str
    # All checks must pass (AND). Empty list = no auto-validation.
    checks: list[ExerciseCheck] = Field(default_factory=list)


class ClabConfig(BaseModel):
    """Containerlab topology deployed on a remote host via SSH."""

    model_config = ConfigDict(extra="ignore")

    lab_name: str
    topology_file: str = "rutas_estaticas.clab.yml"
    # Absolute directory on the lab server that contains the .clab.yml
    path: str
    entry_node: str = "r1"
    node_credentials: LabCredentials = Field(
        default_factory=lambda: LabCredentials(username="root", password="clab123")
    )


class LabFormula(BaseModel):
    """Server-side recipe used to provision a container lab instance."""

    provider: Literal["docker", "clab"] = "docker"
    image: str = ""
    container_name_prefix: str = ""
    port: int = Field(default=22, description="Port exposed to the user")
    protocol: Literal["ssh", "http", "rdp"] = "ssh"
    credentials: LabCredentials | None = None
    timeout_minutes: int = 60
    build_context: str | None = Field(
        default=None,
        description="Optional Docker build context path relative to the compose project",
    )
    networks: list[str] = Field(default_factory=lambda: ["lab-net"])
    environment: dict[str, str] = Field(default_factory=dict)
    enable_ipv6: bool = True
    clab: ClabConfig | None = None


class LabSummary(BaseModel):
    id: str
    title: str
    description: str
    category: str
    difficulty: Literal["easy", "medium", "hard"]
    duration_minutes: int
    tags: list[str]
    exercise_count: int
    # Absolute directory on the lab server that holds the .clab.yml
    path: str


class LabDefinition(LabSummary):
    exercises: list[Exercise]
    formula: LabFormula
