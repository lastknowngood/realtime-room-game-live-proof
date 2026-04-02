import tomllib
from pathlib import Path


def test_websockets_is_runtime_dependency() -> None:
    pyproject = Path(__file__).resolve().parents[1] / 'pyproject.toml'
    data = tomllib.loads(pyproject.read_text(encoding='utf-8'))
    dependencies = data['project']['dependencies']
    assert any(dep.startswith('websockets>=') for dep in dependencies)
