# Adarsh AI Persona Evals Report

## 1. Evaluation Goal

The goal of the evaluation was to measure whether the assistant behaves like a reliable interview-facing persona rather than just a fluent chatbot. I focused on three areas that matter for the Scaler assignment: voice quality, grounded chat behavior, and booking reliability. A good result was not defined as "the model answered something reasonable"; it was defined as "the assistant answered accurately from real evidence, handled follow-ups coherently, and preserved a real scheduling path."

## 2. Voice Quality

I evaluated voice quality on latency, accuracy, and task completion.

- **Latency**
  I measured time from caller utterance end to first assistant response in Vapi browser tests. The target was to keep first response behavior under 2 seconds so the conversation still felt live. In practice, the assistant stayed in the low-1-second range under normal conditions, which felt acceptable for a conversational recruiter-style interaction.

- **Accuracy**
  I used a small set of scripted spoken prompts covering:
  - identity: "Who are you?"
  - role fit: "Why is Adarsh a strong fit for this role?"
  - technical background: "Tell me about his RAG experience."
  - projects: "Tell me about a GitHub project and its tradeoffs."
  - scheduling: "Can you help me schedule an interview?"

  Responses were compared against grounded facts from the resume and project artifacts. The main criterion was whether the answer stayed aligned with what was actually known, and whether it avoided inventing unsupported details when the prompt was vague.

- **Task Completion**
  A voice session counted as successful when the assistant:
  1. introduced itself as Adarsh's AI representative,
  2. answered the first question coherently,
  3. handled at least one follow-up naturally,
  4. and preserved a valid booking path.

  I did not count a session as successful if the assistant sounded fluent but drifted away from grounded facts or broke the scheduling flow.

## 3. Chat Groundedness

I evaluated chat groundedness on hallucination rate, retrieval quality, and answer faithfulness.

- **Hallucination Rate**
  I defined a hallucination as any answer that introduced unsupported employers, dates, achievements, project claims, or technical details that were not justified by the available grounding. This matters especially for a resume agent, because plausible-sounding overclaiming is more damaging than a short but honest answer.

- **Retrieval Quality**
  I checked whether the top retrieved chunks actually matched the question intent. This was especially important for:
  - role-fit prompts, where the resume should dominate,
  - RAG-specific prompts, where WNS / NS Global Services experience should surface,
  - GitHub project prompts, where the system should retrieve the correct project rather than unrelated chunks.

- **Answer Faithfulness**
  Even when retrieval was relevant, the final answer could still drift. So I separately evaluated whether the answer stayed faithful to the retrieved evidence instead of embellishing it.

## 4. LLM-as-a-Judge Methodology

I used LLM-as-a-judge as a structured evaluator, not as the sole source of truth. The judge consumed:
- the user question,
- the retrieved context,
- the assistant answer.

The judge was asked to score:
- groundedness,
- retrieval relevance,
- helpfulness,
- hallucination risk.

Example judge schema:

```json
{
  "groundedness_score": 1,
  "retrieval_relevance_score": 1,
  "helpfulness_score": 1,
  "hallucination": false,
  "notes": ""
}
```

Judge criteria:
- Is the answer fully supported by the retrieved evidence?
- Are the retrieved chunks relevant to the actual question?
- Does the answer remain specific without inventing facts?
- Does the answer stay useful under a follow-up?

This approach worked well because it turned vague qualitative review into something repeatable. However, I still kept manual inspection as the final check, especially for subtle failures where an answer sounded polished but was slightly overstated.

## 5. Failure Modes Found And Fixed

### Failure Mode 1: Booking looked complete before it was actually reliable

Initially, the product had booking paths through Google Calendar and Cal.com, but those integrations were fragile across local and deployed environments. This created the worst kind of UX failure: the UI looked booking-ready, but provider credentials or configuration could still break the actual confirmation path.

**Fix**
I moved the production booking experience to a stable Calendly handoff. That ensured every visible booking action resolved to a real live scheduling flow with confirmation, even if the lower-level provider integrations were not stable enough for demo use.

### Failure Mode 2: Voice scheduling responses sounded unnatural

In early voice tests, the assistant tried to read a raw booking URL aloud. Technically this was correct, but it sounded awkward and brittle on a live call. It also increased the chance of user confusion because a URL spoken with protocol and symbols is hard to follow.

**Fix**
I rewrote the voice prompt so the assistant uses a spoken booking path and shorter scheduling language. This made the interaction feel more like a real recruiter-facing assistant and less like a literal string reader.

### Failure Mode 3: Public UI exposed weak and low-signal states

The original interface exposed availability panels and empty sections that pulled attention away from the actual demo path. Some states were technically accurate but visually weak, which reduced confidence during the demo.

**Fix**
I simplified the homepage to the three core actions that matter: ask the persona, book the interview, and call the voice agent. I also removed noisy source metadata from the visible chat UI so the user sees strong answers rather than retrieval internals.

## 6. What I Would Improve With 2 More Weeks

If I had two more weeks, I would focus on three upgrades:

1. **True end-to-end voice booking**
   Instead of a booking-link handoff, I would connect the voice assistant to tool-driven calendar actions so it could check availability, collect the caller's details, and confirm the interview directly inside the call.

2. **A batch eval harness**
   I would build a repeatable evaluation harness that runs saved prompts through retrieval, generation, and LLM-as-a-judge scoring so groundedness regressions are measurable rather than anecdotal.

3. **Richer GitHub indexing**
   I would improve project-level grounding by extracting more structured repository summaries, tradeoffs, and implementation details directly from project artifacts so repo-specific answers become sharper and less dependent on generic summaries.
