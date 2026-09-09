# PO Exception Triage

An AI assistant that helps retail merchandising planners handle problem purchase orders quickly, with a clear and defensible answer.

## The problem

Large retailers place thousands of purchase orders (POs) every season. A steady stream of them go wrong: the supplier confirms fewer units than ordered, the delivery date slips, too much arrives, stock is going to land in the wrong season, or a wholesale contract is at risk.

Each of these is a decision with money attached: markdowns, stockouts, lost sales, or contract penalties. Today a planner works through them by hand, checking each PO against long policy documents. It is slow, easy to get wrong, and hard to keep consistent at scale.

## What it does

A planner asks a normal question in plain English, for example:

> "PO-88405 came in short and the ETA has slipped, what's going on?"

The assistant replies with a decision they can act on and defend:

- One recommended action
- The key numbers behind it (how far short, how late, value at risk)
- The exact policy clauses the recommendation is based on, quoted
- A confidence level
- Who to escalate to, if needed

If the policy does not cover the case, or the underlying data looks broken, it does not guess. It says so and points to the right person.

## How it works (in plain terms)

Think of it as two specialists working in sequence:

1. **The fact-finder.** Looks up the PO, compares what was ordered against what is coming, checks how late it is, and works out how serious the problem is. It is deliberately not allowed to see the policy, so it can never invent a rule. Its calculations are done in plain code, so the numbers are exactly reproducible.

2. **The policy advisor.** The only part that reads the company rulebook. It must point to a real clause for everything it recommends. When the rules are silent or contradict each other, it escalates instead of making something up.

The result is an answer that is grounded in real policy, shows its working, and is safe to act on.

## What makes it trustworthy

- Every recommendation quotes the actual policy text it relied on.
- The numbers are calculated in code, not guessed by the AI.
- It escalates when it is unsure, rather than sounding confident and being wrong.
- It never exposes personal contact details. Escalation is by role only (for example, "Regional Merchandising Manager").

## What's inside

- `backend/` — the two-agent AI and the API that runs it.
- `frontend/` — the screen a planner uses: a list of flagged POs, a question box, and the recommendation.

## Try it

You will need an OpenAI API key. Step-by-step instructions live in `backend/README.md` and `frontend/README.md`. In short:

1. Start the backend (the AI and its API).
2. Start the frontend and open it in your browser.
3. Pick a flagged PO, ask your question, and read the recommendation.

## Good to know

This is a working prototype built on realistic but synthetic data (sample purchase orders and policy documents). It shows how the approach works; it is not wired into a live retail system.
