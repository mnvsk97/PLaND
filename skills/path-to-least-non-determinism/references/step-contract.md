# Step contract

Each root workflow step must have one of these forms.

## Instruction

Write one direct English instruction. Use it only when the runtime agent must interpret meaning or choose among context-dependent outcomes.

## Reference

Use a relative Markdown link one level below the skill root:

```markdown
Follow [the document analysis procedure](references/document-analysis.md).
```

The referenced file may contain several instructions and commands. Avoid chains in which one reference points to another reference.

## Command

Use an explicit command:

```markdown
Run `python scripts/extract_features.py --input "$DOCUMENT" --output features.json`.
```

The command must define accepted inputs, emitted outputs, exit behavior, dependencies, network policy, and tests. Shell comments may record provenance but must not be required for execution.

## Inventory record

Record compiled steps in `INVENTORY.json` with:

- stable step identifier;
- original instruction;
- representation: `instruction`, `reference`, or `command`;
- artifact path, when applicable;
- input and output contracts;
- permitted network destinations;
- development and validation evidence;
- acceptance status and version.
