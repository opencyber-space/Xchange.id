# Task Listing DB

### Overview

The **Task Listing DB** is a specialized database that stores all submitted tasks in a structured and queryable format. It acts as a central registry for task discovery, auctioning, and execution coordination across the network.

---

### Key Functions

* **Task Storage**
  Maintains a complete record of tasks submitted by various sources (e.g., users, services, automated systems).

* **Subscription-Based Participation**
  Allows **subjects** (such as organizations and agents) to subscribe to the Task Listing DB. These subjects can:

  * Participate in **task auctions**
  * Receive **assigned tasks**
  * Execute and report **task results**

---

### Features

| Feature                        | Description                                                                                                            |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| **Structured Task Format**     | Tasks are stored with well-defined schema to support indexing, filtering, and metadata tagging.                        |
| **Multi-Subject Subscription** | One Task Listing DB can be accessed by multiple agents or orgs, enabling collaborative or competitive task processing. |
| **Auction Compatibility**      | Integrated with task auction systems, enabling dynamic bidding and selection mechanisms.                               |

---

## Schema of a Job/Task

The **JobCoreData** schema defines the structure for a task/job submitted into the Task Listing DB. It captures the job's intent, structure, lifecycle expectations, verification parameters, and ownership metadata.

```js
const JobCoreDataSchema = new mongoose.Schema({
    job_id: { type: String, required: true, unique: true },
    job_goal: { type: mongoose.Schema.Types.Mixed, required: true }, // Made Mixed
    job_objectives: { type: mongoose.Schema.Types.Mixed, required: true }, // Made Mixed
    job_priority_value: { type: Number, required: true },
    job_completion_mode: {
        type: String,
        enum: ["single_window", "multi_window"],
        required: true
    },
    job_steerability_data: { type: mongoose.Schema.Types.Mixed },
    job_knowledge_base_reference_ptr: { type: mongoose.Schema.Types.Mixed },
    job_init_data: { type: mongoose.Schema.Types.Mixed },
    submitted_by: { type: String, required: true },
    job_sla_terms_json: { type: mongoose.Schema.Types.Mixed }, // Flexible for JSON
    job_completion_multiwindow_timeline_map: { type: mongoose.Schema.Types.Mixed },
    job_output_template_id: { type: String, required: true },
    job_output_convertor_dsl_id: { type: String },
    job_verification_subject_ids: { type: [String] },
    job_verification_subject_parameters: { type: mongoose.Schema.Types.Mixed },
    job_output_verification_stages_map: { type: mongoose.Schema.Types.Mixed }
}, { timestamps: true });
```

### Schema Fields

| Field Name                                | Type                    | Required | Description                                                                                                                                 |
| ----------------------------------------- | ----------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `job_id`                                  | `String`                | Yes      | Unique identifier for the job. Must be globally unique.                                                                                     |
| `job_goal`                                | `Mixed` (Object)        | Yes      | Describes the overall goal or intent of the job. Flexible JSON structure.                                                                   |
| `job_objectives`                          | `Mixed` (Object)        | Yes      | Specific sub-goals or detailed objectives of the job.                                                                                       |
| `job_priority_value`                      | `Number`                | Yes      | Priority score for scheduling or bidding purposes. Higher means more urgent/important.                                                      |
| `job_completion_mode`                     | `String` (Enum)         | Yes      | Specifies how the job should be completed:<br>`"single_window"` – One-shot completion<br>`"multi_window"` – Completed in phases or windows. |
| `job_steerability_data`                   | `Mixed` (Object)        | No       | Optional instructions or dynamic parameters to steer the execution (e.g., user feedback or runtime adjustments).                            |
| `job_knowledge_base_reference_ptr`        | `Mixed` (Object)        | No       | Links to external or internal knowledge bases (e.g., URIs, IDs, embeddings).                                                                |
| `job_init_data`                           | `Mixed` (Object)        | No       | Initial input data or parameters required to start the job.                                                                                 |
| `submitted_by`                            | `String`                | Yes      | Identifier of the entity (agent/org/user) that submitted the job.                                                                           |
| `job_sla_terms_json`                      | `Mixed` (Object)        | No       | SLA and contractual terms in JSON format (e.g., deadlines, penalties, expectations).                                                        |
| `job_completion_multiwindow_timeline_map` | `Mixed` (Object)        | No       | If `multi_window` mode is used, maps phases to expected completion timelines.                                                               |
| `job_output_template_id`                  | `String`                | Yes      | Reference to the template to structure the final output.                                                                                    |
| `job_output_convertor_dsl_id`             | `String`                | No       | Optional reference to a DSL ID that defines how to convert raw outputs into final format.                                                   |
| `job_verification_subject_ids`            | `Array of String`       | No       | List of agents or orgs responsible for verifying the job output.                                                                            |
| `job_verification_subject_parameters`     | `Mixed` (Object)        | No       | Per-subject parameters that guide how each verifier should evaluate the job output.                                                         |
| `job_output_verification_stages_map`      | `Mixed` (Object)        | No       | Stage-wise mapping for verification in multi-stage verification workflows.                                                                  |
| `createdAt` / `updatedAt`                 | `Date` (Auto-generated) | No       | Timestamp fields automatically managed by Mongoose.                                                                                         |

---

### Example Document

```json
{
  "job_id": "job-xyz-001",
  "job_goal": { "type": "summarization", "target": "legal_documents" },
  "job_objectives": { "steps": ["ingest", "analyze", "summarize"] },
  "job_priority_value": 10,
  "job_completion_mode": "multi_window",
  "job_steerability_data": { "feedback_loop_enabled": true },
  "job_knowledge_base_reference_ptr": { "kb_uri": "http://kb.example.com/123" },
  "job_init_data": { "input_documents": ["doc1", "doc2"] },
  "submitted_by": "agent-123",
  "job_sla_terms_json": { "response_time_hours": 24 },
  "job_completion_multiwindow_timeline_map": {
    "phase_1": "2025-05-22T10:00:00Z",
    "phase_2": "2025-05-24T10:00:00Z"
  },
  "job_output_template_id": "template-456",
  "job_output_convertor_dsl_id": "dsl-convertor-001",
  "job_verification_subject_ids": ["agent-234", "agent-456"],
  "job_verification_subject_parameters": {
    "agent-234": { "checklist": ["clarity", "accuracy"] }
  },
  "job_output_verification_stages_map": {
    "stage_1": ["agent-234"],
    "stage_2": ["agent-456"]
  }
}
```

---

## Job submission APIs

These APIs allow clients to create, read, update, delete, and query jobs stored in the **JobCoreData** collection. Jobs represent structured task units submitted for execution.

---

### POST `/jobs`

**Description:**
Create a new job entry with complete metadata. Automatically notifies subscribed organizations via Redis after a short delay.

**Request Body:**

```json
{
  "job_id": "job-001",
  "job_goal": { "type": "summarization", "target": "legal_docs" },
  "job_objectives": { "steps": ["ingest", "parse", "summarize"] },
  "job_priority_value": 5,
  "job_completion_mode": "single_window",
  "job_output_template_id": "template-123",
  "submitted_by": "org-456"
  // other optional fields from schema...
}
```

**Response:**

* `201 Created`: Job successfully created.
* `500 Internal Server Error`: Creation failed.

**Notes:**

* Internally publishes a Redis event (`job_notification`) after 5 seconds with job data and list of organizations.

---

### GET `/jobs/:jobId`

**Description:**
Retrieve a job by its unique `job_id`.

**Path Parameter:**

* `jobId`: ID of the job to fetch.

**Response:**

* `200 OK`: Job found.
* `404 Not Found`: Job does not exist.
* `500 Internal Server Error`: Retrieval error.

---

### PUT `/jobs/:jobId`

**Description:**
Update an existing job entry.

**Path Parameter:**

* `jobId`: ID of the job to update.

**Request Body:**

```json
{
  "job_priority_value": 10,
  "job_completion_mode": "multi_window"
}
```

**Response:**

* `200 OK`: Job updated.
* `404 Not Found`: Job not found.
* `500 Internal Server Error`: Update failed.

---

### DELETE `/jobs/:jobId`

**Description:**
Delete a job by its `job_id`.

**Path Parameter:**

* `jobId`: ID of the job to delete.

**Response:**

* `200 OK`: Job deleted successfully.
* `404 Not Found`: Job does not exist.
* `500 Internal Server Error`: Deletion error.

---

### POST `/jobs/query`

**Description:**
Run a MongoDB-style query on jobs using flexible JSON criteria.

**Request Body:**

```json
{
  "submitted_by": "org-456",
  "job_completion_mode": "multi_window"
}
```

**Response:**

* `200 OK`: Array of matching jobs.
* `500 Internal Server Error`: Query error.

---

Here's the documentation and sample Python code as requested.

---

### Internal Event: `job_posting`

#### Overview

When a new job is posted in the system, an internal event of type `job_posting` is published over **NATS** to notify subscribed components (e.g., agents, orgs) of the new job entry.

---

#### Event Structure

```json
{
  "event_type": "job_posting",
  "sender_subject_id": "task_db",
  "event_data": {
    // Full contents of the submitted job (matches JobCoreData schema)
  }
}
```

---

#### Topic

* **Format:** `<subject_id>_events`
* **Example:**
  If the subject/agent ID is `agent-007`, the topic would be:
  `agent-007_events`

---

#### Sample Python Listener for `job_posting` Events

Below is a sample Python listener using `asyncio` and the `nats-py` library:

```python
import asyncio
import json
from nats.aio.client import Client as NATS

async def run():
    # Create NATS client
    nc = NATS()

    # Connect to NATS server
    await nc.connect("nats://localhost:4222")  # Update if hosted elsewhere

    # Define your subject ID
    subject_id = "agent-007"
    topic = f"{subject_id}_events"

    async def message_handler(msg):
        data = json.loads(msg.data.decode())
        if data.get("event_type") == "job_posting":
            print("Received job_posting event:")
            print(json.dumps(data["event_data"], indent=2))

    # Subscribe to the events topic
    await nc.subscribe(topic, cb=message_handler)

    print(f"Listening for job_posting events on topic: {topic}")

    # Keep running
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run())
```

---

## Subject associations

Here's a **structured documentation** for your `OrgSchema`, designed for inclusion in internal system specs, developer docs, or data schema references:

---

## Organization Schema (`OrgSchema`)

The **OrgSchema** defines the metadata and association structure for organizations and agents that subscribe to a **Task Listing DB**.

```js
const OrgSchema = new mongoose.Schema({
    org_id: { type: String, required: true, unique: true },
    org_pub_sub_topic_name: { type: String, required: true },
    org_metadata: { type: mongoose.Schema.Types.Mixed, default: {} },
    org_type: { type: String, required: true }
}, {
    timestamps: true
});

```

---

### Schema Fields

| Field Name               | Type             | Required | Description                                                                                                                              |
| ------------------------ | ---------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `org_id`                 | `String`         | Yes      | A unique identifier for the organization or agent. Used across task systems for identification.                                          |
| `org_pub_sub_topic_name` | `String`         | Yes      | Name of the **pub/sub topic** (usually used with NATS) where the org listens for events like job postings, completions, or updates.      |
| `org_metadata`           | `Mixed` (Object) | No       | Optional metadata describing the org or agent. Can include tags, location, team, preferences, etc. Defaults to an empty object.          |
| `org_type`               | `String` (Enum)  | Yes      | Type of entity: <br> • `org` – Represents a full-fledged organization <br> • `agent` – Represents an autonomous or user-controlled agent |

---


## Organization Association APIs

These APIs manage the registration and management of **organizations** and **agents** that subscribe to a Task Listing DB or participate in job execution.

---

### POST `/orgs`

**Description:**
Register a new organization or agent in the system.

**Request Body:**

```json
{
  "org_id": "agent-007",
  "org_pub_sub_topic_name": "agent-007_events",
  "org_metadata": {
    "region": "us-east",
    "team": "QA",
    "capabilities": ["classification", "qa"]
  },
  "org_type": "agent"
}
```

**Responses:**

* `201 Created`: Organization successfully created.
* `500 Internal Server Error`: Failed to create organization.

---

### GET `/orgs/:orgId`

**Description:**
Fetch details of a specific organization or agent by `org_id`.

**Path Parameter:**

* `orgId` – ID of the organization or agent.

**Responses:**

* `200 OK`: Organization found.
* `404 Not Found`: Organization does not exist.
* `500 Internal Server Error`: Retrieval failed.

---

### PUT `/orgs/:orgId`

**Description:**
Update metadata or configuration of an organization or agent.

**Path Parameter:**

* `orgId` – ID of the organization to update.

**Request Body (partial or full update):**

```json
{
  "org_metadata": {
    "team": "operations",
    "capabilities": ["qa", "monitoring"]
  }
}
```

**Responses:**

* `200 OK`: Organization updated successfully.
* `404 Not Found`: Organization not found.
* `500 Internal Server Error`: Update failed.

---

### DELETE `/orgs/:orgId`

**Description:**
Delete a specific organization or agent.

**Path Parameter:**

* `orgId` – ID of the organization to delete.

**Responses:**

* `200 OK`: Organization deleted.
* `404 Not Found`: Organization not found.
* `500 Internal Server Error`: Deletion failed.

---

### POST `/orgs/query`

**Description:**
Query multiple organizations based on filter criteria (e.g., org type, region, capabilities).

**Request Body:**

```json
{
  "org_type": "agent",
  "org_metadata.region": "us-east"
}
```

**Responses:**

* `200 OK`: List of matching organizations.
* `500 Internal Server Error`: Query execution failed.

---



