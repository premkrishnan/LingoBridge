# ============================================================
# FILE: utils/logger.py
#
# PURPOSE:
#   Provides a centralised logger factory for the entire project.
#   All service and utility modules call get_logger(__name__) to
#   obtain a consistently formatted logger instance.
#   Using one factory ensures every module's log lines share the
#   same timestamp format and level alignment.
#
# INPUTS:
#   - name (str): logger name, typically __name__ of the caller
#
# OUTPUTS:
#   - logging.Logger: configured logger instance
#
# DEPENDENCIES:
#   - logging (Python standard library)
#
# CALLED BY:
#   - All service modules (services/*.py)
#   - All utility modules (utils/*.py)
#   - main.py
#
# AUTHOR: Clip Project
# LAST UPDATED: 2026-05-23
# ============================================================

import logging


# Log format follows SKILL.md Section 7.3:
#   [HH:MM:SS] LEVEL  module_name — message
#
# %(name)-12s left-pads the module name to 12 chars so the "—"
# separator stays vertically aligned across different module names.
_LOG_FORMAT = "[%(asctime)s] %(levelname)-8s %(name)-12s — %(message)s"
_TIME_FORMAT = "%H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger for the calling module.

    Steps:
      1. Retrieve (or create) a logger with the given name.
      2. If the logger already has handlers, return it as-is to
         avoid duplicate log lines when get_logger is called
         multiple times in the same process.
      3. Set the log level to INFO (debug messages are hidden
         unless explicitly changed during development).
      4. Attach a StreamHandler so logs appear in the terminal.
      5. Apply the shared format defined at module level.

    Args:
        name (str): Logger name — always pass __name__ so log lines
                    show the originating module automatically.
                    Example: "services.transcribe"

    Returns:
        logging.Logger: Ready-to-use logger instance.
                        Example output:
                        [14:32:05] INFO     services.transcribe — Transcript: 你好

    Example:
        from utils.logger import get_logger
        logger = get_logger(__name__)

        logger.info("Recording started.")
        logger.error("Ollama unreachable.\nFix: run 'ollama serve'")
    """
    logger = logging.getLogger(name)

    # Guard: if handlers are already attached, the logger was already
    # configured by a previous call — return it without adding more
    # handlers (which would print every line twice).
    if logger.handlers:
        return logger

    # INFO shows all normal pipeline steps.
    # Set to logging.DEBUG locally when diagnosing a specific issue.
    logger.setLevel(logging.INFO)

    # Console handler — writes to stdout so the owner can watch
    # the pipeline in real time from the terminal.
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_TIME_FORMAT)
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    # Prevent log records from bubbling up to the root logger,
    # which could produce duplicate output if the root logger also
    # has handlers configured elsewhere.
    logger.propagate = False

    return logger
