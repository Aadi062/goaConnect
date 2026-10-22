"""
Security specialist agents:
- AuthenticationGuardianAgent
- APISecurityGuardianAgent
- AlertTriageAgent
- RiskPrioritizationAgent
- ContainmentAdvisorAgent
Each has a minimal, least-privilege permitted_tools set.
"""
from __future__ import annotations

from app.agents.core.base import (
    AgentInput, AgentOutput, AgentRole, BaseAgent, ToolPermission
)
from app.agents.core.manager import register_agent
from app.core.logging import get_logger

logger = get_logger("agent.security")


@register_agent
class AuthenticationGuardianAgent(BaseAgent):
    """
    Detects unusual login patterns, repeated failures, suspicious sessions.
    Read-only access to audit log — no write permissions to user accounts.
    """
    role = AgentRole.AUTHENTICATION_GUARDIAN
    permitted_tools = {ToolPermission.READ_AUDIT_LOG, ToolPermission.WRITE_ALERTS}
    timeout_seconds = 15

    async def run(self, task: AgentInput) -> AgentOutput:
        payload = task.payload
        events = payload.get("login_events", [])
        user_id = payload.get("user_id")

        # Heuristic analysis (rules-based, no LLM required for basic checks)
        failed_count = sum(1 for e in events if e.get("outcome") == "failure")
        distinct_ips = len({e.get("ip") for e in events if e.get("ip")})
        locked = any(e.get("outcome") == "blocked" for e in events)

        findings = []
        confidence = 0.0

        if failed_count >= 5:
            findings.append({
                "type": "brute_force_suspected",
                "failed_count": failed_count,
                "recommendation": "Review account and consider temporary lockout",
            })
            confidence = min(0.5 + (failed_count - 5) * 0.05, 0.95)

        if distinct_ips >= 3:
            findings.append({
                "type": "credential_stuffing_suspected",
                "distinct_ips": distinct_ips,
                "recommendation": "Investigate IP addresses for known malicious ranges",
            })
            confidence = max(confidence, 0.6)

        status = "success" if findings else "success"
        alert_needed = bool(findings)

        return self._build_output(
            task.task_id,
            status=status,
            result={
                "user_id": user_id,
                "findings": findings,
                "alert_required": alert_needed,
                "failed_attempts": failed_count,
                "distinct_ips": distinct_ips,
                "account_locked": locked,
            },
            confidence=confidence,
            evidence=[{"source": "login_event_analysis", "count": len(events)}],
            reasoning=f"Analyzed {len(events)} login events. "
                      f"Found {failed_count} failures across {distinct_ips} IPs.",
            requires_human_approval=locked and failed_count >= 10,
        )


@register_agent
class APISecurityGuardianAgent(BaseAgent):
    """
    Detects API anomalies: rate-limit hits, authorization failures, malformed requests.
    """
    role = AgentRole.API_SECURITY_GUARDIAN
    permitted_tools = {ToolPermission.READ_AUDIT_LOG, ToolPermission.WRITE_ALERTS}
    timeout_seconds = 15

    async def run(self, task: AgentInput) -> AgentOutput:
        events = task.payload.get("api_events", [])
        auth_failures = sum(1 for e in events if e.get("status_code") in [401, 403])
        rate_limit_hits = sum(1 for e in events if e.get("status_code") == 429)
        malformed = sum(1 for e in events if e.get("status_code") == 422)

        findings = []
        confidence = 0.3

        if auth_failures > 10:
            findings.append({
                "type": "authorization_abuse",
                "count": auth_failures,
                "recommendation": "Review endpoints for authorization bypass attempts",
            })
            confidence = 0.75

        if rate_limit_hits > 5:
            findings.append({
                "type": "rate_limit_exhaustion",
                "count": rate_limit_hits,
                "recommendation": "Check for automated scraping or DoS attempt",
            })
            confidence = max(confidence, 0.7)

        return self._build_output(
            task.task_id,
            status="success",
            result={
                "findings": findings,
                "auth_failures": auth_failures,
                "rate_limit_hits": rate_limit_hits,
                "malformed_requests": malformed,
            },
            confidence=confidence,
            evidence=[{"source": "api_event_analysis", "event_count": len(events)}],
            reasoning=f"Analyzed {len(events)} API events.",
        )


@register_agent
class AlertTriageAgent(BaseAgent):
    """
    Deduplicates and classifies incoming alerts.
    Groups by alert_type + affected_resource to suppress noise.
    """
    role = AgentRole.ALERT_TRIAGE
    permitted_tools = {ToolPermission.READ_ALERTS, ToolPermission.WRITE_ALERTS}
    timeout_seconds = 10

    async def run(self, task: AgentInput) -> AgentOutput:
        alerts = task.payload.get("alerts", [])
        groups: dict[str, list] = {}
        for alert in alerts:
            key = f"{alert.get('alert_type')}::{alert.get('affected_resource', 'unknown')}"
            groups.setdefault(key, []).append(alert)

        deduplicated = []
        for key, group in groups.items():
            most_severe = sorted(
                group,
                key=lambda a: ["info", "low", "medium", "high", "critical"].index(
                    a.get("severity", "info")
                ),
                reverse=True,
            )[0]
            most_severe["duplicate_count"] = len(group) - 1
            deduplicated.append(most_severe)

        return self._build_output(
            task.task_id,
            status="success",
            result={
                "original_count": len(alerts),
                "deduplicated_count": len(deduplicated),
                "alerts": deduplicated,
            },
            confidence=0.9,
            evidence=[{"source": "alert_deduplication", "groups": len(groups)}],
            reasoning=f"Deduplicated {len(alerts)} alerts into {len(deduplicated)} unique groups.",
        )


@register_agent
class RiskPrioritizationAgent(BaseAgent):
    """Ranks findings by severity, exploitability, and business impact."""
    role = AgentRole.RISK_PRIORITIZATION
    permitted_tools = {ToolPermission.READ_ALERTS, ToolPermission.READ_AUDIT_LOG}
    timeout_seconds = 10

    SEVERITY_SCORE = {"critical": 10, "high": 7, "medium": 4, "low": 2, "info": 1}

    async def run(self, task: AgentInput) -> AgentOutput:
        findings = task.payload.get("findings", [])
        scored = []
        for f in findings:
            base = self.SEVERITY_SCORE.get(f.get("severity", "info"), 1)
            exploitability = f.get("exploitability_score", 0.5)
            business_impact = f.get("business_impact_score", 0.5)
            score = base * exploitability * business_impact * 10
            scored.append({**f, "risk_score": round(score, 2)})

        ranked = sorted(scored, key=lambda x: x["risk_score"], reverse=True)
        return self._build_output(
            task.task_id,
            status="success",
            result={"ranked_findings": ranked},
            confidence=0.85,
            evidence=[{"source": "risk_scoring", "finding_count": len(findings)}],
            reasoning=f"Scored and ranked {len(findings)} findings by CVSS-inspired formula.",
        )


@register_agent
class ContainmentAdvisorAgent(BaseAgent):
    """
    Recommends reversible, proportionate containment actions.
    High-risk containment requires human approval — never self-approves.
    """
    role = AgentRole.CONTAINMENT_ADVISOR
    permitted_tools = {
        ToolPermission.READ_ALERTS,
        ToolPermission.READ_AUDIT_LOG,
        ToolPermission.REQUEST_APPROVAL,
    }
    timeout_seconds = 20

    CONTAINMENT_PLAYBOOK = {
        "brute_force_suspected": {
            "action": "temporary_account_lockout",
            "reversible": True,
            "risk_level": "medium",
            "description": "Lock account for 15 minutes and alert user by email",
        },
        "credential_stuffing_suspected": {
            "action": "rate_limit_by_ip_range",
            "reversible": True,
            "risk_level": "medium",
            "description": "Reduce login rate limit for suspected IP range",
        },
        "authorization_abuse": {
            "action": "temporary_api_key_suspension",
            "reversible": True,
            "risk_level": "high",
            "description": "Suspend API key pending investigation — requires human approval",
        },
        "rate_limit_exhaustion": {
            "action": "enforce_stricter_rate_limit",
            "reversible": True,
            "risk_level": "low",
            "description": "Reduce rate limit for source IP",
        },
    }

    async def run(self, task: AgentInput) -> AgentOutput:
        alert_type = task.payload.get("alert_type", "unknown")
        playbook = self.CONTAINMENT_PLAYBOOK.get(alert_type)

        if not playbook:
            return self._build_output(
                task.task_id,
                status="partial",
                result={"recommendation": "Manual investigation required — no playbook entry for this alert type"},
                confidence=0.2,
                reasoning=f"No containment playbook for alert_type={alert_type}",
            )

        requires_approval = playbook["risk_level"] in ("high", "critical")
        return self._build_output(
            task.task_id,
            status="success",
            result=playbook,
            confidence=0.8,
            evidence=[{"source": "containment_playbook", "alert_type": alert_type}],
            reasoning=f"Matched '{alert_type}' to containment playbook. Risk={playbook['risk_level']}.",
            requires_human_approval=requires_approval,
            audit_trail=[
                f"ContainmentAdvisor retrieved playbook for {alert_type}",
                f"Requires human approval: {requires_approval}",
            ],
        )
