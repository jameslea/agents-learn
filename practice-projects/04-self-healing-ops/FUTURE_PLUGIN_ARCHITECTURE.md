# Future Plugin Architecture

This project intentionally does not implement a generic self-healing operations platform.

If the idea is revisited later, keep the D-lite core separate from environment-specific plugins:

- `EnvironmentPlugin`: local Docker, Kubernetes, SSH host, CI runner.
- `SignalPlugin`: logs, metrics, traces, alerts, test output.
- `ActionPlugin`: restart service, roll back config, run command, apply patch.
- `VerificationPlugin`: health check, unit test, API probe, metric recovery.
- `PermissionPlugin`: action risk level, dry-run support, approval requirement.
- `RollbackPlugin`: explicit rollback for failed actions.

The current D-lite project only proves the smallest loop:

```text
execute -> classify error -> repair -> verify
```

Do not add real infrastructure adapters until the small loop is reliable and evaluated.
