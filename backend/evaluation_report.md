# Model Evaluation Report: Base vs. Fine-Tuned Llama-3.1-8B

This report documents the performance comparison between the raw baseline model and the fine-tuned adapter version on internal corporate triage tickets.

## Summary Metrics

| Metric | Base (Un-tuned) | Fine-Tuned (Adapters) | Change |
| :--- | :---: | :---: | :---: |
| JSON Parse Success Rate (Any Format) | 100.0% | 100.0% | **+0.0%** |
| Strict JSON Output (No fences/filler) | 0.0% | 100.0% | **+100.0%** |
| Markdown Fences Output (```json) | 100.0% | 0.0% | **-100.0%** |
| Preamble / Conversational Filler | 100.0% | 0.0% | **-100.0%** |
| Department Classification Accuracy | 100.0% | 100.0% | **+0.0%** |
| Priority Classification Accuracy | 40.0% | 60.0% | **+20.0%** |
| Perfect Triage Match (Strict + Correct) | 40.0% | 60.0% | **+20.0%** |
| Average Generation Latency | 4.2s | 2.9s | **-1.36s** |
| Average Output Character Length | 448.2 chars | 258.9 chars | **-189.30 chars** |


## Sample Outputs Comparison

Here is a side-by-side comparison of the first 3 test samples:

### Sample 1 Ticket Input
> **Input Text:** yo i heard we get a bonus this year for performance? but its not clear to me how that works or who qualifies and stuff.

> **Expected JSON:** `{"department": "HR", "priority": "High", "llm_draft_reply": "Hello,\n\nThank you for your inquiry regarding bonuses. I can confirm that we do have a performance bonus structure in place. Let me explain how it works and who qualifies. Please let me know when you can chat.\n\nRegards,\nHR Team"}`

#### 🔴 Raw Base Output:
```text
```
{
  "department": "HR",
  "priority": "Medium",
  "llm_draft_reply": "The performance bonus is indeed a new initiative this year. To qualify, employees must meet or exceed their individual performance goals, which are set by their managers. The bonus amount will be based on a percentage of the employee's annual salary, and the exact percentage will depend on the company's overall performance. If you have any specific questions or concerns about your performance goals or the bonus process, I recommend reaching out to your manager or HR representative for more information."
}
```
```

#### 🟢 Raw Fine-Tuned Output:
```text
{"department": "HR", "priority": "Medium", "llm_draft_reply": "Thank you for your inquiry about the performance bonus. I will provide you with the necessary details regarding eligibility and the application process. Please let me know if you have any further questions."}
```

---

### Sample 2 Ticket Input
> **Input Text:** can u confirm if we still have mental health days? or was that part of the old policy? just trying to figure it all out!

> **Expected JSON:** `{"department": "HR", "priority": "High", "llm_draft_reply": "Hi,\n\nThank you for your question! Yes, we still offer mental health days as part of our leave policies. Let me know if you have any more questions, and I'll be happy to assist you further.\n\nBest,\nHR Team"}`

#### 🔴 Raw Base Output:
```text
```json
{
  "department": "HR",
  "priority": "Low",
  "llm_draft_reply": "Mental health days are still a part of our company's updated policy. You can take up to 3 mental health days per year, and they don't need to be taken consecutively. If you need more time, please discuss it with your manager. Remember, your well-being is important to us!"
}
```
```

#### 🟢 Raw Fine-Tuned Output:
```text
{"department": "HR", "priority": "Medium", "llm_draft_reply": "Yes, mental health days are still a part of our policy. If you need to take a day off for mental health reasons, please let HR know and we can help facilitate the process."}
```

---

### Sample 3 Ticket Input
> **Input Text:** uhhhh so what’s the policy on remote work hours? like can we clock in whenever or is there a set time we needa follow?

> **Expected JSON:** `{"department": "HR", "priority": "Medium", "llm_draft_reply": "Hello,\n\nThanks for reaching out! We have flexible remote work hours, but there are specific core hours when we expect all employees to be available. I'd be glad to explain more details.\n\nBest,\nHR Team"}`

#### 🔴 Raw Base Output:
```text
```
{
  "department": "HR",
  "priority": "Medium",
  "llm_draft_reply": "Hello! Our company allows flexible remote work hours, but we do have a core working hour policy from 10am-4pm. You can clock in outside of these hours, but you're expected to be available and responsive during core hours. If you have any specific scheduling needs or concerns, please reach out to your manager or HR for support."
}
```
```

#### 🟢 Raw Fine-Tuned Output:
```text
{"department": "HR", "priority": "Medium", "llm_draft_reply": "Thank you for your question. The remote work policy does allow for some flexibility in scheduling, but it’s essential to adhere to the standard working hours. Please refer to the employee handbook for specific details on remote work hours and any necessary approvals."}
```

---

