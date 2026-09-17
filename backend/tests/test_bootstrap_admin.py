"""One-time bootstrap ADMIN service and CLI security tests."""

from io import StringIO

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.cli.bootstrap_admin import main
from app.domain.rbac_catalog import PERMISSION_DEFINITIONS
from app.models.rbac import Role, UserRole
from app.models.user import User
from app.security.password import hash_password
from app.services.bootstrap_admin_service import (
    AdminAlreadyExistsError,
    BootstrapAdminError,
    BootstrapAdminService,
    ExistingUserPasswordError,
)
from app.domain.exceptions import BusinessRuleError
from app.services.rbac_service import RBACService


PASSWORD = "Bootstrap-Test-Password-123!"


def _admin_count(session: Session) -> int:
    return int(
        session.scalar(
            select(func.count(UserRole.id))
            .join(Role, Role.id == UserRole.role_id)
            .where(Role.name == "ADMIN")
        )
        or 0
    )


def test_bootstrap_creates_first_admin_with_all_permissions(
    db_session: Session,
) -> None:
    result = BootstrapAdminService(db_session).bootstrap(
        username="BootstrapAdmin",
        real_name="系统管理员",
        password=PASSWORD,
    )

    assert result.user_created is True
    assert result.user.username == "bootstrapadmin"
    assert _admin_count(db_session) == 1
    permission_codes = {
        item.code
        for item in RBACService(db_session).list_user_permissions(result.user.id)
    }
    assert permission_codes == {code for code, _ in PERMISSION_DEFINITIONS}


def test_second_bootstrap_is_refused_without_creating_another_admin(
    db_session: Session,
) -> None:
    service = BootstrapAdminService(db_session)
    service.bootstrap(
        username="first_admin",
        real_name="首个管理员",
        password=PASSWORD,
    )

    with pytest.raises(AdminAlreadyExistsError):
        service.bootstrap(
            username="second_admin",
            real_name="第二管理员",
            password=PASSWORD,
        )

    assert _admin_count(db_session) == 1
    assert db_session.scalar(
        select(User).where(User.username == "second_admin")
    ) is None


def test_last_admin_role_cannot_be_removed_through_rbac_service(
    db_session: Session,
) -> None:
    result = BootstrapAdminService(db_session).bootstrap(
        username="protected_admin",
        real_name="受保护管理员",
        password=PASSWORD,
    )
    admin_role = db_session.scalar(select(Role).where(Role.name == "ADMIN"))
    assert admin_role is not None

    with pytest.raises(BusinessRuleError, match="最后一个管理员"):
        RBACService(db_session).remove_role(result.user.id, admin_role.id)

    assert _admin_count(db_session) == 1


def test_existing_user_can_be_promoted_with_correct_password(
    db_session: Session,
) -> None:
    user = User(
        username="existing_user",
        password_hash=hash_password(PASSWORD),
        real_name="已有用户",
    )
    db_session.add(user)
    db_session.commit()
    original_hash = user.password_hash

    result = BootstrapAdminService(db_session).bootstrap(
        username="existing_user",
        real_name="不会覆盖",
        password=PASSWORD,
    )

    assert result.user_created is False
    assert result.user.id == user.id
    assert result.user.password_hash == original_hash
    assert result.user.real_name == "已有用户"
    assert _admin_count(db_session) == 1


def test_existing_user_wrong_password_cannot_be_promoted(
    db_session: Session,
) -> None:
    user = User(
        username="existing_user",
        password_hash=hash_password(PASSWORD),
        real_name="已有用户",
    )
    db_session.add(user)
    db_session.commit()

    with pytest.raises(ExistingUserPasswordError):
        BootstrapAdminService(db_session).bootstrap(
            username="existing_user",
            real_name="已有用户",
            password="Wrong-Password-123!",
        )

    assert _admin_count(db_session) == 0


def test_user_creation_rolls_back_when_role_assignment_fails(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_assignment(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise IntegrityError("forced assignment failure", {}, RuntimeError())

    monkeypatch.setattr(RBACService, "assign_role", fail_assignment)

    with pytest.raises(BootstrapAdminError):
        BootstrapAdminService(db_session).bootstrap(
            username="rolled_back_admin",
            real_name="事务测试",
            password=PASSWORD,
        )

    assert db_session.scalar(
        select(User).where(User.username == "rolled_back_admin")
    ) is None
    assert _admin_count(db_session) == 0


def test_cli_uses_hidden_password_and_never_prints_secret(db_engine: Engine) -> None:
    factory = sessionmaker(bind=db_engine, expire_on_commit=False)
    answers = iter(["cli_admin", "CLI 管理员"])
    passwords = iter([PASSWORD, PASSWORD])
    output = StringIO()
    errors = StringIO()

    exit_code = main(
        input_fn=lambda prompt: next(answers),
        password_fn=lambda prompt: next(passwords),
        session_factory=factory,
        stdout=output,
        stderr=errors,
        argv=[],
    )

    serialized = output.getvalue() + errors.getvalue()
    assert exit_code == 0
    assert "Bootstrap admin created successfully." in serialized
    assert "Username: cli_admin" in serialized
    assert "Role: ADMIN" in serialized
    assert PASSWORD not in serialized
    assert "password_hash" not in serialized


def test_cli_refuses_second_run_before_prompting(db_engine: Engine) -> None:
    factory = sessionmaker(bind=db_engine, expire_on_commit=False)
    with factory() as session:
        BootstrapAdminService(session).bootstrap(
            username="existing_admin",
            real_name="已有管理员",
            password=PASSWORD,
        )
    errors = StringIO()

    exit_code = main(
        input_fn=lambda prompt: pytest.fail(f"unexpected prompt: {prompt}"),
        password_fn=lambda prompt: pytest.fail(f"unexpected password prompt: {prompt}"),
        session_factory=factory,
        stderr=errors,
        argv=[],
    )

    assert exit_code == 1
    assert errors.getvalue() == (
        "Bootstrap refused: an ADMIN user already exists.\n"
    )


def test_cli_rejects_password_arguments_without_echoing_them(
    db_engine: Engine,
) -> None:
    factory = sessionmaker(bind=db_engine, expire_on_commit=False)
    errors = StringIO()

    exit_code = main(
        input_fn=lambda prompt: pytest.fail(f"unexpected prompt: {prompt}"),
        password_fn=lambda prompt: pytest.fail(f"unexpected password prompt: {prompt}"),
        session_factory=factory,
        stderr=errors,
        argv=["--password", "must-not-be-printed"],
    )

    assert exit_code == 2
    assert "command-line arguments are not supported" in errors.getvalue()
    assert "must-not-be-printed" not in errors.getvalue()


def test_cli_validation_error_does_not_echo_password(db_engine: Engine) -> None:
    factory = sessionmaker(bind=db_engine, expire_on_commit=False)
    short_password = "secret"
    answers = iter(["invalid_password_admin", "管理员"])
    passwords = iter([short_password, short_password])
    errors = StringIO()

    exit_code = main(
        input_fn=lambda prompt: next(answers),
        password_fn=lambda prompt: next(passwords),
        session_factory=factory,
        stderr=errors,
        argv=[],
    )

    assert exit_code == 1
    assert "invalid username, real name, or password" in errors.getvalue()
    assert short_password not in errors.getvalue()
