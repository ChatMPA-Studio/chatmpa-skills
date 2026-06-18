# Vocabulary Guide: Action Types and Confidence

## Action types — detailed criteria and edge cases

### `Information gap`
The plan **does not mention** the topic at all, or mentions it so superficially that there is no guidance for action. The evidence demonstrates that the topic is relevant to the MPA.

**Typical cases:**
- A protection subprogram that does not mention climate change while the evidence documents recent mass bleaching.
- A plan that includes no invasive species response protocol despite records of new detections in the area.

**Key distinction:** If the plan *mentions* the topic but with old data, use `Outdated data`. If it *does not mention it*, use `Information gap`.

---

### `Outdated data`
The plan cites figures, studies, or diagnoses that the evidence supersedes with more recent or contradictory data. The topic is covered, but the content has become obsolete.

**Typical cases:**
- The plan cites coral coverage from 2000; the evidence documents current values that are significantly lower.
- The plan classifies a species as "not at risk"; the evidence reports its recent inclusion on the IUCN Red List.
- The plan mentions a visitor target based on carrying capacity studies predating documented tourism growth.

**Key distinction:** The evidence does not merely "complement" — it specifically contradicts or supersedes what the plan states.

---

### `Urgent activity`
The evidence documents an active threat, an ongoing process, or a critical threshold requiring short-term action — not at the next quinquennial review. The plan does not address it or treats it as a future concern.

**Typical cases:**
- Confirmed record of an invasive species in the MPA; the plan has no rapid-response protocol.
- Mass bleaching events documented in the last two years; the plan has no emergency monitoring protocol.
- Sea temperature crossing critical thresholds for coral; the plan provides no response measures.

**Key distinction:** The criterion is temporal urgency, not severity. A serious but long-term threat is a `Recommendation` or `Outdated data`. A threat requiring action this monitoring cycle is an `Urgent activity`.

---

### `Recommendation`
Concrete improvement directly supported by the evidence that does not involve immediate urgency. The plan could function without it, but the evidence shows that incorporating it would significantly strengthen it.

**Typical cases:**
- Adopting a reef health index that the evidence describes and calculates for the area.
- Incorporating a numerical coverage target that the evidence suggests as achievable.
- Adjusting zoning based on updated species distribution data.

---

### `New idea`
A proposal the reviewer considers valuable but **not supported by any of the provided evidence documents**. It may be logical and well-grounded in expert knowledge, but it cannot be cited with a specific source from the provided documents.

**Mandatory rule:** Every row with Confidence `Uncertain` must be `New idea`. If a recommendation cannot be cited with a page and document, it is a `New idea`.

---

## Confidence levels — application guide

| Situation | Confidence |
|---|---|
| The data, figure, or protocol appears verbatim in the evidence with an identifiable page | `High` |
| The topic is covered in the evidence but the specific recommendation is inferred, not directly cited | `Medium` |
| The recommendation comes from expert knowledge, not from the provided documents | `Uncertain` → force `New idea` |

**Note on `Medium` confidence:** It is not a "filler" level. Use it when the evidence documents the problem but does not propose the specific solution. Example: the evidence reports severe bleaching (verifiable data → `High` for the diagnosis), but the proposed recovery target is calculated by interpolation (→ `Medium` or `[derived]` for the numerical target).
