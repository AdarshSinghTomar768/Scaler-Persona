# Evals Report

## Voice Quality

I measured voice quality on three dimensions:

- Latency: time to first spoken response after caller utterance end. Target was under 2 seconds. The design keeps retrieval local and uses a single backend call path so the main remaining variable is the voice platform and LLM latency.
- Accuracy: whether answers match grounded resume and repo facts. I reviewed calls against source excerpts returned by the backend.
- Task completion: whether the agent answered follow-ups, handled availability lookup, and completed booking without human intervention.

## Chat Groundedness

I measured chat quality using:

- Hallucination rate: percentage of responses containing unsupported facts. I sampled prompt sets across resume, project tradeoffs, and edge-case questions.
- Retrieval quality: whether top retrieved chunks came from the right source. I used targeted prompts for RAG work, repo summaries, and role fit.
- Citation usefulness: whether the UI surfaced enough source context for manual inspection.

## Failure Modes And Fixes

1. Resume retrieval was too coarse.
   Fix: I added PDF text extraction plus smaller chunking so questions about RAG work and experience hit the correct section.

2. Generic “why are you a fit” prompts retrieved repo docs instead of the resume.
   Fix: I added lightweight query expansion and a resume-source boost in ranking.

3. Booking flow could appear complete without real provider credentials.
   Fix: I made the API explicitly return `missing_credentials` when Cal.com or Google Calendar is not configured, instead of pretending to confirm a booking.

## Two More Weeks

- Add full tool-calling orchestration so the chat assistant can collect booking details in a single conversational thread without a separate form.
- Add production eval harnesses for voice interruption handling, first-token latency, and retrieval precision at k.
- Add deployment automation for Vercel or Fly.io plus provider bootstrap scripts for Vapi, Twilio, and Cal.com.
