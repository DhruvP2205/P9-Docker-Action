# P9 – Dockerfile Pin Check (Docker container action)

A GitHub Action that reads a Dockerfile and reports every `FROM` base image that is **not pinned**. It can fail the step, and it exposes a count and a report as outputs.

Built as Project 9 of my GitHub Actions series. It is the Docker-container counterpart of Project 8 (a JavaScript action).

## What "pinned" means here

| `FROM` line | Result | Why |
|---|---|---|
| `FROM python:3.12-slim` | pinned | has a tag that is not `latest` |
| `FROM python@sha256:…` | pinned | digest |
| `FROM localhost:5000/app:1.0` | pinned | registry port is not mistaken for a tag |
| `FROM python` | **unpinned** | no tag, so it means `latest` |
| `FROM node:latest` | **unpinned** | explicit `latest` |
| `FROM ${BASE}` | **unpinned** | see "Decisions" below |
| `FROM builder` (earlier `AS builder`) | ignored | reuse of a stage, not an external image |
| `FROM scratch` | ignored | no image to pin |

Also handled: `--platform=…` flags, lowercase `from`/`as`, indented lines, trailing `# comments`, comment-only lines, a UTF-8 BOM, and CRLF line endings.

## Usage

```yaml
- uses: actions/checkout@v7

- name: Check Dockerfile pins
  id: pins
  uses: DhruvP2205/P9-Docker-Action@main   # pin to a tag/SHA in real use
  with:
    dockerfile: Dockerfile
    fail_on_unpinned: "true"

- name: Show report
  if: always()
  run: |
    echo "count: ${{ steps.pins.outputs.unpinned_count }}"
    echo "${{ steps.pins.outputs.report }}"
```

### Inputs

| Name | Required | Default | Meaning |
|---|---|---|---|
| `dockerfile` | yes | – | Path to the Dockerfile, relative to the workspace |
| `fail_on_unpinned` | no | `"true"` | `true`/`yes` (any case) fails the step when something is unpinned. Any other value only reports |

### Outputs

| Name | Meaning |
|---|---|
| `unpinned_count` | Number of unpinned base images |
| `report` | One line per finding: `Line N: FROM … -> Image '…' is unpinned.` (empty when all pinned) |

A missing Dockerfile prints `Docker File Not Found...` and exits 1.

## How it works

`action.yml` declares `runs: using: docker`. The runner builds the `Dockerfile` in this repo, runs the container with the workspace mounted at `/github/workspace`, and passes the inputs as arguments. `entrypoint.py` parses the file and writes the outputs to `$GITHUB_OUTPUT`.

Two details that cost me time:

- The multi-line `report` output uses the `name<<DELIMITER` form with a random delimiter (`uuid4`). Writing `report=` once per line broke the file format. The random delimiter also stops a Dockerfile line from injecting a fake output.
- The runner starts the container with `--workdir /github/workspace`, which overrides the image's `WORKDIR`. That is why `ENTRYPOINT` uses the absolute path `/flag-app/entrypoint.py`.

## Testing

`.github/workflows/test.yml` runs the action on **17 fixtures** (`fixtures/*.Dockerfile`) as a matrix with `fail-fast: false`. The action step uses `continue-on-error: true`, then a second step compares what actually happened with what the row expects:

- step `outcome` (success/failure) against `expected-outcome`
- `unpinned_count` output against `expected-count`

The job fails if either differs, so a test can only be green when the action behaves exactly as expected, including failing when it should.

| # | Row | fail_on_unpinned | Expected outcome | Expected count |
|---|---|---|---|---|
| 1 | good | true | success | 0 |
| 2 | no tag | true | failure | 1 |
| 3 | latest | true | failure | 1 |
| 4 | multistage | true | success | 0 |
| 5 | mixed | true | failure | 2 |
| 6 | digest | true | success | 0 |
| 7 | lowercase | true | failure | 1 |
| 8 | comment | true | success | 0 |
| 9 | indented | true | failure | 1 |
| 10 | crlf | true | failure | 1 |
| 11 | arg tag | true | success | 0 |
| 12 | arg image | true | failure | 1 |
| 13 | empty | true | success | 0 |
| 14 | no tag, fail off | false | success | 1 |
| 15 | latest, fail off | false | success | 1 |
| 16 | mixed, fail off | false | success | 2 |
| 17 | indented, fail off | false | success | 1 |

Result: **17 / 17 green.**

### Proof the matrix can fail

An earlier run was 15 / 17. Two rows went red and the comparison step caught both:

- `crlf` – the fixture file was not in the repo, so the action printed `Docker File Not Found...` and the count was empty.
- `arg image` – I expected `success / 0`, but the script (correctly, by its own rules) flagged `FROM ${BASE}`. I fixed the test expectation, not the script. See "Decisions".

> _Screenshot: matrix with the two red jobs_ — `docs/red-run.png`
> _Screenshot: matrix, 17 green_ — `docs/green-run.png`

### Fixture notes

- `crlf.Dockerfile` really has CRLF endings. `.gitattributes` has `fixtures/crlf.Dockerfile -text` so Git does not normalise it. Check with `git ls-files --eol fixtures/crlf.Dockerfile` (expect `i/crlf w/crlf`).
- The BOM bug was found by a fixture: a BOM file was reported clean until I opened it as `utf-8-sig`.

## Decisions

- **`FROM ${BASE}` counts as unpinned.** A build argument can't be resolved by reading the file, so the checker cannot prove it is pinned. I chose the fail-safe side. If the `ARG` has a pinned default (`ARG BASE=python:3.12-slim`) the check still flags the `FROM` line, because the default can be overridden at build time. The rule is tested by the `arg image` row. A softer option (warn but don't count) is easy to add if this is too strict for a given repo.
- **An empty Dockerfile is "all pinned".** There is nothing to flag.
- **`fail_on_unpinned` defaults to `"true"` in `action.yml`**, so a normal use of the action always passes the argument.

## Docker action vs JavaScript action (P8 vs P9)

| | P8 JavaScript | P9 Docker |
|---|---|---|
| Runs on | runner Node directly | container built from the repo's `Dockerfile` |
| Runners | Linux, Windows, macOS | Linux only |
| Startup | ~0.07–0.16 s in my runs | image build ~3.5–6 s + run ~0.3–0.5 s (from the logs) |
| Language | JS (needs `dist/` committed) | anything (here Python, no build artifact to commit) |
| Dependencies | bundled with ncc | whatever the image installs |

The Docker action's cost is the build on every run. Pushing a prebuilt image to a registry and pointing `image:` at it (`docker://ghcr.io/…`) would remove that, but I have not done it.

## What I didn't do

- Prebuilt image in GHCR (the build runs on every use)
- Handling a missing second argument when `entrypoint.py` is run by hand (via the action it always has the default).
- Treating an unknown `fail_on_unpinned` value (for example `ture`) as an error. It silently means "don't fail".
- Distinct messages per reason (no tag vs `latest` vs variable).
- Resolving `ARG` defaults or checking that a digest actually exists in the registry.

## Layout

```
.
├── action.yml
├── Dockerfile
├── entrypoint.py
├── fixtures/                 # 13 Dockerfiles used by the matrix
└── .github/workflows/test.yml
```
