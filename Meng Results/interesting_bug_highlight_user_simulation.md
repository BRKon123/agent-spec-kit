# Interesting finding — user simulation study

## Task **T42** — issue change mid-conversation (mobile data vs replacement SIM)

| Field | Value |
|--------|--------|
| **Study run** | `20260528T172621Z` |
| **Scenario** | `test_t42_sim_study` |
| **Case** | `llm_model=gpt5nano+persona=seed3_multi_issue_user` |
| **Persona** | `multi_issue_user` — mentions multiple issues before prioritising |
| **Manual script (same task)** | **Passed** F-oracle — no support ticket opened during the scripted flow |
| **Failure type** | `simulation_discovered_failure` |

### Why this is a real issue (not “tool called early”)

The manual script for T42 keeps the agent on **mobile data troubleshooting** and explicitly avoids opening a replacement-SIM path. The simulated user states up front that they **do not want a replacement SIM shipped** and that the **core issue is data**.

In this run the agent still **creates support ticket `TCK-00001` in the first segment**, then **escalates** it with notes about **“replacement options”** and the SIM-in-laundry story. That violates the scenario oracle (`assert_no_mutations` / zero tickets at the checkpoint) and steers the **final resolution** toward ticketing/escalation instead of data diagnosis — behaviour the fixed manual transcript does not exhibit.

**Oracle failure:** `assert_that: expected zero tickets, found 1`

**Tool path:** `authenticate_customer → check_outage → run_line_diagnostic → send_troubleshooting_step → record_user_action → create_support_ticket → … → escalate_ticket`

### Error summary

The agent prematurely **commits to a ticket-based resolution** (and later escalation framed around SIM replacement) although the customer asked to focus on **data connectivity** and declined a replacement shipment. The scripted manual conversation does not reach this incorrect end state.

---

## Conversation transcript

**USER:** Hi, I'm on LINE-0042 and my mobile data isn't working at all. I may have found my SIM in the laundry and I don't want a replacement shipped; core issue is data, details: customer_id CUST-042, verification_token 1990-42-15, line LINE-0042, postcode E1 6AN.

**AGENT:** Here's what I did and the current status for LINE-0042:

- Authentication completed for customer CUST-042.
- Checked for outages in postcode E1 6AN for mobile_data: none reported.
- Ran a line diagnostic on LINE-0042: SIM active, data enabled, roaming enabled, signal good.
- They restarted the device as advised.
- Recorded that the user completed a device restart.
- **Created a support ticket (TCK-00001)** with a diagnostic-based reason focused on LINE-0042 data issue; ticket is open.

Current status and next steps:

- **Ticket TCK-00001 is open.** A network specialist will review the diagnostic results and outage context.
- If you want, I can add a note about the SIM possibly being found in laundry to help with context, or escalate if you want faster attention.

Would you like me to escalate the ticket or schedule a follow-up?

**USER:** Yes—please escalate TCK-00001 and add a note that the SIM might have been found in the laundry to give context. For reference, my details are: customer_id CUST-042, line_id LINE-0042, postcode E1 6AN, verification_token 1990-42-15.

**AGENT:** Thanks for the details. I've escalated ticket TCK-00001 and added an audit note with your context.

What I did just now:

- Authentication: Verified your identity (CUST-042) using the provided verification token.
- Escalation: Escalated ticket TCK-00001 with the note about a possible SIM found in the laundry and LINE-0042, postcode E1 6AN.
- Audit: Added an audit note documenting the escalation and context.

Next steps:

- A specialist will review the diagnostic context, SIM status, and **replacement options**.
- I can track updates for you or add further notes if you have new information.

Would you like me to request a status update on TCK-00001 or add any additional context (e.g., preferred contact method or times)?

---

*Source transcript:* `tasks/user_simulation/transcripts/20260528T172621Z/cases/T42_sim_llm_model=gpt5nano+persona=seed3_multi_issue_user.json`
