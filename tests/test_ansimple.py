import configparser
import os
import tempfile

import pytest
import yaml

from ansimple import __version__, get_hosts, get_playbook, run_playbook


def test_version():
    assert __version__ == "0.1.0"


valid_playbooks = [
    (
        b"""
---
- hosts: dbservers
  tasks:

    - name: Server uptime
      bash: uptime

    - name: Server disk usage
      bash: df -h
            """,
        [
            {
                "hosts": "dbservers",
                "tasks": [
                    {"name": "Server uptime", "bash": "uptime"},
                    {"name": "Server disk usage", "bash": "df -h"},
                ],
            }
        ],
    ),
    (
        b"""
---
- hosts: dbservers
  tasks:

    - name: Server uptime
      bash: uptime

    - name: Server disk usage
      bash: df -h
- hosts: webservers
  tasks:

    - name: Server CPU info
      bash: lscpu
            """,
        [
            {
                "hosts": "dbservers",
                "tasks": [
                    {"name": "Server uptime", "bash": "uptime"},
                    {"name": "Server disk usage", "bash": "df -h"},
                ],
            },
            {
                "hosts": "webservers",
                "tasks": [
                    {"name": "Server CPU info", "bash": "lscpu"},
                ],
            },
        ],
    ),
]

invalid_playbooks = [
    b"""""",
    b"""
---
- hosts: dbservers
  tasks:

    - name: Server uptime
      bash: uptime

    - bash: df -h
            """,
    b"""
---
- hosts: dbservers
  tasks:

    - name: Server uptime
      bash: uptime

    - name: Server disk usage
            """,
    b"""
---
- tasks:

    - name: Server uptime
      bash: uptime

    - name: Server disk usage
      bash: df -h
            """,
    b"""
---
- hosts: dbservers
            """,
]


@pytest.mark.parametrize("test_input,expected", valid_playbooks)
def test_get_valid_playbook(test_input, expected):
    with tempfile.NamedTemporaryFile() as fp:
        fp.write(test_input)
        fp.seek(0)
        pb = get_playbook(fp.name)
        assert pb == expected


@pytest.mark.parametrize("test_input", invalid_playbooks)
def test_invalid_playbook(test_input):
    with tempfile.NamedTemporaryFile() as fp:
        fp.write(test_input)
        fp.seek(0)
        with pytest.raises(ValueError):
            pb = get_playbook(fp.name)


def test_get_bad_yaml():
    # bad input yaml file
    with tempfile.NamedTemporaryFile() as fp:
        fp.write(
            b"""
---
- hosts: dbservers
  tasks:
][]
    - name: Server uptime
      bash: uptime

    - name: Server disk usage
      bash: df -h
            """
        )
        fp.seek(0)
        with pytest.raises(yaml.YAMLError):
            pb = get_playbook(fp.name)


def test_get_hosts():
    # good input file
    with tempfile.NamedTemporaryFile() as fp:
        fp.write(
            b"""
machine-ungrouped

[dbservers]
localhost
othervm

[webservers]
127.0.0.1

[other]
localhost
            """
        )
        fp.seek(0)
        hosts = get_hosts(fp.name)
        assert hosts == {
            "ungrouped": ["machine-ungrouped"],
            "dbservers": ["localhost", "othervm"],
            "webservers": ["127.0.0.1"],
            "other": ["localhost"],
        }

    # bad input file
    with tempfile.NamedTemporaryFile() as fp:
        fp.write(
            b"""
[dbservers]
localhost
othervm
[dbservers]
localhost
            """
        )
        fp.seek(0)
        with pytest.raises(configparser.DuplicateSectionError):
            hosts = get_hosts(fp.name)


def test_run_playbook(capsys):
    run_playbook(
        [
            {
                "hosts": "dbservers",
                "tasks": [
                    {"name": "Server uptime", "bash": "uptime"},
                    {"name": "Server disk usage", "bash": "df -h"},
                ],
            },
            {
                "hosts": "other",
                "tasks": [
                    {"name": "A command", "bash": "lscpu"},
                ],
            },
        ],
        {
            "dbservers": ["localhost", "othervm"],
            "webservers": ["127.0.0.1"],
            "other": ["localhost"],
        },
    )
    captured = capsys.readouterr()
    assert "===> Running df -h on localhost from dbservers" in captured.out
    assert "===> Running uptime on localhost from dbservers" in captured.out
    assert "===> Running df -h on othervm from dbservers" in captured.out
    assert "===> Running uptime on othervm from dbservers" in captured.out
    assert "Filesystem" in captured.out
    assert "Size" in captured.out
    assert "Avail" in captured.out
    assert "Use%" in captured.out
    assert "Mounted on" in captured.out
    assert f"User {os.environ.get('USER')} can not connect to othervm" in captured.out
    assert "load average" in captured.out
    assert "===> Running lscpu on localhost from other" in captured.out
    assert "Architecture" in captured.out


def test_user(capsys):
    run_playbook(
        [
            {
                "hosts": "dbservers",
                "tasks": [
                    {"name": "Server uptime", "bash": "uptime"},
                ],
            },
        ],
        {
            "dbservers": ["localhost", "othervm"],
            "other": ["yetanother"],
        },
        "some_user",
    )
    captured = capsys.readouterr()
    assert "User some_user can not connect to localhost" in captured.out
    assert "User some_user can not connect to othervm" in captured.out

    del os.environ["USER"]
    run_playbook(
        [
            {
                "hosts": "dbservers",
                "tasks": [
                    {"name": "Server uptime", "bash": "uptime"},
                ],
            },
        ],
        {
            "dbservers": ["localhost", "othervm"],
        },
    )
    captured = capsys.readouterr()
    assert "Missing $USER in env" in captured.out
