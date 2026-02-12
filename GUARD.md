Below is a minimal, build-in-a-day ruleset (regex + probes) and a clean way to wire it into your FSM transition logic as guards.

1) Minimal ruleset: regex signals + “semantic probes”
1.1 Preprocess (do this once)

lowercase

normalize whitespace

keep punctuation (useful)

optional: strip code blocks if present

Keep two text views:

t_raw

t_norm (lower, normalized)

1.2 Regex signal sets (minimal but effective)
Ambiguity signals

Vague improvement verbs / goals

\b(improve|better|enhance|optimi[sz]e|increase|reduce|make|handle|support|enable|ensure)\b
Vague quality adjectives

\b(scalable|robust|reliable|secure|safe|fast|efficient|user[- ]?friendly|production[- ]?ready)\b
Missing object patterns (super cheap heuristic)

“make it …”, “improve it …”, “handle this …”

\b(make|improve|optimi[sz]e|fix)\s+(it|this|that)\b
No-metric hint (detect absence by checking if any metric token appears)

metric tokens:

\b(ms|s|sec|seconds|latency|throughput|qps|rps|fps|accuracy|f1|precision|recall|auc|bleu|rouge|wer|cer|cost|€|\$|budget|memory|gb|mb|cpu|gpu|watt|wh|kwh|sla|slo)\b
If none found and there are vague verbs/adjectives → ambiguity score up.

Conflicting constraints keywords

\b(fast|low latency)\b + \b(cheap|low cost)\b + \b(high accuracy|reliable|safe|secure)\b
(Implement as co-occurrence counts rather than one regex.)

Adversarial signals

\b(adversar(y|ial)|attack|bypass|evade|abuse|fraud|spam|bot(s)?|cheat|exploit|poison(ing)?|prompt injection|jailbreak|scrap(e|ing)|ddos|phish(ing)?|malware|red team)\b

\b(content moderation|trust and safety|t&s)\b

Incentives language:

\b(incentive|game(d|ing)?|arms race|cat[- ]?and[- ]?mouse|adaptive|strateg(y|ic))\b

Irreversibility signals

High-stakes domains:

\b(medical|patient|clinical|diagnos(is|e)|treatment|surgery|drug|dose|legal|court|lawsuit|compliance|regulator(y)?|safety[- ]critical|aviation|automotive|nuclear|financial advice|credit decision)\b

Irreversible/rollback language:

\b(irrevocable|irreversible|cannot undo|no rollback|one[- ]?way door|point of no return|permanent)\b

“High impact” markers:

\b(life|death|harm|injur(y|ies)|liability|fine(s)?|penalt(y|ies)|prison|reputation(al)? damage)\b

Institutional signals

Stakeholder / authority words:

\b(board|committee|leadership|exec(s)?|legal team|procurement|union|works council|regulator|auditor|compliance|risk team|security team|stakeholder(s)?)\b

Politics/optics/bureaucracy:

\b(politic(s|al)|optics|narrative|buy[- ]?in|alignment|approval|sign[- ]?off|veto|governance|bureaucrac(y|ies)|public sector)\b

Blocked-by-org phrasing:

\b(they (won't|will not|refuse)|not allowed|forbidden|blocked|cannot get approval)\b

1.3 Minimal scoring (transparent)

For each archetype, compute:

regex_hits: count of matched patterns (cap at e.g. 5)

absence_penalties: for ambiguity mainly (no metric tokens present)

probe_scores: from semantic probes (0/1 with confidence)

Example scoring (works well)

score = clip01(0.18*regex_hits + 0.35*probe_yes + 0.25*absence + 0.12*conflict)
Where:

probe_yes ∈ [0,1] (LLM says yes with confidence)

absence ∈ {0,1} (e.g., missing metric)

conflict ∈ [0,1] (co-occurrence of competing constraints)

Thresholds

>= 0.30: present

>= 0.60: dominant

>= 0.80: critical

1.4 Semantic probes (tiny set, high value)

Run these on the initial statement (and optionally the last user turn). Each returns: yes/no + confidence.

Ambiguity probes

“Is the success criterion (metric + target + horizon) explicitly defined?”

“Is scope clearly defined (in/out)?”

“Are constraints clearly listed?”

Interpretation:

If “no” with high confidence on (1) or (2) ⇒ ambiguity up.

Adversarial probes

“Is there an agent that may try to evade, exploit, or adapt to the solution?”

“Is this in security, fraud, abuse, moderation, or competitive setting?”

Irreversibility probes

“Would an error cause serious harm, legal exposure, or be hard to roll back?”

“Is a rollback/pilot feasible?”

Institutional probes

“Are approvals, politics, optics, or governance likely to be the binding constraint?”

“Is there a named authority/veto holder involved?”

Minimal implementation tip

Ask the model to output strict JSON:

{probe_id, answer: "yes"|"no", confidence: 0..1}

1.5 Output (what you store)

Store both:

danger_scores (4 floats)

evidence (top regex hits + probe answers)

This makes debugging the classifier easy.

2) Integration into FSM logic: guards on edges

Think of your FSM as:

states: S0..S9

transitions: edges

guards: boolean predicates that must pass

2.1 Add a “DangerGate” step at the top

Before you commit to any main FSM:

Entry

On new problem statement:

run danger_classifier(text)

set autonomy_level

set required_modifiers

Then route

If ambiguity ≥ 0.60 → force FSM-1 (Clarify & Frame)

Else choose initial base FSM via your normal router (not covered here)

Apply modifiers (adversarial, irreversible, institutional)

2.2 Guards: minimal set that prevents bad moves
Guard G1: “No execution while ambiguous”

Block transitions into Execute/Build states unless definition is complete.

Blocks

Any S3 Plan → S4 Execute

Any S2 Model → S4 Execute
when:

ambiguity >= 0.60 AND definition_complete == false

definition_complete can be a simple boolean you set when you have:

metric/target/horizon OR explicitly “no metric, exploratory”

scope in/out

constraints list

Guard G2: “No irreversible decisions without verification gate”

Block irreversible transitions unless review/verification done.

Blocks

S6 Evaluate → S7 Decide (if decision is irreversible)

S7 Decide → S4 Execute (if execution is irreversible)
when:

irreversibility >= 0.60 AND verification_passed == false

verification_passed becomes true after either:

FSM-5 Verify completed

OR explicit independent review recorded

Guard G3: “Adversarial requires monitoring loop”

Block “finalize” unless monitoring/iteration plan exists.

Blocks

S8 Harden → S9 Close
when:

adversarial >= 0.60 AND monitoring_plan_exists == false

Guard G4: “Institutional requires stakeholder/veto map”

Block “commit” decisions unless stakeholder map exists.

Blocks

S3 Plan → S7 Decide

S7 Decide → S8 Harden
when:

institutional >= 0.60 AND stakeholder_map_exists == false

2.3 Modifiers: how they change the FSM

Instead of separate FSMs, treat danger archetypes as wrappers that inject required substates.

Ambiguity modifier (A)

Inject required substates before progress:

S1 Clarify must include: metric, scope, constraints

Create an explicit ProblemDefinition artifact node

Irreversibility modifier (I)

Inject “gates”:

IndependentReview

Pilot/Canary

RollbackPlan (or explicit “none possible”)

Adversarial modifier (D)

Inject:

ThreatModel

DefenseInDepth

Detection/Response

IterationCadence

Institutional modifier (P)

Inject:

StakeholderMap

VetoPoints

CommsPlan

IncrementalRollout

These are graph nodes + checklist completion flags.

3) Day-1 implementation plan (concrete)
Step 1: Implement danger_regex_features(text)

returns counts + flags:

has_metric_tokens

cooccur_fast_cheap_safe

hit lists per archetype

Step 2: Implement danger_probes(text) (4–8 probes total)

strict JSON output

cache results per text hash

Step 3: Implement danger_score(features, probes)

compute 4 scores + evidence

Step 4: Integrate with FSM engine

Create DangerContext on trace start

Add guards G1–G4 to transition table

Add “checklist flags” that get set as the conversation proceeds

Step 5: Test quickly with 50–100 hand examples

Aim for high recall

False positives are acceptable (they just cause extra questions)

4) Tiny example (how it behaves)

Input: “Make our model safer and scalable for production.”

Classifier:

Ambiguity: high (vague + no metrics)

Irreversibility: maybe medium if “safer” triggers (depends)

Institutional: maybe low unless stakeholders mentioned

Routing:

Force FSM-1 (Clarify)

Block execute/design until definition complete