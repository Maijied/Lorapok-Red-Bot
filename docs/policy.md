# Lorapok Red Bot policy
## Purpose statement
Lorapok Red Bot supports developer communities by assisting moderators with content triage, spam detection, and helpful guidance responses while keeping humans in control of impactful moderation decisions.

## Allowed bot actions
- Flag uncertain content for moderator review.
- Remove clear spam/promotional abuse based on deterministic and explainable rules.
- Post practical help prompts for developer troubleshooting context.
- Send operational alerts to approved moderator channels.

## Disallowed bot actions
- Silent or deceptive moderation actions.
- Permanent bans without moderator confirmation.
- Collection or publication of unnecessary personal data.
- Bypassing subreddit-specific moderator instructions.

## Escalation rules
- Any low-confidence or ambiguous moderation outcome must be placed in the review queue.
- Classifier parsing failures must default to `review`.
- Repeated false positives should trigger rule/prompt adjustments before expanding automation.

## Moderator override process
- Moderators can approve, reject, or escalate queued cases.
- Override notes should be recorded for future tuning.
- Override outcomes take precedence over automated decisions.
