# Third-party boundaries

The Data Core runtime does not vendor external libraries, binary SDKs,
model weights, private runtime stores, or external datasets. Its dependencies are
installed from the component's `pyproject.toml` and retain their own licenses.
The project's Apache-2.0 and CC BY 4.0 grants do not relicense dependencies.

Direct dependencies inspected in the migration environment:

| Package | Version inspected | License from installed distribution metadata |
|---|---|---|
| FastAPI | 0.162.0 | MIT |
| pypdf | 6.21.2 | BSD-3-Clause |
| python-docx | 1.2.0 | MIT |
| Uvicorn | 0.54.0 | BSD-3-Clause |
| HTTPX, development | 0.28.1 | BSD-3-Clause |
| pytest, development | 8.4.2 | MIT |

These are observations of one test environment, not a lock file or a license
inventory for future dependency versions. Their transitive dependencies remain
subject to their own notices. Anyone distributing a packaged environment should
retain the licenses and notices supplied with the distributions they ship.

Bundled demo and test fixtures are project sample data, not imported user records.
Documentation references to other products do not imply affiliation or a grant
of rights in those products. The website's existing license remains unchanged.

## Documentation artwork

The system concept illustration uses a bundled copy of the **Anatomy SVG kit**,
copyright (c) 2026 Ryan, under the MIT license. Its [full license](docs/media/system/vendor/LICENSE)
and [kit source](docs/media/system/vendor/iso-kit.mjs) are retained beside the
figure. This helper is used to generate documentation artwork; it is not a
Data Core runtime dependency. Original figure/build sources and media scope
are described in the [visual asset guide](docs/media/README.md).
