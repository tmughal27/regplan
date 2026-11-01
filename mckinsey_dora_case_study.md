# Case study: Large European FI DORA programme (McKinsey, 2024)

Documentation for running the regplan Optimize → Evaluate → Simulate path on a real, published programme.

Suggested location in repo: `docs/case_studies/mckinsey_dora.md`, with inputs in `src/regplan/examples/mckinsey_dora/`.

---

## 1. Purpose

Run regplan on a real regulatory programme with a real deadline and a published budget, so that:

1. The scheduler (CP-SAT) is exercised on a genuine resource-constrained, deadline-driven problem.
2. The finance engine and Monte Carlo output can be **calibrated** against a published cost figure.
3. The simulation can be **backtested**, because the deadline has already passed.

This is a calibration case, not a reproduction. The source publishes aggregates only. Everything below the aggregate level is an explicit assumption (see section 4).

## 2. Source and provenance

| Item | Detail |
|---|---|
| Primary source | McKinsey & Company, "Europe's new resilience regime: The race to get ready for DORA" (Boehm, Schneider et al.), 28 June 2024 |
| URL | https://www.mckinsey.com/capabilities/risk-and-resilience/our-insights/europes-new-resilience-regime-the-race-to-get-ready-for-dora |
| Nature of source | Consultancy survey of major European FIs and ICT providers, plus one anonymised large-FI vignette |
| Regulation | Digital Operational Resilience Act, Regulation (EU) 2022/2554, applicable from 17 January 2025 |
| Secondary (scale contrast only) | Hard2bit, Spanish asset manager DORA case study, ~120 employees, 5-month programme (vendor case, no cost data): https://hard2bit.com/en/case-studies/dora-financial-institution/ |

Verify all regulatory references against the Official Journal text on EUR-Lex before treating the pack as authoritative.

## 3. Case narrative (facts only)

- The institution is EU-based, market-leading, with operations in 50+ countries. It finished a major technology risk remediation programme in 2023.
- It set up a small DORA programme in Q4 2023, found it could not scale across the group, and redesigned it from the start of Q1 2024 with a target of meeting requirements by January 2025.
- Redesigned structure was in place within one month: 300+ staff onboarded, planning and gap assessment complete.
- Organised as activity clusters per DORA content area, each with a cluster lead, plus a single point of contact per operating entity, with centralised tracking tooling.
- Final planned group-wide DORA spend: nearly EUR 100M, split between programme orchestration and technology control upgrades.

Industry context from the same article: typical earmark of EUR 5-15M for strategy/planning/design/orchestration, with full implementation estimates 5-10x that; contract remediation scope ranging from 20 to 3,000 contracts; about one third of FIs confident of meeting all expectations by January 2025; all expecting some work to continue past the deadline; 70% expecting permanently higher run costs.

## 4. Parameter register

Every numeric input carries an ID and a provenance tag. Use these IDs as the `source`/`assumption_id` fields in your Assumptions YAML so every output traces back (design principle 2).

Provenance tags: **SRC** = stated in the McKinsey article. **DER** = derived arithmetically from SRC values. **ASM** = my modelling assumption, not sourced; replace freely.

### 4.1 Sourced and derived

| ID | Parameter | Value | Tag | Note |
|---|---|---|---|---|
| S-01 | Regulatory deadline | 2025-01-17 | SRC | DORA application date |
| S-02 | Programme redesign start | 2024-01-01 (start of Q1 2024) | SRC | |
| S-03 | Mobilisation time | 1 month | SRC | Planning and gap assessment complete |
| S-04 | Staff onboarded | 300+ | SRC | Use 300 |
| S-05 | Content areas (clusters) | 5: ICT risk mgmt; incident mgmt/reporting; resilience testing; third-party risk; information sharing | SRC | |
| S-06 | Typical planning/orchestration earmark | EUR 5-15M | SRC | Industry survey |
| S-07 | Full-implementation multiple | 5-10x S-06 | SRC | Early estimates |
| S-08 | Reference total programme spend | ~EUR 100M | SRC | "Final planned", not audited actuals |
| S-09 | Contract remediation scope range | 20 to 3,000 contracts | SRC | Across institutions |
| S-10 | Deadline confidence | ~1/3 of FIs confident of full compliance by Jan 2025 | SRC | Directional validation only |
| S-11 | Post-deadline work | All FIs expect some effort beyond Jan 2025 | SRC | Model a BAU rollout tail |
| S-12 | Permanent run-cost uplift | 70% of FIs expect it | SRC | Optional: include as post-programme cost stream |
| S-13 | RTS batch 2 finalisation | July 2024 | SRC | Source of regulatory-timing risk |
| D-01 | Full-implementation envelope | EUR 25-150M | DER | S-06 x S-07 |
| D-02 | Implied labour-cost consistency | 300 staff x 12 months x EUR 10k = ~EUR 36M, i.e. ~35% of EUR 100M | DER (uses ASM A-03) | Sanity check on A-03 and A-04 |

### 4.2 Assumptions (replace with your own; keep the IDs)

| ID | Parameter | Value | Rationale |
|---|---|---|---|
| A-01 | Programme calendar | Monthly buckets, 2024-02 to 2025-12 | Feb start = S-02 + S-03; tail covers post-deadline rollout (S-11) |
| A-02 | Resource pools (FTE) | Risk & Compliance 90; Technology 130; Legal & Procurement 50; PMO 30 (sum 300) | Split is unsourced; only the total (S-04) is sourced |
| A-03 | Loaded cost per FTE-month | EUR 10,000 | Chosen so labour ~ 35% of S-08 (see D-02) |
| A-04 | Labour share of total cost | 35% | Remainder is technology spend, licences, external providers |
| A-05 | Discount rate | 8% | Placeholder |
| A-06 | Cost of delay | EUR 1.0M per month late on any hard-deadline item | Placeholder; tune or run a sweep |
| A-07 | Contract remediation unit cost | EUR 18,000 per contract | Calibrated so 500 contracts = 9% of EUR 100M |
| A-08 | Contract remediation throughput | 150 contracts per month (Legal pool) | Placeholder; counterparty responsiveness drives variance |
| A-09 | Baseline contract count | 500 | Between S-09 bounds |
| A-10 | Duration uncertainty | Triangular (min, mode, max) per item, table 5.1 | Unsourced |
| A-11 | Regulatory-timing shock | P = 0.30; adds +1 to +2 months to TPR-03 and TST-02 | Motivated by S-13 but values are assumed |
| A-12 | Counterparty delay | Lognormal multiplier on TPR-03 duration, median 1.0, sigma 0.3 | McKinsey notes smaller third parties struggle to comply; sigma assumed |
| A-13 | Overall cost-total target | EUR 100M | Equals S-08; used for calibration, not as a constraint |

## 5. Model structure

### 5.1 WorkItems

Dependencies are inferred from the scoping section of the article (critical functions drive everything else; provider scoping precedes contract remediation; recovery times drive testing). They are not stated as a network by the source.

"Share" is the item's share of the EUR 100M total (calibration target A-13). Durations are triangular (min, mode, max) in months (A-10).

| Item | Cluster | Description | Share | Duration | Pool | Predecessors |
|---|---|---|---|---|---|---|
| PMO-01 | Orchestration | Programme orchestration, central tracking tool | 12% | 12 (fixed) | PMO | none |
| ICT-01 | ICT risk | Risk framework, policies, independent control function | 8% | (3, 4, 6) | Risk | none |
| ICT-02 | ICT risk | Critical/important function mapping and recovery objectives | 7% | (2, 3, 5) | Risk | none |
| ICT-03 | ICT risk | Technology control upgrades | 30% | (6, 8, 12) | Technology | ICT-02 |
| INC-01 | Incident | Incident classification and reporting process | 4% | (2, 3, 5) | Risk | ICT-01 |
| INC-02 | Incident | Incident tooling and centralised reporting | 6% | (3, 5, 8) | Technology | INC-01 |
| TST-01 | Testing | Resilience testing programme incl. switchover tests | 6% | (3, 5, 8) | Technology | ICT-02 |
| TST-02 | Testing | Threat-led penetration test scenarios and execution | 5% | (3, 5, 9) | Technology | TST-01 |
| TPR-01 | Third-party | ICT provider scoping and criticality classification | 3% | (2, 3, 5) | Legal | ICT-02 |
| TPR-02 | Third-party | Register of information | 4% | (2, 3, 5) | Legal | TPR-01 |
| TPR-03 | Third-party | Contract remediation (N contracts) | 9% at N=500 | N / 150 + 1, then A-12 multiplier | Legal | TPR-01 |
| TPR-04 | Third-party | Concentration risk, monitoring, exit plans | 3% | (3, 4, 6) | Risk | TPR-02 |
| INF-01 | Info sharing | Information-sharing arrangements | 1% | (1, 2, 3) | Risk | none |
| TRN-01 | Orchestration | Training and BAU rollout across entities | 2% | (3, 4, 6) | PMO | ICT-01 |

Shares sum to 100%. Cost for TPR-03 scales as `A-07 x N` rather than a fixed share.

Item FTE demand (for the capacity constraint):

```
labour_cost   = share x total_cost x A-04
fte_demand    = labour_cost / (duration_months x A-03)
```

### 5.2 Deadline handling

- Hard deadline S-01 applies to ICT-01, ICT-02, ICT-03, INC-01, INC-02, TST-01, TPR-01, TPR-02, TPR-03.
- TST-02, TPR-04, INF-01, TRN-01 and PMO-01 are soft: late completion incurs A-06 per month, and TRN-01 is allowed to run past the deadline to represent S-11.
- Expected critical path in the baseline: ICT-02 -> ICT-03 (about 3 + 8 = 11 months against roughly 11.5 available). With these assumed durations, deadline risk is high by construction. That is intended, as it is consistent with S-10, but it is a consequence of A-10, not a finding.

### 5.3 Modelling note for regplan

DORA obligations apply at entity level, not per application, while regplan matches obligations to applications. Pick one mapping and document it:

- **Option A (recommended):** model "applications" as service groupings, e.g. `APP-GRP` (group governance), `APP-CIF` (critical-function platforms), `APP-TPR` (third-party estate), `APP-SOC` (incident/testing tooling). Obligations match by trigger conditions on those.
- **Option B:** a single synthetic application `APP-DORA` carrying all obligations. Simpler, but the scorer and trigger logic get little exercise.

## 6. Scenarios

| ID | Name | Change vs baseline | What it tests |
|---|---|---|---|
| SC-0 | Baseline | N = 500 contracts, start 2024-01, deadline S-01 | Calibration to EUR 100M |
| SC-1 | Narrow scope | N = 20 | Lower bound of S-09 |
| SC-2 | Broad scope | N = 3,000 | Upper bound of S-09; should stress capacity and likely breach the deadline |
| SC-3 | Late mobilisation | Start 2024-04-01 | Deadline infeasibility and explanation |
| SC-4 | Capacity squeeze | Legal 50 -> 25 FTE | Which constraint binds; minimal infeasibility reason |
| SC-5 | Budget cap | Cap total at EUR 70M | Cost vs schedule trade-off, mode selection |
| SC-6 | Greedy baseline | Replace CP-SAT with earliest-deadline-first heuristic | Optimisation gain (headline result) |

## 7. Simulation specification

| Setting | Value |
|---|---|
| Runs | 10,000 |
| Seed | 42 (fixed) |
| CP-SAT | `random_seed` fixed, `num_workers=1` for determinism |
| Item durations | Triangular per section 5.1 |
| Regulatory-timing shock | Bernoulli(0.30), +1 to +2 months to TPR-03 and TST-02 (A-11) |
| Counterparty delay | Lognormal multiplier on TPR-03 duration (A-12) |
| Scope uncertainty | Sample N from {20, 500, 3000} with weights you choose, or run as separate scenarios (SC-0/1/2) |
| Outputs | P50/P80/P95 total cost; P50/P80/P95 NPV; P(all hard-deadline items complete by S-01); completion-month distribution per item |

## 8. Validation criteria

Pass/fail checks. The thresholds are my suggestions, so adjust them but record the change.

| ID | Check | Criterion |
|---|---|---|
| V-1 | Cost calibration | SC-0 P50 total cost within +/-25% of EUR 100M (S-08) |
| V-2 | Envelope | SC-0 P5-P95 cost range lies inside the D-01 envelope (EUR 25-150M) |
| V-3 | Deadline risk, directional | P(all hard items on time) clearly below 100% and above 0%; compare to S-10 (about 1/3 confidence) as a directional check only, not a calibration target |
| V-4 | Post-deadline tail | Non-zero cost and activity after S-01 in baseline (S-11) |
| V-5 | Scope monotonicity | Cost and finish date non-decreasing from SC-1 to SC-0 to SC-2 |
| V-6 | Infeasibility | SC-3 and SC-4 produce a loud, specific explanation, not a silent plan |
| V-7 | Determinism | Two runs with identical inputs, seed and package versions yield byte-identical JSON |
| V-8 | Traceability | `regplan explain` on TPR-03 resolves to the inputs and assumption IDs that drove its date and cost |
| V-9 | Optimiser value | SC-0 CP-SAT NPV cost lower than SC-6 greedy; report the percentage gap |

## 9. Running it

Expected layout:

```
src/regplan/examples/mckinsey_dora/
├── landscape.yaml
├── assumptions.yaml
├── packs/
│   └── dora.yaml
└── scenarios/
    ├── sc1_narrow.yaml
    ├── sc2_broad.yaml
    ├── sc3_late_start.yaml
    └── sc4_capacity_squeeze.yaml
```

Commands (from the project README):

```bash
D=src/regplan/examples/mckinsey_dora

# 1. Validate inputs
regplan validate $D/landscape.yaml

# 2. Baseline plan
regplan plan $D/landscape.yaml --packs $D/packs/dora.yaml

# 3. Monte Carlo
regplan simulate $D/landscape.yaml --runs 10000 --seed 42

# 4. Scenario comparison
regplan compare baseline sc2_broad

# 5. Trace the critical item
regplan explain $D/landscape.yaml APP-TPR:R-DORA-TPR-03

# 6. Report
regplan report ./runs/<run-dir>/ --out ./reports/

# 7. Determinism check
regplan simulate $D/landscape.yaml --runs 10000 --seed 42 > a.json
regplan simulate $D/landscape.yaml --runs 10000 --seed 42 > b.json
cmp a.json b.json && echo "byte-identical"
```

Adjust the `compare` and `explain` identifiers to match your scenario and WorkItem ID conventions.

## 10. Input templates

These templates are illustrative. The keys are placeholders; map them to your actual Pydantic models in `src/regplan/models/`. What matters is that every value carries its register ID.

### assumptions.yaml

```yaml
assumptions:
  - id: S-01
    description: DORA application date
    value: "2025-01-17"
    provenance: SRC
  - id: S-04
    description: Staff onboarded
    value: 300
    provenance: SRC
  - id: S-08
    description: Reference total programme spend (EUR)
    value: 100000000
    provenance: SRC
  - id: A-03
    description: Loaded cost per FTE-month (EUR)
    value: 10000
    provenance: ASM
  - id: A-04
    description: Labour share of total cost
    value: 0.35
    provenance: ASM
  - id: A-05
    description: Discount rate
    value: 0.08
    provenance: ASM
  - id: A-06
    description: Cost of delay per month on hard-deadline items (EUR)
    value: 1000000
    provenance: ASM
  - id: A-07
    description: Contract remediation unit cost (EUR)
    value: 18000
    provenance: ASM
  - id: A-08
    description: Contract remediation throughput (contracts per month)
    value: 150
    provenance: ASM
  - id: A-09
    description: Baseline contract count
    value: 500
    provenance: ASM
```

### landscape.yaml (excerpt)

```yaml
resource_pools:
  - id: POOL-RISK
    capacity_fte: 90        # A-02
  - id: POOL-TECH
    capacity_fte: 130       # A-02
  - id: POOL-LEGAL
    capacity_fte: 50        # A-02
  - id: POOL-PMO
    capacity_fte: 30        # A-02

horizon:
  start: "2024-02-01"       # S-02 + S-03
  end: "2025-12-31"         # A-01
  bucket: month

work_items:
  - id: ICT-02
    description: Critical/important function mapping and recovery objectives
    cost_share: 0.07
    duration_months: {min: 2, mode: 3, max: 5}   # A-10
    pool: POOL-RISK
    predecessors: []
    deadline: {date: "2025-01-17", kind: hard}   # S-01
  - id: ICT-03
    description: Technology control upgrades
    cost_share: 0.30
    duration_months: {min: 6, mode: 8, max: 12}
    pool: POOL-TECH
    predecessors: [ICT-02]
    deadline: {date: "2025-01-17", kind: hard}
  - id: TPR-03
    description: Contract remediation
    scale_driver: A-09
    unit_cost: A-07
    throughput: A-08
    pool: POOL-LEGAL
    predecessors: [TPR-01]
    deadline: {date: "2025-01-17", kind: hard}
  # ... remaining items from section 5.1
```

### dora.yaml (RegulationPack, chapter level)

```yaml
pack: dora
source: "Regulation (EU) 2022/2554"
verify_against: "EUR-Lex Official Journal text"
obligations:
  - id: R-DORA-ICT
    area: ICT risk management
  - id: R-DORA-INC
    area: ICT-related incident management, classification and reporting
  - id: R-DORA-TST
    area: Digital operational resilience testing (incl. TLPT)
  - id: R-DORA-TPR
    area: ICT third-party risk management (incl. register of information)
  - id: R-DORA-INF
    area: Information-sharing arrangements
```

The five areas match the content areas McKinsey lists. Replace area-level entries with article-level obligations (verified against the legal text) if you want finer WorkItem matching.

## 11. What you can and cannot claim

Can claim:
- The model is calibrated to a published planning figure (about EUR 100M) from a real large-FI DORA programme.
- Scenario ranges for contract scope (20 to 3,000) come from published industry data.
- Results are deterministic and every number traces to an input or assumption ID.

Cannot claim:
- That the simulation reproduces the institution's actual schedule or spend. The source gives a planned total and no schedule, cluster costs or dependencies.
- That P(deadline miss) is validated against reality. The survey's confidence share is a directional signal only, and "confident" is not the same as "met".
- That any ASM-tagged value is evidence-based. Present them as stated assumptions and show sensitivity to the ones that matter (A-06, A-08, A-10).

Recommended sensitivity sweeps: A-06 (cost of delay), A-08 (legal throughput), duration modes for ICT-03, and the A-11 shock probability.

## 12. Known limitations

- Single anonymised vignette plus survey aggregates. No audited actuals.
- The EUR 100M is a final planned figure and the orchestration/technology split is not disclosed, so the item cost shares are mine.
- The article predates the January 2025 deadline, so no outcome is reported.
- The Hard2bit case is a vendor write-up with no cost figures. Use it only for duration scale.
- Regulatory references here are at the content-area level; confirm article-level obligations against EUR-Lex.
