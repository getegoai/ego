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

**This first public version contains the project definition and roadmap. The existing implementation has not yet been imported here.**

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

- Import the existing EgoBase/Data Core implementation under `projects/egobase/data-core/`, with its current tests and run instructions.
- Bring EgoLink's actual firmware, services, hardware materials, and tools into its own repository.
- Connect versioned EgoLink events to user-controlled storage, replay, and a small policy/action loop on a PC.
- Develop through public commits, issues, and pull requests. Publish incomplete work and known failures alongside progress.

See the [roadmap](docs/ROADMAP.md) for Now / Next / Later and concrete import tasks.

## Participate

Help shape and build the actual system: discuss a use case, question an interface, report a problem, improve documentation, or contribute an implementation. Start with an [issue](https://github.com/getegoai/ego/issues) or read [CONTRIBUTING.md](CONTRIBUTING.md).

## License

The original documentation in this initial publication is licensed under **CC BY 4.0**; see [LICENSE](LICENSE). No implementation source is included in this version. We intend to publish our own software under **Apache-2.0** when it is imported and explicitly licensed. Hardware, models, data, and third-party materials will have their applicable licenses stated separately.
