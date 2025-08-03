from pathlib import Path
from pydantic import BaseModel

class Job(BaseModel):
    id: str
    title: str
    company: str
    location: str
    url: str
    tags: list[str]

class JobData(BaseModel):
    jobs: list[Job]


_DATA_FILE = Path("data/jobs.sample.json")
json_text = _DATA_FILE.read_text(encoding="utf-8")
JOBS = JobData.model_validate_json(json_text)

jobs = JOBS.jobs
tags_set = set()
for job in jobs:
    tags_set.update(job.tags)

tags = list(tags_set)


def filter_jobs(*, keyword: str = "", selectedTags: list[str] = []) -> list[dict]:
    kw = keyword.lower()
    return [
        j for j in jobs
        if (
            not keyword
            or kw in j.title.lower()
            or kw in j.company.lower()
            or kw in j.location.lower()
        ) and (
            not selectedTags
            or any(tag in selectedTags for tag in j.tags)
        )
    ]

__all__ = ["filter_jobs", "jobs", "tags"]
