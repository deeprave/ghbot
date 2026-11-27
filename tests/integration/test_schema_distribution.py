"""Distribution-level checks for packaged report schemas."""

from __future__ import annotations

import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path


def test_built_distributions_contain_every_schema_resource(tmp_path: Path):
    subprocess.run(
        ["uv", "build", "--out-dir", str(tmp_path)],
        check=True,
        cwd=Path(__file__).parents[2],
    )

    expected_wheel_paths = {
        f"ghbot/schemas/{report}/1.0.json"
        for report in ("security", "issues", "drift", "combined", "settings")
    }
    wheel = next(tmp_path.glob("*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        assert expected_wheel_paths <= set(archive.namelist())

    expected_output = [
        "|".join(
            f"ghbot://schemas/{report}/1.0.json"
            for report in ("security", "issues", "drift", "combined", "settings")
        ),
        "ghbot://schemas/issues/1.0.json",
    ]

    sdist = next(tmp_path.glob("*.tar.gz"))
    with tarfile.open(sdist) as archive:
        names = set(archive.getnames())
    assert all(
        any(name.endswith(f"/src/{path}") for name in names)
        for path in expected_wheel_paths
    )

    for artifact in (wheel, sdist):
        result = subprocess.run(
            [
                "uv",
                "run",
                "--isolated",
                "--no-project",
                "--python",
                sys.executable,
                "--with",
                str(artifact),
                "python",
                "-c",
                (
                    "from ghbot.schemas import current_schema, schema_for_id; "
                    "reports = ('security', 'issues', 'drift', 'combined', 'settings'); "
                    "print('|'.join(current_schema(report)['$id'] for report in reports)); "
                    "print(schema_for_id('ghbot://schemas/issues/1.0.json')['$id'])"
                ),
            ],
            check=True,
            capture_output=True,
            cwd=tmp_path,
            text=True,
        )
        assert result.stdout.splitlines() == expected_output
