"""Interactive entry point for one-time ADMIN bootstrap."""

import getpass
import sys
from collections.abc import Callable
from typing import TextIO

from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.services.bootstrap_admin_service import (
    AdminAlreadyExistsError,
    BootstrapAdminError,
    BootstrapAdminService,
)


def main(
    *,
    input_fn: Callable[[str], str] = input,
    password_fn: Callable[[str], str] = getpass.getpass,
    session_factory: sessionmaker[Session] = SessionLocal,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    argv: list[str] | None = None,
) -> int:
    """Run an interactive bootstrap without accepting password arguments."""
    output = stdout or sys.stdout
    error_output = stderr or sys.stderr
    command_arguments = sys.argv[1:] if argv is None else argv
    if command_arguments:
        print(
            "Bootstrap refused: command-line arguments are not supported.",
            file=error_output,
        )
        return 2

    try:
        with session_factory() as session:
            BootstrapAdminService(session).assert_bootstrap_available()
    except AdminAlreadyExistsError as exc:
        print(f"Bootstrap refused: {exc}", file=error_output)
        return 1
    except BootstrapAdminError as exc:
        print(f"Bootstrap refused: {exc}", file=error_output)
        return 1
    except Exception:
        print(
            "Bootstrap failed due to an unexpected error.",
            file=error_output,
        )
        return 1

    username = input_fn("Username: ")
    real_name = input_fn("Real name: ")
    password = password_fn("Password: ")
    password_confirmation = password_fn("Confirm password: ")
    if password != password_confirmation:
        print("Bootstrap refused: passwords do not match.", file=error_output)
        return 1

    try:
        with session_factory() as session:
            result = BootstrapAdminService(session).bootstrap(
                username=username,
                real_name=real_name,
                password=password,
            )
    except BootstrapAdminError as exc:
        print(f"Bootstrap refused: {exc}", file=error_output)
        return 1
    except ValidationError:
        print(
            "Bootstrap refused: invalid username, real name, or password.",
            file=error_output,
        )
        return 1
    except Exception:
        print(
            "Bootstrap failed due to an unexpected error.",
            file=error_output,
        )
        return 1

    print("Bootstrap admin created successfully.", file=output)
    print(f"Username: {result.user.username}", file=output)
    print("Role: ADMIN", file=output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
