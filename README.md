# Ego

**Personal AI, built in the open.**

[中文](README.zh-CN.md) · [EgoLabs](https://github.com/getegoai) · [getego.ai](https://getego.ai) · [Roadmap](docs/ROADMAP.md)

Our goal is to give people an AI companion that expands what they can understand and do, while keeping them in control of their data, permissions, and long-term context. We call this an **AI shadow**: a system that can grow with a person across devices and help carry important goals forward.

We are starting with two connected projects:

| Project | Role | Current stage |
|---|---|---|
| [EgoLink](https://github.com/getegoai/egolink) | Wearable sensing, location, cellular communication, and physical interaction | Engineering prototype; existing source is being prepared for import |
| EgoBase | User-controlled storage, personal context, policies, and coordinated action | Local software prototype; intended to remain in this repository initially |

This repository is the home for the overall vision, system boundaries, and cross-project roadmap. EgoBase will become a separate repository only when its development or release needs justify that change.

## Current status

**The existing [EgoBase/Data Core implementation](projects/egobase/data-core/) is now included with its original 34-commit development history.** The public project definition, roadmap, and [website source](website/) are retained. The website files are unchanged by this import.

Development started before this public launch. An existing Data Core prototype supports local evidence storage, document processing, search, daily briefs, policies, audit records, and authorized action dry-runs. EgoLink has separate hardware and firmware work. The complete EgoLink-to-EgoBase product loop has not yet been validated.

The intended system is:

```text
EgoLink and other personal devices
  -> events and evidence
  -> EgoBase: personal state, policies, and context
  -> suggestions or authorized actions
  -> recorded results and feedback
```

Local control is a design direction. It does not mean every current component already runs locally or that privacy and reliability are fully validated.

## What happens next

- Continue development of the imported EgoBase/Data Core implementation and its existing tests.
- Bring EgoLink's actual firmware, services, hardware materials, and tools into its own repository.
- Connect versioned EgoLink events to user-controlled storage, replay, and a small policy/action loop on a PC.
- Develop through public commits, issues, and pull requests. Publish incomplete work and known failures alongside progress.

See the [roadmap](docs/ROADMAP.md) for Now / Next / Later and concrete import tasks.

## Run Data Core

Python 3.11 or newer is required. From `projects/egobase/data-core/`, create and activate a virtual environment, then run:

```sh
python -m pip install -e ".[dev]"
python scripts/run_demo.py
python -m pytest
```

See the [component README](projects/egobase/data-core/README.md) for setup, API, CLI, local UI, and data locations. The bundled sample run is one way to exercise the actual implementation; this repository remains the product development home.

The [history index](docs/HISTORY.md) records original commits, migration boundaries, and historical milestones. Older milestones preserve the development process; they are not new claims that every old version runs on current dependencies.

## Participate

Help shape and build the actual system: discuss a use case, question an interface, report a problem, improve documentation, or contribute an implementation. Start with an [issue](https://github.com/getegoai/ego/issues) or read [CONTRIBUTING.md](CONTRIBUTING.md).

## License

The original documentation is licensed under **CC BY 4.0**; see [LICENSE](LICENSE). The [website implementation](website/) is licensed under **Apache-2.0**, as specified in [website/LICENSE](website/LICENSE). The imported original Data Core source, tests, schemas, configuration, and sample fixtures are licensed under **Apache-2.0**; see [Data Core LICENSE](projects/egobase/data-core/LICENSE). Prose documentation remains CC BY 4.0. See [third-party notices](THIRD_PARTY_NOTICES.md) for dependency boundaries. Hardware, models, data, and third-party materials will have their applicable licenses stated separately.
