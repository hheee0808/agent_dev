"""eval 실행 CLI — python -m evals.run"""

import asyncio
import logging
import sys

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from backend.agents.ci_triage.agent import CITriageAgent
from backend.agents.curator.agent import CuratorAgent
from backend.agents.qa_gen.agent import QAGenAgent
from backend.agents.rag.agent import RAGAgent
from backend.agents.research.agent import DeepResearchAgent
from backend.common.supervisor import Supervisor
from evals.harness import load_cases, run_eval, summary
from evals.reporter import print_report, report_to_langfuse


async def main():
    supervisor = Supervisor()
    supervisor.register(CuratorAgent())
    supervisor.register(RAGAgent())
    supervisor.register(DeepResearchAgent())
    supervisor.register(CITriageAgent())
    supervisor.register(QAGenAgent())

    cases_path = sys.argv[1] if len(sys.argv) > 1 else "evals/cases.json"
    cases = load_cases(cases_path)
    print(f"Running {len(cases)} eval cases...")

    results = await run_eval(cases, supervisor)
    stats = summary(results)

    print_report(results, stats)
    report_to_langfuse(results, stats)


if __name__ == "__main__":
    asyncio.run(main())
