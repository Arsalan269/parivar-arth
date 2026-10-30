"""
Multi-Provider Context-Aware Chatbot Agent for Parivar Arth.
Integrates live local app tools with external LLMs (if API key provided)
or intelligent local offline rule/tool dispatcher.
Never exposes raw transaction data or personal identifying information.
"""

import os
from typing import Dict, Any, List
from chatbot.tools import tool_get_financial_status, tool_project_expenses, tool_simulate_what_if
from chatbot.faq import OfflineFaqMatcher


class ParivarChatbotAgent:
    def __init__(self):
        self.faq_matcher = OfflineFaqMatcher()

    def get_aggregated_system_context(self, user_id: int) -> str:
        """Construct privacy-safe aggregated numeric context for the assistant."""
        status = tool_get_financial_status(user_id)
        return (
            f"Logged-in Family Financial Summary (Aggregated):\n"
            f"- Monthly Take-Home Income: {status['monthly_income']}\n"
            f"- Essential Monthly Living Costs: {status['essential_outflows']}\n"
            f"- Net Current Monthly Surplus: {status['current_monthly_surplus']}\n"
            f"- Risk Status: {status['status']} ({status['explanation']})\n"
            f"- Month of Projected Shortfall: {status['shortfall_month']}\n"
            f"- Debt-to-Income (DTI): {status['dti_ratio']}\n"
            f"- Liquid Emergency Runway: {status['emergency_runway']}\n"
            f"Guidelines: Be friendly, warm, and concise in Indian English. Use ₹ symbol. Never provide definitive stock tips or medical diagnosis. Note uncertainty in forecasts."
        )

    def process_message(self, user_id: int, user_message: str) -> str:
        """
        Process user question with intent classification:
        1. Tool intent matching (Status, Shortfall, Projection, Repo Shock)
        2. Semantic FAQ retrieval
        3. Professional fallback
        """
        msg_lower = user_message.strip().lower()

        # Guardrails: Out of scope checks
        if any(w in msg_lower for w in ["buy stock", "which crypto", "best mutual fund to buy", "multibagger", "share tip"]):
            return (
                "⚠️ **Statutory Disclaimer**: Parivar Arth is an educational planning tool, not a SEBI-registered financial advisor or broker. "
                "I cannot provide specific stock recommendations, trading tips, or crypto advice. "
                "Please consult a certified financial planner for specific security purchases."
            )

        if any(w in msg_lower for w in ["prescribe", "take medicine for", "diagnose", "cure illness", "disease symptoms"]):
            return (
                "⚕️ **Medical Disclaimer**: I am an economic planning assistant and cannot provide medical advice, diagnosis, or drug prescriptions. "
                "For health conditions or treatment, please consult a registered medical practitioner."
            )

        # Intent 1: Direct Status / Shortfall Check
        if any(w in msg_lower for w in ["my status", "am i safe", "shortfall", "deficit", "surplus", "how am i doing", "health check"]):
            status = tool_get_financial_status(user_id)
            return (
                f"### 📊 Your Household Financial Health Status: **{status['status']}**\n\n"
                f"- **Monthly Inflow:** {status['monthly_income']}\n"
                f"- **Essential Outflows:** {status['essential_outflows']}\n"
                f"- **Current Surplus:** {status['current_monthly_surplus']}\n"
                f"- **Shortfall Outlook:** {status['shortfall_month']}\n"
                f"- **Emergency Runway:** {status['emergency_runway']}\n"
                f"- **Debt-to-Income (DTI):** {status['dti_ratio']}\n\n"
                f"💡 **Analysis:** {status['explanation']}"
            )

        # Intent 2: Projection / Future Costs Check
        if any(w in msg_lower for w in ["future cost", "in 12 months", "in 1 year", "project", "in 6 months", "in 24 months"]):
            months = 12
            if "6" in msg_lower:
                months = 6
            elif "24" in msg_lower:
                months = 24
            proj = tool_project_expenses(user_id, months_ahead=months)
            return (
                f"### 🔮 Projection in {months} Months (with Category Inflation):\n\n"
                f"- **Projected Essential Expenses:** {proj['projected_monthly_essential_costs']}\n"
                f"- **Projected Monthly Surplus:** {proj['projected_monthly_surplus']}\n"
                f"- **Shortfall Expected:** {'⚠️ Yes, deficit detected!' if proj['shortfall_detected'] else '✅ No shortfall expected.'}\n\n"
                f"*Note: Calculations compound category-specific forecasts for food, education, utilities, and healthcare.*"
            )

        # Intent 3: Repo Rate Shock Check
        if any(w in msg_lower for w in ["repo", "rate hike", "interest rate rises", "rbi hike"]):
            shock = tool_simulate_what_if(user_id, scenario_type="repo", parameter_value=50.0)
            if "monthly_emi_increase" in shock:
                return (
                    f"### ⚡ RBI Repo Rate Hike Simulation (+50 bps):\n\n"
                    f"- **Monthly EMI Increase:** +{shock['monthly_emi_increase']}\n"
                    f"- **New Total EMI:** {shock['new_emi']}\n"
                    f"- **Tenure Extension Alternative:** {shock['tenure_extension_months']}\n\n"
                    f"When the RBI raises rates, commercial banks pass the hike to floating loans. You can review debt prepayment options in the **Loans & Emergency Fund** tab."
                )
            return "You currently have no floating rate loans registered in your profile. On a standard ₹40 Lakh home loan, a 50 bps repo hike increases monthly EMI by ~₹1,276."

        # Intent 4: Job Loss / Emergency Runway Check
        if any(w in msg_lower for w in ["job loss", "lost job", "no salary", "lose income", "layoff"]):
            shock = tool_simulate_what_if(user_id, scenario_type="job_loss")
            absorb_txt = "✅ Yes, your emergency fund successfully covers a 3-month transition." if shock["absorbs_3_months"] else "🔴 Insufficient buffer! Your liquid reserves would be exhausted before 3 months."
            return (
                f"### 💼 3-Month Income Loss Stress Test:\n\n"
                f"- **Current Liquid Buffer:** {shock['liquid_buffer']}\n"
                f"- **Monthly Essential Burn Rate:** {shock['monthly_burn_rate']}\n"
                f"- **Emergency Runway:** {shock['runway_months']}\n\n"
                f"**Verdict:** {absorb_txt}"
            )

        # Intent 5: FAQ & Knowledge Retrieval
        faq_ans, score = self.faq_matcher.find_best_match(user_message)
        if faq_ans:
            return faq_ans

        # Generic Helpful Fallback
        return (
            "Namaste! I am your Parivar Arth personal finance assistant. I can help you understand:\n"
            "- Your household's **risk status and shortfall month** (ask: *'What is my financial status?'*)\n"
            "- Projected living costs 12 months ahead (ask: *'What will my costs be in 12 months?'*)\n"
            "- Impact of **RBI repo rate hikes** on your loans (ask: *'What happens if repo rate rises?'*)\n"
            "- How long your **emergency fund lasts** during a job loss (ask: *'What if I lose my job for 3 months?'*)\n"
            "- Sinking funds, DTI ratios, and inflation adjustments."
        )
