import json
import os
from models import Task

class TaskStore:
    """Persists tasks to a JSON file."""

    def __init__(self, path: str):
        self.path = path
        self.tasks = self._load()

    def _load(self) -> list:
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path) as f:
                return [Task(**d) for d in json.load(f)]
        except json.JSONDecodeError:
            return []

    def _save(self):
        with open(self.path, "w") as f:
            json.dump([t.to_dict() for t in self.tasks], f, indent=2)

    def add(self, task: Task):
        self.tasks.append(task)
        self._save()

    def all(self) -> list:
        return self.tasks

    def complete(self, index: int):
        self.tasks[index].done = True
        self._save()
