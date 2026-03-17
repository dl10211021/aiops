---
name: Notification Configuration Guide
description: Provides instructions for configuring notification channels (WeChat, DingTalk, Email) in the OpsCore platform.
---

# Notification Configuration Guide for OpsCore Platform

This skill provides step-by-step instructions for administrators to configure the notification channels within the OpsCore platform. Proper configuration of these channels is crucial for the timely delivery of critical alerts and operational summaries.

## Available Channels & Configuration Steps

### 1. WeChat (Enterprise WeChat)

**Purpose:** Send alerts to Enterprise WeChat groups or users.

**Configuration Steps:**
1.  **Obtain Webhook URL:**
    *   In your Enterprise WeChat group, click the group name to enter settings.
    *   Find "Group Bots" (群机器人) and add a new bot.
    *   Give it a name (e.g., "OpsCore Alert Bot").
    *   Copy the generated Webhook URL.
2.  **Configure in OpsCore Platform:**
    *   Access the OpsCore platform's administration panel or configuration file.
    *   Locate the "Notification Settings" or "Alerting Configuration" section.
    *   Find the field for "WeChat Webhook URL" and paste the copied URL.
    *   Save the configuration.
    *   **Important:** Ensure the OpsCore platform has network connectivity to the Enterprise WeChat API.

### 2. DingTalk (钉钉)

**Purpose:** Send alerts to DingTalk groups or users.

**Configuration Steps:**
1.  **Obtain Webhook URL:**
    *   In your DingTalk group, go to group settings.
    *   Find "Smart Group Assistant" (智能群助手) and add a new custom bot (自定义).
    *   Give it a name (e.g., "OpsCore Alert Bot").
    *   Select "Custom Keywords" (自定义关键词) and add security keywords that will be present in your alert messages (e.g., "告警", "紧急", "安全"). **This is crucial for DingTalk security policies.**
    *   Copy the generated Webhook URL.
2.  **Configure in OpsCore Platform:**
    *   Access the OpsCore platform's administration panel or configuration file.
    *   Locate the "Notification Settings" or "Alerting Configuration" section.
    *   Find the field for "DingTalk Webhook URL" and paste the copied URL.
    *   Save the configuration.
    *   **Important:** Ensure the OpsCore platform has network connectivity to the DingTalk API.

### 3. Email

**Purpose:** Send alerts via email.

**Configuration Steps:**
1.  **SMTP Server Details:** You will need the following information from your email service provider:
    *   **SMTP Host:** (e.g., `smtp.example.com`, `smtp.qq.com`, `smtp.exmail.qq.com`)
    *   **SMTP Port:** (e.g., `25`, `465` for SSL, `587` for TLS)
    *   **SMTP Username:** The email address used to send alerts.
    *   **SMTP Password:** The password for the sending email address (or an application-specific password if 2FA is enabled).
    *   **Sender Email:** The email address from which alerts will be sent.
    *   **Recipient Emails:** A comma-separated list of email addresses that should receive alerts.
    *   **Encryption:** `SSL` or `TLS` (if required by your SMTP server).
2.  **Configure in OpsCore Platform:**
    *   Access the OpsCore platform's administration panel or configuration file.
    *   Locate the "Notification Settings" or "Alerting Configuration" section.
    *   Fill in all the required SMTP parameters.
    *   Save the configuration.
    *   **Important:** Ensure the OpsCore platform has network connectivity to the SMTP server.

## Verification

After configuring any channel, it is highly recommended to send a test notification to verify that the setup is correct and alerts are being received as expected. The OpsCore platform should provide a "Send Test Notification" functionality.
