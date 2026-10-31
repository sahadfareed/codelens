from storage import TaskStore
from models import Task

def run():
    store = TaskStore("tasks.json")
    while True:
        cmd = input("add/list/done/quit > ").strip()
        if cmd == "add":
            title = input("Title: ")
            store.add(Task(title))
        elif cmd == "list":
            for i, t in enumerate(store.all()):
                print(i, t)
        elif cmd == "done":
            try:
                store.complete(int(input("Task number: ")))
            except (ValueError, IndexError):
                print("Invalid task number")
        elif cmd == "quit":
            break

if __name__ == "__main__":
    run()
