Ansimple
========

Simple version of Ansible, specifically the ansible-playbook program.

# Features

The program allows to run the tasks from the playbook specified in YAML file (by default `playbook.yaml` in current directory or specified with `--playbook`). Tasks are run on all the hosts from the group determined in the playbook. Available hosts are defined in INI file, by default taken from `/etc/ansible/hosts` or specified with `--hosts`.

# Setup

## Input files
Before running the playbook, please make sure that you defined the hosts in INI file, and the playbook in YAML file.

## SSH
You need to set up the password-less `ssh` connection so that `ansimple` can connect to the nodes specified in the hosts file. Please generate the keys and propagate the public one to the nodes. For example, for `localhost`:
```bash
ssh-keygen -t rsa
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
chmod og-wx ~/.ssh/authorized_keys
```
Test the connection with `ssh username@host`.

# Usage

- First, install the package:
```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install .
```
- To run the ansimple with the provided, exemplary input files:
```bash
ansimple --hosts ./data/hosts --playbook ./data/playbook.yaml
```
By default, the username `$USER` is used to connect to the nodes. You may tweak it, passing `--user` flag and the relevant name.

# Development:

This code makes use of [Poetry](https://python-poetry.org/) to build, test, and package the project.

## Testing

To run the tests:
```bash
poetry run pytest .
```

## Code quality

The code is formatted using [black](https://black.readthedocs.io/en/stable/). Imports are sorted with [isort](https://github.com/PyCQA/isort). The code is linted with [mypy](http://mypy-lang.org/). All those tools run with [pre-commit](https://pre-commit.com/).
