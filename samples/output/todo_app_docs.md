# todo_app — Technical Documentation

## 1. Project Overview
`todo_app` is a command-line interface (CLI) application for tracking personal tasks. It allows users to create new to-do items, view existing items with their completion status, and mark specific items as complete using zero-based indices. All tasks are serialized and persisted locally in a JSON file between sessions. The application runs through an interactive command loop until explicitly exited.

## 2. Architecture and File Structure
The project follows a modular architecture separating data representation, data persistence, and the user interface. `todo_app/models.py` defines the domain entity, `todo_app/storage.py` handles reading and writing task data to disk, and `todo_app/main.py` drives the interactive CLI loop.

| File | Responsibility |
| --- | --- |
| `todo_app/main.py` | CLI entry point and interactive loop; handles user input and orchestrates task operations. |
| `todo_app/models.py` | Defines the `Task` dataclass, its string formatting, and dictionary serialization. |
| `todo_app/storage.py` | Manages file-based JSON persistence and in-memory state via `TaskStore`. |

## 3. Function and Class Reference

### `todo_app/models.py`

#### `Task`
A dataclass representing a single to-do item.
* **Attributes**:
  * `title` (`str`): The description or title of the task.
  * `done` (`bool`): The completion status of the task. Defaults to `False`.
* **Methods**:
  * `to_dict()`: Converts the `Task` instance into a standard dictionary using `dataclasses.asdict`.
    * **Parameters**: None.
    * **Return value**: `dict` containing `title` and `done`.
  * `__str__()`: Formats the task as a string with a checkbox indicating completion status.
    * **Parameters**: None.
    * **Return value**: `str` formatted as `"[x] <title>"` if completed or `"[ ] <title>"` if incomplete.

---

### `todo_app/storage.py`

#### `TaskStore`
Handles loading, modifying, and persisting a collection of `Task` objects to a JSON file.
* **Methods**:
  * `__init__(path: str)`: Initializes the store with the specified file path and loads existing tasks into memory.
    * **Parameters**: `path` (`str`) — Path to the JSON persistence file.
    * **Return value**: `None`.
  * `_load()`: Reads JSON data from the file system and converts each entry into a `Task` instance.
    * **Parameters**: None.
    * **Return value**: `list` of `Task` objects. Returns an empty list if the file does not exist or contains invalid JSON.
  * `_save()`: Serializes all tasks in `self.tasks` into dictionary format and writes them to the file at `self.path` with an indentation of 2.
    * **Parameters**: None.
    * **Return value**: `None`.
  * `add(task: Task)`: Appends a `Task` to the internal list and saves changes to disk.
    * **Parameters**: `task` (`Task`) — The task to store.
    * **Return value**: `None`.
  * `all()`: Returns the in-memory list of tasks.
    * **Parameters**: None.
    * **Return value**: `list` containing all `Task` objects.
  * `complete(index: int)`: Marks the task at the specified index as done (`done = True`) and saves changes to disk.
    * **Parameters**: `index` (`int`) — The index of the task to mark as complete.
    * **Return value**: `None`.

---

### `todo_app/main.py`

#### `run()`
Main interactive loop for the application.
* **Parameters**: None.
* **Return value**: `None`.
* **Notable behaviour**: Instantiates a `TaskStore` using `"tasks.json"`. Continuously prompts the user with `add/list/done/quit > ` and executes corresponding operations until `"quit"` is entered.

## 4. Execution and Data Flow
1. **Startup**: Execution begins in `todo_app/main.py` inside `run()` when the file is run as `__main__`.
2. **Initialization**: `run()` calls `TaskStore("tasks.json")` in `todo_app/storage.py`.
3. **Data Loading**: `TaskStore.__init__()` invokes `_load()`. If `"tasks.json"` exists, it parses the JSON data and unpacks each record into a `Task()` model from `todo_app/models.py`. If the file does not exist or fails JSON decoding, an empty list is loaded.
4. **Command Processing**: `run()` enters a `while True` loop listening for user commands:
   * **`add`**: Prompts the user for a title, instantiates `Task(title)`, and calls `store.add()`. `TaskStore.add()` appends the task to `self.tasks` and invokes `_save()`, which serializes the tasks with `Task.to_dict()` and writes them back to `"tasks.json"`.
   * **`list`**: Calls `store.all()` to retrieve the list of `Task` instances and prints each item with its index using `Task.__str__()`.
   * **`done`**: Prompts for a task number and invokes `store.complete(index)`. `TaskStore.complete()` updates the task's `done` attribute to `True` and calls `_save()` to persist the update.
   * **`quit`**: Breaks the loop and terminates execution.

## 5. Dependencies
| Package | Purpose in this project |
| --- | --- |
| *None detected* | The project uses only Python standard library modules (`dataclasses`, `json`, `os`). |

## 6. Error Handling and Limitations
* **Corrupt or Missing Storage**: In `TaskStore._load()`, if the storage file does not exist (`os.path.exists()`), it gracefully defaults to an empty list. If the file contains malformed JSON, `json.JSONDecodeError` is caught and an empty list is returned.
* **CLI Input Validation**: In `run()`, when the `done` command is executed, `ValueError` (if input cannot be parsed as an integer) and `IndexError` (if the integer exceeds the bounds of `self.tasks`) are caught, printing `"Invalid task number"`.
* **Negative Indexing**: Python allows negative list indexing. Supplying a negative number (e.g., `-1`) to the `done` command does not raise an `IndexError` and will modify tasks from the end of the list without validation.
* **I/O and Permission Errors**: `TaskStore._save()` does not catch file system exceptions (such as `PermissionError` or `OSError`).
* **Unrecognized Commands**: Entering a command other than `add`, `list`, `done`, or `quit` is ignored without any user feedback or warning.
* **Empty Titles**: The `add` command does not validate whether the entered title string is empty or whitespace.

## 7. Notes on Analysis Coverage
* No files were truncated or omitted; all 3 files identified in the code map (`todo_app/main.py`, `todo_app/models.py`, `todo_app/storage.py`) were provided and fully analyzed.
* Configuration options, build systems, or deployment configurations outside of the provided source files are: Not determinable from the provided code.