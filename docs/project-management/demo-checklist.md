# Demo checklist

## Product behavior

- [ ] Learner A and Learner B begin with the same HSK1 goal.
- [ ] Their different mastery/error histories are visible.
- [ ] Their daily plans differ for explainable reasons.
- [ ] An open-ended answer receives rubric-based feedback.
- [ ] The error changes learner state and triggers appropriate remediation.
- [ ] Retention decay schedules a previously learned concept for review.
- [ ] Overall progress reflects mastery multiplied by retention.
- [ ] State survives application restart.

## Reliability

- [ ] Hosted API credentials and budget are checked without displaying secrets.
- [ ] Ollama and the selected local model are installed and warmed up.
- [ ] Forced hosted-provider failure successfully uses local fallback.
- [ ] Fixed demo content works without ChromaDB or network retrieval.
- [ ] Reset/seed procedure is rehearsed and non-destructive.
- [ ] Latency, token use, cost, and fallback state are observable.

## Evidence

- [ ] Human-labelled grader dataset is frozen and versioned.
- [ ] Agreement metrics and important error examples are ready.
- [ ] Tests pass from a documented clean setup.
- [ ] Architecture diagram matches the running system.
- [ ] Known limitations and open decisions are stated honestly.
- [ ] Each presenter knows the handoff and fallback narrative.

`TODO(demo)`: add the final date, environment, presenter order, seed command, and backup recording location.
