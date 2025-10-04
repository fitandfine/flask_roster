

# Test-Driven Development (TDD) in Python — Complete Beginner’s Guide

## Table of Contents

1. [Introduction](#introduction)
2. [What is TDD?](#what-is-tdd)
3. [Benefits of TDD](#benefits-of-tdd)
4. [Types of Tests](#types-of-tests)
5. [Python Testing Tools](#python-testing-tools)
6. [Folder Structure for Tests](#folder-structure-for-tests)
7. [Writing Your First Test](#writing-your-first-test)
8. [Understanding Pytest](#understanding-pytest)
9. [Fixtures and Setup/Teardown](#fixtures-and-setupteardown)
10. [Testing Functions](#testing-functions)
11. [Testing Classes](#testing-classes)
12. [Testing Flask Applications](#testing-flask-applications)
13. [Testing Databases](#testing-databases)
14. [Testing File I/O](#testing-file-io)
15. [Best Practices](#best-practices)
16. [Step-by-Step TDD Workflow](#step-by-step-tdd-workflow)
17. [Common Mistakes](#common-mistakes)
18. [Conclusion](#conclusion)

---

## Introduction

Test-Driven Development (TDD) is a **programming methodology** where tests are written **before the code**.
It is a **design-first approach**: you think about **what your code should do** before implementing it.

> The core philosophy of TDD:
> “Red → Green → Refactor”

* **Red:** Write a test and see it fail.
* **Green:** Write code to make the test pass.
* **Refactor:** Clean your code while keeping tests green.

TDD helps ensure your code is **correct, maintainable, and well-structured**.

---

## What is TDD?

TDD is not just about testing; it is about **designing your code with testing in mind**.

### Key Principles:

1. **Write a test before the code.**
2. **Keep tests small and focused.**
3. **Test one behavior per test.**
4. **Refactor safely.** Tests act as safety nets.

---

## Benefits of TDD

* **Fewer bugs:** Every feature is covered by a test.
* **Better code structure:** Forces modular, testable design.
* **Faster debugging:** Failing tests pinpoint the problem.
* **Living documentation:** Tests explain what the code does.

---

## Types of Tests

| Test Type                 | Purpose                                         | Example                                   |
| ------------------------- | ----------------------------------------------- | ----------------------------------------- |
| **Unit Test**             | Test a single function/class in isolation       | `add(2,3) → 5`                            |
| **Integration Test**      | Test multiple components together               | Flask route querying database             |
| **Functional Test**       | Test application behavior from user perspective | Login flow, form submission               |
| **End-to-End (E2E) Test** | Simulate full system usage                      | Register → Login → Create Roster → Logout |

**TDD primarily uses unit and integration tests.**

---

## Python Testing Tools

| Tool           | Use                                                               |
| -------------- | ----------------------------------------------------------------- |
| `pytest`       | Popular testing framework, supports fixtures and parametric tests |
| `unittest`     | Built-in Python testing module                                    |
| `pytest-cov`   | Measure test coverage                                             |
| `pytest-flask` | Test Flask apps with fixtures                                     |
| `mock`         | Mock external dependencies like APIs or databases                 |

**Install with:**

```bash
pip install pytest pytest-cov pytest-flask
```

---

## Folder Structure for Tests

A standard Python project with TDD:

```
project/
│
├─ app/
│   ├─ __init__.py
│   ├─ routes.py
│   ├─ database.py
│   └─ utils.py
│
├─ tests/
│   ├─ __init__.py
│   ├─ test_routes.py
│   ├─ test_database.py
│   └─ test_utils.py
│
├─ roster.db
└─ run.py
```

* `tests/` folder contains **all test scripts**.
* Test filenames **must start with `test_`** for `pytest` to discover them.
* Test functions **must start with `test_`**.

---

## Writing Your First Test

**1. Example function:**

```python
# app/utils.py
def add(a, b):
    return a + b
```

**2. Corresponding test:**

```python
# tests/test_utils.py
from app.utils import add

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
```

**3. Run test:**

```bash
pytest -v
```

**Output:**

* Red: Test fails if function doesn’t exist.
* Green: Test passes when function is implemented.

---

## Understanding Pytest

* `pytest` discovers test files automatically.
* Functions starting with `test_` are executed.
* Assertions are simple: `assert expression == expected`.
* Can run **all tests**: `pytest`
* Can run **one test file**: `pytest tests/test_utils.py`

---

## Fixtures and Setup/Teardown

**Fixture:** A reusable setup for tests.
Useful for databases, Flask apps, or shared objects.

```python
# tests/conftest.py
import pytest
from app import create_app

@pytest.fixture
def app():
    app = create_app({"TESTING": True})
    return app

@pytest.fixture
def client(app):
    return app.test_client()
```

* `app` fixture creates a Flask app in **testing mode**.
* `client` fixture provides a **test client** for HTTP requests.

**Usage:**

```python
def test_home_redirect(client):
    rv = client.get("/")
    assert rv.status_code == 302  # Redirect to login
```

---

## Testing Functions

```python
# app/math_utils.py
def multiply(a, b):
    return a * b

# tests/test_math_utils.py
from app.math_utils import multiply

def test_multiply():
    assert multiply(2, 3) == 6
    assert multiply(0, 100) == 0
```

* Isolated function → unit test.
* Easy to debug and fast to run.

---

## Testing Classes

```python
# app/user.py
class User:
    def __init__(self, username):
        self.username = username

    def greet(self):
        return f"Hello, {self.username}!"
```

**Test:**

```python
# tests/test_user.py
from app.user import User

def test_user_greet():
    u = User("Alice")
    assert u.greet() == "Hello, Alice!"
```

* Tests object behavior, not implementation details.
* Allows **safe refactoring**.

---

## Testing Flask Applications

### Example Route:

```python
# app/routes.py
from flask import Flask, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "dev"

@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    return "Welcome"

@app.route("/login")
def login():
    return "Login Page"
```

### Test:

```python
# tests/test_routes.py
import pytest
from app.routes import app as flask_app

@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    return flask_app.test_client()

def test_index_redirect(client):
    rv = client.get("/")
    assert rv.status_code == 302
    assert "/login" in rv.location
```

* `client.get()` simulates **HTTP GET** requests.
* Can test **POST, redirects, flash messages**, etc.

---

## Testing Databases

* Use **temporary or in-memory database**.
* Example: SQLite `:memory:` database.

```python
# tests/test_database.py
import sqlite3
import pytest
from app.database import create_tables

@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    yield conn
    conn.close()

def test_insert_employee(db):
    cursor = db.cursor()
    cursor.execute("INSERT INTO staff (name, email) VALUES (?, ?)", ("Alice", "alice@test.com"))
    db.commit()

    cursor.execute("SELECT * FROM staff WHERE name=?", ("Alice",))
    employee = cursor.fetchone()
    assert employee["email"] == "alice@test.com"
```

* Keeps tests **isolated**.
* Avoids polluting production database.

---

## Testing File I/O

```python
# tests/test_files.py
import tempfile
import os

def test_write_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test.txt")
        with open(file_path, "w") as f:
            f.write("Hello TDD")
        assert os.path.exists(file_path)
        with open(file_path) as f:
            content = f.read()
        assert content == "Hello TDD"
```

* Use `tempfile` to avoid polluting real directories.
* Ensures tests are repeatable.

---

## Best Practices

1. **Small, isolated tests** → easier to debug.
2. **One assertion per test** → clear failure.
3. **Independent tests** → do not rely on order.
4. **Use fixtures** → avoid repetitive setup.
5. **Mock external services** → APIs, files, email.
6. **Test behavior, not implementation.**

---

## Step-by-Step TDD Workflow

1. **Write a failing test (Red)**
2. **Write minimal code to pass the test (Green)**
3. **Run all tests**
4. **Refactor code**
5. **Repeat**

Example:

```python
# Step 1: Test
def test_add():
    assert add(2, 3) == 5

# Step 2: Code
def add(a, b):
    return a + b

# Step 3: Run test (should pass)
```

---

## Common Mistakes

| Mistake                | Solution                       |
| ---------------------- | ------------------------------ |
| Using production DB    | Use `:memory:` or temporary DB |
| Complex tests          | Keep one behavior per test     |
| Skipping failing tests | Fix root cause, don’t ignore   |
| Shared state           | Reset fixtures per test        |
| Ignoring file cleanup  | Use `tempfile` or teardown     |

---

## Conclusion

TDD in Python:

* Makes **your code safer and modular**
* Gives **confidence to refactor**
* Creates **living documentation**
* Works for **functions, classes, Flask routes, databases, and files**

> Start small. Write one failing test. Make it pass. Refactor. Repeat. TDD is a habit, not a one-time task.

---

