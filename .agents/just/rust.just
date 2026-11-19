# Written by just install. Do not edit: the next just install writes it again.
# The recipes of the rust profile: just rust NAME. They run in the folder of the project.
set positional-arguments
set working-directory := '../..'
# A module has settings of its own, so it sets jlog as its shell too
set shell := ["jlog", "sh", "-cu"]

import? 'rust/base.just'
import? 'rust/lint.just'
import? 'rust/typecheck.just'
import? 'rust/integration.just'
import? 'rust/test.just'

# Every check of the rust profile that is installed: fmt-check, lint, typecheck, integration, test, coverage-check
verify: fmt-check lint typecheck integration test coverage-check
