---
description: Turn Claude Router on. Every prompt gets a routing instruction until you turn it off
disable-model-invocation: true
allowed-tools: Bash({{ROUTER_CMD}} --on)
---
!`{{ROUTER_CMD}} --on`

The line above is the output of the router switch. Repeat it to the user exactly, on one line, and do nothing else.
