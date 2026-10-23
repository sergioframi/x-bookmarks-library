from pathlib import Path


ROOT=Path(__file__).parents[1]


def compact(value:str)->str:
    return "".join(value.split())


def test_compose_builds_locally_with_an_optional_host_port():
    compose=(ROOT/"compose.yaml").read_text()
    normalized=compact(compose)
    assert "build:" in compose
    assert '"${PORT:-8080}:8080"' in compose
    assert "env_file:" not in compose
    assert '${DATA_VOLUME:-library-data}:/app/data' in compose
    assert "library-data:" in compose
    assert "SESSION_SECRET:${SESSION_SECRET:-}" in normalized


def test_image_builds_the_extension_and_uses_a_fixed_internal_port():
    dockerfile=(ROOT/"Dockerfile").read_text()
    assert "AS extension-builder" in dockerfile
    assert "build-extension-package.py" in dockerfile
    assert "EXPOSE 8080" in dockerfile
    assert '"--port","8080"' in compact(dockerfile)


def test_public_defaults_do_not_contain_private_deployment_coordinates():
    public_files=[ROOT/"compose.yaml",ROOT/".env.example",ROOT/"README.md",ROOT/"README.es.md"]
    combined="\n".join(path.read_text() for path in public_files)
    assert "http://192.168." not in combined
    assert "/home/" not in combined
    assert "PORT=8080" in combined


def test_english_readme_documents_onboarding_and_hidden_interactions():
    readme=(ROOT/"README.md").read_text()
    for instruction in (
        "The onboarding walks you through everything",
        "Double-click a bookmark card to expand it",
        "Drag a column by its header handle",
        "Double-click that resize handle to restore the default width",
        "Search and filters",
        "light or dark mode",
    ):
        assert instruction in readme
