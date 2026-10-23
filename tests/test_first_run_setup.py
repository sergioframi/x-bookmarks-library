from fastapi import HTTPException, Response

from app.db import connect, initialize_schema
from app.main import InitialSetup, Login, initial_setup, login, onboarding_payload
from app.security import read_session
from app.config import Settings,ensure_session_secret,settings


def test_session_secret_is_generated_once_in_persistent_data(tmp_path):
    secret_path=tmp_path/"session-secret"
    first_settings=Settings(database_path=tmp_path/"library.sqlite3",session_secret="",session_secret_path=secret_path)
    first=ensure_session_secret(first_settings)
    second_settings=Settings(database_path=tmp_path/"library.sqlite3",session_secret="",session_secret_path=secret_path)
    second=ensure_session_secret(second_settings)
    assert first==second
    assert len(first)>=32
    assert secret_path.stat().st_mode&0o777==0o600


def test_initial_setup_creates_the_only_user_and_persists_preferences(tmp_path):
    object.__setattr__(settings, "session_secret", "test-secret")
    connection = connect(tmp_path / "setup.sqlite3")
    initialize_schema(connection)
    response = Response()
    result = initial_setup(InitialSetup(username="alice", password="correct horse battery", locale="en", theme="dark", palette="lavender"), response, connection)
    assert result["username"] == "alice"
    assert result["onboarding"]["step"] == "welcome"
    assert result["onboarding"]["locale"] == "en"
    assert result["onboarding"]["theme"] == "dark"
    token = response.headers["set-cookie"].split("xb_session=", 1)[1].split(";", 1)[0]
    assert read_session(token, "test-secret")["sub"] == "alice"
    try:
        initial_setup(InitialSetup(username="bob", password="another secure password"), Response(), connection)
    except HTTPException as error:
        assert error.status_code == 409
    else:
        raise AssertionError("a second initial user was accepted")
    object.__setattr__(settings, "username", "unrelated-env-user")
    logged_in = login(Login(username="alice", password="correct horse battery"), Response(), connection)
    assert logged_in["username"] == "alice"
    assert onboarding_payload(connection)["completed"] is False
    connection.close()
