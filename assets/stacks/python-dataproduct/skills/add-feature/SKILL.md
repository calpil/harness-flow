---
name: add-feature
description: Implement a scoped feature in the generic Python Data Product by changing only the layers genuinely required.
---

# Add Feature

Classify the requested outcome first:

- source acquisition
- validation
- transformation/domain
- persistence/output
- serving API
- platform concern

Do not modify every layer automatically.

Preserve dependency direction and explicit mappings. Reuse existing ports before creating new abstractions.

Validate progressively from the lowest affected layer upward.

If behavior changes, treat local flow execution as a separate I4 step rather than assuming tests alone are enough.
