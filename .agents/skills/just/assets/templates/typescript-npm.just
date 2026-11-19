# A TypeScript project with npm. `just` lists the recipes. `just install lint` adds a tool; `just install` adds the rest.
import? '.agents/install.just'

# A step of just check, such as lint, ends with jlog step NAME, so the run log of jlog shows that it passed. jlog
# step works only in a recipe that runs through jlog, and the index of just install sets jlog as the shell. So run
# just install before the steps.

# Each word after a recipe's name reaches its commands whole, as "$1", "$2" and so on; "$@" is all of them
set positional-arguments

export npm_config_cache := ".local/npm-cache"

# uv runs node and npm from the nodejs-wheel package, so the machine needs just and uv only
node := "uvx --from 'nodejs-wheel==24.*' node"
npm := "uvx --from 'nodejs-wheel==24.*' npm"

[private]
default:
    @just --list --unsorted

# Install every dependency into node_modules, as package-lock.json says
setup:
    {{npm}} install

# Format the code. Extra arguments go to biome: just fmt src
fmt *args:
    {{npm}} exec -- biome format --write "$@"

# Check the code against the rules in biome.json. Extra arguments go to biome: just lint --write
lint *args:
    {{npm}} exec -- biome check "$@"
    jlog step lint

# Check the types with tsc and tsconfig.json
typecheck:
    {{npm}} exec -- tsc --noEmit
    jlog step typecheck

# Compile src into dist
build:
    {{npm}} exec -- tsc

# Compile, then run the tests in dist with node --test
test *args:
    {{npm}} exec -- tsc
    {{node}} --test "${@:-dist/**/*.test.js}"
    jlog step test

# Find whitespace errors in the changes
diff-check:
    git diff --check
    jlog step diff-check

# Everything a commit must pass: the lint, the types, the tests and the diff check
verify:
    just lint
    just typecheck
    just test
    just diff-check
