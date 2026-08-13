# PyPI Release Checklist

**Current status: READY, NOT PUBLISHED.**

PatchWitness has passed local source/wheel build, Twine metadata validation and clean-wheel installation. On 2026-08-13, the official PyPI project page at `https://pypi.org/project/patchwitness/` returned `404`, so no public project was found at that time. This is an observation, not a reservation or a guarantee that the name will remain available.

## Maintainer-only first-release steps

The first PyPI publication is a high-impact, irreversible action. Complete these steps only after the release candidate is approved and after explicitly confirming the publication action.

1. Re-run `make release-check` from the tagged commit; confirm the version, changelog and all artifact digests.
2. Sign in to PyPI and configure a **Trusted Publisher** for `pangxueyuan2-creator/patchwitness`, workflow file `.github/workflows/release.yml`, and GitHub environment `pypi`. Use the exact owner, repository, workflow and environment values; an incorrect trust relationship is equivalent to granting publication authority.[1] [2]
3. In GitHub, create the `pypi` environment and add an appropriate protection rule for release tags. This is strongly recommended by PyPI and GitHub for a predictable publication boundary.[1] [2]
4. Set the repository variable `PYPI_TRUSTED_PUBLISHING` to `true` only after Step 2 succeeds. The release workflow keeps the publish job skipped otherwise.
5. Merge the release candidate after all required CI, CodeQL and PatchWitness gates succeed. Create an annotated tag matching `v<package-version>` and push that tag.
6. The tag workflow runs tests, Ruff, mypy, the real Demo, the change-risk benchmark, build, Twine validation, clean-wheel install, digest creation and provenance attestation before uploading release assets. Its PyPI job receives only an OIDC `id-token: write` permission and uses the official PyPA publishing Action; it does not store a long-lived PyPI token.
7. After the workflow succeeds, verify the PyPI project page, release version, distributions and SHA-256 digests. In a clean environment, test `pipx install patchwitness` and `uvx patchwitness --help` from PyPI.
8. Record the version, tag SHA, GitHub Release URL, PyPI URL, artifact digests and clean-install results in the release notes.

## Local preflight commands

```bash
python -m pip install -e ".[dev]"
make release-check
```

The preflight is intentionally local: it builds and validates artifacts without relying on a PyPI publication. Package-name lookup and Trusted Publisher setup are separate read-only/account configuration steps.

## References

[1]: https://docs.pypi.org/trusted-publishers/using-a-publisher/ "PyPI: Publishing with a Trusted Publisher"
[2]: https://docs.github.com/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-pypi "GitHub: Configuring OpenID Connect in PyPI"
