# Lorapok Red Bot privacy and retention
## Data stored
- Text hash of processed content.
- Action result (`allow`, `review`, `remove`).
- Decision reason.
- Decision source (`rules`, `ai`, or combined pipeline).
- Queue timestamps and reviewer notes for reviewed cases.

## Data not stored by default
- Raw credentials or tokens.
- Private messages beyond what is required for moderation workflows.
- Expanded personal profile data unrelated to moderation decisions.

## Retention policy (initial)
- In-memory bootstrap storage is ephemeral and resets on restart.
- For persistent storage phases, retain decision logs for 90 days by default unless moderators configure otherwise.
- Security and audit logs should be retained longer only when required for incident response.

## Review and correction process
- Moderators can override queued decisions and attach corrective notes.
- Corrective notes are used as training signals for rule and prompt updates.
- Future persistent implementation should expose export and correction endpoints for moderator accountability workflows.
