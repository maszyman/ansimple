import configparser
import os
import sys
from collections import defaultdict
from pathlib import Path
from subprocess import CalledProcessError, run

import click
import yaml


def get_playbook(path: Path) -> list:
    """Reads the playbook in YAML from path.
    Args:
      pathlib.Path: path to playbook in YAML file
    Returns:
      list: playbook
    """
    plays = []
    with open(path) as infile:
        plays = yaml.safe_load(infile.read())
    # let's validate the playbook
    if not plays:
        raise ValueError("Empty playbook")
    if "hosts" not in plays[0]:
        raise ValueError("Invalid playbook, missing hosts")
    if "tasks" not in plays[0]:
        raise ValueError("Invalid playbook, missing tasks")
    for task in plays[0]["tasks"]:
        if "name" not in task:
            raise ValueError("Invalid playbook, missing description of the task")
        if "bash" not in task:
            raise ValueError("Invalid playbook, missing bash command to run")
    return plays


def get_hosts(path: Path) -> dict:
    """Reads the hosts inventory file in INI format.
    Args:
      pathlib.Path: path to hosts inventory INI file
    Returns:
      dict: hosts grouped by key
    """
    with open(path, "r") as infile:
        # configparser does not allow for ungrouped items
        # but ansible does: https://docs.ansible.com/ansible/latest/user_guide/intro_inventory.html
        config_string = "[ungrouped]\n" + infile.read()
    config = configparser.ConfigParser(allow_no_value=True)
    config.read_string(config_string)
    grouped_hosts = defaultdict(list)
    for section in config.sections():
        for item in config[section]:
            grouped_hosts[section].append(item)
    return dict(grouped_hosts)


def run_playbook(playbook: list = None, hosts: dict = None, user: str = None) -> None:
    """Run commands from playbook on all hosts from given group.
    Prints the output of the commands to the standard output.
    Args:
      list: playbook
      dict: hosts
    Returns:
      None
    """

    if playbook is None:
        playbook = []
    if hosts is None:
        hosts = {}
    if user is None:
        try:
            user = os.environ["USER"]
        except KeyError:
            sys.stdout.write("Missing $USER in env\n")
            return

    for hostgroup in playbook:
        for host in hosts.get(hostgroup.get("hosts"), []):
            for task in hostgroup.get("tasks", {}):
                try:
                    sys.stdout.write(
                        f"===> Running {task['bash']} on {host} from {hostgroup['hosts']}\n"
                    )
                    # check if a user can connect to the node without the password
                    cmd = [
                        "ssh",
                        "-o",
                        "PasswordAuthentication=no",
                        "-o",
                        "BatchMode=yes",
                        f"{user}@{host}",
                        "exit",
                    ]
                    if run(cmd).returncode:
                        sys.stdout.write(f"User {user} can not connect to {host}\n")
                        continue
                    cmd = ["ssh", f"{user}@{host}"] + task["bash"].split()
                    try:
                        output = run(cmd, capture_output=True, check=True)
                        sys.stdout.writelines(output.stdout.decode())
                    except CalledProcessError as cpe:
                        sys.stdout.writelines(cpe.stderr.decode())
                except KeyError:
                    # we ignore missing `bash` entry
                    pass


@click.command()
@click.option(
    "--hosts",
    default="/etc/ansible/hosts",
    help="Name of the hosts input file, by default /etc/ansible/hosts",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--playbook",
    default="./playbook.yaml",
    help="Name of the YAML input file with the playbook, by default ./playbook.yaml",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--user",
    default=os.environ.get("USER"),
    help="Username used to connect to the remote nodes, by default $USER",
    type=click.STRING,
)
def main(user, playbook, hosts):
    """Main script to run the playbook"""
    run_playbook(get_playbook(playbook), get_hosts(hosts), user)
