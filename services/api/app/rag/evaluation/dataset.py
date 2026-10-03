import json
from pathlib import Path
from typing import List

from app.rag.evaluation.models import EvaluationItem

CONTROLLED_EVALUATION_ITEMS = [
    EvaluationItem(
        id="EVAL-01",
        category="fact_lookup",
        query="Who benefits from cloud computing according to the notes, specifically regarding collaborators?",
        ground_truth_answer="Collaborators benefit from cloud computing because multiple users can view, edit, and collaborate on documents in real time without passing files back and forth via email.",
        relevant_page_start=10,
        relevant_page_end=11,
        ground_truth_keywords=["collaborators", "sharing", "documents", "real-time", "multiple users", "collaboration"],
        ground_truth_section="Benefits of Cloud Computing",
        history=[],
    ),
    EvaluationItem(
        id="EVAL-02",
        category="concept_explanation",
        query="What is a Community Cloud and who does it serve?",
        ground_truth_answer="A community cloud is an infrastructure shared by several organizations that have common concerns, such as mission, security requirements, policy, and compliance considerations. It may be managed by the organizations or a third party.",
        relevant_page_start=35,
        relevant_page_end=36,
        ground_truth_keywords=["community cloud", "shared concerns", "mission", "security", "organizations", "third party"],
        ground_truth_section="Cloud Deployment Models",
        history=[],
    ),
    EvaluationItem(
        id="EVAL-03",
        category="comparative_analysis",
        query="Compare Infrastructure as a Service (IaaS) and Software as a Service (SaaS) regarding consumer management responsibility.",
        ground_truth_answer="In IaaS, the consumer controls the operating system, storage, deployed applications, and select networking components. In SaaS, the consumer has no control over the underlying infrastructure, operating systems, or application capabilities, only user-specific configuration settings.",
        relevant_page_start=25,
        relevant_page_end=28,
        ground_truth_keywords=["IaaS", "SaaS", "operating system", "applications", "consumer control", "underlying infrastructure"],
        ground_truth_section="Service Models (SPI Model)",
        history=[],
    ),
    EvaluationItem(
        id="EVAL-04",
        category="fact_lookup",
        query="What are the essential characteristics of cloud computing according to NIST?",
        ground_truth_answer="NIST specifies five essential characteristics of cloud computing: on-demand self-service, broad network access, resource pooling, rapid elasticity, and measured service.",
        relevant_page_start=19,
        relevant_page_end=21,
        ground_truth_keywords=["on-demand self-service", "broad network access", "resource pooling", "rapid elasticity", "measured service", "NIST"],
        ground_truth_section="NIST Cloud Definition",
        history=[],
    ),
    EvaluationItem(
        id="EVAL-05",
        category="fact_lookup",
        query="What are the primary disadvantages and security concerns of cloud storage?",
        ground_truth_answer="Disadvantages include dependency on reliable internet connectivity, potential data privacy and security breaches by unauthorized third parties, recurring bandwidth limitations, and provider downtime.",
        relevant_page_start=70,
        relevant_page_end=74,
        ground_truth_keywords=["security", "internet connection", "unauthorized access", "bandwidth", "downtime", "privacy"],
        ground_truth_section="Cloud Storage Disadvantages",
        history=[],
    ),
    EvaluationItem(
        id="EVAL-06",
        category="comparative_analysis",
        query="How does a Public Cloud differ from a Private Cloud regarding accessibility and infrastructure ownership?",
        ground_truth_answer="A Public Cloud makes infrastructure accessible to the general public or a large industry group owned by an organization selling cloud services. A Private Cloud infrastructure is provisioned for exclusive use by a single organization comprising multiple consumers.",
        relevant_page_start=31,
        relevant_page_end=34,
        ground_truth_keywords=["public cloud", "private cloud", "general public", "single organization", "firewall", "dedicated"],
        ground_truth_section="Public vs Private Cloud",
        history=[],
    ),
    EvaluationItem(
        id="EVAL-07",
        category="conversational_followup",
        query="What are its primary benefits for software developers?",
        ground_truth_answer="For software developers, PaaS benefits include increased developer productivity, simplified application lifecycle deployment, built-in frameworks and libraries, and eliminating the burden of managing operating system updates and server hardware.",
        relevant_page_start=26,
        relevant_page_end=27,
        ground_truth_keywords=["PaaS", "developers", "productivity", "deployment", "libraries", "frameworks", "lifecycle"],
        ground_truth_section="Platform as a Service Benefits",
        history=[
            {
                "role": "user",
                "content": "What is Platform as a Service (PaaS)?",
            },
            {
                "role": "assistant",
                "content": "Platform as a Service (PaaS) provides runtime environments, programming tools, and development frameworks so developers can build, test, and host applications without managing underlying hardware.",
            },
        ],
    ),
    EvaluationItem(
        id="EVAL-08",
        category="conversational_followup",
        query="How does virtualization differ from traditional dual-core computing and what are its trade-offs?",
        ground_truth_answer="Virtualization uses a software hypervisor layer to isolate and abstract physical hardware into multiple logical virtual machines, unlike traditional multi-core processing where operating systems run natively on bare metal. Trade-offs include hypervisor resource overhead and potential I/O performance degradation balanced against high server utilization and workload isolation.",
        relevant_page_start=50,
        relevant_page_end=58,
        ground_truth_keywords=["virtualization", "hypervisor", "dual-core", "hardware abstraction", "overhead", "isolation", "performance"],
        ground_truth_section="Virtualization Architecture and Trade-offs",
        history=[
            {
                "role": "user",
                "content": "Explain virtualization in cloud computing architectures.",
            },
            {
                "role": "assistant",
                "content": "Virtualization enables running multiple independent operating systems and applications on a single physical machine through a hypervisor abstraction layer.",
            },
        ],
    ),
]


def get_evaluation_dataset() -> List[EvaluationItem]:
    """Returns the version-controlled list of evaluation items."""
    return list(CONTROLLED_EVALUATION_ITEMS)


def export_dataset_json(filepath: Path) -> None:
    """Exports the evaluation dataset to structured JSON format."""
    data = [
        {
            "id": it.id,
            "category": it.category,
            "query": it.query,
            "ground_truth_answer": it.ground_truth_answer,
            "relevant_page_start": it.relevant_page_start,
            "relevant_page_end": it.relevant_page_end,
            "ground_truth_keywords": it.ground_truth_keywords,
            "ground_truth_section": it.ground_truth_section,
            "history": it.history,
        }
        for it in CONTROLLED_EVALUATION_ITEMS
    ]
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
