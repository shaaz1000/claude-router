<!-- claude-router:start -->
## Router protocol
- Prompts may carry a `[router]` instruction. Follow it silently; never mention the router in replies.
- A subagent brief must be self contained: it cannot see this conversation.
- If router-fast replies `ESCALATE`, handle the task yourself.
- User prefixes `!fast` `!std` `!deep` `!max` force a tier. Ignore the prefix text itself.
<!-- claude-router:end -->
