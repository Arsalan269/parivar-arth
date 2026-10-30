"""
Offline TF-IDF FAQ and Knowledge Retrieval Engine for Parivar Arth.
Provides intelligent, offline responses based on TF-IDF cosine similarity
over official app guidelines and Indian personal finance concepts.
"""

from typing import Tuple, List, Dict, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


FAQ_CORPUS: List[Dict[str, str]] = [
    {
        "question": "What is a sinking fund and how does it help my family?",
        "answer": (
            "A Sinking Fund is a dedicated reserve where you break down heavy, irregular annual costs "
            "(such as school annual fees, car insurance, or festival travel) into predictable monthly savings. "
            "For example, instead of scrambling for ₹48,000 in April for school admission, you allocate ₹4,000/month "
            "into a liquid account, compounded with education inflation."
        )
    },
    {
        "question": "How is my emergency fund target determined (3 vs 6 months)?",
        "answer": (
            "Parivar Arth dynamically tailors your emergency buffer based on your household's risk factors: "
            "(1) 3 Months: Dual stable salaried earners with low dependency risk. "
            "(2) 6 Months: Single earner, freelance/gig variable income, or dependent family members with chronic health conditions. "
            "Only strictly liquid assets (savings accounts, FDs, cash) count toward your emergency runway."
        )
    },
    {
        "question": "What does Debt-to-Income (DTI) mean and why does 40% matter?",
        "answer": (
            "Debt-to-Income (DTI) is the percentage of your monthly take-home income that goes toward servicing loan EMIs. "
            "Indian banking guidelines consider DTI <= 30% as Safe, 30-45% as Watch, and > 45% as At Risk. "
            "Crossing 40% leaves very little room to absorb unexpected grocery or healthcare inflation spikes."
        )
    },
    {
        "question": "Why does Parivar Arth use category-specific inflation instead of a flat 6%?",
        "answer": (
            "A single flat inflation number misleads Indian families because different household necessities inflate at drastically different rates. "
            "In India, private school fees typically rise by 7-8% annually, medical bills by 7%, and vegetable prices fluctuate wildly with monsoons, "
            "whereas manufactured goods inflate much slower. We forecast category-specific CPI to ensure your future savings target matches actual rupee costs."
        )
    },
    {
        "question": "What is Monte Carlo simulation and how should I interpret the probability?",
        "answer": (
            "The Monte Carlo engine runs 1,000 independent economic pathways for your family, sampling inflation from the model's prediction intervals. "
            "A result like '70% probability of shortfall' means that in 700 out of 1,000 realistic inflation scenarios, your monthly expenses will exceed income "
            "within 24 months, indicating that relying on current savings margins alone is risky."
        )
    },
    {
        "question": "How does an RBI Repo Rate hike affect my floating Home Loan?",
        "answer": (
            "When the Reserve Bank of India increases the repo rate (e.g. +50 bps / +0.50%), commercial banks immediately increase the external benchmark lending rate (EBLR). "
            "This either increases your monthly EMI immediately or, if your EMI is held constant, automatically extends your loan tenure by several months/years, "
            "significantly increasing the total interest paid."
        )
    },
    {
        "question": "How does the app protect my financial privacy?",
        "answer": (
            "All queries are strictly isolated to your authenticated session ID. Passwords are encrypted with bcrypt, "
            "and no user transaction records or identifying personal details are ever transmitted to external third parties. "
            "Only aggregated numeric summaries are used for planning calculations."
        )
    },
    {
        "question": "Can you recommend specific stocks, crypto, or mutual fund schemes?",
        "answer": (
            "No. Parivar Arth is strictly an educational financial planning tool, not a SEBI-registered investment advisor or stock broker. "
            "We provide macro category forecasts and mathematical cash-flow projections, but cannot provide specific stock tips or product recommendations."
        )
    },
    {
        "question": "What medical or health advice can the assistant provide?",
        "answer": (
            "None. Parivar Arth estimates healthcare costs and insurance gap provisions from an economic perspective only. "
            "Always consult qualified medical professionals for diagnosis, prescriptions, or clinical treatments."
        )
    },
    {
        "question": "How can I reduce my rent and necessary living expenses?",
        "answer": (
            "Our 'Reduce Necessary Expenses' engine focuses on high-rupee practical levers: "
            "(1) Home Loan balance transfer refinancing (saving 0.5-0.75% APR), "
            "(2) Requesting a lease renewal escalation freeze from your landlord, "
            "(3) Managing AC thermostats at 24°C-25°C to stay within lower electricity tariff slabs, and "
            "(4) Seasonal vegetable substitution and bulk staple buying during commodity spikes."
        )
    }
]


class OfflineFaqMatcher:
    def __init__(self):
        self.corpus = FAQ_CORPUS
        self.questions = [item["question"] for item in self.corpus]
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.tfidf_matrix = self.vectorizer.fit_transform(self.questions)

    def find_best_match(self, user_query: str, similarity_threshold: float = 0.18) -> Tuple[Optional[str], float]:
        """Return the closest FAQ answer using cosine similarity or None if below threshold."""
        query_vec = self.vectorizer.transform([user_query])
        sims = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        best_idx = int(sims.argmax())
        best_score = float(sims[best_idx])

        if best_score >= similarity_threshold:
            return self.corpus[best_idx]["answer"], best_score
        return None, best_score
