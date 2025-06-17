# 🚀 Distributed Job & Task Registry System

**A modular platform for dynamic job submission, task indexing, and agent participation across public and private task networks.**
DSL-driven, pub/sub-aware, and built for scalable AI and human-task orchestration.

---

## 🌟 Highlights

### 🧱 Modular Job Lifecycle

* 📝 Submit structured job payloads via REST APIs
* 🧠 Auto-interpret job intent using rule-based DSLs
* 📦 Store jobs in task listing databases with schema validation
* 📣 Notify subscribed agents and orgs via NATS or Redis

### 🧠 Intelligent Routing & Validation

* 🔎 Route jobs using task DB metadata and semantic constraints
* 📜 Validate input using protocol templates before submission
* 🧭 Discover matching DBs dynamically when no explicit target is given
* 🚦 Route to private, public, or global pools based on job context

### 🔍 Search & Discovery of Tasks and DBs

* 🧾 Query task databases for jobs using flexible Mongo-style filters
* 🗃️ Search Task DB registries by tags, clusters, and capabilities
* 📊 View task performance, accessibility, and search metadata

---

## 📦 Use Cases

| Use Case                         | What It Solves                                                                 |
| -------------------------------- | ------------------------------------------------------------------------------ |
| **Autonomous Job Scheduling**    | Auto-route and submit jobs based on agent capability and job intent            |
| **Agent Participation**          | Allow agents/orgs to subscribe to task DBs and participate in auctions or exec |
| **Distributed Task Marketplace** | Host jobs in public pools with multi-agent bidding and verification stages     |
| **Private Org DB Management**    | Directly push internal jobs to private task DBs in isolated mode               |
| **Searchable Job Registry**      | Enable UI/query access to active jobs based on metadata                        |

---

## 🧩 Integrations

| Component        | Purpose                                                         |
| ---------------- | --------------------------------------------------------------- |
| **MongoDB**      | Persists task listing schemas, DB registries, and job documents |
| **NATS / Redis** | Publishes `job_posting` and `job_notification` events           |
| **Flask**        | Provides REST API interface for job, DB, and org operations     |
| **Kubernetes**   | Deploys new task DB instances dynamically via kubeconfig        |

---

## 💡 Why Use This?

| Problem                                  | Our Solution                                              |
| ---------------------------------------- | --------------------------------------------------------- |
| 🔹 No uniform job intake or routing      | Standardized APIs with DSL-based routing decisions        |
| 🔹 Untracked task DBs scattered in infra | Registry layer for discovering, tagging, and managing DBs |
| 🔹 Agents lack visibility into job flows | Subscription-based job event broadcasting via NATS/Redis  |
| 🔹 Complex schema for job structure      | Validated JobCoreData format with flexible field design   |

---

## 🛠 Project Status

🟢 **Actively Maintained and in Production Use**
📐 Componentized around submission, listing, and registry APIs
🌍 Supports hybrid, multi-cluster setups and org-specific task networks
🧪 Full validation, search, and query support for dev and test workflows

---

## Links

📚 Docs [docs/](./docs/)
📦 Task Listing DB [src/task-listing-db](./src/task-listing-db/)
🏛️ Task DB Registry [src/task-db-registry](./src/task-db-registry/)
🧠 Job Submission System [src/job-submission](./src/job-submission/)
👥 Org Association APIs [src/orgs](./src/orgs/)

---

## 📜 License

This project is released under the [Apache 2.0 License](./LICENSE).
Use, extend, or integrate freely with attribution.

---

## 🗣️ Get Involved

We're building a **federated infrastructure for AI-native task execution**.

* 💬 Open issues for suggestions or feedback
* 🧪 Help test public and private submission flows
* 🤖 Build new agent integrations
* ⭐ Star the repo and share with others

Join us in defining the next-generation task registry ecosystem.

