# VPN Troubleshooting Guide

Document ID: KB-001 | Owner: Fabrikam IT Help Desk | Last reviewed: 2026-09-01

## Overview

Fabrikam employees connect to the corporate network from outside the office with the Fabrikam Secure Connect VPN client. The client connects to one of two gateways: vpn-in.fabrikam.example (India) or vpn-eu.fabrikam.example (Europe). The client must be version 5.2 or later.

## Common problems and fixes

1. The VPN disconnects every few minutes on Wi-Fi. Open Device Manager, open the Wi-Fi adapter properties, and turn off "Allow the computer to turn off this device to save power". Then reconnect.
2. Error 809 or "connection timed out". This usually means UDP port 4500 is blocked by a hotel or public network. In Fabrikam Secure Connect, open Settings and turn on "TCP fallback", then reconnect.
3. The VPN connects but internal sites do not open. Flush the DNS cache by running `ipconfig /flushdns` in a terminal, then reconnect.
4. The client says it is out of date. Open Software Center and install the latest Fabrikam Secure Connect update.
5. Slow connection. Switch to the other gateway in the client settings.

## If the steps fail

Raise a ticket in category VPN. Use priority Medium. Use priority High if you cannot work at all. Response targets: Critical 1 hour, High 4 hours, Medium 1 business day, Low 3 business days.
