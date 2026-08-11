# Python service example

This tiny repository shape demonstrates a task contract that limits an agent to pricing code and its
checks.

```bash
cd examples/python-service
git init
git add . && git commit -m "example base"
python -m pytest checks
patchwitness gate --base HEAD --contract .patchwitness.toml
```

The example contract protects CI and PatchWitness policy, limits the patch to eight files/300 lines,
and records the real test command.

