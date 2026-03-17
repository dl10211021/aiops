---
name: Linux Security Hardening Plan
description: Comprehensive guide and phased action plan for hardening Linux server security based on identified vulnerabilities.
tags:
  - linux
  - security
  - hardening
  - remediation
---
# Linux Security Hardening Plan

## Overview
This skill provides a structured, prioritized, and phased action plan to address critical security vulnerabilities and improve the overall security posture of Linux servers. It is designed to guide human administrators through the remediation process.

## Phased Hardening Plan

### Phase 1: Emergency Response & Critical Protection (Immediate Action Required)

1.  **Enable and Configure Firewall**: Immediately activate `firewalld` (or equivalent) and implement strict ingress/egress rules.
    *   **Action**: `systemctl enable firewalld --now`, then `firewall-cmd --permanent --add-service=ssh`, `firewall-cmd --permanent --add-source=TRUSTED_IP_RANGE --add-port=22/tcp`, `firewall-cmd --reload`, `firewall-cmd --permanent --zone=public --set-target=DROP` (or similar for other zones).
    *   **Rationale**: The server is currently completely exposed. This is the first line of defense.

2.  **Secure SSH Access**: Disable password authentication and root direct login.
    *   **Action**: Edit `/etc/ssh/sshd_config`: `PasswordAuthentication no`, `PermitRootLogin no` (or `prohibit-password`).
    *   **Prerequisite**: Ensure all legitimate users have SSH key-based authentication set up (`~/.ssh/authorized_keys`).
    *   **Action**: `systemctl restart sshd`.
    *   **Rationale**: Prevents brute-force attacks and limits root exposure.

3.  **Fix Insecure File System Mount Options**: Apply `noexec,nodev,nosuid` to critical partitions.
    *   **Action**: Edit `/etc/fstab` for `/tmp`, `/var/tmp`, `/dev/shm`, `/boot` and `/` (or relevant partitions). Add `noexec,nodev,nosuid` (for `/tmp`, `/var/tmp`, `/dev/shm`, `/boot`). For `/`, at least add `nodev,nosuid`.
    *   **Action**: `mount -o remount,exec,dev,suid /path` for each affected mount point, or reboot.
    *   **Rationale**: Prevents execution of malicious code, creation of device files, and privilege escalation via SUID/SGID bits in critical areas.

4.  **Register System for Updates**: Configure the system to receive security patches.
    *   **Action**: `subscription-manager register` (for RHEL), or configure appropriate `yum` repositories (for CentOS).
    *   **Action**: `yum update -y` to apply immediate patches.
    *   **Rationale**: Close known vulnerability gaps.

### Phase 2: System Hardening & Cleanup (High Priority)

1.  **Rectify NFS `no_root_squash`**: Enforce proper root privilege mapping for NFS shares.
    *   **Action**: Edit `/etc/exports`, change `no_root_squash` to `root_squash` or `all_squash` for `/data` share.
    *   **Action**: `exportfs -ra && systemctl restart nfs-server`.
    *   **Rationale**: Prevents privilege escalation from NFS clients.

2.  **Investigate and Handle `chroot` User**: Remove or disable if not required.
    *   **Action**: User interview, `userdel -r chroot` (if not needed), or `usermod -L chroot` (lock account).
    *   **Rationale**: Remove unnecessary attack surface.

3.  **Optimize Kernel Parameters**: Adjust `ip_forward` and `sysrq`.
    *   **Action**: Create `/etc/sysctl.d/99-custom-security.conf`: `net.ipv4.ip_forward = 0` (if not a router), `kernel.sysrq = 4` (or 0 if fully disabled).
    *   **Action**: `sysctl --system` to apply.
    *   **Rationale**: Reduce network attack surface and prevent SysRq abuse.

### Phase 3: Resource Optimization & Best Practices (Medium Priority)

1.  **Remove/Disable Desktop Environment**: If not required for a server.
    *   **Action**: `systemctl set-default multi-user.target`, then `yum groupremove "GNOME Desktop"` (or similar).
    *   **Rationale**: Free up resources and reduce attack surface.

## Future Enhancements (Self-Evolution for OpsCore)

- Develop Python scripts for automated pre-checks and post-remediation verification for each hardening step.
- Integrate these scripts into existing `linux-security-audit` skill for continuous compliance checks.
- Explore automated patch management solutions for registered systems.
