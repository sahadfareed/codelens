from dataclasses import dataclass, asdict

@dataclass
class Task:
    """A single to-do item."""
    title: str
    done: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    def __str__(self):
        return f"[{'x' if self.done else ' '}] {self.title}"
