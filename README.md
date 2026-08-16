# zygos ζυγός

A library of complete AI agent harness specifications, researched and maintained by agents.

**ζυγός** — the yoke that couples draught animals to pull together, and the balance the same word
names in Greek (Ζυγός is Libra). A harness does both: it couples a model to the world, and it trades
capability against constraint.

Read [`DESIGN.md`](DESIGN.md) for the full specification, [`CLAUDE.md`](CLAUDE.md) for the working
rules, and [`docs/research/SKILL.md`](docs/research/SKILL.md) for how to actually research one. Two
specs so far: [`exo`](docs/research/harnesses/exo.md) and [`temper`](docs/research/harnesses/temper.md).

## What this is not

Not a comparison of 100+ harnesses — [`best-of-Agent-Harnesses`](https://github.com/RyanAlberts/best-of-Agent-Harnesses)
already does that well, at a breadth this repo doesn't try to match. zygos goes deep on individual
harnesses instead: one complete, sourced, structured spec per entry, built so two specs can be read
side by side.

Not a harness itself, and not a framework. It studies them.

## Status

Two specs (exo, Temper), format survived its first live hand-written research pass and an independent
fidelity review before merge. RLM and DeepSeek Harness targeted next — chosen to bracket the design
space rather than sample it. See [`docs/research/README.md`](docs/research/README.md) for the target
list.

## License

[CC BY 4.0](LICENSE) on the written content — research specs, concepts, ADRs. Each harness studied
keeps its own license, recorded in its spec's `license` frontmatter field; this repository makes no
claim over the projects it describes.
