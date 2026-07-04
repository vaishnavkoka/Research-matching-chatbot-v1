"""15 faculty profiles grounded in REAL IIT Gandhinagar CSE faculty
(names, designations, and research areas sourced from iitgn.ac.in/faculty/cse).

The narrative bodies are elaborated into realistic, RAG-friendly profiles that
cover diverse CS/AI subfields (NLP, Computer Vision, IoT/Sensing, Cybersecurity,
Data Mining, Systems, Theory, HCI) so vector matching produces sharp
distinctions. `active_projects` supports the professor "workload check".

Each record:
  id, name, designation, email, subfield (primary bucket), areas (list),
  keywords (list), active_projects (int), profile (rich text used for embedding).
"""
from __future__ import annotations

FACULTY = [
    {
        "id": "mayank_singh",
        "name": "Dr. Mayank Singh",
        "designation": "Jibaben Patel Chair Associate Professor",
        "email": "",
        "subfield": "NLP",
        "areas": ["Natural Language Processing", "Text Mining", "Information Retrieval",
                   "Network Science", "Machine Learning"],
        "keywords": ["nlp", "text mining", "language models", "llm", "information retrieval",
                      "scholarly documents", "network science", "ir"],
        "active_projects": 4,
        "profile": (
            "Dr. Mayank Singh leads the LINGO group and works at the intersection of "
            "Natural Language Processing, text mining, and information retrieval. His "
            "research builds large language model pipelines for scholarly document "
            "understanding, scientific claim verification, citation intent classification, "
            "and low-resource Indian-language NLP. He also applies network science to "
            "model co-authorship and knowledge diffusion. Students working on transformers, "
            "retrieval-augmented generation, question answering, or academic search engines "
            "are a strong fit. He currently advises four ongoing projects this semester."
        ),
    },
    {
        "id": "shanmuganathan_raman",
        "name": "Dr. Shanmuganathan Raman",
        "designation": "Professor",
        "email": "",
        "subfield": "Computer Vision",
        "areas": ["Computer Vision", "Image and Video Processing", "Computer Graphics",
                   "Deep Learning"],
        "keywords": ["computer vision", "cv", "image processing", "video", "graphics",
                      "deep learning", "gan", "diffusion", "3d reconstruction"],
        "active_projects": 5,
        "profile": (
            "Dr. Shanmuganathan Raman heads the Computer Vision, Imaging and Graphics "
            "lab. His work spans computational photography, high-dynamic-range imaging, "
            "image and video enhancement, generative models (GANs and diffusion) for "
            "image synthesis, neural rendering, and 3D scene reconstruction. He supervises "
            "deep-learning projects on segmentation, super-resolution, and human motion "
            "capture. Ideal guide for students keen on vision, graphics, or generative "
            "imaging. He is running five projects and is near capacity this term."
        ),
    },
    {
        "id": "nipun_batra",
        "name": "Dr. Nipun Batra",
        "designation": "Associate Professor",
        "email": "",
        "subfield": "IoT",
        "areas": ["Sensor Networks", "Internet of Things", "Machine Learning",
                   "Computational Sustainability"],
        "keywords": ["iot", "sensor networks", "sensors", "smart buildings", "energy",
                      "sustainability", "time series", "bayesian", "edge"],
        "active_projects": 3,
        "profile": (
            "Dr. Nipun Batra works on the Internet of Things, sensor networks, and "
            "machine learning for computational sustainability. His group builds "
            "non-intrusive load monitoring systems, smart-building energy analytics, "
            "air-quality sensing, and probabilistic (Bayesian) machine-learning models "
            "for noisy time-series sensor data at the edge. Students interested in "
            "applied ML, IoT deployments, or climate-and-energy data science thrive "
            "here. He has three active student projects this semester."
        ),
    },
    {
        "id": "yogesh_meena",
        "name": "Dr. Yogesh Kumar Meena",
        "designation": "Assistant Professor",
        "email": "",
        "subfield": "HCI",
        "areas": ["Human-Computer Interaction", "Brain-Computer Interface", "Eye Tracking",
                   "IoT", "UX"],
        "keywords": ["hci", "human computer interaction", "brain computer interface", "bci",
                      "eye tracking", "gaze", "assistive technology", "ux", "iot"],
        "active_projects": 2,
        "profile": (
            "Dr. Yogesh Kumar Meena researches Human-Computer Interaction with a focus on "
            "brain-computer interfaces, eye-gaze tracking, and multimodal assistive "
            "technology. His lab designs accessible interfaces for people with motor "
            "impairments, combining EEG signal processing, gaze-based typing, and IoT "
            "wearables. Students who want to blend signal processing, machine learning, "
            "and user-centered design should reach out. Two projects are active now, so "
            "he has room to take on more."
        ),
    },
    {
        "id": "sameer_kulkarni",
        "name": "Dr. Sameer Gundurao Kulkarni",
        "designation": "Assistant Professor",
        "email": "",
        "subfield": "Cybersecurity",
        "areas": ["Network Function Virtualization", "Software Defined Networking",
                   "Cloud Computing", "Network Security"],
        "keywords": ["networking", "sdn", "nfv", "network security", "cloud", "5g",
                      "packet processing", "firewall", "ddos"],
        "active_projects": 3,
        "profile": (
            "Dr. Sameer Kulkarni works on computer networking and network security through "
            "Software Defined Networking (SDN) and Network Function Virtualization (NFV). "
            "His research optimizes high-performance packet processing, programmable data "
            "planes, service function chaining, and secure, elastic cloud/5G network "
            "infrastructure, including DDoS mitigation and intrusion detection. A good "
            "match for students who enjoy systems, networking, and security. He supervises "
            "three ongoing projects this semester."
        ),
    },
    {
        "id": "abhishek_bichhawat",
        "name": "Dr. Abhishek Bichhawat",
        "designation": "Associate Professor",
        "email": "",
        "subfield": "Cybersecurity",
        "areas": ["Language-based Security", "Formal Methods", "Information Flow Security",
                   "Program Verification"],
        "keywords": ["security", "formal methods", "verification", "information flow",
                      "language based security", "web security", "static analysis"],
        "active_projects": 2,
        "profile": (
            "Dr. Abhishek Bichhawat specializes in language-based security and formal "
            "methods. His work uses information-flow control, static and dynamic analysis, "
            "and machine-checked proofs to guarantee that software (especially web browsers "
            "and JavaScript applications) does not leak sensitive data. Students who like "
            "logic, programming languages, compilers, and provable security will fit well. "
            "He has two active projects and capacity for more."
        ),
    },
    {
        "id": "anirban_dasgupta",
        "name": "Dr. Anirban Dasgupta",
        "designation": "Professor",
        "email": "",
        "subfield": "Data Mining",
        "areas": ["Algorithms for Large-scale Data", "Social Networks",
                   "Computational Social Science", "Crowdsourcing"],
        "keywords": ["data mining", "large scale data", "big data", "social networks",
                      "graph mining", "randomized algorithms", "sketching", "crowdsourcing"],
        "active_projects": 4,
        "profile": (
            "Dr. Anirban Dasgupta designs algorithms for large-scale data mining. His "
            "research covers randomized algorithms, streaming and sketching techniques, "
            "graph and social-network analysis, computational social science, and "
            "crowdsourcing quality control. Previously at Yahoo! Research, he brings a "
            "web-scale data perspective. Students who love algorithms plus real data at "
            "scale are ideal. He currently guides four projects and is fairly loaded."
        ),
    },
    {
        "id": "manisha_padala",
        "name": "Dr. Manisha Padala",
        "designation": "Assistant Professor",
        "email": "",
        "subfield": "Machine Learning",
        "areas": ["Fairness in Machine Learning", "Game Theory", "Mechanism Design",
                   "Multi-agent Systems"],
        "keywords": ["fairness", "machine learning", "game theory", "mechanism design",
                      "multi agent", "reinforcement learning", "responsible ai", "ethics"],
        "active_projects": 2,
        "profile": (
            "Dr. Manisha Padala works on trustworthy and fair machine learning through the "
            "lens of game theory and mechanism design. Her research develops algorithms "
            "that are fair across demographic groups, studies strategic behavior in "
            "multi-agent learning, and designs incentive-compatible mechanisms for "
            "resource allocation. Students interested in responsible AI, ML theory, or "
            "reinforcement learning are welcome. She has two active projects this term."
        ),
    },
    {
        "id": "udit_bhatia",
        "name": "Dr. Udit Bhatia",
        "designation": "Pandya-Shivpuri Chair Associate Professor",
        "email": "",
        "subfield": "Machine Learning",
        "areas": ["Physics-Guided Machine Learning", "Climate Resilience",
                   "Network Science", "Urban Flooding"],
        "keywords": ["physics guided machine learning", "climate", "urban flooding",
                      "resilience", "infrastructure networks", "sustainability", "graph"],
        "active_projects": 3,
        "profile": (
            "Dr. Udit Bhatia applies physics-guided machine learning to climate and "
            "infrastructure resilience. His group models urban flooding, cascading "
            "failures in interdependent infrastructure networks, the food-water-energy "
            "nexus, and climate variability using network science and scientific ML that "
            "respects physical constraints. Students who want AI for climate, complex "
            "networks, or sustainability should connect. Three projects are active now."
        ),
    },
    {
        "id": "rajat_moona",
        "name": "Dr. Rajat Moona",
        "designation": "Professor",
        "email": "",
        "subfield": "Systems",
        "areas": ["Computer Architecture", "VLSI Design", "Operating Systems",
                   "Embedded Systems", "Security", "Smart Cards"],
        "keywords": ["computer architecture", "vlsi", "operating systems", "embedded",
                      "smart cards", "hardware security", "processors", "systems"],
        "active_projects": 3,
        "profile": (
            "Dr. Rajat Moona is a systems and hardware expert spanning computer "
            "architecture, VLSI design, operating systems, and embedded systems. He "
            "architected national-scale secure smart-card and e-passport systems and works "
            "on hardware security and trustworthy processors. Students who enjoy low-level "
            "systems, chip design, or hardware-rooted security will benefit from his "
            "industry-and-government-scale experience. He supervises three projects now."
        ),
    },
    {
        "id": "neeldhara_misra",
        "name": "Dr. Neeldhara Misra",
        "designation": "Sastry Chair Associate Professor",
        "email": "",
        "subfield": "Theory",
        "areas": ["Algorithm Design and Analysis", "Parameterized Complexity",
                   "Computational Social Choice", "Combinatorial Games"],
        "keywords": ["algorithms", "theory", "parameterized complexity", "graph algorithms",
                      "computational social choice", "combinatorics", "satisfiability", "games"],
        "active_projects": 2,
        "profile": (
            "Dr. Neeldhara Misra is a theoretical computer scientist working on algorithm "
            "design and analysis, parameterized and fine-grained complexity, computational "
            "social choice (voting and fair division), and combinatorial game theory. Her "
            "work asks what makes problems tractable and designs provably efficient "
            "algorithms. Students who love mathematics, proofs, and elegant algorithms are "
            "an excellent match. She currently advises two projects."
        ),
    },
    {
        "id": "shouvick_mondal",
        "name": "Dr. Shouvick Mondal",
        "designation": "Assistant Professor",
        "email": "",
        "subfield": "Software Engineering",
        "areas": ["Software Engineering with Generative AI", "Software Testing",
                   "Empirical Software Engineering", "Compiler Design"],
        "keywords": ["software engineering", "software testing", "generative ai", "llm for code",
                      "automated testing", "debugging", "compilers", "program repair"],
        "active_projects": 2,
        "profile": (
            "Dr. Shouvick Mondal researches software engineering powered by generative AI. "
            "His work automates software testing, fault localization, automated program "
            "repair, and continuous-integration efficiency, and studies how large language "
            "models can generate and fix code reliably. He also works on compiler design. "
            "Students who want to combine LLMs with rigorous software engineering and "
            "testing are a great fit. Two projects are active this semester."
        ),
    },
    {
        "id": "joycee_mekie",
        "name": "Dr. Joycee M. Mekie",
        "designation": "Professor",
        "email": "",
        "subfield": "Hardware",
        "areas": ["Approximate Computing", "Low-power SRAM", "Radiation-hardened Systems",
                   "VLSI"],
        "keywords": ["vlsi", "approximate computing", "low power", "sram", "memory design",
                      "hardware accelerators", "energy efficient", "circuits"],
        "active_projects": 4,
        "profile": (
            "Dr. Joycee M. Mekie designs energy-efficient hardware: approximate computing "
            "circuits, ultra-low-power SRAM and memory, radiation-hardened and "
            "fault-tolerant systems, and hardware accelerators for machine learning. Her "
            "group co-optimizes across devices, circuits, and architecture. Students who "
            "want VLSI, circuit design, or efficient ML-hardware co-design should apply. "
            "She runs four projects and is heavily loaded this term."
        ),
    },
    {
        "id": "krishna_miyapuram",
        "name": "Dr. Krishna Prasad Miyapuram",
        "designation": "Professor",
        "email": "",
        "subfield": "Data Mining",
        "areas": ["Computational Cognitive Science", "Neuroimaging", "Neuroeconomics",
                   "Machine Learning for Neuroscience"],
        "keywords": ["cognitive science", "neuroimaging", "eeg", "fmri", "brain data",
                      "neuroeconomics", "machine learning", "signal processing", "data mining"],
        "active_projects": 2,
        "profile": (
            "Dr. Krishna Prasad Miyapuram bridges computational cognitive science and "
            "machine learning. His group mines large neuroimaging datasets (EEG and fMRI), "
            "decodes brain responses to music and decision-making, and studies "
            "neuroeconomics and neuromarketing with data-driven models. Students who want "
            "to apply machine learning and data mining to brain and behavioral data will "
            "fit well. He advises two projects currently."
        ),
    },
    {
        "id": "manu_awasthi",
        "name": "Dr. Manu Awasthi",
        "designation": "Associate Professor of Practice",
        "email": "",
        "subfield": "Systems",
        "areas": ["Computer Architecture", "Embedded Systems", "Cloud Computing",
                   "Performance Modeling"],
        "keywords": ["computer architecture", "cloud computing", "memory systems", "storage",
                      "performance modeling", "embedded", "data centers", "systems"],
        "active_projects": 3,
        "profile": (
            "Dr. Manu Awasthi works on computer architecture and systems for the data "
            "center: memory and storage systems, non-volatile memory, cloud computing "
            "economics, and performance modeling of large-scale workloads. With deep "
            "industry experience, he mentors students on systems performance, storage "
            "engineering, and cloud infrastructure. A strong fit for students who like "
            "building and profiling real systems. He supervises three projects now."
        ),
    },
]

# Privacy: real professor email addresses are intentionally NOT stored here.
# We synthesize a clearly-fake placeholder on the reserved example.edu domain so
# the email-draft demo still has a unique per-faculty "to" address without
# exposing anyone's actual contact details.
for _f in FACULTY:
    _f["email"] = f"{_f['id'].replace('_', '.')}@example.edu"


def all_profiles() -> list[dict]:
    return FACULTY


def get_by_name(query_name: str) -> dict | None:
    """Loose name match used by ScopedDetailLookup and follow-ups."""
    q = query_name.lower().strip()
    q = q.replace("dr.", "").replace("dr ", "").replace("prof.", "").replace("professor", "").strip()
    best = None
    for f in FACULTY:
        name = f["name"].lower().replace("dr.", "").strip()
        parts = [p for p in name.split() if len(p) > 2]
        if q and (q in name or name in q or any(p in q for p in parts if len(p) > 3)):
            # Prefer the match that shares the most surname tokens.
            score = sum(1 for p in parts if p in q)
            if best is None or score > best[0]:
                best = (score, f)
    return best[1] if best else None
