# query-formatter
## Easy way to format sql templates in python
![img](https://github.com/NikitaKokarev/query-formatter/blob/3e0ededf4c74024095a72071f25951dd2ef88a0c/query_formatter/images/select1.png)
![img](https://github.com/NikitaKokarev/query-formatter/blob/3e0ededf4c74024095a72071f25951dd2ef88a0c/query_formatter/images/select2.png)
___
## How to use:
Write your SQL templates in string format and join them with this formatter using string literals in the templates body.
___
## Examples:
Get the formatting template by template with literal ***'if'***. In that case, input value is checked with pythonic if and constant string was added to the template with a condition:
```python
from query_formatter import SqlEscaper, QueryFormatter

tmpl =  """
    SELECT *
    FROM table1
    WHERE col_name1 = 1
    {input_value:if:
        OR
        col_name2 = 10 AND
        EXISTS(
            SELECT t2.id
            FROM table2 t2
            WHERE t2.col_name1 = 100
            LIMIT 1
        )
    }
    OR col_name3 = 100
"""
input_value = 10

QF = QueryFormatter(SqlEscaper())
ans = QF.format(tmpl, input_value=input_value)

>>> print(ans)

SELECT *
FROM table1
WHERE col_name1 = 1

    OR
    col_name2 = 10 AND
    EXISTS(
        SELECT t2.id
        FROM table2 t2
        WHERE t2.col_name1 = 100
        LIMIT 1
    )

OR col_name3 = 100
```
In the next case, input value is checked to in the sequence of values and constant string was added to the template with a condition:
```python
from query_formatter import SqlEscaper, QueryFormatter

tmpl =  """
    SELECT *
    FROM table1
    WHERE col_name1 = 1
    {input_value:in:10,20,30,100
        OR col_name2 = 10
    }
"""
input_value = 10

QF = QueryFormatter(SqlEscaper())
ans = QF.format(tmpl, input_value=input_value)

>>> print(ans)

SELECT *
    FROM table1
    WHERE col_name1 = 1

        OR col_name2 = 10
```
___
## Install package:
```
pip3 install git+https://github.com/NikitaKokarev/query-formatter
```
___
## Get package from cloned repository:
## 1. Clone the repository from GitHub:

```bash
git clone https://github.com/username/repository.git
```

Optional: Replace `username` with the GitHub username and `repository` with the repository name.

## 2. Navigate to the Repository Directory

Navigate into the directory created after cloning:

```bash
cd repository
```

Replace `repository` with the directory name you see after cloning.

## 3. Install the Library into `site-packages`

Now that you are inside the repository directory, install it into `site-packages` using `pip`:

```bash
pip install .
```

The `.` symbol here tells `pip` to reference the current directory (where the `setup.py` or equivalent installation file resides).

## 4. Verify the Installation

To ensure the library was successfully installed, import it into your Python script or interactive shell:

```python
import library_name
```

Replace `library_name` with the name of the library.
___
## Run autotests:
```python
# -*- coding: utf-8 -*-
""" Autotests runner
"""
## How to find the location of Python site-packages:
# import site
# print(site.getsitepackages())

from query_formatter.unit_tests import unittest_main


unittest_main()
```
