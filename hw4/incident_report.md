# SSH Incident Report

## Summary
This report details findings from an analysis of `sample_auth.log` and `allowlist.txt` for SSH authentication security.

## Findings

### Top Offending Source IPs
The following IP addresses were identified as having the most failed SSH login attempts:
*   **203.0.113.45**: 10 failed attempts
*   **198.51.100.22**: 5 failed attempts

### Top Targeted Usernames
The most frequently targeted usernames for SSH login attempts were:
*   **root**: 5 failed attempts
*   **admin**: 3 failed attempts
*   **ubuntu**: 2 failed attempts

### Possible Compromise Detected
A critical finding indicates a potential successful brute-force attack:
*   **IP Address**: `203.0.113.45`
*   **Failed Attempts**: 10
*   **Successful Login Username**: `root`
*   **Timestamp of Successful Login**: `Oct 20 02:13:40`
This IP successfully logged in as 'root' after numerous failed attempts, strongly suggesting a compromise of the 'root' account.

## Unauthorized IPs
The following offending IPs are NOT present in the `allowlist.txt` and are considered unauthorized:
*   **203.0.113.45** (involved in a potential compromise)
*   **198.51.100.22**

## Recommended Remediation Steps

1.  **Immediate Action for Compromised Host:**
    *   Isolate the host associated with the compromised `root` account.
    *   Change the `root` password immediately.
    *   Investigate the compromised host for any unauthorized access, privilege escalation, or backdoor installations.
    *   Review all user accounts and their last login times.

2.  **Firewall/ACL Updates:**
    *   Block IP addresses `203.0.113.45` and `198.51.100.22` at the network perimeter firewall or host-based firewall.

3.  **SSH Hardening:**
    *   Disable password authentication for SSH and enforce key-based authentication.
    *   Disable direct `root` login via SSH.
    *   Implement fail2ban or similar intrusion prevention systems to automatically ban IPs with repeated failed login attempts.
    *   Ensure all SSH services use strong, unique passwords for any remaining password-based authentication.
    *   Regularly review SSH logs for unusual activity.

4.  **Security Awareness:**
    *   Educate users on creating strong, unique passwords and the importance of reporting suspicious activity.

5.  **Review and Update Allowlist:**
    *   Regularly review and update `allowlist.txt` to ensure it contains only legitimate, known-good source IPs.