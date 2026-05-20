#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Package utilitaires NobaraForgeKDE."""

from .state_manager import (
    StateManager, StateEntry, StateError, get_state_manager,
    ACTION_DNF_INSTALL, ACTION_DNF_REMOVE,
    ACTION_FLATPAK_INSTALL, ACTION_EXTERNAL_INSTALL,
)

from .subprocess_utils import (
    run_command, run_sudo_command,
    check_package_installed, check_command_exists,
    dnf_install, dnf_remove, dnf_update, dnf_upgrade, system_update,
    flatpak_install, flatpak_list, check_flatpak_installed,
    git_clone, run_bash_script, run_python_script,
    timeshift_available, timeshift_create_snapshot,
    CommandResult
)

from .logging_utils import (
    Logger, Colors,
    info, success, warn, error, debug, step, header,
    log_info, log_success, log_warn, log_error,
    log_debug, log_step, log_header,
    set_log_file
)

from .file_utils import (
    load_json, save_json, load_package_list,
    ensure_directory, safe_read_file, safe_write_file,
    get_user_home, find_file_in_paths,
    ConfigManager, ConfigError
)

from .validation import (
    validate_config,
    validate_install_config, validate_remove_config,
    validate_flatpak_config, validate_external_config,
    validate_theme_config, validate_all_configs,
    ConfigValidationError
)

from schemas import (
    Package, PackageList,
    FlatpakApp, FlatpakList,
    ExternalPackage, ExternalPackageList,
    Theme, ThemeList
)
