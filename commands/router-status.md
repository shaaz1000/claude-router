---
description: Show whether Claude Router is on or off
disable-model-invocation: true
allowed-tools: Bash({{ROUTER_CMD}} --status)
---
!`{{ROUTER_CMD}} --status`

The line above is the output of the router switch. Repeat it to the user exactly, on one line, and do nothing else.
