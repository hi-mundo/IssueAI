# Validation methods

Prefer static proof, then a direct call to a real function, an isolated
temporary probe, local execution, and finally a controlled real interface.
Probes record input, output, effects, and conclusion. Keep them temporary and
deny external writes, production services, secrets, personal data, payments,
messages, migrations, and persistent changes by default.
