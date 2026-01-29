# Copyright 2026 Johan Hallbäck
# See LICENSE file for licensing details.

"""Functions for managing and interacting with the workload.

The intention is that this module could be used outside the context of a charm.
"""

import logging
import subprocess

from charmlibs import apt
from charms.operator_libs_linux.v1.systemd import service_restart, service_enable, service_running
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


def install() -> None:
    """Install the workload (by installing a snap, for example)."""
    # You'll need to implement this function.
    cmd = (
        "curl -1sLf https://dl.cloudsmith.io/public/isc/stork/cfg/setup/bash.deb.sh"
        "| sudo bash"
    )
    try:
        subprocess.run(cmd, shell=True, check=True)
        apt.add_package(["isc-stork-server"])
    except Exception as e:
        # Throw an error to ensure automatic retry later
        logger.error(f"Error installing stork: {str(e)}")
        sys.exit(1)


def start() -> None:
    """Start the workload (by running a commamd, for example)."""
    # We do not start isc-stork-server here, we let systemd handle it
    # once the configuration is rendered.

def get_version() -> str | None:
    """Get the running version of the workload."""
    # If we can't get the version, it is assumed the software isn't installed
    try:
        cmd = ["stork-server", "--version"]
        sp = subprocess.run(cmd, check=True, capture_output=True, encoding="utf-8")
        logger.info(f"stork.get_version()): got version: {sp.stdout}")
        # Remove trailing newline
        return sp.stdout.rstrip()
    except Exception as e:
        logger.warning(f"stork.get_version()): Failed to get version: {e}")
        return None

    return None

def get_status() -> str:
    return "This is the default normal status"

def is_running() -> bool:
    """Let systemd determine if the service is running"""
    return service_running("isc-stork-server")

def db_init(dbconn) -> int:
    """Initialize the database"""
    logger.debug(f": {dbconn}")

    dbinit = ["stork-tool", "db-init",
        f"--db-host={dbconn["dbhost"]}",
        f"--db-name={dbconn["dbname"]}",
        f"--db-user={dbconn["dbuser"]}",
        f"--db-password={dbconn["dbpass"]}"]

    try:
        sp = subprocess.run(dbinit, check=False, capture_output=True, encoding="utf-8")
        logger.info(f"Database creation result: {sp}")
    except Exception as e:
        # Throw an error to ensure automatic retry later
        logger.error(f"Error initializing database: {str(e)}")
        sys.exit(1)

    return 0

def render_and_reload(dbconn) -> int:
    # TODO: This should later only reload on actual config change
    env = Environment(loader=FileSystemLoader("templates"),
            keep_trailing_newline=True, trim_blocks=False)
    stork_server_env_tmpl = env.get_template("server.env.j2")
    
    # TODO: If we have no postgres relation, we must do something here
    stork_server_env = stork_server_env_tmpl.render(
        dbhost=dbconn["dbhost"],
        dbname=dbconn["dbname"],
        dbuser=dbconn["dbuser"],
        dbpass=dbconn["dbpass"],
    )
    with open("/etc/stork/server.env", "w") as file:
        file.write(stork_server_env)

    # reload/restart in some way here
    service_enable("isc-stork-server")
    service_restart("isc-stork-server")
