# Document classification requirements

Classify one supplied OCR text document into exactly one of these labels:

`advertisement`, `email`, `form`, `letter`, `memo`, `news`, `note`, `report`,
`resume`, or `scientific`.

Use the document's content and structure. Return only JSON matching:

```json
{"label":"email","confidence":0.95}
```

`label` must be one of the canonical labels. `confidence` must be a number from
0 through 1. Do not return an explanation or any additional keys.

The runtime model is local Ollama `qwen3:14b`. Use temperature 0, a fixed seed,
and non-thinking mode. Do not call paid or remote model services.
