# GSU TypeScript Hello World Lab

This disposable lab exercises `gsu` concepts on a tiny TypeScript project. It is
meant to prove the setup surface before doing real work in a target repository.

## Create The Repo

```bash
skills_repo=/path/to/agent_gest_git_skills
lab=/tmp/gsu-typescript-hello
rm -rf "$lab"
mkdir -p "$lab/src"
cd "$lab"
git init -b main
"$skills_repo/scripts/install.sh" "$lab"
```

Create `package.json`:

```json
{
  "name": "gsu-typescript-hello",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "build": "tsc",
    "format": "biome format --write .",
    "lint": "biome check .",
    "test": "tsc && node --test dist/*.test.js",
    "typecheck": "tsc --noEmit",
    "start": "node dist/index.js"
  },
  "devDependencies": {
    "@biomejs/biome": "^2.4.14",
    "@types/node": "^25.0.0",
    "typescript": "^5.9.3"
  }
}
```

Create `tsconfig.json`:

```json
{
  "compilerOptions": {
    "declaration": true,
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "target": "ES2022"
  },
  "include": ["src/**/*.ts"]
}
```

Create `biome.json`:

```json
{
  "formatter": {
    "enabled": true,
    "indentStyle": "space",
    "indentWidth": 2
  },
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true
    }
  }
}
```

Create `.gitignore`:

```gitignore
node_modules/
dist/
coverage/
.local/
.env
.DS_Store
```

Create `src/index.ts`:

```ts
export function greet(name = "world"): string {
  return `Hello, ${name}!`;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  console.log(greet());
}
```

Create `src/index.test.ts`:

```ts
import assert from "node:assert/strict";
import test from "node:test";
import { greet } from "./index.js";

test("greet defaults to the world", () => {
  assert.equal(greet(), "Hello, world!");
});

test("greet accepts a name", () => {
  assert.equal(greet("Gest"), "Hello, Gest!");
});
```

## Add The Command Contract

Create `Justfile`:

```just
export npm_config_cache := ".local/npm-cache"

default:
  just --list

setup:
  npm install

fmt path="src package.json tsconfig.json":
  npm exec -- biome format --write {{path}}

lint path="src package.json tsconfig.json":
  npm exec -- biome check {{path}}

typecheck:
  npm exec -- tsc --noEmit

build:
  npm exec -- tsc

test target="":
  npm exec -- tsc
  node --test dist/*.test.js {{target}}

smoke:
  npm exec -- tsc
  node dist/index.js

diff-check:
  git diff --check

verify: lint typecheck build test smoke diff-check

dev:
  npm exec -- tsc
  npm run start
```

Update `AGENTS.md` from the template placeholders so it maps setup, format,
lint, typecheck, build, test, smoke, verify, and dev to the `just` targets. For
the disposable lab, appending a concrete section is enough:

````md
## Lab Command Contract

Use the `Justfile` as the stable command interface:

```bash
just setup
just fmt [path]
just lint [path]
just typecheck
just build
just test [target]
just smoke
just verify
just dev
git diff --check
```

Mappings:

- Setup: `just setup`, which runs `npm install` with `.local/npm-cache`.
- Format: `just fmt [path]`, which runs Biome format.
- Lint: `just lint [path]`, which runs Biome check.
- Typecheck: `just typecheck`, which runs `tsc --noEmit`.
- Build: `just build`, which runs `tsc`.
- Tests: `just test [target]`, which compiles then runs `node --test`.
- Smoke: `just smoke`, which compiles then runs the hello-world program.
- Diff hygiene: `just diff-check`, which runs `git diff --check`.
- Full verification: `just verify`, which depends on `lint`, `typecheck`,
  `build`, `test`, `smoke`, and `diff-check`.
````

## Verify

```bash
just --list
just setup
just lint src/index.ts
just typecheck
just test
just verify
```

Expected result:

- `just setup` installs dependencies using `.local/npm-cache`.
- `just lint src/index.ts` proves focused argument passing.
- `just verify` runs lint, typecheck, build, tests, smoke, and diff hygiene
  through native Just dependencies.

## Lessons For GSU

- Prefer project-local caches for npm setup when reproducibility matters.
- Include `@types/node` for Node-targeted TypeScript projects.
- Scope lint defaults to source/config files so generated `dist/` output is not
  checked by default.
- Keep tool choices in `AGENTS.md` and `Justfile`; the reusable skills stay
  language-agnostic.
