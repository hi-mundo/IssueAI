# Repository normalization phase

Consume the review contract and normalized repository artifact. Preserve every
file record, canonical path, content hash, language, generated/vendor flags,
and decode/parse status. Do not infer symbols or dependencies here; those
belong to the repository-map phase. Return only a validated phase envelope.
