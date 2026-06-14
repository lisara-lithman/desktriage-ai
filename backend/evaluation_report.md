# Model Evaluation Report: Base vs. Fine-Tuned Llama-3.1-8B

This report documents the performance comparison between the raw baseline model and the fine-tuned adapter version on internal corporate triage tickets.

## Summary Metrics

| Metric | Base (Un-tuned) | Fine-Tuned (Adapters) | Change |
| :--- | :---: | :---: | :---: |
| JSON Parse Success Rate (Any Format) | 100.0% | 100.0% | **+0.0%** |
| Strict JSON Output (No fences/filler) | 13.3% | 100.0% | **+86.7%** |
| Markdown Fences Output (```json) | 86.7% | 0.0% | **-86.7%** |
| Preamble / Conversational Filler | 86.7% | 0.0% | **-86.7%** |
| Department Classification Accuracy | 60.0% | 100.0% | **+40.0%** |
| Priority Classification Accuracy | 46.7% | 46.7% | **+0.0%** |
| Perfect Triage Match (Strict + Correct) | 26.7% | 46.7% | **+20.0%** |
| Average Generation Latency | 4.7s | 3.2s | **-1.54s** |
| Average Output Character Length | 455.8 chars | 252.5 chars | **-203.27 chars** |


## Sample Outputs Comparison

Here is a side-by-side comparison of the first 3 test samples:

### Sample 1 Ticket Input
> **Input Text:** Hey, I saw something about reviews being due next month, but my calendar is just blank. I’m really not sure what’s going on with my team’s schedule. Can I get a heads up?

> **Expected JSON:** `{"department": "HR", "priority": "Medium", "llm_draft_reply": "Thank you for reaching out about the performance review schedule. I will verify the timeline for your team and get back to you with the necessary details to ensure you're prepared."}`

#### 🔴 Raw Base Output:
```text
```json
{
  "department": "HR",
  "priority": "Medium",
  "llm_draft_reply": "I've checked the team's schedule and it looks like the review dates were not synced with your calendar. I've sent a reminder to the team to update their calendars and also notified the HR department to double-check the review schedule. In the meantime, I recommend checking the team's shared calendar for any updates. If you have any further concerns, feel free to reach out to me directly."
}
```
```

#### 🟢 Raw Fine-Tuned Output:
```text
{"department": "HR", "priority": "Medium", "llm_draft_reply": "Thank you for your inquiry. I will verify the review schedule and get back to you with the details."}
```

---

### Sample 2 Ticket Input
> **Input Text:** Okay, so I thought the performance reviews were going to be done online but now I’m hearing they might be in-person? So confused! Are there any emails or something I can check?

> **Expected JSON:** `{"department": "HR", "priority": "Low", "llm_draft_reply": "I understand the confusion regarding the format of the performance reviews. I will confirm the arrangements and ensure you have all the necessary information to prepare."}`

#### 🔴 Raw Base Output:
```text
```json
{
  "department": "HR",
  "priority": "Medium",
  "llm_draft_reply": "I'd be happy to help you clarify the performance review process. Can you try checking your company's intranet or HR website for any updates on the review format? If you still can't find any information, you may want to reach out to your supervisor or HR representative directly to ask about the plans. They should be able to provide you with the most up-to-date information."
}
```
```

#### 🟢 Raw Fine-Tuned Output:
```text
{"department": "HR", "priority": "Medium", "llm_draft_reply": "Thank you for your inquiry. I will verify the performance review format and get back to you with the correct information."}
```

---

### Sample 3 Ticket Input
> **Input Text:** I heard from our last team meeting somethin’ about performance assessments? But I don’t think I caught the dates right, can someone help? I’m a bit all over the place with this!

> **Expected JSON:** `{"department": "HR", "priority": "Medium", "llm_draft_reply": "Thank you for your message. I will review the notes from the last team meeting and provide you with the details regarding the upcoming performance assessments."}`

#### 🔴 Raw Base Output:
```text
```
{
  "department": "HR",
  "priority": "Medium",
  "llm_draft_reply": "The performance assessments for Q2 are scheduled for June 15th and 16th. Please check the company calendar for confirmation. If you have any questions or concerns, feel free to reach out to your supervisor or HR representative."
}
```
```

#### 🟢 Raw Fine-Tuned Output:
```text
{"department": "HR", "priority": "Medium", "llm_draft_reply": "Thank you for your inquiry. The performance assessment dates were discussed in the last team meeting, and I can provide you with the details. Please let me know a good time to talk, and I will clarify the schedule for you."}
```

---

