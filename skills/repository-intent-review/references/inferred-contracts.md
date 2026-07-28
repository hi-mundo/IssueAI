# Inferred contracts for weakly typed or partially typed code

Repository Intent Review may need to infer contracts when the code does not
state them explicitly.

## Use inference to look for break paths

- infer expected input shape from how a value is read
- infer expected output shape from how a value is consumed
- infer nullability assumptions from direct property access or indexing
- infer protection assumptions from route and middleware structure

## Why this matters

Many real bugs survive because the implementation *acts as if* a type,
validator, or middleware guarantee exists even when the repository does not
actually enforce it everywhere.

That inferred guarantee is itself evidence worth reviewing.
