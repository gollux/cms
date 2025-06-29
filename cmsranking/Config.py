#!/usr/bin/env python3

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2011-2016 Luca Wehrstedt <luca.wehrstedt@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import errno
import logging
import os
import sys
import tomllib
import typing

import pkg_resources

from cmsranking.Logger import add_file_handler


logger = logging.getLogger(__name__)


CMS_RANKING_CONFIG_ENV_VAR = "CMS_RANKING_CONFIG"


class Config:
    """An object holding the current configuration.

    """
    def __init__(self):
        """Fill this object with the default values for each key.

        """
        # Connection.
        self.bind_address = ''
        self.http_port: int | None = 8890
        self.https_port: int | None = None
        self.https_certfile: str | None = None
        self.https_keyfile: str | None = None
        # TODO unused???
        self.timeout = 600  # 10 minutes (in seconds)

        # Authentication.
        self.realm_name = 'Scoreboard'
        self.username = 'usern4me'
        self.password = 'passw0rd'

        # Buffers
        self.buffer_size = 100  # Needs to be strictly positive.

        self.web_dir = pkg_resources.resource_filename("cmsranking", "static")
        self.log_dir = os.path.join("/", "var", "local", "log", "cms", "ranking")
        self.lib_dir = os.path.join("/", "var", "local", "lib", "cms", "ranking")
        self.conf_paths = [
            os.path.join("/", "usr", "local", "etc", "cms_ranking.toml"),
            os.path.join("/", "etc", "cms_ranking.toml"),
        ]

        # Allow users to override config file path using environment
        # variable 'CMS_RANKING_CONFIG'.
        if CMS_RANKING_CONFIG_ENV_VAR in os.environ:
            self.conf_paths = [os.environ[CMS_RANKING_CONFIG_ENV_VAR]] \
                + self.conf_paths

    def get(self, key):
        """Get the config value for the given key.

        """
        return getattr(self, key)

    def load(self, config_override_fobj=None):
        """Look for config files on disk and load them.

        """
        # If a command-line override is given it is used exclusively.
        if config_override_fobj is not None:
            if not self._load_one(config_override_fobj):
                sys.exit(1)
        else:
            if not self._load_many(self.conf_paths):
                sys.exit(1)

        try:
            os.makedirs(self.lib_dir)
        except OSError:
            pass  # We assume the directory already exists...

        try:
            os.makedirs(self.web_dir)
        except OSError:
            pass  # We assume the directory already exists...

        try:
            os.makedirs(self.log_dir)
        except OSError:
            pass  # We assume the directory already exists...

        add_file_handler(self.log_dir)

    def _load_many(self, conf_paths: list[str]) -> bool:
        """Load the first existing config file among the given ones.

        Take a list of paths where config files may reside and attempt
        to load the first one that exists.

        conf_paths: paths of config file candidates, from most
            to least prioritary.
        returns: whether loading was successful.

        """
        for conf_path in conf_paths:
            try:
                with open(conf_path, "rb") as conf_fobj:
                    logger.info("Using config file %s.", conf_path)
                    return self._load_one(conf_fobj)
            except FileNotFoundError:
                # If it doesn't exist we just skip to the next one.
                pass
            except OSError as error:
                logger.critical("Unable to access config file %s: [%s] %s.",
                                conf_path, errno.errorcode[error.errno],
                                os.strerror(error.errno))
                return False
        logger.warning("No config file found, using hardcoded defaults.")
        return True

    def _load_one(self, conf_fobj: typing.BinaryIO) -> bool:
        """Populate config parameters from the given file.

        Parse it as TOML and store in self all configuration properties
        it defines. Log critical message and return False if anything
        goes wrong or seems odd.

        conf_fobj: the config file.
        returns: whether parsing was successful.

        """
        # Parse config file.
        try:
            data = tomllib.load(conf_fobj)
        except ValueError:
            logger.critical("Config file is invalid TOML.")
            return False

        # Store every config property.
        for key, value in data.items():
            if not hasattr(self, key):
                logger.critical("Invalid field %s in config file, maybe a "
                                "typo?", key)
                return False
            setattr(self, key, value)
        return True
