# Writing and maintaining filters

Filters are the policy layer of `patchsplit`. Their job is to report evidence
about a change; they do not generate patches and they do not mutate repository
state. A good filter is small, explainable, and conservative enough that a
reviewer can understand every match from the inventory record.

## Classification model

Every filter receives one `ChangeUnit`, currently a zero-context libgit2 hunk,
and yields zero or more `Evidence` objects. All filters run. Evidence for the
same category is combined, while evidence for different strong categories
marks the unit as mixed.

The resolver follows these rules:

1. Exactly one `EXACT` category: assign it as the owner. It overrides strong,
   weak and fallback hints.
2. Two or more `EXACT` categories: mark the unit mixed and leave its owner
   unset.
3. With no exact match, exactly one `STRONG` category owns the unit.
4. With no exact match, two or more strong categories make the unit mixed.
5. Only `WEAK` evidence leaves the owner unset for review.
6. Exactly one `FALLBACK` and no weak or stronger evidence owns the unit.
7. Filter registration order never breaks a tie between categories.

This is deliberately not a first-match system. A strict global order would
make `dark-mode` hide `history-settings` when both occur in one hunk. Ordered
checks are appropriate only *inside* a filter when alternatives are known to
be mutually exclusive, as in `ConsoleMainFilter`.

## Categories

All public category identifiers live in `src/patchsplit/categories.py` as
members of `Category`. Filters must use those members rather than string
literals:

```python
from patchsplit.categories import Category, MatchStrength

yield evidence(
    self,
    Category.UI_DARK_MODE,
    MatchStrength.STRONG,
    "dark-mode API or compile guard",
)
```

Before adding a category:

1. Check whether an existing category describes the same independently
   reviewable patch.
2. Prefer a purpose such as `ui.compression-levels` over a filename or class
   name.
3. Use a dotted, lowercase external value for feature categories. The prefix
   identifies the broad subsystem; the remainder identifies the purpose.
   Resolution-state categories retain the stable `unresolved` and `mixed`
   labels.
4. Add the enum member before changing filters or manifests.
5. Treat the enum value as stable persisted data. Renaming the Python member is
   safe; changing its value requires migrating saved inventories and overrides.
6. Place it at the intended position in the enum. `PATCH_SERIES_ORDER` is
   generated from declaration order and is the canonical patch export order.

Do not create a category merely because a new keyword appeared. A category
should correspond to a patch that could be reviewed, reordered, or omitted as
a coherent feature.

## Match strengths

`MatchStrength` is an ordinal enum, not a probability and not a tuning knob.
Maintainers should not invent intermediate numeric values.

| Strength | Use when | Ownership effect |
|---|---|---|
| `EXACT` | The evidence uniquely identifies the purpose: an imported-tree path, explicit override, or purpose-specific symbol in a narrowly scoped file | Owns over lower strengths; two exact categories become mixed |
| `STRONG` | A feature-specific identifier or combination is very unlikely to be incidental | May own automatically; conflicts become mixed |
| `WEAK` | The token supports a hypothesis but occurs in unrelated features too | Never owns by itself; requests review |
| `FALLBACK` | Broad path ownership such as `CPP/7zip/UI/` | Used only when nothing more informative matched |

Examples:

- `C/zstd/` is `EXACT` for `vendor.zstd` because directory ownership is
  definitive.
- `WantLowercaseHashes` is `STRONG` for `ui.lowercase-hashes`.
- `numThreads` is `WEAK` for `codec.thread-properties`; many features mention
  thread counts without being primarily about thread-property plumbing.
- `CPP/7zip/UI/` is a `FALLBACK` for `ui.misc`.

If choosing between `STRONG` and `WEAK`, ask: “Would I be comfortable assigning
this hunk automatically if this were the only non-fallback match?” If not, use
`WEAK`.

## Adding a built-in filter

Implement `ChangeFilter.classify()` in `src/patchsplit/filters/`. Filters should
be stateless after construction and must not rely on another filter having run
first.

```python
class ExampleFilter(ChangeFilter):
    name = "example-feature"

    def classify(self, change: ChangeUnit) -> Iterable[Evidence]:
        if not change.path.startswith("CPP/7zip/UI/"):
            return
        if "ExampleFeatureFlag" in change.searchable_text:
            yield evidence(
                self,
                Category.UI_EXAMPLE_FEATURE,
                MatchStrength.STRONG,
                "ExampleFeatureFlag in a UI change",
            )
```

Then register the instance in `builtin_filters()` and add focused tests.

Prefer several narrow filters over one large filter if the features have
different owners or maintenance histories. A table of related declarative
regex rules, as used by `UiPurposeFilter`, is appropriate when the scope and
matching behavior are shared.

## Pattern guidance

- Scope by path before inspecting content. This prevents common identifiers
  from classifying unrelated subsystems.
- Prefer stable identifiers, resource IDs, enum members, option names and
  function names over prose or formatting.
- Include the enclosing diff section when it adds meaning; `searchable_text`
  contains both the section and changed lines.
- Match both additions and deletions. A feature-removal patch still belongs to
  that feature.
- Avoid generic tokens such as `level`, `method`, `hash`, `thread`, or `mode`
  on their own.
- Use a reason that describes why the pattern is diagnostic, not merely that a
  regular expression matched.
- Do not suppress another category just to reduce mixed counts. Mixed output is
  valuable: it identifies where sub-hunk or structural atomization is needed.

When a hunk contains table entries for an extra codec and its supported level
mask, both `ui.extra-codecs` and `ui.compression-levels` should match. The
maintainer can then split at initializer boundaries or deliberately assign the
whole record to an integration component.

## External filter modules

Use `--filter-module package.module` to add repository- or experiment-specific
filters without modifying the built-ins. The module must expose either
`get_filters()` or an iterable named `FILTERS`:

```python
from patchsplit.filters.base import ChangeFilter

FILTERS: tuple[ChangeFilter, ...] = (ExampleFilter(),)
```

External filters use the same `Category` enum. If a genuinely new persisted
category is needed, add it centrally first instead of emitting an arbitrary
string. `FilterSet` validates both category and strength types at runtime so a
misspelled or ad-hoc category fails immediately rather than leaking into a
manifest.

## Tests and review workflow

Each new or changed rule should have tests for:

1. a positive example;
2. a nearby negative example that must not match;
3. a mixed-purpose example when the feature commonly shares hunks;
4. the expected strength and reason;
5. stable owner behavior after resolution.

After unit tests, regenerate both inventories and review:

```powershell
uv run patchsplit --repository ../.. `
  --output ../../patch-split/full-inventory.jsonl
uv run patchsplit --repository ../.. `
  --path-prefix CPP/7zip/UI/ `
  --output ../../patch-split/ui-inventory.jsonl
```

Pay particular attention to changes in:

- mixed and unresolved counts;
- category counts;
- previously reviewed unit IDs;
- broad increases caused by an over-general pattern;
- line-slice boundaries inside mixed hunks.

A lower unresolved count is not automatically an improvement. Correctly
unresolved evidence is preferable to a confident-looking misclassification.
