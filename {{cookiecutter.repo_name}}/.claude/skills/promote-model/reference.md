# Model Registry API reference (comet-ml >= 3.55)

Loaded on demand by `/promote-model`; the rule in `.claude/rules/comet-em-best-practices.md` holds the
conventions. Docs: <https://www.comet.com/docs/v2/api-and-sdk/python-sdk/reference/Model/>,
<https://www.comet.com/docs/v2/guides/model-registry/model-approval/>.

## Registering from a run

```python
api.get_experiment_by_key(key).register_model(   # synchronous; raises when the backend rejects it
    "iris-classifier",            # registry name, workspace-unique
    version="1.0.3",              # semver; defaults to "1.0.0", duplicates are rejected
    status="Development",         # one of the workspace's allowed statuses
    tags=["example"],
    metadata={"dataset_version": "1.0.0", "val_accuracy": 0.97},
)
```

The model must have been logged to that experiment first (`experiment.log_model(name, path)`).
`experiment.register_model(...)` also exists but is fire-and-forget (a rejection is only logged at
`end()`). `train.py` picks the next patch version with `bump_patch(model.find_versions()[0])`.

## Reading and mutating after registration

```python
from comet_ml import API

api = API()                                             # key from the environment
ws = config.COMET_WORKSPACE or api.get_default_workspace()
model = api.get_model(ws, "iris-classifier")            # raises when the model does not exist

api.model_registry_allowed_status_values(ws)            # ["None", "Development", "Staging", "QA", "Production"]
model.find_versions()                                   # newest first
model.find_versions(status="Production")                # filter by status (or tag=)
model.get_details("1.0.3")                              # dict: status, tags, experimentKey, createdAt, ...
model.status("1.0.3")                                   # just the status
model.set_status("1.0.3", "Production")                 # request or direct change, per workspace policy
model.add_tag("1.0.3", "champion"); model.delete_tag("1.0.2", "champion")
model.download("1.0.3", output_folder="models/registry/1.0.3")
```

Framework loaders that take a registry URI (no manual download):
`comet_ml.integration.sklearn.load_model("registry://<ws>/iris-classifier:1.0.3")`,
`comet_ml.integration.pytorch.load_model("registry://<ws>/iris-classifier:1.0.3", map_location="cpu")`.

`api.download_registry_model(...)` still exists but is deprecated; use `Model.download`.

## Status semantics

- One status per version; the set is per workspace (`allowed-statuses`). Workspace owners can require
  approval: then `set_status` creates a pending request, visible under "pending requests" in the UI.
- Setting `Production` on a new version does not clear it from the old one. Demote explicitly.
- Webhooks fire on status change after approval (`MODEL_STATUS_CHANGED`), on version creation, deletion
  and tag change. The deploy workflow in `.github/workflows/deploy-model.yml` consumes the first one.
