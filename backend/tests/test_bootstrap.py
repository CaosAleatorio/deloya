import sys

import pytest

from app import bootstrap_admin


@pytest.fixture(autouse=True)
def clear_test_database():
    """Invalid bootstrap input must be rejected before any database access."""


@pytest.mark.parametrize("email,password", [
    ("admin-bootstrap@example.com", "Segredo!42"),
    ("email-invalido", "Segredo!42-muito-sensivel"),
])
def test_bootstrap_validation_never_exposes_password(email, password, monkeypatch, capsys):
    monkeypatch.setenv("ADMIN_PASSWORD", password)
    monkeypatch.setattr(sys, "argv", ["bootstrap_admin", "--email", email])
    def unexpected_database_access():
        raise AssertionError("A validação deve ocorrer antes de abrir a base de dados")
    monkeypatch.setattr(bootstrap_admin, "SessionLocal", unexpected_database_access)
    with pytest.raises(SystemExit, match="nenhuma conta foi criada") as failure:
        bootstrap_admin.main()
    output = capsys.readouterr()
    assert password not in str(failure.value)
    assert password not in output.out
    assert password not in output.err
    assert "input_value" not in str(failure.value)
